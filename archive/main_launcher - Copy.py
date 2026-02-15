#!/usr/bin/env python3
"""
Main Bot Platform Launcher
Centralized launcher for all social media automation
Starting with BlueSky, will expand to Twitter, Mastodon, etc.

Current version: Testing BlueSky every 5 minutes
"""

import sys
import os
import time
import schedule
from datetime import datetime
from pathlib import Path

# Add project path
sys.path.append(str(Path(__file__).parent))

def bsky_post():
    """Post to BlueSky - scheduled function."""
    current_time = datetime.now()
    
    try:
        # Import and call bsky main posting function
        from bsky import bsky
        bsky.main()
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] bsky.main() completed")
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in bsky.main(): {e}")

def run_launcher():
    """Run BlueSky interactions - follow-backs, likes, replies."""
    current_time = datetime.now()
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Running BlueSky interactions...")
    
    try:
        from bsky.modules import hello_reply, custom_reply, follow, reactions
        
        hello_reply.main()
        
        
        custom_reply.main()
        
        
        follow.main()
        
        
        reactions.main()
        
        
        
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky interactions: {e}")

def process_interactions_main():
    """Process BlueSky interactions - comprehensive daily processing."""
    current_time = datetime.now()
    
    
    try:
        from bsky.modules import custom_reply, follow, reactions
        custom_reply.main()
        
        follow.main()
        
        reactions.main()
        
        
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error processing BlueSky interactions: {e}")

def bsky_bestthing_main():
    """Run BlueSky best thing posting."""
    current_time = datetime.now()
    
    
    try:
        from bskyBESTTHING import main as bestthing_main
        bestthing_main()
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] BlueSky best thing posting completed")
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky best thing posting: {e}")

def bsky_taunt_main():
    """Run BlueSky taunt bot posting."""
    current_time = datetime.now()
    print(f"\n[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Running BlueSky taunt bot posting...")
    
    try:
        from bsky_taunt.bsky_taunt import main as taunt_main
        taunt_main()
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] BlueSky taunt bot posting completed")
    except Exception as e:
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Error in BlueSky taunt bot posting: {e}")

def main():
    """Main launcher using schedule library."""
    print("Starting Main Bot Platform Launcher...")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Using schedule library for timing")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    # Schedule BlueSky posting and interactions with original timings
    # schedule.every(5).minutes.do(bsky_post)  # Every 5 minutes for testing
    # schedule.every().hour.at(":54").do(bsky_post)  # Every hour at 54 minutes
    
    # BlueSky interactive functionality - restored from original scheduling
    schedule.every(5).minutes.do(run_launcher)  # BlueSky interactions every 5 minutes
    schedule.every().hour.at(":00").do(run_launcher)  # BlueSky interactions every hour
    schedule.every().day.at("00:15").do(process_interactions_main)  # Process interactions daily
    schedule.every().hour.at(":31").do(bsky_post)  # BlueSky main posting hourly (original timing)
    schedule.every().day.at("00:01").do(bsky_bestthing_main)  # BlueSky best thing daily
    
    # BlueSky taunt bot - separate account with taunts
    schedule.every().day.at("19:00").do(bsky_taunt_main)  # Taunt bot daily at 7pm
    
    print("Scheduled times:")
    for job in schedule.jobs:
        print(f"  - {job}")
    
    print("\nScheduler running...")
    
    # Main loop - same as original newcore.py
    retry_count = 0
    max_retries = 5
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
            retry_count = 0
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Launcher stopped by user")
            break
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Error in main loop: {e}")
            retry_count += 1
            if retry_count > max_retries:
                print("Exceeded maximum retry limit. Skipping this cycle.")
                retry_count = 0
                time.sleep(60)

if __name__ == "__main__":
    main()
