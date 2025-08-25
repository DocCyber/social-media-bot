#!/usr/bin/env python3
"""
Monitoring Dashboard
Real-time system health and performance monitoring dashboard.
Provides comprehensive visibility into the social media bot's operation.

Compatible with Python 3.10+ including 3.13.
"""

import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def clear_screen():
    """Clear the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def format_duration(seconds: float) -> str:
    """Format duration in human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

def format_bytes(bytes_value: int) -> str:
    """Format bytes in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f}TB"

def format_percentage(value: float) -> str:
    """Format percentage with color coding."""
    if value < 50:
        status = "GOOD"
    elif value < 80:
        status = "WARN"
    else:
        status = "HIGH"
    
    return f"{value:.1f}% [{status}]"

class MonitoringDashboard:
    """Real-time monitoring dashboard."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.monitoring_dir = self.base_path / "monitoring"
        self.start_time = time.time()
        
        # Ensure monitoring directory exists
        self.monitoring_dir.mkdir(exist_ok=True, parents=True)
    
    def load_performance_snapshot(self) -> Dict[str, Any]:
        """Load the latest performance snapshot."""
        snapshot_file = self.monitoring_dir / "performance_snapshot.json"
        
        if snapshot_file.exists():
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            'timestamp': datetime.now().isoformat(),
            'performance_stats': {'counters': {}, 'timing_stats': {}},
            'health_status': {}
        }
    
    def get_recent_logs(self, lines: int = 10) -> List[str]:
        """Get recent log entries."""
        logs_dir = self.monitoring_dir / "logs"
        
        if not logs_dir.exists():
            return ["No logs directory found"]
        
        # Get today's log file
        today = datetime.now().strftime('%Y%m%d')
        log_file = logs_dir / f"structured_{today}.log"
        
        if not log_file.exists():
            return ["No log file for today"]
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                
                formatted_logs = []
                for line in recent_lines:
                    try:
                        log_data = json.loads(line.strip())
                        timestamp = log_data.get('timestamp', '').split('T')[1].split('.')[0]
                        level = log_data.get('level', 'INFO')
                        message = log_data.get('message', '')
                        module = log_data.get('module', 'system')
                        
                        formatted_logs.append(f"{timestamp} [{level}] {module}: {message}")
                    except json.JSONDecodeError:
                        formatted_logs.append(line.strip())
                
                return formatted_logs
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information."""
        try:
            import psutil
            
            # CPU information
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory information
            memory = psutil.virtual_memory()
            
            # Disk information
            disk = psutil.disk_usage(str(self.base_path))
            
            # Current process information
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            process_cpu = current_process.cpu_percent()
            
            return {
                'system': {
                    'cpu_percent': cpu_percent,
                    'cpu_count': cpu_count,
                    'memory_total': memory.total,
                    'memory_available': memory.available,
                    'memory_percent': memory.percent,
                    'disk_total': disk.total,
                    'disk_free': disk.free,
                    'disk_percent': (disk.used / disk.total) * 100
                },
                'process': {
                    'memory_rss': process_memory.rss,
                    'memory_vms': process_memory.vms,
                    'cpu_percent': process_cpu,
                    'pid': current_process.pid,
                    'create_time': current_process.create_time()
                }
            }
        except ImportError:
            return {'error': 'psutil not available'}
        except Exception as e:
            return {'error': f'Failed to get system info: {e}'}
    
    def render_dashboard(self):
        """Render the complete monitoring dashboard."""
        clear_screen()
        
        # Header
        print("=" * 80)
        print("SOCIAL MEDIA BOT - MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Dashboard Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Dashboard Uptime: {format_duration(time.time() - self.start_time)}")
        print()
        
        # System Health Section
        print("SYSTEM HEALTH")
        print("-" * 40)
        
        try:
            from utils.health_checks import SystemHealthMonitor
            health_monitor = SystemHealthMonitor()
            health_summary = health_monitor.get_summary()
            
            status_symbols = {'healthy': '[OK]', 'warning': '[WARN]', 'critical': '[FAIL]'}
            overall_symbol = status_symbols.get(health_summary['overall_status'], '[?]')
            
            print(f"Overall Status: {overall_symbol} {health_summary['overall_status'].upper()}")
            print(f"Health Score: {health_summary['health_score']}%")
            print(f"Checks Passing: {health_summary['healthy_checks']}/{health_summary['total_checks']}")
            
            # Show critical issues
            critical_issues = [name for name, details in health_summary['details'].items() 
                             if details['status'] == 'critical']
            if critical_issues:
                print(f"Critical Issues: {', '.join(critical_issues)}")
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
        
        print()
        
        # System Resources Section
        print("SYSTEM RESOURCES")
        print("-" * 40)
        
        system_info = self.get_system_info()
        if 'error' in system_info:
            print(f"❌ {system_info['error']}")
        else:
            sys_info = system_info['system']
            proc_info = system_info['process']
            
            print(f"CPU Usage: {format_percentage(sys_info['cpu_percent'])} ({sys_info['cpu_count']} cores)")
            print(f"Memory Usage: {format_percentage(sys_info['memory_percent'])} ({format_bytes(sys_info['memory_total'] - sys_info['memory_available'])}/{format_bytes(sys_info['memory_total'])})")
            print(f"Disk Usage: {format_percentage(sys_info['disk_percent'])} ({format_bytes(sys_info['disk_total'] - sys_info['disk_free'])}/{format_bytes(sys_info['disk_total'])})")
            print(f"Process Memory: {format_bytes(proc_info['memory_rss'])} RSS, {format_bytes(proc_info['memory_vms'])} VMS")
            print(f"Process CPU: {proc_info['cpu_percent']:.1f}%")
            
            process_uptime = time.time() - proc_info['create_time']
            print(f"Process Uptime: {format_duration(process_uptime)}")
        
        print()
        
        # Performance Metrics Section
        print("PERFORMANCE METRICS")
        print("-" * 40)
        
        snapshot = self.load_performance_snapshot()
        perf_stats = snapshot.get('performance_stats', {})
        counters = perf_stats.get('counters', {})
        timing_stats = perf_stats.get('timing_stats', {})
        
        if counters:
            print("Counters:")
            for name, count in sorted(counters.items()):
                if count > 0:  # Only show non-zero counters
                    print(f"  {name}: {count}")
        else:
            print("No performance counters available")
        
        if timing_stats:
            print("\\nTiming Statistics:")
            for name, stats in sorted(timing_stats.items()):
                print(f"  {name}: {stats['avg_ms']:.1f}ms avg ({stats['count']} calls)")
        
        print()
        
        # Platform Status Section  
        print("PLATFORM STATUS")
        print("-" * 40)
        
        health_status = snapshot.get('health_status', {})
        if health_status:
            for platform, status in health_status.items():
                status_symbol = "+" if status.get('status') == 'healthy' else "-"
                response_time = status.get('response_time_ms', 0)
                print(f"{status_symbol} {platform}: {status.get('message', 'No message')} ({response_time:.1f}ms)")
        else:
            print("No platform status available")
        
        print()
        
        # Recent Activity Section
        print("RECENT ACTIVITY")
        print("-" * 40)
        
        recent_logs = self.get_recent_logs(5)
        for log_entry in recent_logs:
            # Truncate long log entries
            if len(log_entry) > 75:
                log_entry = log_entry[:72] + "..."
            print(f"  {log_entry}")
        
        print()
        
        # Footer
        print("-" * 80)
        print("Press Ctrl+C to exit | Refreshes every 30 seconds")
    
    def run(self, refresh_interval: int = 30):
        """Run the dashboard with automatic refresh."""
        try:
            while True:
                self.render_dashboard()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            clear_screen()
            print("Monitoring dashboard stopped.")
            print("Thank you for using the Social Media Bot Monitoring Dashboard!")

def run_health_check():
    """Run a quick health check and display results."""
    try:
        from utils.health_checks import generate_health_report
        print(generate_health_report())
    except Exception as e:
        print(f"Health check failed: {e}")

def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "health":
            run_health_check()
            return
        elif sys.argv[1] == "test":
            # Test monitoring system
            try:
                from utils.monitoring import get_monitoring
                monitoring = get_monitoring()
                
                # Test logging
                monitoring.log_event("info", "Testing monitoring system", "dashboard")
                
                # Test metrics
                monitoring.record_metric("test_metric", 42.0, "dashboard")
                monitoring.increment_counter("test_counter", "dashboard")
                
                # Test health checks
                status = monitoring.get_system_status()
                print("Monitoring system test completed successfully!")
                print(f"System status: {status.get('overall_status', 'unknown')}")
                return
            except Exception as e:
                print(f"Monitoring test failed: {e}")
                return
    
    # Run dashboard
    dashboard = MonitoringDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()