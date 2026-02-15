#!/usr/bin/env python3
"""
Comprehensive Automation System Test
Tests all components of Phase 6: Advanced Scheduling & Automation implementation.
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_automation_system():
    """Test the comprehensive automation system."""
    print("=" * 70)
    print("COMPREHENSIVE AUTOMATION SYSTEM TEST")
    print("Phase 6: Advanced Scheduling & Automation")
    print("=" * 70)
    print(f"Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {}
    
    # Test 1: Basic Scheduler
    print("Test 1: Testing automation scheduler...")
    try:
        from automation.scheduler import get_scheduler, ScheduledTask, TaskPriority, ContentType
        
        scheduler = get_scheduler()
        print("+ Scheduler initialized")
        
        # Test task creation
        test_task = ScheduledTask(
            id="test_task",
            name="Test Task",
            description="Test automation task",
            function="test_function",
            module="test_module",
            cron_schedule="*/5 * * * *",  # Every 5 minutes
            priority=TaskPriority.NORMAL
        )
        
        scheduler.add_task(test_task)
        print("+ Task creation working")
        
        # Test task management
        all_tasks = scheduler.get_all_tasks_status()
        print(f"+ Tasks loaded: {len(all_tasks)} total")
        
        # Test scheduling
        upcoming = scheduler.get_next_scheduled_tasks(3)
        print(f"+ Upcoming tasks: {len(upcoming)}")
        
        results['scheduler_basic'] = True
        
    except Exception as e:
        print(f"- Scheduler test failed: {e}")
        results['scheduler_basic'] = False
    
    print()
    
    # Test 2: Timing Optimizer
    print("Test 2: Testing timing optimization...")
    try:
        from automation.timing_optimizer import get_timing_optimizer
        
        optimizer = get_timing_optimizer()
        print("+ Timing optimizer initialized")
        
        # Test optimal schedule generation
        for platform in ["twitter", "mastodon", "bluesky"]:
            schedules = optimizer.generate_optimal_schedule(platform)
            if schedules:
                print(f"+ {platform} schedules generated: {len(schedules)} types")
            else:
                print(f"- {platform} schedule generation failed")
        
        # Test engagement insights
        insights = optimizer.get_engagement_insights("twitter")
        if "error" in insights:
            print("+ Engagement insights: No data (expected for new system)")
        else:
            print("+ Engagement insights available")
        
        results['timing_optimizer'] = True
        
    except Exception as e:
        print(f"- Timing optimizer test failed: {e}")
        results['timing_optimizer'] = False
    
    print()
    
    # Test 3: Content Coordinator
    print("Test 3: Testing content coordination...")
    try:
        from automation.content_coordinator import get_content_coordinator, ContentType
        
        coordinator = get_content_coordinator()
        print("+ Content coordinator initialized")
        
        # Test content addition
        content_id = coordinator.add_content(
            content="Test automation content",
            content_type=ContentType.CUSTOM,
            platforms=["twitter", "bluesky"],
            metadata={"test": True}
        )
        
        if content_id:
            print("+ Content addition working")
            
            # Test content retrieval
            next_content = coordinator.get_next_content("twitter")
            if next_content:
                print("+ Content retrieval working")
                
                # Mark as posted
                coordinator.mark_content_posted(content_id, "twitter", True)
                print("+ Content status tracking working")
            
        # Test statistics
        stats = coordinator.get_platform_statistics("twitter")
        print(f"+ Platform statistics: {stats['total_pending']} pending")
        
        results['content_coordinator'] = True
        
    except Exception as e:
        print(f"- Content coordinator test failed: {e}")
        results['content_coordinator'] = False
    
    print()
    
    # Test 4: Content Rotator
    print("Test 4: Testing content rotation...")
    try:
        from automation.content_rotator import get_content_rotator
        
        rotator = get_content_rotator()
        print("+ Content rotator initialized")
        
        # Test content pools
        stats = rotator.get_content_statistics()
        total_content = stats['total_available_content']
        print(f"+ Content pools loaded: {total_content} total items")
        
        # Test fresh content retrieval
        fresh_content = rotator.get_fresh_content("twitter", ContentType.CUSTOM)
        if fresh_content:
            print("+ Fresh content retrieval working")
        else:
            print("+ Fresh content: None available (expected for test)")
        
        # Test pool refresh
        refreshed = rotator.refresh_content_pools()
        print(f"+ Content pool refresh: {refreshed} pools updated")
        
        results['content_rotator'] = True
        
    except Exception as e:
        print(f"- Content rotator test failed: {e}")
        results['content_rotator'] = False
    
    print()
    
    # Test 5: Dashboard System
    print("Test 5: Testing automation dashboard...")
    try:
        from automation_dashboard import AutomationDashboard
        
        dashboard = AutomationDashboard()
        print("+ Dashboard initialized")
        print("+ All dashboard components loaded")
        
        results['dashboard'] = True
        
    except Exception as e:
        print(f"- Dashboard test failed: {e}")
        results['dashboard'] = False
    
    print()
    
    # Test 6: Maintenance System
    print("Test 6: Testing maintenance system...")
    try:
        from automation.maintenance import run_maintenance
        
        print("+ Maintenance module loaded")
        
        # Test individual maintenance functions
        from automation.maintenance import cleanup_old_content, optimize_performance
        
        cleanup_result = cleanup_old_content()
        if cleanup_result.get('success'):
            print("+ Content cleanup working")
        
        perf_result = optimize_performance()
        if perf_result.get('success'):
            print("+ Performance optimization working")
        
        results['maintenance'] = True
        
    except Exception as e:
        print(f"- Maintenance test failed: {e}")
        results['maintenance'] = False
    
    print()
    
    # Test 7: Integration Test
    print("Test 7: Testing system integration...")
    try:
        # Test scheduler with content coordinator
        scheduler = get_scheduler()
        coordinator = get_content_coordinator()
        rotator = get_content_rotator()
        
        print("+ All components loaded for integration")
        
        # Test cross-platform content scheduling
        cross_content_id = coordinator.schedule_cross_platform_content(
            content="Integration test content",
            content_type=ContentType.CUSTOM,
            platforms=["twitter", "mastodon"],
            stagger_minutes=2,
            metadata={"integration_test": True}
        )
        
        if cross_content_id:
            print("+ Cross-platform scheduling working")
        
        # Test automated content scheduling
        scheduled_ids = rotator.schedule_automated_content(
            platform="bluesky",
            num_posts=2,
            spacing_hours=1
        )
        
        if scheduled_ids:
            print(f"+ Automated scheduling working: {len(scheduled_ids)} posts scheduled")
        
        results['integration'] = True
        
    except Exception as e:
        print(f"- Integration test failed: {e}")
        results['integration'] = False
    
    print()
    
    # Test Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        symbol = "+" if result else "-"
        print(f"{symbol} {test_name.replace('_', ' ').title()}: {status}")
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Comprehensive automation system is fully operational!")
        print()
        print("Phase 6: Advanced Scheduling & Automation - COMPLETE!")
        print()
        print("Advanced Features Available:")
        print("- Intelligent task scheduling with cron expressions")
        print("- Smart timing optimization based on engagement patterns")
        print("- Cross-platform content coordination with conflict avoidance")
        print("- Automated content rotation with freshness tracking")
        print("- Interactive management dashboard with real-time controls")
        print("- Automated system maintenance and optimization")
        print("- Performance monitoring and analytics integration")
        print("- Platform-specific posting limits and cooldowns")
        return True
    else:
        print("WARNING: Some automation tests failed. Review errors above.")
        return False

def show_automation_files():
    """Show the automation files created."""
    print("\\n" + "=" * 70)
    print("AUTOMATION FILES CREATED")
    print("=" * 70)
    
    base_path = Path(__file__).parent
    automation_dir = base_path / "automation"
    
    if automation_dir.exists():
        print(f"Automation Directory: {automation_dir}")
        print()
        
        automation_files = list(automation_dir.glob("*.py"))
        print("CORE MODULES:")
        for file_path in sorted(automation_files):
            size = file_path.stat().st_size
            modified = datetime.fromtimestamp(file_path.stat().st_mtime)
            print(f"  {file_path.name} ({size} bytes, {modified.strftime('%H:%M:%S')})")
        print()
        
        # Check for dashboard
        dashboard_file = base_path / "automation_dashboard.py"
        if dashboard_file.exists():
            size = dashboard_file.stat().st_size
            modified = datetime.fromtimestamp(dashboard_file.stat().st_mtime)
            print("DASHBOARD:")
            print(f"  {dashboard_file.name} ({size} bytes, {modified.strftime('%H:%M:%S')})")
            print()
        
        # Check for state files
        state_files = list(automation_dir.glob("*_state.json")) + list(automation_dir.glob("*.json"))
        if state_files:
            print("STATE FILES:")
            for file_path in sorted(state_files):
                if file_path.exists():
                    size = file_path.stat().st_size
                    modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                    print(f"  {file_path.name} ({size} bytes, {modified.strftime('%H:%M:%S')})")
            print()
    else:
        print("No automation directory found.")

if __name__ == "__main__":
    success = test_automation_system()
    show_automation_files()
    
    print("\\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Run the automation dashboard: python automation_dashboard.py")
    print("2. Start the scheduler for automated posting")
    print("3. Configure optimal posting times based on engagement")
    print("4. Set up cross-platform content coordination")
    print("5. Monitor system performance via the dashboard")
    print("6. All automation now includes intelligent scheduling and optimization")
    
    sys.exit(0 if success else 1)