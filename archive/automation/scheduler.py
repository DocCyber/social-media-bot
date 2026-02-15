#!/usr/bin/env python3
"""
Advanced Unified Automation Scheduler
Phase 6: Intelligent scheduling system with cross-platform coordination.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Union
import threading
import time
from dataclasses import dataclass, asdict
from croniter import croniter
import pytz

sys.path.append(str(Path(__file__).parent.parent))

from utils.config_manager import ConfigManager
from utils.monitoring import get_monitoring, log_event, record_metric
from utils.date_aware_logger import get_enhanced_logger

class TaskPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ScheduledTask:
    id: str
    name: str
    description: str
    function: str
    module: str
    cron_schedule: str
    priority: TaskPriority
    platform: Optional[str] = None
    enabled: bool = True
    max_runtime: int = 300
    retry_count: int = 0
    max_retries: int = 3
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.next_run is None:
            self._calculate_next_run()

    def _calculate_next_run(self):
        try:
            cron = croniter(self.cron_schedule, datetime.now())
            self.next_run = cron.get_next(datetime)
        except Exception as e:
            logging.error(f"Invalid cron schedule for task {self.id}: {e}")
            self.enabled = False

class AutomationScheduler:
    def __init__(self, config_path: Optional[str] = None, setup_tasks: bool = False):
        self.config_manager = ConfigManager()
        self.config_manager.load_all_configs()
        
        self.monitoring = get_monitoring(auto_start_background=False)
        self.logger = get_enhanced_logger("automation_scheduler", enable_background_markers=False)
        
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, threading.Thread] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()
        
        self.timezone = pytz.timezone(
            self.config_manager.get_nested_value("scheduling.timezone", "UTC")
        )
        
        # Only setup tasks if explicitly requested (to avoid hangs during init)
        if setup_tasks:
            self._setup_default_tasks()
            self._load_custom_tasks()
        
        self.logger.info("Automation scheduler initialized")

    def _setup_default_tasks(self):
        """Setup default tasks based on configuration."""
        config = self.config_manager.unified_config
        
        if not config:
            self.logger.warning("No configuration loaded")
            return
        
        # Content posting tasks
        posting_freq = config.get("scheduling", {}).get("posting_frequency", {})
        
        for platform, cron_schedule in posting_freq.items():
            if config.get("platforms", {}).get(platform, {}).get("enabled", False):
                self.add_task(ScheduledTask(
                    id=f"post_content_{platform}",
                    name=f"Post Content - {platform.title()}",
                    description=f"Automated content posting for {platform}",
                    function="post_content",
                    module=f"platforms.{platform}_platform",
                    cron_schedule=cron_schedule,
                    priority=TaskPriority.NORMAL,
                    platform=platform,
                    metadata={"type": "content_posting"}
                ))
        
        # Interactive tasks
        interactive_freq = config.get("scheduling", {}).get("interactive_frequency", "*/15 * * * *")
        
        for platform in ["twitter", "mastodon", "bluesky"]:
            if config.get("platforms", {}).get(platform, {}).get("enabled", False):
                self.add_task(ScheduledTask(
                    id=f"process_interactions_{platform}",
                    name=f"Process Interactions - {platform.title()}",
                    description=f"Process notifications and interactions for {platform}",
                    function="process_interactions",
                    module=f"platforms.{platform}_platform",
                    cron_schedule=interactive_freq,
                    priority=TaskPriority.HIGH,
                    platform=platform,
                    metadata={"type": "interactive"}
                ))
        
        # Maintenance tasks
        maintenance_freq = config.get("scheduling", {}).get("maintenance_frequency", "0 2 * * *")
        
        self.add_task(ScheduledTask(
            id="system_maintenance",
            name="System Maintenance",
            description="Daily system maintenance and cleanup",
            function="run_maintenance",
            module="automation.maintenance",
            cron_schedule=maintenance_freq,
            priority=TaskPriority.LOW,
            metadata={"type": "maintenance"}
        ))
        
        # Health monitoring task
        self.add_task(ScheduledTask(
            id="health_monitoring",
            name="Health Monitoring",
            description="Periodic system health checks",
            function="run_health_checks",
            module="utils.health_checks",
            cron_schedule="*/30 * * * *",  # Every 30 minutes
            priority=TaskPriority.HIGH,
            metadata={"type": "monitoring"}
        ))

    def _load_custom_tasks(self):
        """Load custom tasks from configuration file."""
        tasks_file = Path(__file__).parent / "tasks.json"
        
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    custom_tasks = json.load(f)
                    
                for task_data in custom_tasks.get('tasks', []):
                    task = ScheduledTask(**task_data)
                    self.add_task(task)
                    
                self.logger.info(f"Loaded {len(custom_tasks.get('tasks', []))} custom tasks")
                
            except Exception as e:
                self.logger.error(f"Error loading custom tasks: {e}")

    def add_task(self, task: ScheduledTask):
        """Add a task to the scheduler."""
        self.tasks[task.id] = task
        self.logger.debug(f"Added task: {task.name} (ID: {task.id})")
        record_metric("tasks_added", 1, "scheduler")

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the scheduler."""
        if task_id in self.tasks:
            if task_id in self.running_tasks:
                self.logger.warning(f"Cannot remove running task: {task_id}")
                return False
            
            del self.tasks[task_id]
            self.logger.info(f"Removed task: {task_id}")
            record_metric("tasks_removed", 1, "scheduler")
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            self.tasks[task_id]._calculate_next_run()
            self.logger.info(f"Enabled task: {task_id}")
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            self.logger.info(f"Disabled task: {task_id}")
            return True
        return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a task."""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "id": task.id,
            "name": task.name,
            "status": task.status.value,
            "enabled": task.enabled,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "retry_count": task.retry_count,
            "platform": task.platform,
            "priority": task.priority.value
        }

    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """Get status for all tasks."""
        return [self.get_task_status(task_id) for task_id in self.tasks.keys()]

    def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task."""
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting task: {task.name}")
            task.status = TaskStatus.RUNNING
            task.last_run = start_time
            
            record_metric("task_started", 1, "scheduler", {"task_id": task.id})
            
            # Import and execute the task function
            module_path = task.module
            function_name = task.function
            
            # Dynamic import
            if module_path.startswith("platforms."):
                sys.path.append(str(Path(__file__).parent.parent / "platforms"))
            
            module = __import__(module_path, fromlist=[function_name])
            task_function = getattr(module, function_name)
            
            # Execute with timeout
            if asyncio.iscoroutinefunction(task_function):
                asyncio.run(task_function())
            else:
                task_function()
            
            # Success
            task.status = TaskStatus.COMPLETED
            task.retry_count = 0
            execution_time = (datetime.now() - start_time).total_seconds()
            
            record_metric("task_completed", 1, "scheduler", {"task_id": task.id})
            record_metric("task_execution_time", execution_time, "scheduler", {"task_id": task.id})
            
            self.logger.success(f"Task completed: {task.name} ({execution_time:.2f}s)")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.retry_count += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            
            self.logger.error(f"Task failed: {task.name} - {str(e)}")
            log_event("error", f"Task {task.name} failed: {str(e)}", "scheduler")
            
            record_metric("task_failed", 1, "scheduler", {"task_id": task.id})
            
            # Retry logic
            if task.retry_count < task.max_retries:
                retry_delay = min(60 * (2 ** task.retry_count), 3600)  # Exponential backoff
                task.next_run = datetime.now() + timedelta(seconds=retry_delay)
                self.logger.info(f"Task {task.name} will retry in {retry_delay}s")
            else:
                self.logger.error(f"Task {task.name} exceeded max retries")
                task.enabled = False
        
        finally:
            # Calculate next run for successful tasks
            if task.status == TaskStatus.COMPLETED and task.enabled:
                task._calculate_next_run()
            
            # Remove from running tasks
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]

    def _scheduler_loop(self):
        """Main scheduler loop."""
        self.logger.info("Scheduler loop started")
        
        while not self.shutdown_event.is_set():
            try:
                current_time = datetime.now()
                
                # Check for tasks that need to run
                for task in self.tasks.values():
                    if not task.enabled or task.status == TaskStatus.RUNNING:
                        continue
                    
                    if task.next_run and task.next_run <= current_time:
                        if task.id not in self.running_tasks:
                            # Start task in separate thread
                            thread = threading.Thread(
                                target=self._execute_task,
                                args=(task,),
                                name=f"Task-{task.id}"
                            )
                            
                            self.running_tasks[task.id] = thread
                            thread.start()
                            
                            self.logger.debug(f"Started task thread: {task.name}")
                
                # Clean up completed threads
                completed_threads = []
                for task_id, thread in self.running_tasks.items():
                    if not thread.is_alive():
                        completed_threads.append(task_id)
                
                for task_id in completed_threads:
                    del self.running_tasks[task_id]
                
                # Log scheduler status periodically
                if current_time.minute % 10 == 0 and current_time.second < 10:
                    active_tasks = len(self.running_tasks)
                    total_tasks = len(self.tasks)
                    enabled_tasks = sum(1 for t in self.tasks.values() if t.enabled)
                    
                    self.logger.debug(f"Scheduler status: {active_tasks} running, {enabled_tasks}/{total_tasks} enabled")
                    record_metric("scheduler_active_tasks", active_tasks, "scheduler")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(30)  # Wait longer on errors

    def setup_tasks(self):
        """Setup default and custom tasks if not already done."""
        if not self.tasks:  # Only setup if no tasks exist
            self._setup_default_tasks()
            self._load_custom_tasks()
            self.logger.info(f"Set up {len(self.tasks)} tasks")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.logger.warning("Scheduler is already running")
            return
        
        # Setup tasks before starting if not already done
        self.setup_tasks()
        
        self.shutdown_event.clear()
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="AutomationScheduler"
        )
        self.scheduler_thread.start()
        
        self.logger.info("Automation scheduler started")
        # Temporarily disable log_event to avoid potential issues
        # log_event("info", "Automation scheduler started", "scheduler")

    def stop(self):
        """Stop the scheduler."""
        self.logger.info("Stopping automation scheduler...")
        self.shutdown_event.set()
        
        # Wait for scheduler thread to finish
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=30)
        
        # Wait for running tasks to complete or force stop
        for task_id, thread in self.running_tasks.items():
            if thread.is_alive():
                self.logger.warning(f"Force stopping task: {task_id}")
                thread.join(timeout=10)
        
        self.logger.info("Automation scheduler stopped")
        log_event("info", "Automation scheduler stopped", "scheduler")

    def force_run_task(self, task_id: str) -> bool:
        """Force run a task immediately."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.id in self.running_tasks:
            self.logger.warning(f"Task {task_id} is already running")
            return False
        
        # Run in separate thread
        thread = threading.Thread(
            target=self._execute_task,
            args=(task,),
            name=f"ForceTask-{task.id}"
        )
        
        self.running_tasks[task.id] = thread
        thread.start()
        
        self.logger.info(f"Force started task: {task.name}")
        return True

    def get_next_scheduled_tasks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the next scheduled tasks."""
        upcoming_tasks = []
        
        for task in self.tasks.values():
            if task.enabled and task.next_run:
                upcoming_tasks.append({
                    "id": task.id,
                    "name": task.name,
                    "platform": task.platform,
                    "next_run": task.next_run,
                    "priority": task.priority.value
                })
        
        # Sort by next run time and priority
        upcoming_tasks.sort(key=lambda x: (x["next_run"], -x["priority"]))
        
        return upcoming_tasks[:limit]

    def save_tasks_config(self, file_path: Optional[str] = None):
        """Save current tasks configuration to file."""
        if not file_path:
            file_path = Path(__file__).parent / "tasks.json"
        
        tasks_data = {
            "tasks": [asdict(task) for task in self.tasks.values()],
            "generated_at": datetime.now().isoformat()
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, indent=2, default=str)
            
            self.logger.info(f"Saved tasks configuration to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving tasks configuration: {e}")

def get_scheduler() -> AutomationScheduler:
    """Get the global automation scheduler instance."""
    if not hasattr(get_scheduler, '_instance'):
        get_scheduler._instance = AutomationScheduler()
    return get_scheduler._instance