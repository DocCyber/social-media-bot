#!/usr/bin/env python3
"""
Automated System Maintenance Module
Handles cleanup, optimization, and routine maintenance tasks.
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import sys

sys.path.append(str(Path(__file__).parent.parent))

from utils.date_aware_logger import get_enhanced_logger
from utils.monitoring import record_metric, log_event
from automation.content_coordinator import get_content_coordinator
from automation.content_rotator import get_content_rotator

def run_maintenance():
    """Run all maintenance tasks."""
    logger = get_enhanced_logger("maintenance")
    logger.info("Starting automated maintenance")
    
    maintenance_results = {}
    
    try:
        # Content cleanup
        maintenance_results['content_cleanup'] = cleanup_old_content()
        
        # Log file rotation
        maintenance_results['log_rotation'] = rotate_log_files()
        
        # Performance optimization
        maintenance_results['performance_optimization'] = optimize_performance()
        
        # System health check
        maintenance_results['health_check'] = run_health_verification()
        
        # Report results
        total_tasks = len(maintenance_results)
        successful_tasks = sum(1 for result in maintenance_results.values() if result.get('success', False))
        
        logger.info(f"Maintenance completed: {successful_tasks}/{total_tasks} tasks successful")
        record_metric("maintenance_completed", 1, "maintenance")
        record_metric("maintenance_success_rate", successful_tasks / total_tasks, "maintenance")
        
        return maintenance_results
        
    except Exception as e:
        logger.error(f"Maintenance failed: {e}")
        log_event("error", f"Maintenance failed: {str(e)}", "maintenance")
        return {"error": str(e)}

def cleanup_old_content():
    """Clean up old content and reset freshness."""
    logger = get_enhanced_logger("maintenance_content")
    
    try:
        coordinator = get_content_coordinator()
        rotator = get_content_rotator()
        
        # Clean up old posted content (older than 7 days)
        coordinator.cleanup_old_content(days_old=7)
        
        # Reset content freshness for content older than 1 week
        reset_count = rotator.reset_content_freshness(hours_old=168)
        
        # Refresh content pools
        refreshed_pools = rotator.refresh_content_pools()
        
        logger.info(f"Content cleanup: {reset_count} freshness resets, {refreshed_pools} pools refreshed")
        
        return {
            "success": True,
            "freshness_resets": reset_count,
            "pools_refreshed": refreshed_pools
        }
        
    except Exception as e:
        logger.error(f"Content cleanup failed: {e}")
        return {"success": False, "error": str(e)}

def rotate_log_files():
    """Rotate and compress old log files."""
    logger = get_enhanced_logger("maintenance_logs")
    
    try:
        rotated_files = 0
        
        # Monitoring logs
        monitoring_logs_dir = Path(__file__).parent.parent / "monitoring" / "logs"
        if monitoring_logs_dir.exists():
            for log_file in monitoring_logs_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    backup_name = f"{log_file.stem}_{datetime.now().strftime('%Y%m%d')}.bak"
                    backup_path = log_file.parent / backup_name
                    
                    shutil.move(str(log_file), str(backup_path))
                    rotated_files += 1
        
        # Clean old backup files (older than 30 days)
        cutoff_date = datetime.now() - timedelta(days=30)
        for backup_file in monitoring_logs_dir.glob("*.bak"):
            if datetime.fromtimestamp(backup_file.stat().st_mtime) < cutoff_date:
                backup_file.unlink()
                rotated_files += 1
        
        logger.info(f"Log rotation: {rotated_files} files processed")
        
        return {
            "success": True,
            "files_rotated": rotated_files
        }
        
    except Exception as e:
        logger.error(f"Log rotation failed: {e}")
        return {"success": False, "error": str(e)}

def optimize_performance():
    """Optimize system performance."""
    logger = get_enhanced_logger("maintenance_performance")
    
    try:
        optimizations = 0
        
        # Clear Python cache
        import gc
        collected = gc.collect()
        optimizations += 1
        
        # Optimize automation state files
        automation_dir = Path(__file__).parent
        
        for state_file in automation_dir.glob("*_state.json"):
            if state_file.stat().st_size > 1024 * 1024:  # 1MB
                # Backup and compress state file
                with open(state_file, 'r') as f:
                    data = json.load(f)
                
                # Keep only recent data
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list) and len(value) > 1000:
                            data[key] = value[-1000:]  # Keep last 1000 items
                            optimizations += 1
                
                with open(state_file, 'w') as f:
                    json.dump(data, f, indent=2)
        
        logger.info(f"Performance optimization: {optimizations} optimizations applied, {collected} objects collected")
        
        return {
            "success": True,
            "optimizations": optimizations,
            "gc_collected": collected
        }
        
    except Exception as e:
        logger.error(f"Performance optimization failed: {e}")
        return {"success": False, "error": str(e)}

def run_health_verification():
    """Run health verification checks."""
    logger = get_enhanced_logger("maintenance_health")
    
    try:
        from utils.health_checks import SystemHealthMonitor
        
        health_monitor = SystemHealthMonitor()
        health_results = health_monitor.run_all_checks()
        
        healthy_checks = sum(1 for result in health_results.values() if result['status'] == 'healthy')
        total_checks = len(health_results)
        
        critical_issues = [name for name, result in health_results.items() 
                          if result['status'] == 'critical']
        
        if critical_issues:
            logger.warning(f"Critical health issues detected: {', '.join(critical_issues)}")
        
        logger.info(f"Health verification: {healthy_checks}/{total_checks} checks passing")
        
        return {
            "success": True,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "critical_issues": critical_issues
        }
        
    except Exception as e:
        logger.error(f"Health verification failed: {e}")
        return {"success": False, "error": str(e)}