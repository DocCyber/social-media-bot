#!/usr/bin/env python3
"""
Social Media Bot - Main Launch File
Modern replacement for newcore.py using advanced automation system.
"""

import sys
import signal
import time
from pathlib import Path
from datetime import datetime
import argparse

# Add project paths
sys.path.append(str(Path(__file__).parent))

try:
    from automation.scheduler import get_scheduler
    from automation.content_coordinator import get_content_coordinator, ContentType
    from automation.content_rotator import get_content_rotator
    from automation.timing_optimizer import get_timing_optimizer
    from utils.monitoring import get_monitoring, log_event
    from utils.config_manager import ConfigManager
    from utils.date_aware_logger import get_enhanced_logger
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all required modules are installed.")
    sys.exit(1)

class SocialMediaBot:
    def __init__(self, config_mode="auto"):
        self.logger = get_enhanced_logger("main")
        self.config_manager = ConfigManager()
        
        # Initialize core components
        self.scheduler = get_scheduler()
        self.coordinator = get_content_coordinator()
        self.rotator = get_content_rotator()
        self.timing_optimizer = get_timing_optimizer()
        self.monitoring = get_monitoring()
        
        self.running = False
        self.config_mode = config_mode
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("Social Media Bot initialized")
        log_event("info", "Bot main process started", "main")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def setup_default_schedules(self):
        """Setup default posting schedules if not configured."""
        config = self.config_manager.unified_config
        
        if not config:
            self.logger.error("No configuration loaded")
            return False
        
        platforms = config.get("platforms", {})
        enabled_platforms = [name for name, cfg in platforms.items() if cfg.get("enabled", False)]
        
        self.logger.info(f"Setting up schedules for platforms: {', '.join(enabled_platforms)}")
        
        # Setup automated content for each platform
        for platform in enabled_platforms:
            if platform in ["twitter", "mastodon", "bluesky"]:
                try:
                    # Schedule 3-5 posts per day with intelligent timing
                    scheduled_ids = self.rotator.schedule_automated_content(
                        platform=platform,
                        num_posts=4,  # 4 posts per day
                        spacing_hours=6  # Every 6 hours
                    )
                    
                    if scheduled_ids:
                        self.logger.info(f"Scheduled {len(scheduled_ids)} automated posts for {platform}")
                    
                except Exception as e:
                    self.logger.error(f"Error scheduling content for {platform}: {e}")
        
        return True

    def start_interactive(self):
        """Start in interactive mode with menu."""
        while True:
            print("\n" + "="*50)
            print("SOCIAL MEDIA BOT - MAIN LAUNCHER")
            print("="*50)
            print(f"Status: {'RUNNING' if self.running else 'STOPPED'}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # Show quick status
            try:
                all_tasks = self.scheduler.get_all_tasks_status()
                running_tasks = sum(1 for task in all_tasks if task["status"] == "running")
                enabled_tasks = sum(1 for task in all_tasks if task["enabled"])
                
                print(f"Tasks: {running_tasks} running, {enabled_tasks} enabled")
                
                # Show next few scheduled tasks
                upcoming = self.scheduler.get_next_scheduled_tasks(3)
                if upcoming:
                    print("Next scheduled:")
                    for task in upcoming:
                        next_run = task["next_run"].strftime("%H:%M")
                        print(f"  {next_run} - {task['name'][:30]} ({task['platform'] or 'system'})")
                
            except Exception as e:
                print(f"Status error: {e}")
            
            print("\nOPTIONS:")
            if not self.running:
                print("1. Start Automation")
            else:
                print("1. Stop Automation")
            
            print("2. Setup Default Schedules")
            print("3. Open Automation Dashboard")
            print("4. Open Monitoring Dashboard") 
            print("5. Force Run Task")
            print("6. View System Status")
            print("0. Exit")
            
            try:
                choice = input("\nSelect option (0-6): ").strip()
                
                if choice == "0":
                    if self.running:
                        self.stop()
                    break
                elif choice == "1":
                    if not self.running:
                        self.start()
                    else:
                        self.stop()
                elif choice == "2":
                    self.setup_default_schedules()
                    input("Press Enter to continue...")
                elif choice == "3":
                    self._launch_dashboard("automation")
                elif choice == "4":
                    self._launch_dashboard("monitoring")
                elif choice == "5":
                    self._force_run_task()
                elif choice == "6":
                    self._show_system_status()
                    input("Press Enter to continue...")
                else:
                    print("Invalid option")
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                if self.running:
                    self.stop()
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(2)

    def _launch_dashboard(self, dashboard_type):
        """Launch dashboard in subprocess."""
        try:
            import subprocess
            
            if dashboard_type == "automation":
                script = "automation_dashboard.py"
            else:
                script = "monitoring_dashboard.py"
            
            print(f"Launching {dashboard_type} dashboard...")
            subprocess.Popen([sys.executable, script], cwd=str(Path(__file__).parent))
            
        except Exception as e:
            print(f"Error launching dashboard: {e}")
            input("Press Enter to continue...")

    def _force_run_task(self):
        """Force run a specific task."""
        try:
            all_tasks = self.scheduler.get_all_tasks_status()
            
            print("\nAvailable tasks:")
            for i, task in enumerate(all_tasks[:10]):
                print(f"{i+1}. {task['name']} ({task['platform'] or 'system'}) - {task['status']}")
            
            if len(all_tasks) > 10:
                print(f"... and {len(all_tasks) - 10} more tasks")
            
            choice = input("\nEnter task number to run (or Enter to cancel): ").strip()
            
            if choice and choice.isdigit():
                task_index = int(choice) - 1
                if 0 <= task_index < len(all_tasks):
                    task = all_tasks[task_index]
                    success = self.scheduler.force_run_task(task["id"])
                    if success:
                        print(f"Task '{task['name']}' started successfully")
                    else:
                        print(f"Failed to start task '{task['name']}'")
                else:
                    print("Invalid task number")
            
        except Exception as e:
            print(f"Error running task: {e}")
        
        input("Press Enter to continue...")

    def _show_system_status(self):
        """Show detailed system status."""
        try:
            print("\n" + "="*60)
            print("SYSTEM STATUS")
            print("="*60)
            
            # Scheduler status
            all_tasks = self.scheduler.get_all_tasks_status()
            running_tasks = sum(1 for task in all_tasks if task["status"] == "running")
            enabled_tasks = sum(1 for task in all_tasks if task["enabled"])
            
            print(f"Scheduler: {enabled_tasks} enabled, {running_tasks} running")
            
            # Content status
            for platform in ["twitter", "mastodon", "bluesky"]:
                stats = self.coordinator.get_platform_statistics(platform)
                print(f"{platform.title()}: {stats['total_pending']} pending, "
                      f"{stats['posts_last_hour']}/hour")
            
            # Content pools
            pool_stats = self.rotator.get_content_statistics()
            print(f"Content: {pool_stats['total_available_content']} items in pools")
            
            # System health
            system_status = self.monitoring.get_system_status()
            print(f"Health: {system_status.get('overall_status', 'unknown')}")
            
        except Exception as e:
            print(f"Error getting system status: {e}")

    def start(self):
        """Start the automation system."""
        if self.running:
            self.logger.warning("Bot is already running")
            return
        
        try:
            self.logger.info("Starting social media bot automation...")
            
            # Start scheduler
            self.scheduler.start()
            
            # Setup default schedules if in auto mode
            if self.config_mode == "auto":
                self.setup_default_schedules()
            
            self.running = True
            self.logger.info("Social media bot started successfully")
            log_event("info", "Bot automation started", "main")
            
            print("✅ Automation started successfully!")
            
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            print(f"❌ Failed to start: {e}")

    def stop(self):
        """Stop the automation system."""
        if not self.running:
            self.logger.warning("Bot is not running")
            return
        
        try:
            self.logger.info("Stopping social media bot...")
            
            # Stop scheduler
            self.scheduler.stop()
            
            self.running = False
            self.logger.info("Social media bot stopped")
            log_event("info", "Bot automation stopped", "main")
            
            print("✅ Automation stopped successfully!")
            
        except Exception as e:
            self.logger.error(f"Error stopping bot: {e}")
            print(f"❌ Error stopping: {e}")

    def run_continuous(self):
        """Run in continuous mode (for background execution)."""
        self.start()
        
        try:
            print("Social media bot running in background...")
            print("Press Ctrl+C to stop")
            
            while self.running:
                time.sleep(60)  # Check every minute
                
                # Perform periodic maintenance
                if datetime.now().minute == 0:  # Every hour
                    try:
                        # Refresh content pools
                        refreshed = self.rotator.refresh_content_pools()
                        if refreshed > 0:
                            self.logger.info(f"Refreshed {refreshed} content pools")
                    except Exception as e:
                        self.logger.error(f"Error in periodic maintenance: {e}")
        
        except KeyboardInterrupt:
            print("\nReceived interrupt signal")
        finally:
            self.stop()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Social Media Bot - Advanced Automation System")
    parser.add_argument("--mode", choices=["interactive", "background", "dashboard"], 
                       default="interactive", help="Launch mode")
    parser.add_argument("--config", choices=["auto", "manual"], 
                       default="auto", help="Configuration mode")
    parser.add_argument("--setup", action="store_true", help="Setup default schedules only")
    
    args = parser.parse_args()
    
    try:
        bot = SocialMediaBot(config_mode=args.config)
        
        if args.setup:
            print("Setting up default schedules...")
            success = bot.setup_default_schedules()
            if success:
                print("✅ Default schedules configured successfully!")
            else:
                print("❌ Failed to setup schedules")
            return
        
        if args.mode == "interactive":
            bot.start_interactive()
        elif args.mode == "background":
            bot.run_continuous()
        elif args.mode == "dashboard":
            # Launch automation dashboard directly
            from automation_dashboard import AutomationDashboard
            dashboard = AutomationDashboard()
            dashboard.run()
    
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()