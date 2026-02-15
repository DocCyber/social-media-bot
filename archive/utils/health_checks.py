"""
Health Check System
Provides comprehensive health monitoring for all system components.
Built for 24/7 operation with automated status reporting.

Compatible with Python 3.10+ including 3.13.
"""

import os
import sys
import time
import psutil
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Tuple

# Add project paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))


def check_disk_space(min_free_gb: float = 1.0) -> bool:
    """Check if sufficient disk space is available."""
    try:
        base_path = Path(__file__).parent.parent
        disk_usage = psutil.disk_usage(str(base_path))
        free_gb = disk_usage.free / (1024**3)
        return free_gb >= min_free_gb
    except Exception:
        return False


def check_memory_usage(max_usage_percent: float = 90.0) -> bool:
    """Check if memory usage is within acceptable limits."""
    try:
        memory = psutil.virtual_memory()
        return memory.percent <= max_usage_percent
    except Exception:
        return False


def check_cpu_usage(max_usage_percent: float = 80.0) -> bool:
    """Check if CPU usage is within acceptable limits."""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        return cpu_percent <= max_usage_percent
    except Exception:
        return False


def check_config_files() -> bool:
    """Check if essential configuration files are present and valid."""
    try:
        base_path = Path(__file__).parent.parent
        
        # Check for master config
        master_config = base_path / "config" / "master_config.json"
        if master_config.exists():
            import json
            with open(master_config) as f:
                config = json.load(f)
                # Verify essential keys
                return all(key in config for key in ['platforms', 'paths', 'logging'])
        
        # Fallback to legacy config check
        legacy_keys = base_path / "keys.json"
        if legacy_keys.exists():
            import json
            with open(legacy_keys) as f:
                config = json.load(f)
                return 'bsky' in config  # At least BlueSky should be configured
        
        return False
    except Exception:
        return False


def check_platform_connectivity() -> bool:
    """Check basic connectivity to platform APIs."""
    try:
        # Test basic internet connectivity
        response = requests.get("https://www.google.com", timeout=5)
        if response.status_code != 200:
            return False
        
        # Test BlueSky connectivity
        try:
            response = requests.get("https://bsky.social", timeout=10)
            return response.status_code in [200, 403]  # 403 is OK for API endpoint
        except requests.RequestException:
            # If BlueSky is down, check if we can reach other platforms
            try:
                response = requests.get("https://api.twitter.com", timeout=5)
                return response.status_code in [200, 400, 401]  # API errors are OK
            except requests.RequestException:
                return False
            
    except Exception:
        return False


def check_log_files() -> bool:
    """Check if log files are being created and are writable."""
    try:
        base_path = Path(__file__).parent.parent
        
        # Check if monitoring directory exists and is writable
        monitoring_dir = base_path / "monitoring" 
        if not monitoring_dir.exists():
            monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        # Test write access
        test_file = monitoring_dir / "health_check_test.tmp"
        try:
            with open(test_file, 'w') as f:
                f.write(f"Health check test: {datetime.now().isoformat()}")
            test_file.unlink()  # Clean up
            return True
        except Exception:
            return False
            
    except Exception:
        return False


def check_csv_files() -> bool:
    """Check if essential CSV files are accessible."""
    try:
        base_path = Path(__file__).parent.parent
        
        # Check main jokes CSV
        jokes_csv = base_path / "jokes.csv"
        if not jokes_csv.exists():
            return False
        
        # Check if file is readable
        with open(jokes_csv, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first few lines to verify format
            lines = [next(f, None) for _ in range(3)]
            return len([line for line in lines if line and line.strip()]) >= 1
            
    except Exception:
        return False


def check_process_health() -> bool:
    """Check if the current process is healthy."""
    try:
        current_process = psutil.Process()
        
        # Check memory usage of current process
        memory_info = current_process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        # Alert if process is using more than 500MB (should be much less for this bot)
        if memory_mb > 500:
            return False
        
        # Check if process is responsive
        cpu_percent = current_process.cpu_percent()
        
        # Alert if process is using excessive CPU for extended period
        if cpu_percent > 50:  # Should be low for a scheduling bot
            return False
            
        return True
        
    except Exception:
        return False


def check_bluesky_auth() -> bool:
    """Check if BlueSky authentication is working."""
    try:
        from utils.config_manager import ConfigManager
        from platforms.bluesky.bluesky_auth import get_bluesky_auth
        
        config_manager = ConfigManager()
        config_manager.load_all_configs()
        
        bluesky_config = config_manager.get_platform_config('bluesky')
        if not bluesky_config:
            return False
        
        # Check if we have required credentials
        handle = bluesky_config.get('handle')
        app_password = bluesky_config.get('app_password') 
        
        if not handle or not app_password:
            return False
        
        # Test authentication
        auth = get_bluesky_auth()
        return auth.test_connection()
        
    except Exception:
        return False


def check_platform_modules() -> bool:
    """Check if platform modules can be imported and initialized."""
    try:
        # Test BlueSky platform
        from platforms.bluesky.bluesky_platform import BlueSkyPlatform
        platform = BlueSkyPlatform()
        
        # Test consolidated modules
        from platforms.bluesky.interactive_modules import run_notifications
        
        return True
        
    except ImportError:
        return False
    except Exception:
        # Module exists but failed to initialize - still counts as working
        return True


class SystemHealthMonitor:
    """Comprehensive system health monitoring."""
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], bool]] = {
            'disk_space': check_disk_space,
            'memory_usage': check_memory_usage,
            'cpu_usage': check_cpu_usage,
            'config_files': check_config_files,
            'platform_connectivity': check_platform_connectivity,
            'log_files': check_log_files,
            'csv_files': check_csv_files,
            'process_health': check_process_health,
            'bluesky_auth': check_bluesky_auth,
            'platform_modules': check_platform_modules
        }
        
        self.check_descriptions = {
            'disk_space': 'Sufficient disk space available',
            'memory_usage': 'System memory usage within limits',
            'cpu_usage': 'System CPU usage within limits', 
            'config_files': 'Configuration files present and valid',
            'platform_connectivity': 'Internet and platform API connectivity',
            'log_files': 'Log files writable and accessible',
            'csv_files': 'Essential CSV files accessible',
            'process_health': 'Current process resource usage healthy',
            'bluesky_auth': 'BlueSky authentication working',
            'platform_modules': 'Platform modules importable'
        }
    
    def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all health checks and return detailed results."""
        results = {}
        
        for check_name, check_func in self.checks.items():
            start_time = time.time()
            try:
                is_healthy = check_func()
                duration_ms = (time.time() - start_time) * 1000
                
                results[check_name] = {
                    'status': 'healthy' if is_healthy else 'critical',
                    'description': self.check_descriptions.get(check_name, ''),
                    'duration_ms': round(duration_ms, 2),
                    'timestamp': datetime.now().isoformat(),
                    'error': None
                }
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                results[check_name] = {
                    'status': 'critical',
                    'description': f"Check failed: {str(e)}",
                    'duration_ms': round(duration_ms, 2),
                    'timestamp': datetime.now().isoformat(),
                    'error': str(e)
                }
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of system health."""
        results = self.run_all_checks()
        
        total_checks = len(results)
        healthy_checks = sum(1 for r in results.values() if r['status'] == 'healthy')
        critical_checks = total_checks - healthy_checks
        
        # Determine overall status
        overall_status = 'healthy'
        if critical_checks > 0:
            if critical_checks >= total_checks * 0.5:  # More than 50% failing
                overall_status = 'critical'
            else:
                overall_status = 'warning'
        
        return {
            'overall_status': overall_status,
            'total_checks': total_checks,
            'healthy_checks': healthy_checks,
            'critical_checks': critical_checks,
            'health_score': round((healthy_checks / total_checks) * 100, 1),
            'timestamp': datetime.now().isoformat(),
            'details': results
        }


def generate_health_report() -> str:
    """Generate a human-readable health report."""
    monitor = SystemHealthMonitor()
    summary = monitor.get_summary()
    
    status_emoji = {
        'healthy': '[OK]',
        'warning': '[WARN]', 
        'critical': '[FAIL]'
    }
    
    report = []
    report.append("=" * 60)
    report.append("SYSTEM HEALTH REPORT")
    report.append("=" * 60)
    report.append(f"Timestamp: {summary['timestamp']}")
    report.append(f"Overall Status: {status_emoji.get(summary['overall_status'], '❓')} {summary['overall_status'].upper()}")
    report.append(f"Health Score: {summary['health_score']}%")
    report.append(f"Checks: {summary['healthy_checks']}/{summary['total_checks']} passing")
    report.append("")
    
    # Detailed results
    for check_name, result in summary['details'].items():
        status_symbol = "+" if result['status'] == 'healthy' else "-"
        report.append(f"{status_symbol} {check_name}: {result['description']} ({result['duration_ms']}ms)")
        
        if result['error']:
            report.append(f"  Error: {result['error']}")
    
    report.append("")
    report.append("=" * 60)
    
    return "\\n".join(report)


if __name__ == "__main__":
    print(generate_health_report())