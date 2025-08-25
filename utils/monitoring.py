"""
Comprehensive Monitoring and Logging System
Provides unified logging, metrics collection, performance monitoring, and health checks.
Built for 24/7 operation with structured output and alerting capabilities.

Compatible with Python 3.10+ including 3.13.
"""

import json
import logging
import time
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics


@dataclass 
class MetricEntry:
    """Single metric entry with timestamp and metadata."""
    timestamp: datetime
    metric_name: str
    value: Union[float, int, str]
    tags: Dict[str, str]
    module: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'metric_name': self.metric_name,
            'value': self.value,
            'tags': self.tags,
            'module': self.module
        }


@dataclass
class HealthStatus:
    """System health status information."""
    component: str
    status: str  # healthy, warning, critical, unknown
    message: str
    last_check: datetime
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'component': self.component,
            'status': self.status,
            'message': self.message,
            'last_check': self.last_check.isoformat(),
            'response_time_ms': self.response_time_ms,
            'details': self.details or {}
        }


class PerformanceTracker:
    """Tracks performance metrics and system statistics."""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timings: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self._lock = threading.Lock()
    
    def record_metric(self, name: str, value: Union[float, int], tags: Dict[str, str] = None):
        """Record a metric value."""
        with self._lock:
            entry = MetricEntry(
                timestamp=datetime.now(),
                metric_name=name,
                value=value,
                tags=tags or {},
                module='performance'
            )
            self.metrics[name].append(entry)
    
    def increment_counter(self, name: str, amount: int = 1):
        """Increment a counter metric."""
        with self._lock:
            self.counters[name] += amount
    
    def record_timing(self, name: str, duration_ms: float):
        """Record timing information."""
        with self._lock:
            self.timings[name].append(duration_ms)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        with self._lock:
            stats = {
                'counters': dict(self.counters),
                'metrics_count': {name: len(entries) for name, entries in self.metrics.items()},
                'timing_stats': {}
            }
            
            # Calculate timing statistics
            for name, timings in self.timings.items():
                if timings:
                    timing_list = list(timings)
                    stats['timing_stats'][name] = {
                        'count': len(timing_list),
                        'avg_ms': statistics.mean(timing_list),
                        'min_ms': min(timing_list),
                        'max_ms': max(timing_list),
                        'p95_ms': statistics.quantiles(timing_list, n=20)[18] if len(timing_list) > 1 else timing_list[0]
                    }
            
            return stats


class MonitoringSystem:
    """
    Comprehensive monitoring system with structured logging, metrics, and health checks.
    """
    
    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        """
        Initialize monitoring system.
        
        Args:
            base_path: Base directory for log files and monitoring data
        """
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        # Setup directories
        self.monitoring_dir = self.base_path / "monitoring"
        self.logs_dir = self.monitoring_dir / "logs"
        self.metrics_dir = self.monitoring_dir / "metrics"
        
        for directory in [self.monitoring_dir, self.logs_dir, self.metrics_dir]:
            directory.mkdir(exist_ok=True, parents=True)
        
        # Initialize components
        self.performance = PerformanceTracker()
        self.health_checks: Dict[str, HealthStatus] = {}
        self.registered_checks: Dict[str, Callable] = {}
        
        # Setup logging
        self._setup_structured_logging()
        
        # Metrics collection
        self.metrics_queue = queue.Queue()
        self.metrics_thread = None
        self._running = False
        
        # Start background processing
        self.start_background_processing()
    
    def _setup_structured_logging(self):
        """Setup structured logging with multiple outputs."""
        # Create custom formatter for structured logs
        class StructuredFormatter(logging.Formatter):
            def format(self, record):
                # Create structured log entry
                log_entry = {
                    'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                    'module': getattr(record, 'module_name', 'unknown'),
                    'function': record.funcName,
                    'line': record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry['exception'] = self.formatException(record.exc_info)
                
                # Add custom fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                                   'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                                   'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                                   'thread', 'threadName', 'processName', 'process', 'getMessage']:
                        log_entry[key] = value
                
                return json.dumps(log_entry)
        
        # Setup file handler for structured logs
        structured_log_file = self.logs_dir / f"structured_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(structured_log_file)
        file_handler.setFormatter(StructuredFormatter())
        file_handler.setLevel(logging.DEBUG)
        
        # Setup console handler for human-readable logs
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(name)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # Create logger
        self.logger = logging.getLogger('monitoring')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def start_background_processing(self):
        """Start background threads for metrics processing."""
        if not self._running:
            self._running = True
            self.metrics_thread = threading.Thread(target=self._process_metrics, daemon=True)
            self.metrics_thread.start()
    
    def stop_background_processing(self):
        """Stop background processing."""
        self._running = False
        if self.metrics_thread and self.metrics_thread.is_alive():
            self.metrics_thread.join(timeout=5)
    
    def _process_metrics(self):
        """Background thread for processing metrics."""
        while self._running:
            try:
                # Process any queued metrics
                while not self.metrics_queue.empty():
                    try:
                        metric = self.metrics_queue.get_nowait()
                        self._write_metric_to_file(metric)
                    except queue.Empty:
                        break
                
                # Periodic tasks
                self._save_performance_snapshot()
                self._cleanup_old_files()
                
                # Sleep between processing cycles
                time.sleep(60)  # Process every minute
                
            except Exception as e:
                self.logger.error(f"Error in metrics processing: {e}", exc_info=True)
    
    def _write_metric_to_file(self, metric: MetricEntry):
        """Write metric to daily metrics file."""
        metrics_file = self.metrics_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(metrics_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(metric.to_dict()) + '\\n')
        except Exception as e:
            self.logger.error(f"Failed to write metric to file: {e}")
    
    def _save_performance_snapshot(self):
        """Save current performance snapshot."""
        snapshot_file = self.monitoring_dir / "performance_snapshot.json"
        
        try:
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'performance_stats': self.performance.get_stats(),
                'health_status': {name: status.to_dict() for name, status in self.health_checks.items()}
            }
            
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save performance snapshot: {e}")
    
    def _cleanup_old_files(self):
        """Clean up old log and metric files."""
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for directory in [self.logs_dir, self.metrics_dir]:
            try:
                for file_path in directory.glob("*"):
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_date.timestamp():
                        file_path.unlink()
                        self.logger.info(f"Cleaned up old file: {file_path}")
            except Exception as e:
                self.logger.error(f"Error during file cleanup: {e}")
    
    def log_event(self, level: str, message: str, module: str = "system", **kwargs):
        """Log an event with structured data."""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        
        # Add module info to log record
        extra = {'module_name': module}
        extra.update(kwargs)
        
        log_func(message, extra=extra)
    
    def record_metric(self, name: str, value: Union[float, int], module: str = "system", tags: Dict[str, str] = None):
        """Record a metric value."""
        metric = MetricEntry(
            timestamp=datetime.now(),
            metric_name=name,
            value=value,
            tags=tags or {},
            module=module
        )
        
        # Add to performance tracker
        self.performance.record_metric(name, value, tags)
        
        # Queue for file writing
        self.metrics_queue.put(metric)
    
    def increment_counter(self, name: str, module: str = "system", amount: int = 1):
        """Increment a counter metric."""
        self.performance.increment_counter(f"{module}.{name}", amount)
        self.record_metric(f"{module}.{name}.count", amount, module, {"type": "counter"})
    
    def time_function(self, func_name: str, module: str = "system"):
        """Decorator to time function execution."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    success = True
                    error = None
                except Exception as e:
                    result = None
                    success = False
                    error = str(e)
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Record timing
                    self.performance.record_timing(f"{module}.{func_name}", duration_ms)
                    
                    # Record metrics
                    self.record_metric(f"{module}.{func_name}.duration_ms", duration_ms, module, 
                                     {"function": func_name, "success": str(success)})
                    
                    if success:
                        self.increment_counter(f"{func_name}.success", module)
                    else:
                        self.increment_counter(f"{func_name}.error", module)
                        self.log_event("error", f"Function {func_name} failed: {error}", module)
                
                return result
            return wrapper
        return decorator
    
    def register_health_check(self, name: str, check_func: Callable[[], bool], description: str = ""):
        """Register a health check function."""
        self.registered_checks[name] = {
            'func': check_func,
            'description': description
        }
    
    def run_health_checks(self) -> Dict[str, HealthStatus]:
        """Run all registered health checks."""
        results = {}
        
        for name, check_info in self.registered_checks.items():
            start_time = time.time()
            try:
                is_healthy = check_info['func']()
                response_time = (time.time() - start_time) * 1000
                
                status = HealthStatus(
                    component=name,
                    status="healthy" if is_healthy else "critical",
                    message=check_info['description'] if is_healthy else "Health check failed",
                    last_check=datetime.now(),
                    response_time_ms=response_time
                )
                
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                status = HealthStatus(
                    component=name,
                    status="critical",
                    message=f"Health check error: {str(e)}",
                    last_check=datetime.now(),
                    response_time_ms=response_time
                )
                
                self.log_event("error", f"Health check {name} failed", "monitoring", error=str(e))
            
            results[name] = status
            self.health_checks[name] = status
        
        return results
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        # Run health checks
        health_status = self.run_health_checks()
        
        # Determine overall status
        overall_status = "healthy"
        if any(status.status == "critical" for status in health_status.values()):
            overall_status = "critical"
        elif any(status.status == "warning" for status in health_status.values()):
            overall_status = "warning"
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status,
            'health_checks': {name: status.to_dict() for name, status in health_status.items()},
            'performance_stats': self.performance.get_stats(),
            'uptime_seconds': time.time() - self._start_time if hasattr(self, '_start_time') else 0
        }
    
    def generate_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate monitoring report for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Load metrics from files
        metrics_data = []
        for metrics_file in self.metrics_dir.glob("metrics_*.jsonl"):
            try:
                with open(metrics_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            metric_data = json.loads(line)
                            metric_timestamp = datetime.fromisoformat(metric_data['timestamp'])
                            if metric_timestamp >= cutoff_time:
                                metrics_data.append(metric_data)
            except Exception as e:
                self.logger.error(f"Error reading metrics file {metrics_file}: {e}")
        
        # Analyze metrics
        report = {
            'period_hours': hours,
            'period_start': cutoff_time.isoformat(),
            'period_end': datetime.now().isoformat(),
            'total_metrics': len(metrics_data),
            'current_status': self.get_system_status()
        }
        
        return report


# Global monitoring instance
_monitoring_instance: Optional[MonitoringSystem] = None

def get_monitoring() -> MonitoringSystem:
    """Get global monitoring system instance."""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = MonitoringSystem()
        _monitoring_instance._start_time = time.time()
    return _monitoring_instance


def log_event(level: str, message: str, module: str = "system", **kwargs):
    """Convenience function to log an event."""
    return get_monitoring().log_event(level, message, module, **kwargs)


def record_metric(name: str, value: Union[float, int], module: str = "system", tags: Dict[str, str] = None):
    """Convenience function to record a metric."""
    return get_monitoring().record_metric(name, value, module, tags)


def time_function(func_name: str, module: str = "system"):
    """Convenience decorator to time function execution."""
    return get_monitoring().time_function(func_name, module)