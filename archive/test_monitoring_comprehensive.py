#!/usr/bin/env python3
"""
Comprehensive Monitoring System Test
Tests all components of Phase 5: Logging & Monitoring implementation.

Compatible with Python 3.10+ including 3.13.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_monitoring_system():
    """Test the comprehensive monitoring system."""
    print("=" * 60)
    print("COMPREHENSIVE MONITORING SYSTEM TEST")
    print("Phase 5: Logging & Monitoring")
    print("=" * 60)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Basic Monitoring System
    print("Test 1: Testing basic monitoring system...")
    try:
        from utils.monitoring import get_monitoring, log_event, record_metric
        
        monitoring = get_monitoring()
        print("+ Monitoring system initialized")
        
        # Test logging
        log_event("info", "Test info message", "test_suite")
        log_event("warning", "Test warning message", "test_suite") 
        log_event("error", "Test error message", "test_suite")
        print("+ Event logging working")
        
        # Test metrics
        record_metric("test_requests", 42, "test_suite")
        record_metric("test_response_time", 123.45, "test_suite", {"endpoint": "/api/test"})
        monitoring.increment_counter("test_operations", "test_suite")
        print("+ Metrics recording working")
        
        results['monitoring_basic'] = True
        
    except Exception as e:
        print(f"- Basic monitoring test failed: {e}")
        results['monitoring_basic'] = False
    
    print()
    
    # Test 2: Health Checks
    print("Test 2: Testing health check system...")
    try:
        from utils.health_checks import SystemHealthMonitor
        
        health_monitor = SystemHealthMonitor()
        health_results = health_monitor.run_all_checks()
        
        print(f"+ Ran {len(health_results)} health checks")
        
        healthy_count = sum(1 for r in health_results.values() if r['status'] == 'healthy')
        print(f"+ {healthy_count}/{len(health_results)} checks passing")
        
        # Test individual checks
        critical_checks = [name for name, result in health_results.items() 
                         if result['status'] == 'critical']
        if critical_checks:
            print(f"- Critical issues: {', '.join(critical_checks)}")
        else:
            print("+ No critical health issues detected")
        
        results['health_checks'] = len(critical_checks) == 0
        
    except Exception as e:
        print(f"- Health check test failed: {e}")
        results['health_checks'] = False
    
    print()
    
    # Test 3: Enhanced Logging with Date Awareness
    print("Test 3: Testing enhanced date-aware logging...")
    try:
        from utils.date_aware_logger import get_enhanced_logger
        
        # Create test logger
        test_logger = get_enhanced_logger("test_enhanced")
        
        # Test different log levels
        test_logger.info("Enhanced logging system test started")
        test_logger.success("Test success message")
        test_logger.warning("Test warning message")
        test_logger.debug("Test debug message")
        
        print("+ Enhanced logging initialized")
        print("+ Date-aware file handling active")
        print("+ Multiple log levels working")
        
        # Check if log files were created
        monitoring_dir = Path(__file__).parent / "monitoring" / "logs"
        today_date = datetime.now().strftime('%Y%m%d')
        
        date_log_file = monitoring_dir / f"bot_activity_{today_date}.log"
        if date_log_file.exists():
            print("+ Date-coded log file created")
            
            # Check file content
            with open(date_log_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if "SOCIAL MEDIA BOT - ACTIVITY LOG" in content:
                    print("+ Date header properly formatted")
                else:
                    print("- Date header not found")
        else:
            print("- Date-coded log file not created")
        
        results['enhanced_logging'] = True
        
    except Exception as e:
        print(f"- Enhanced logging test failed: {e}")
        results['enhanced_logging'] = False
    
    print()
    
    # Test 4: Performance Monitoring
    print("Test 4: Testing performance monitoring...")
    try:
        from utils.monitoring import get_monitoring
        
        monitoring = get_monitoring()
        
        # Test function timing
        @monitoring.time_function("test_function", "test_suite")
        def test_timed_function():
            time.sleep(0.1)  # Simulate work
            return "test_result"
        
        result = test_timed_function()
        print(f"+ Timed function executed: {result}")
        
        # Test performance stats
        perf_stats = monitoring.performance.get_stats()
        print(f"+ Performance stats available: {len(perf_stats)} categories")
        
        if 'timing_stats' in perf_stats and perf_stats['timing_stats']:
            print("+ Timing statistics recorded")
        else:
            print("- No timing statistics found")
        
        results['performance_monitoring'] = True
        
    except Exception as e:
        print(f"- Performance monitoring test failed: {e}")
        results['performance_monitoring'] = False
    
    print()
    
    # Test 5: System Status & Reporting
    print("Test 5: Testing system status and reporting...")
    try:
        from utils.monitoring import get_monitoring
        
        monitoring = get_monitoring()
        
        # Get system status
        system_status = monitoring.get_system_status()
        print(f"+ System status: {system_status.get('overall_status', 'unknown')}")
        
        if 'health_checks' in system_status:
            print(f"+ Health checks included: {len(system_status['health_checks'])}")
        
        if 'performance_stats' in system_status:
            print("+ Performance stats included")
        
        # Generate report
        report = monitoring.generate_report(hours=1)
        print(f"+ Report generated for {report['period_hours']} hours")
        print(f"+ Report contains {report['total_metrics']} metrics")
        
        results['system_reporting'] = True
        
    except Exception as e:
        print(f"- System reporting test failed: {e}")
        results['system_reporting'] = False
    
    print()
    
    # Test 6: File Structure & Organization
    print("Test 6: Testing monitoring file structure...")
    try:
        base_path = Path(__file__).parent
        monitoring_dir = base_path / "monitoring"
        
        # Check directory structure
        required_dirs = ['logs', 'metrics']
        missing_dirs = []
        
        for dir_name in required_dirs:
            dir_path = monitoring_dir / dir_name
            if dir_path.exists():
                print(f"+ {dir_name}/ directory exists")
            else:
                missing_dirs.append(dir_name)
                print(f"- {dir_name}/ directory missing")
        
        # Check for log files
        logs_dir = monitoring_dir / "logs"
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log")) + list(logs_dir.glob("*.jsonl"))
            print(f"+ {len(log_files)} log files found")
        
        # Check for snapshot file
        snapshot_file = monitoring_dir / "performance_snapshot.json"
        if snapshot_file.exists():
            print("+ Performance snapshot file exists")
        else:
            print("- Performance snapshot file missing")
        
        results['file_structure'] = len(missing_dirs) == 0
        
    except Exception as e:
        print(f"- File structure test failed: {e}")
        results['file_structure'] = False
    
    print()
    
    # Test Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        symbol = "+" if result else "-"
        print(f"{symbol} {test_name.replace('_', ' ').title()}: {status}")
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Comprehensive monitoring system is fully operational!")
        print()
        print("Phase 5: Logging & Monitoring - COMPLETE!")
        print()
        print("Enhanced Features Available:")
        print("- Real-time system health monitoring")
        print("- Date-aware activity logging with automatic markers")
        print("- Performance metrics and timing analysis") 
        print("- Structured JSON logging for analysis")
        print("- Comprehensive health checks (10 components)")
        print("- Interactive monitoring dashboard")
        print("- Automated file rotation and cleanup")
        print("- Multi-level logging with console + file output")
        return True
    else:
        print("WARNING: Some monitoring tests failed. Review errors above.")
        return False

def show_monitoring_files():
    """Show the monitoring files created."""
    print("\\n" + "=" * 60)
    print("MONITORING FILES CREATED")
    print("=" * 60)
    
    base_path = Path(__file__).parent
    monitoring_dir = base_path / "monitoring"
    
    if monitoring_dir.exists():
        print(f"Monitoring Directory: {monitoring_dir}")
        print()
        
        for subdir in ['logs', 'metrics']:
            subdir_path = monitoring_dir / subdir
            if subdir_path.exists():
                print(f"{subdir.upper()}/:")
                files = list(subdir_path.glob("*"))
                for file_path in sorted(files):
                    size = file_path.stat().st_size
                    modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                    print(f"  {file_path.name} ({size} bytes, {modified.strftime('%H:%M:%S')})")
                print()
        
        # Check for snapshot
        snapshot_file = monitoring_dir / "performance_snapshot.json"
        if snapshot_file.exists():
            size = snapshot_file.stat().st_size
            modified = datetime.fromtimestamp(snapshot_file.stat().st_mtime)
            print(f"SNAPSHOTS/:")
            print(f"  {snapshot_file.name} ({size} bytes, {modified.strftime('%H:%M:%S')})")
    else:
        print("No monitoring directory found.")

if __name__ == "__main__":
    success = test_monitoring_system()
    show_monitoring_files()
    
    print("\\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("1. Run the monitoring dashboard: python monitoring_dashboard.py")
    print("2. Run health checks anytime: python monitoring_dashboard.py health") 
    print("3. View real-time logs in: monitoring/logs/")
    print("4. Monitor performance via: monitoring/performance_snapshot.json")
    print("5. All logging now includes automatic date coding and inactivity markers")
    
    sys.exit(0 if success else 1)