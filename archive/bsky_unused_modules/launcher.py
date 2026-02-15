import json
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add consolidated platform path
sys.path.append(str(Path(__file__).parent.parent / "platforms" / "bluesky"))

# Try importing consolidated modules first, fallback to legacy
try:
    from interactive_modules import (
        run_notifications,
        run_reactions,
        run_follow,
        run_custom_reply,
        run_custom_reposts
    )
    from bluesky_auth import get_bluesky_auth
    USING_CONSOLIDATED = True
    print("Using consolidated BlueSky modules")
except ImportError:
    # Fallback to legacy modules
    from modules import (
        auth,
        notifications,
        reactions,
        follow,
        hello_reply,
        custom_reply,
        custom_reposts,
        baddadjokes_reposter,
        pinning,
        shout_out,
        unfollower
    )
    USING_CONSOLIDATED = False
    print("Using legacy BlueSky modules")

# Load configuration using centralized system
try:
    # Add the correct paths for imports
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Try unified config first
    from utils.config_manager import ConfigManager
    config_manager = ConfigManager()
    config_manager.load_all_configs()
    
    # Convert to legacy format for existing code compatibility
    config = {
        'bsky': config_manager.get_platform_config('bluesky').config if config_manager.get_platform_config('bluesky') else {},
        'paths': config_manager.get_paths() or {
            'data_dir': 'd:/jokes/bsky/data',
            'csv_file': 'D:/jokes/bsky/data',
            'log_file': 'D:/jokes/bsky/logs'
        }
    }
    print("Using centralized configuration system")
except ImportError:
    # Fallback to legacy config loading
    config_file_path = os.path.join("..", "config.json")
    if os.path.exists(config_file_path):
        with open(config_file_path, "r") as config_file:
            config = json.load(config_file)
        print("Using legacy configuration file")
    else:
        print("ERROR: No configuration found")
        sys.exit(1)

# Define modules based on whether we're using consolidated or legacy
if USING_CONSOLIDATED:
    # Consolidated module functions
    module_functions = [
        ("notifications", run_notifications),
        ("reactions", run_reactions),
        ("follow", run_follow),
        ("custom_reply", run_custom_reply),
        ("custom_reposts", run_custom_reposts)
    ]
else:
    # Legacy modules
    modules = [
        notifications,
        reactions,
        follow,
        hello_reply,
        custom_reply,
        custom_reposts,
        baddadjokes_reposter,
        pinning,
        shout_out,
        unfollower
    ]

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    # Print current time in GMT-5 format
    current_time = datetime.now()
    formatted_time = current_time.strftime("%I:%M %p %m/%d/%y")  # Format to 3:23 AM 11/30/24
    print(f"Launcher called at {formatted_time} (GMT-5)")

    logging.info("Bot started.")

    # Check if it's the top of the hour, excluding midnight
    if current_time.minute < 5 and current_time.hour != 0:
        logging.info("Running dadjoke_reposter.py module.")
        try:
            from modules import dadjoke_reposter  # Import only when needed
            
            if USING_CONSOLIDATED:
                bluesky_auth = get_bluesky_auth()
                if bluesky_auth.authenticate():
                    session = bluesky_auth.get_session()
                    dadjoke_reposter.run(config, session)
                else:
                    logging.error("Authentication failed for dadjoke_reposter.py. Skipping.")
            else:
                # Legacy authentication
                session = auth.run(config)
                if session:
                    dadjoke_reposter.run(config, session)
                else:
                    logging.error("Authentication failed for dadjoke_reposter.py. Skipping.")
        except Exception as e:
            logging.error(f"Error in dadjoke_reposter.py: {e}", exc_info=True)
    else:
        logging.info("Skipping dadjoke_reposter.py. Not at the top of the hour or it's midnight.")
    
    # Run all other modules
    if USING_CONSOLIDATED:
        # Use consolidated modules with unified authentication
        bluesky_auth = get_bluesky_auth()
        if not bluesky_auth.authenticate():
            logging.error("Authentication failed. Exiting.")
            return
        
        session = bluesky_auth.get_session()
        for module_name, module_func in module_functions:
            try:
                logging.info(f"Running {module_name} module (consolidated)")
                module_func(config, session)
            except Exception as e:
                logging.error(f"Error in {module_name}: {e}", exc_info=True)
    else:
        # Use legacy modules
        session = auth.run(config)
        if not session:
            logging.error("Authentication failed. Exiting.")
            return

        for module in modules:
            try:
                logging.info(f"Running {module.__name__} module (legacy)")
                module.run(config, session)  # Pass session to each module
            except Exception as e:
                logging.error(f"Error in {module.__name__}: {e}", exc_info=True)

    logging.info("Bot finished.")

if __name__ == "__main__":
    main()
