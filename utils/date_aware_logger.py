"""
Date-Aware Enhanced Logging System
Provides date-coded logging with automatic date markers and daily file rotation.
Inserts date markers when no logging occurs to maintain continuity.

Compatible with Python 3.10+ including 3.13.
"""

import os
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Union
from logging.handlers import RotatingFileHandler


class DateMarkerHandler(logging.Handler):
    """Custom handler that inserts date markers and manages daily files."""
    
    def __init__(self, base_path: Union[str, Path], max_file_size: int = 10 * 1024 * 1024):
        super().__init__()
        self.base_path = Path(base_path)
        self.logs_dir = self.base_path / "monitoring" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_file_size = max_file_size
        self.current_date = None
        self.current_file = None
        self.last_log_time = datetime.now()
        self.lock = threading.Lock()
        
        # Start background thread for date markers
        self.marker_thread = threading.Thread(target=self._date_marker_loop, daemon=True)
        self.marker_thread.start()
    
    def _get_log_file_path(self, date: datetime) -> Path:
        """Get log file path for a specific date."""
        date_str = date.strftime('%Y%m%d')
        return self.logs_dir / f"bot_activity_{date_str}.log"
    
    def _ensure_current_file(self, log_date: datetime):
        """Ensure we have the correct file open for the current date."""
        date_str = log_date.strftime('%Y-%m-%d')
        
        if self.current_date != date_str:
            # Close current file if open
            if self.current_file:
                self.current_file.close()
            
            # Open new file
            log_file = self._get_log_file_path(log_date)
            self.current_file = open(log_file, 'a', encoding='utf-8')
            
            # Write date header if file is new or first entry of day
            if log_file.stat().st_size == 0 or self.current_date is None:
                self._write_date_header(log_date)
            elif self.current_date != date_str:
                self._write_date_transition(log_date)
            
            self.current_date = date_str
    
    def _write_date_header(self, log_date: datetime):
        """Write date header for new files."""
        header_lines = [
            "=" * 80,
            f"SOCIAL MEDIA BOT - ACTIVITY LOG",
            f"Date: {log_date.strftime('%A, %B %d, %Y')}",
            f"Log Started: {log_date.strftime('%H:%M:%S')}",
            "=" * 80,
            ""
        ]
        for line in header_lines:
            self.current_file.write(line + "\\n")
        self.current_file.flush()
    
    def _write_date_transition(self, log_date: datetime):
        """Write transition marker when date changes."""
        transition_lines = [
            "",
            "-" * 80,
            f"DATE CHANGED TO: {log_date.strftime('%A, %B %d, %Y')} at {log_date.strftime('%H:%M:%S')}",
            "-" * 80,
            ""
        ]
        for line in transition_lines:
            self.current_file.write(line + "\\n")
        self.current_file.flush()
    
    def _write_inactivity_marker(self):
        """Write inactivity marker when no logs for extended period."""
        now = datetime.now()
        marker_lines = [
            "",
            f"[{now.strftime('%H:%M:%S')}] --- NO ACTIVITY SINCE {self.last_log_time.strftime('%H:%M:%S')} ---",
            f"[{now.strftime('%H:%M:%S')}] System Status: Running (no events to log)",
            ""
        ]
        
        with self.lock:
            self._ensure_current_file(now)
            for line in marker_lines:
                self.current_file.write(line + "\\n")
            self.current_file.flush()
    
    def _date_marker_loop(self):
        """Background thread that writes date markers during inactivity."""
        while True:
            try:
                time.sleep(300)  # Check every 5 minutes
                
                now = datetime.now()
                time_since_last_log = now - self.last_log_time
                
                # Write inactivity marker if no logs for 30 minutes
                if time_since_last_log > timedelta(minutes=30):
                    self._write_inactivity_marker()
                    self.last_log_time = now
                
                # Write hourly marker during quiet periods
                if (time_since_last_log > timedelta(hours=1) and 
                    now.minute < 5):  # Only on the hour
                    
                    with self.lock:
                        self._ensure_current_file(now)
                        hourly_marker = f"[{now.strftime('%H:00:00')}] --- HOURLY STATUS: Bot operational, waiting for events ---"
                        self.current_file.write(hourly_marker + "\\n\\n")
                        self.current_file.flush()
                        self.last_log_time = now
                
            except Exception as e:
                # Don't let the marker thread crash
                print(f"Date marker thread error: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def emit(self, record):
        """Emit a log record."""
        with self.lock:
            try:
                now = datetime.now()
                self._ensure_current_file(now)
                
                # Format the log entry
                timestamp = now.strftime('%H:%M:%S')
                level = record.levelname
                module = getattr(record, 'module_name', record.name)
                message = record.getMessage()
                
                # Create formatted log entry
                log_entry = f"[{timestamp}] {level:8} {module}: {message}"
                
                # Add exception info if present
                if record.exc_info:
                    log_entry += "\\n" + self.format(record)
                
                # Write to file
                self.current_file.write(log_entry + "\\n")
                self.current_file.flush()
                
                # Update last log time
                self.last_log_time = now
                
                # Check file size and rotate if needed
                if self.current_file.tell() > self.max_file_size:
                    self._rotate_file(now)
                    
            except Exception as e:
                # Don't crash the logger
                print(f"Logging error: {e}")
    
    def _rotate_file(self, log_date: datetime):
        """Rotate log file when it gets too large."""
        if self.current_file:
            # Write rotation marker
            rotation_marker = f"\\n[{log_date.strftime('%H:%M:%S')}] --- LOG FILE ROTATED (size limit reached) ---\\n"
            self.current_file.write(rotation_marker)
            self.current_file.close()
            
            # Rename current file with timestamp
            old_file = self._get_log_file_path(log_date)
            timestamp_suffix = log_date.strftime('%H%M%S')
            rotated_file = old_file.with_name(f"{old_file.stem}_{timestamp_suffix}.log")
            old_file.rename(rotated_file)
            
            # Create new file
            self.current_file = open(old_file, 'a', encoding='utf-8')
            rotation_header = f"[{log_date.strftime('%H:%M:%S')}] --- NEW LOG FILE (rotated from {rotated_file.name}) ---\\n\\n"
            self.current_file.write(rotation_header)
            self.current_file.flush()
    
    def close(self):
        """Close the handler."""
        if self.current_file:
            # Write closing marker
            close_time = datetime.now()
            closing_marker = f"\\n[{close_time.strftime('%H:%M:%S')}] --- LOG SESSION ENDED ---\\n"
            self.current_file.write(closing_marker)
            self.current_file.close()
        super().close()


class EnhancedBotLogger:
    """Enhanced logger with date awareness and activity tracking."""
    
    def __init__(self, module_name: str, base_path: Optional[Union[str, Path]] = None):
        """
        Initialize enhanced bot logger.
        
        Args:
            module_name: Name of the module (e.g., 'bluesky', 'twitter')
            base_path: Base directory for logs
        """
        self.module_name = module_name
        
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        # Create logger
        self.logger = logging.getLogger(f'bot.{module_name}')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers."""
        # Date-aware file handler
        date_handler = DateMarkerHandler(self.base_path)
        date_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(date_handler)
        
        # Console handler for immediate feedback
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(asctime)s] %(name)s %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
        
        # Structured JSON handler for monitoring
        json_handler = self._create_json_handler()
        if json_handler:
            self.logger.addHandler(json_handler)
    
    def _create_json_handler(self):
        """Create JSON structured logging handler."""
        try:
            json_logs_dir = self.base_path / "monitoring" / "logs"
            json_logs_dir.mkdir(parents=True, exist_ok=True)
            
            json_file = json_logs_dir / f"structured_{datetime.now().strftime('%Y%m%d')}.jsonl"
            
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_entry = {
                        'timestamp': datetime.fromtimestamp(record.created).isoformat(),
                        'level': record.levelname,
                        'module': getattr(record, 'module_name', record.name),
                        'message': record.getMessage(),
                        'function': record.funcName,
                        'line': record.lineno
                    }
                    
                    if record.exc_info:
                        log_entry['exception'] = self.formatException(record.exc_info)
                    
                    return json.dumps(log_entry)
            
            json_handler = logging.FileHandler(json_file, encoding='utf-8')
            json_handler.setFormatter(JSONFormatter())
            json_handler.setLevel(logging.DEBUG)
            
            return json_handler
            
        except Exception as e:
            print(f"Failed to create JSON handler: {e}")
            return None
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra={'module_name': self.module_name, **kwargs})
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self.logger.info(f"{message} [OK]", extra={'module_name': self.module_name, **kwargs})
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra={'module_name': self.module_name, **kwargs})
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log error message."""
        if exception:
            self.logger.error(message, exc_info=exception, extra={'module_name': self.module_name, **kwargs})
        else:
            self.logger.error(message, extra={'module_name': self.module_name, **kwargs})
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra={'module_name': self.module_name, **kwargs})


def get_enhanced_logger(module_name: str) -> EnhancedBotLogger:
    """Get enhanced logger instance for a module."""
    return EnhancedBotLogger(module_name)


# Example usage and testing
if __name__ == "__main__":
    # Test the enhanced logger
    logger = get_enhanced_logger("test")
    
    logger.info("Enhanced logging system started")
    logger.success("Test successful operation")
    logger.warning("Test warning message") 
    logger.error("Test error message")
    logger.debug("Test debug message")
    
    print("Enhanced logging test completed. Check monitoring/logs/ directory for output.")
    
    # Test inactivity marker (short interval for testing)
    print("Waiting 10 seconds to test inactivity detection...")
    time.sleep(10)
    
    logger.info("Activity resumed after pause")
    print("Test completed.")