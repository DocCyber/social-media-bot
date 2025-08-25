#!/usr/bin/env python3
"""
Bot Runner with Comprehensive Error Capture
Wraps main.py with extensive logging and error handling to debug startup issues.
"""

import sys
import os
import traceback
import threading
import time
from datetime import datetime
from pathlib import Path
import logging
import signal

# Add project path
sys.path.append(str(Path(__file__).parent))

# Setup comprehensive logging immediately
def setup_debug_logging():
    """Setup detailed logging to capture all startup issues."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent / "debug_logs"
    log_dir.mkdir(exist_ok=True)
    
    # Create detailed log file
    log_file = log_dir / f"bot_startup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure logging with both file and console
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("bot_runner")
    logger.info(f"Debug logging started: {log_file}")
    return logger

def monitor_threads():
    """Monitor and log all running threads."""
    logger = logging.getLogger("thread_monitor")
    
    while True:
        try:
            active_threads = threading.enumerate()
            thread_info = []
            
            for thread in active_threads:
                thread_info.append(f"{thread.name} (daemon={thread.daemon}, alive={thread.is_alive()})")
            
            logger.debug(f"Active threads ({len(active_threads)}): {', '.join(thread_info)}")
            
            # Check for non-daemon threads that might prevent exit
            non_daemon_threads = [t for t in active_threads if not t.daemon and t != threading.current_thread()]
            if non_daemon_threads:
                logger.warning(f"Non-daemon threads preventing exit: {[t.name for t in non_daemon_threads]}")
            
            time.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Thread monitor error: {e}")
            time.sleep(30)

def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger = logging.getLogger("signal_handler")
    logger.info(f"Received signal {signum}, forcing shutdown...")
    
    # Log all active threads before exit
    active_threads = threading.enumerate()
    logger.info(f"Active threads at shutdown: {[t.name for t in active_threads]}")
    
    # Force exit
    os._exit(1)

def run_with_timeout(func, timeout_seconds=60):
    """Run function with timeout to detect hangs."""
    logger = logging.getLogger("timeout_runner")
    
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target, name="MainFunction")
    thread.daemon = True
    thread.start()
    
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"Function timed out after {timeout_seconds} seconds!")
        logger.error("Function is still running - possible hang detected")
        return None, "TIMEOUT"
    
    if exception[0]:
        return None, exception[0]
    
    return result[0], None

def test_individual_components():
    """Test individual components to isolate the hanging component."""
    logger = logging.getLogger("component_tester")
    
    logger.info("Testing individual components...")
    
    # Test 1: Basic imports
    try:
        logger.info("Testing basic imports...")
        from utils.config_manager import ConfigManager
        logger.info("✓ ConfigManager import OK")
        
        from automation.scheduler import get_scheduler
        logger.info("✓ Scheduler import OK")
        
        from utils.monitoring import get_monitoring
        logger.info("✓ Monitoring import OK")
        
        logger.info("All imports successful")
        
    except Exception as e:
        logger.error(f"Import test failed: {e}")
        logger.error(traceback.format_exc())
        return False
    
    # Test 2: Config loading
    try:
        logger.info("Testing config loading...")
        config_manager = ConfigManager()
        
        logger.info("Config manager created, loading configs...")
        config_manager.load_all_configs()
        
        logger.info("✓ Config loading OK")
        
    except Exception as e:
        logger.error(f"Config test failed: {e}")
        logger.error(traceback.format_exc())
        return False
    
    # Test 3: Component initialization (with timeout)
    logger.info("Testing component initialization with timeout...")
    
    def test_scheduler():
        logger.info("Initializing scheduler...")
        scheduler = get_scheduler()
        logger.info("Scheduler initialized")
        return scheduler
    
    def test_monitoring():
        logger.info("Initializing monitoring...")
        monitoring = get_monitoring()
        logger.info("Monitoring initialized")
        return monitoring
    
    # Test scheduler with timeout
    result, error = run_with_timeout(test_scheduler, 30)
    if error == "TIMEOUT":
        logger.error("SCHEDULER INITIALIZATION TIMED OUT - This is likely the hang source!")
        return False
    elif error:
        logger.error(f"Scheduler test failed: {error}")
        return False
    
    # Test monitoring with timeout
    result, error = run_with_timeout(test_monitoring, 30)
    if error == "TIMEOUT":
        logger.error("MONITORING INITIALIZATION TIMED OUT - This is likely the hang source!")
        return False
    elif error:
        logger.error(f"Monitoring test failed: {error}")
        return False
    
    logger.info("✓ All component tests passed")
    return True

def run_main_bot():
    """Run the main bot with comprehensive error handling."""
    logger = logging.getLogger("main_runner")
    
    try:
        logger.info("Starting main bot import...")
        
        # Import with timeout to catch import hangs
        def import_main():
            from main import SocialMediaBot
            logger.info("✓ Main module imported successfully")
            return SocialMediaBot
        
        SocialMediaBot, error = run_with_timeout(import_main, 30)
        if error == "TIMEOUT":
            logger.error("MAIN MODULE IMPORT TIMED OUT!")
            return False
        elif error:
            logger.error(f"Main import failed: {error}")
            return False
        
        # Initialize bot with timeout
        def init_bot():
            logger.info("Initializing SocialMediaBot...")
            bot = SocialMediaBot(config_mode="manual")  # Avoid auto-setup
            logger.info("✓ Bot initialized successfully")
            return bot
        
        bot, error = run_with_timeout(init_bot, 60)
        if error == "TIMEOUT":
            logger.error("BOT INITIALIZATION TIMED OUT!")
            return False
        elif error:
            logger.error(f"Bot initialization failed: {error}")
            logger.error(traceback.format_exc())
            return False
        
        logger.info("🎉 Bot startup completed successfully!")
        
        # Try to run interactive mode with timeout
        logger.info("Starting interactive mode...")
        
        def run_interactive():
            bot.start_interactive()
        
        result, error = run_with_timeout(run_interactive, 5)  # Short timeout for menu display
        if error == "TIMEOUT":
            logger.warning("Interactive mode didn't start within 5 seconds - checking if menu is displayed...")
        
        return True
        
    except Exception as e:
        logger.error(f"Critical error in main bot: {e}")
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point with comprehensive error handling."""
    
    # Setup logging first
    logger = setup_debug_logging()
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start thread monitor
    monitor_thread = threading.Thread(target=monitor_threads, daemon=True, name="ThreadMonitor")
    monitor_thread.start()
    
    logger.info("=" * 80)
    logger.info("SOCIAL MEDIA BOT - DEBUG STARTUP")
    logger.info("=" * 80)
    logger.info(f"Python: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Arguments: {sys.argv}")
    
    try:
        # Test individual components first
        logger.info("Phase 1: Testing individual components...")
        if not test_individual_components():
            logger.error("❌ Component tests failed - startup aborted")
            return False
        
        logger.info("✅ All component tests passed")
        
        # Run main bot
        logger.info("Phase 2: Running main bot...")
        if not run_main_bot():
            logger.error("❌ Main bot startup failed")
            return False
        
        logger.info("✅ Bot startup sequence completed")
        
        # Keep running to see what happens
        logger.info("Keeping process alive to monitor behavior...")
        
        try:
            while True:
                time.sleep(10)
                logger.debug("Main process still alive...")
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt - shutting down")
        
        return True
        
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        logger.error(traceback.format_exc())
        return False
    
    finally:
        logger.info("Debug startup session ended")

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)