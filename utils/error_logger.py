"""
Error Logger Utility
Consolidates the duplicate error logging functions found in:
- tweet/tweet.py
- toot/toot.py
- bsky/bsky.py  
- advertisment/tweetad.py

Provides both console output (for real-time monitoring) and structured file logging.
Compatible with Python 3.10+ including 3.13.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union


class ErrorLogger:
    """
    Dual-output error logger that maintains console visibility while adding 
    structured file logging for debugging and history.
    """
    
    def __init__(
        self, 
        module_name: str,
        log_file: Optional[Union[str, Path]] = None,
        base_path: Optional[Union[str, Path]] = None
    ):
        """
        Initialize error logger for a specific module.
        
        Args:
            module_name: Name of the module (e.g., 'twitter', 'bluesky')
            log_file: Path to log file. Defaults to 'corrupted_lines.txt' for compatibility
            base_path: Base directory for log files. Defaults to jokes root directory
        """
        self.module_name = module_name
        
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        if log_file is None:
            # Maintain compatibility with existing corrupted_lines.txt
            self.log_file = self.base_path / "corrupted_lines.txt"
        else:
            self.log_file = self.base_path / log_file
        
        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log_corrupted_line(
        self, 
        filename: Union[str, Path], 
        line_info: str, 
        error: Union[str, Exception],
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a corrupted line error (maintains compatibility with existing code).
        
        Args:
            filename: File where error occurred
            line_info: Line number or description
            error: Error message or exception
            details: Additional context information
        """
        error_str = str(error)
        timestamp = datetime.now().isoformat()
        
        # Console output (matches current format for visibility)
        console_msg = f"[{timestamp}] ERROR in {self.module_name}: File: {filename}, Line: {line_info}, Error: {error_str}"
        print(console_msg)
        
        # File output (structured for debugging)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                # Old format line for compatibility
                f.write(f"File: {filename}, Error Line: {line_info}, Error: {error_str}\n")
        except Exception as log_error:
            print(f"[{timestamp}] LOGGING ERROR: Could not write to {self.log_file}: {log_error}")
    
    def info(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log informational message (console only for real-time monitoring)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console_msg = f"[{timestamp}] {self.module_name}: {message}"
        print(console_msg)
    
    def success(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log success message with visual indicator."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console_msg = f"[{timestamp}] {self.module_name}: {message} [OK]"
        print(console_msg)
    
    def warning(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> None:
        """Log warning message (console + structured file)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Console output
        console_msg = f"[{timestamp}] WARNING in {self.module_name}: {message}"
        print(console_msg)
        
        # Structured file logging (for warnings and above)
        self._write_structured_log("WARNING", message, details, context)
    
    def error(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
        exception: Optional[Exception] = None
    ) -> None:
        """Log error message (console + structured file)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Console output
        console_msg = f"[{timestamp}] ERROR in {self.module_name}: {message}"
        if exception:
            console_msg += f" - {str(exception)}"
        print(console_msg)
        
        # Enhanced details for file logging
        if details is None:
            details = {}
        if exception:
            details['exception_type'] = type(exception).__name__
            details['exception_message'] = str(exception)
        
        # Structured file logging
        self._write_structured_log("ERROR", message, details, context)
    
    def critical(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> None:
        """Log critical error (console + structured file)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Console output with emphasis
        console_msg = f"[{timestamp}] CRITICAL ERROR in {self.module_name}: {message}"
        print(console_msg)
        
        # Structured file logging
        self._write_structured_log("CRITICAL", message, details, context)
    
    def _write_structured_log(
        self, 
        level: str, 
        message: str,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> None:
        """Write structured log entry to file."""
        # Create structured log directory if it doesn't exist
        structured_log_file = self.base_path / "logs" / "bot.log"
        structured_log_file.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "module": self.module_name,
            "message": message
        }
        
        if details:
            log_entry["details"] = details
        if context:
            log_entry["context"] = context
        
        try:
            with open(structured_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as log_error:
            # Fallback to console if structured logging fails
            print(f"LOGGING ERROR: Could not write structured log: {log_error}")


# Factory function for easy module-specific logger creation
def get_logger(module_name: str, log_file: Optional[str] = None) -> ErrorLogger:
    """
    Create an error logger for a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'twitter', 'bluesky')
        log_file: Optional custom log file path
        
    Returns:
        ErrorLogger instance configured for the module
    """
    return ErrorLogger(module_name, log_file)


# Backward compatibility function
def log_corrupted_line(filename: str, line: str, error: Union[str, Exception]) -> None:
    """
    Backward compatibility function that matches the existing signature.
    Creates a generic logger for legacy code.
    """
    logger = ErrorLogger("legacy")
    logger.log_corrupted_line(filename, line, error)


# Example usage and testing
if __name__ == "__main__":
    # Test the logger
    print("Testing ErrorLogger...")
    
    # Create loggers for different modules
    twitter_logger = get_logger("twitter")
    bluesky_logger = get_logger("bluesky")
    
    # Test different log levels
    twitter_logger.info("Starting Twitter posting process")
    twitter_logger.success("Posted tweet successfully")
    twitter_logger.warning("Rate limit approaching", details={"remaining": 10})
    twitter_logger.error("Authentication failed", details={"code": 401}, exception=Exception("Token expired"))
    
    bluesky_logger.info("Processing BlueSky notifications")
    bluesky_logger.log_corrupted_line("jokes.csv", "line 123", "Invalid UTF-8 sequence")
    
    # Test backward compatibility
    log_corrupted_line("test.csv", "line 456", "Test error")
    
    print("\nLog files created:")
    print("- corrupted_lines.txt (compatibility)")
    print("- logs/bot.log (structured)")
    print("\nCheck console output vs file contents to verify dual logging.")