#!/usr/bin/env python3
"""
Automation Dashboard & Controls
Interactive dashboard for managing scheduling, content rotation, and automation.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project paths
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "automation"))

try:
    from automation.scheduler import get_scheduler, TaskStatus
    from automation.timing_optimizer import get_timing_optimizer
    from automation.content_coordinator import get_content_coordinator, ContentType
    from automation.content_rotator import get_content_rotator
    from utils.monitoring import get_monitoring
    from utils.config_manager import ConfigManager
    from utils.date_aware_logger import get_enhanced_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Some automation features may not be available.")
    sys.exit(1)

class AutomationDashboard:
    def __init__(self):
        self.logger = get_enhanced_logger("automation_dashboard")
        self.config_manager = ConfigManager()
        
        # Initialize components
        self.scheduler = get_scheduler()
        self.timing_optimizer = get_timing_optimizer()
        self.coordinator = get_content_coordinator()
        self.rotator = get_content_rotator()
        self.monitoring = get_monitoring()
        
        self.running = True

    def display_main_menu(self):
        """Display the main dashboard menu."""
        while self.running:
            self.clear_screen()
            print("=" * 80)
            print(" " * 25 + "AUTOMATION DASHBOARD")
            print("=" * 80)
            print()
            
            # System status
            self.display_system_status()
            print()
            
            # Menu options
            print("MAIN MENU:")
            print("1. Scheduler Management")
            print("2. Content Management") 
            print("3. Timing & Optimization")
            print("4. Platform Coordination")
            print("5. System Monitoring")
            print("6. Configuration")
            print("7. Start/Stop Automation")
            print("0. Exit")
            print()
            
            try:
                choice = input("Select option (0-7): ").strip()
                
                if choice == "0":
                    self.running = False
                elif choice == "1":
                    self.scheduler_menu()
                elif choice == "2":
                    self.content_menu()
                elif choice == "3":
                    self.timing_menu()
                elif choice == "4":
                    self.coordination_menu()
                elif choice == "5":
                    self.monitoring_menu()
                elif choice == "6":
                    self.configuration_menu()
                elif choice == "7":
                    self.automation_control_menu()
                else:
                    print("Invalid option. Press Enter to continue...")
                    input()
                    
            except KeyboardInterrupt:
                self.running = False
            except Exception as e:
                print(f"Error: {e}")
                input("Press Enter to continue...")

    def display_system_status(self):
        """Display current system status."""
        try:
            # Scheduler status
            all_tasks = self.scheduler.get_all_tasks_status()
            running_tasks = sum(1 for task in all_tasks if task["status"] == "running")
            enabled_tasks = sum(1 for task in all_tasks if task["enabled"])
            
            # Content status
            coordinator_stats = {
                "twitter": self.coordinator.get_platform_statistics("twitter"),
                "mastodon": self.coordinator.get_platform_statistics("mastodon"),
                "bluesky": self.coordinator.get_platform_statistics("bluesky")
            }
            
            total_pending = sum(stats["total_pending"] for stats in coordinator_stats.values())
            
            # Display status
            print(f"System Status: {'ACTIVE' if hasattr(self.scheduler, 'scheduler_thread') and self.scheduler.scheduler_thread and self.scheduler.scheduler_thread.is_alive() else 'INACTIVE'}")
            print(f"Tasks: {running_tasks} running, {enabled_tasks}/{len(all_tasks)} enabled")
            print(f"Content: {total_pending} pending posts across all platforms")
            
        except Exception as e:
            print(f"Status Error: {e}")

    def scheduler_menu(self):
        """Scheduler management menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "SCHEDULER MANAGEMENT")
            print("=" * 60)
            
            # Display task status
            try:
                all_tasks = self.scheduler.get_all_tasks_status()
                
                print(f"\nCurrent Tasks ({len(all_tasks)}):")
                print("-" * 60)
                for task in all_tasks[:10]:  # Show first 10 tasks
                    status_symbol = {
                        "pending": "[WAIT]",
                        "running": "[RUN ]",
                        "completed": "[DONE]",
                        "failed": "[FAIL]"
                    }.get(task["status"], "[????]")
                    
                    enabled_symbol = "[ON ]" if task["enabled"] else "[OFF]"
                    
                    print(f"{status_symbol} {enabled_symbol} {task['name'][:30]:<30} "
                          f"({task['platform'] or 'system'})")
                
                if len(all_tasks) > 10:
                    print(f"... and {len(all_tasks) - 10} more tasks")
                
                # Upcoming tasks
                upcoming = self.scheduler.get_next_scheduled_tasks(5)
                if upcoming:
                    print("\nNext Scheduled:")
                    print("-" * 40)
                    for task in upcoming:
                        next_run = task["next_run"].strftime("%H:%M")
                        print(f"{next_run} - {task['name'][:25]} ({task['platform']})")
                
            except Exception as e:
                print(f"Error loading tasks: {e}")
            
            print("\nSCHEDULER OPTIONS:")
            print("1. View All Tasks")
            print("2. Enable/Disable Task") 
            print("3. Force Run Task")
            print("4. Add Custom Task")
            print("5. Task Statistics")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_all_tasks()
            elif choice == "2":
                self.toggle_task()
            elif choice == "3":
                self.force_run_task()
            elif choice == "4":
                self.add_custom_task()
            elif choice == "5":
                self.task_statistics()

    def content_menu(self):
        """Content management menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "CONTENT MANAGEMENT")
            print("=" * 60)
            
            # Display content status
            try:
                content_stats = self.rotator.get_content_statistics()
                
                print("\nContent Pools:")
                print("-" * 40)
                for source, stats in content_stats["content_pools"].items():
                    print(f"{source:<15}: {stats['total_items']:>4} items, "
                          f"{stats['recently_used']:>3} used recently")
                
                print(f"\nTotal Available Content: {content_stats['total_available_content']}")
                print(f"Tracking Freshness: {content_stats['freshness_tracking']} unique items")
                
                # Platform content queues
                print("\nPlatform Queues:")
                print("-" * 30)
                for platform in ["twitter", "mastodon", "bluesky"]:
                    stats = self.coordinator.get_platform_statistics(platform)
                    print(f"{platform:<10}: {stats['queue_length']:>2} queued, "
                          f"{stats['total_pending']:>2} pending")
                
            except Exception as e:
                print(f"Error loading content stats: {e}")
            
            print("\nCONTENT OPTIONS:")
            print("1. View Content Preview")
            print("2. Schedule Content")
            print("3. Refresh Content Pools")
            print("4. Reset Content Freshness")
            print("5. Content Insights")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_content_preview()
            elif choice == "2":
                self.schedule_content_menu()
            elif choice == "3":
                self.refresh_content_pools()
            elif choice == "4":
                self.reset_content_freshness()
            elif choice == "5":
                self.content_insights()

    def timing_menu(self):
        """Timing optimization menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "TIMING & OPTIMIZATION")
            print("=" * 60)
            
            print("\nTIMING OPTIONS:")
            print("1. View Platform Engagement Insights")
            print("2. Generate Optimal Schedules")
            print("3. Record Engagement Data")
            print("4. Optimize Current Schedules")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_engagement_insights()
            elif choice == "2":
                self.generate_optimal_schedules()
            elif choice == "3":
                self.record_engagement_data()
            elif choice == "4":
                self.optimize_schedules()

    def coordination_menu(self):
        """Platform coordination menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "PLATFORM COORDINATION")
            print("=" * 60)
            
            # Display coordination status
            try:
                print("\nPlatform Status:")
                print("-" * 40)
                
                for platform in ["twitter", "mastodon", "bluesky"]:
                    stats = self.coordinator.get_platform_statistics(platform)
                    
                    next_available = "Now"
                    if stats.get("next_available"):
                        next_time = datetime.fromisoformat(stats["next_available"])
                        if next_time > datetime.now():
                            next_available = next_time.strftime("%H:%M")
                    
                    print(f"{platform:<10}: {stats['total_pending']:>2} pending, "
                          f"{stats['posts_last_hour']:>2}/hr, next: {next_available}")
                
            except Exception as e:
                print(f"Error loading coordination status: {e}")
            
            print("\nCOORDINATION OPTIONS:")
            print("1. View Platform Statistics")
            print("2. Schedule Cross-Platform Content")
            print("3. Manage Platform Queues")
            print("4. Set Platform Limits")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_platform_statistics()
            elif choice == "2":
                self.schedule_cross_platform()
            elif choice == "3":
                self.manage_platform_queues()
            elif choice == "4":
                self.set_platform_limits()

    def automation_control_menu(self):
        """Automation control menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "AUTOMATION CONTROL")
            print("=" * 60)
            
            # Check scheduler status
            is_running = (hasattr(self.scheduler, 'scheduler_thread') and 
                         self.scheduler.scheduler_thread and 
                         self.scheduler.scheduler_thread.is_alive())
            
            status = "RUNNING" if is_running else "STOPPED"
            print(f"\nCurrent Status: {status}")
            
            print("\nCONTROL OPTIONS:")
            if is_running:
                print("1. Stop Scheduler")
            else:
                print("1. Start Scheduler")
            
            print("2. Restart Scheduler")
            print("3. View Running Tasks")
            print("4. Emergency Stop All")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                if is_running:
                    self.stop_scheduler()
                else:
                    self.start_scheduler()
            elif choice == "2":
                self.restart_scheduler()
            elif choice == "3":
                self.view_running_tasks()
            elif choice == "4":
                self.emergency_stop()

    def monitoring_menu(self):
        """System monitoring menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "SYSTEM MONITORING")
            print("=" * 60)
            
            print("\nMONITORING OPTIONS:")
            print("1. View System Health")
            print("2. View Performance Metrics")
            print("3. View Recent Logs")
            print("4. Generate System Report")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_system_health()
            elif choice == "2":
                self.view_performance_metrics()
            elif choice == "3":
                self.view_recent_logs()
            elif choice == "4":
                self.generate_system_report()

    def configuration_menu(self):
        """Configuration menu."""
        while True:
            self.clear_screen()
            print("=" * 60)
            print(" " * 25 + "CONFIGURATION")
            print("=" * 60)
            
            print("\nCONFIGURATION OPTIONS:")
            print("1. View Current Configuration")
            print("2. Update Platform Settings")
            print("3. Update Scheduling Settings")
            print("4. Save Configuration")
            print("0. Back to Main Menu")
            
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.view_configuration()
            elif choice == "2":
                self.update_platform_settings()
            elif choice == "3":
                self.update_scheduling_settings()
            elif choice == "4":
                self.save_configuration()

    # Helper methods for menu actions
    def clear_screen(self):
        """Clear the screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def start_scheduler(self):
        """Start the automation scheduler."""
        try:
            self.scheduler.start()
            print("Scheduler started successfully!")
        except Exception as e:
            print(f"Error starting scheduler: {e}")
        input("Press Enter to continue...")

    def stop_scheduler(self):
        """Stop the automation scheduler."""
        try:
            self.scheduler.stop()
            print("Scheduler stopped successfully!")
        except Exception as e:
            print(f"Error stopping scheduler: {e}")
        input("Press Enter to continue...")

    def view_content_preview(self):
        """View content preview."""
        try:
            preview = self.coordinator.get_content_preview(20)
            
            self.clear_screen()
            print("=" * 80)
            print(" " * 30 + "CONTENT PREVIEW")
            print("=" * 80)
            
            for item in preview:
                status_text = ", ".join([f"{k}: {v}" for k, v in item["status"].items()])
                
                print(f"\nID: {item['id'][:8]}...")
                print(f"Type: {item['type']}")
                print(f"Platforms: {', '.join(item['platforms'])}")
                print(f"Status: {status_text}")
                print(f"Content: {item['content']}")
                print("-" * 40)
            
        except Exception as e:
            print(f"Error loading content preview: {e}")
        
        input("\nPress Enter to continue...")

    def view_system_health(self):
        """View system health status."""
        try:
            system_status = self.monitoring.get_system_status()
            
            self.clear_screen()
            print("=" * 60)
            print(" " * 20 + "SYSTEM HEALTH STATUS")
            print("=" * 60)
            
            print(f"\nOverall Status: {system_status.get('overall_status', 'Unknown')}")
            
            if 'health_checks' in system_status:
                print("\nHealth Checks:")
                print("-" * 40)
                for check_name, result in system_status['health_checks'].items():
                    status = result.get('status', 'unknown')
                    message = result.get('message', 'No message')
                    print(f"{check_name:<20}: {status:<10} - {message}")
            
        except Exception as e:
            print(f"Error loading health status: {e}")
        
        input("\nPress Enter to continue...")

    def run(self):
        """Run the dashboard."""
        try:
            print("Starting Automation Dashboard...")
            self.display_main_menu()
        except KeyboardInterrupt:
            print("\nExiting dashboard...")
        finally:
            print("Dashboard shutdown complete.")

def main():
    """Main entry point."""
    dashboard = AutomationDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()