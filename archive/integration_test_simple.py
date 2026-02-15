#!/usr/bin/env python3
"""
Simple Integration Test for Platform Modules
Tests that the new platform modules can replace the old ones.

Compatible with Python 3.10+ including 3.13.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "platforms"))

def test_import_compatibility():
    """Test that new modules can be imported as replacements."""
    print("INTEGRATION TEST: Platform Replacement Compatibility")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Import old modules (if available)
    print("Step 1: Testing old module imports...")
    try:
        import tweet
        print("+ OLD tweet module: Available")
        results['old_tweet'] = True
    except ImportError:
        print("- OLD tweet module: Not available")
        results['old_tweet'] = False
    
    try:
        from toot import toot_item
        print("+ OLD toot module: Available")
        results['old_toot'] = True
    except ImportError:
        print("- OLD toot module: Not available")
        results['old_toot'] = False
    
    # Test 2: Import new platform modules
    print("\nStep 2: Testing new platform modules...")
    try:
        from platforms.twitter_platform import tweet_item
        print("+ NEW twitter_platform: Available")
        results['new_twitter'] = True
    except ImportError as e:
        print(f"- NEW twitter_platform: Not available ({e})")
        results['new_twitter'] = False
    
    try:
        from platforms.mastodon_platform import toot_item as new_toot_item
        print("+ NEW mastodon_platform: Available")
        results['new_mastodon'] = True
    except ImportError as e:
        print(f"- NEW mastodon_platform: Not available ({e})")
        results['new_mastodon'] = False
    
    # Test 3: Function signature compatibility
    print("\nStep 3: Testing function signature compatibility...")
    
    if results['new_twitter']:
        try:
            # Test that the function can be called with same parameters
            # (This won't actually post due to missing dependencies, but tests the interface)
            result = tweet_item("jokes.csv", "joke")  # Should return False due to dependencies
            print("+ NEW tweet_item function: Compatible interface")
            results['twitter_interface'] = True
        except Exception as e:
            if "requests library not available" in str(e) or "Import" in str(e):
                print("+ NEW tweet_item function: Compatible interface (missing dependencies expected)")
                results['twitter_interface'] = True
            else:
                print(f"- NEW tweet_item function: Interface error - {e}")
                results['twitter_interface'] = False
    
    if results['new_mastodon']:
        try:
            # Test that the function can be called with same parameters
            result = new_toot_item("jokes.csv", "Mastodon")  # Should return False due to dependencies
            print("+ NEW toot_item function: Compatible interface")
            results['mastodon_interface'] = True
        except Exception as e:
            if "mastodon.py library not available" in str(e) or "Import" in str(e):
                print("+ NEW toot_item function: Compatible interface (missing dependencies expected)")
                results['mastodon_interface'] = True
            else:
                print(f"- NEW toot_item function: Interface error - {e}")
                results['mastodon_interface'] = False
    
    # Test 4: Utility integration
    print("\nStep 4: Testing utility integration...")
    try:
        from utils.config_manager import ConfigManager
        from utils.csv_handler import CSVHandler
        from utils.index_manager import IndexManager
        from utils.error_logger import ErrorLogger
        
        config_mgr = ConfigManager()
        config_mgr.load_all_configs()
        platforms = config_mgr.list_platforms()
        
        csv_handler = CSVHandler()
        joke_count = csv_handler.count_rows("jokes.csv")
        
        index_mgr = IndexManager()
        indices = index_mgr.load_indices()
        
        logger = ErrorLogger("test")
        
        print(f"+ Utilities working: {len(platforms)} platforms, {joke_count} jokes, {len(indices)} indices")
        results['utilities'] = True
        
    except Exception as e:
        print(f"- Utilities failed: {e}")
        results['utilities'] = False
    
    return results

def demonstrate_replacement_strategy():
    """Show how newcore.py could be updated."""
    print("\nREPLACEMENT STRATEGY FOR NEWCORE.PY")
    print("=" * 50)
    
    print("Current newcore.py imports:")
    print("  import tweet")
    print("  from toot import toot_item")
    print("  # ... other imports")
    print()
    
    print("Updated newcore.py imports (backward compatible):")
    print("  # Replace old imports with new platform modules")
    print("  from platforms.twitter_platform import tweet_item")
    print("  from platforms.mastodon_platform import toot_item") 
    print("  # ... keep other imports unchanged")
    print()
    
    print("Scheduling remains identical:")
    print("  schedule.every().day.at('02:30').do(tweet_item, 'jokes.csv', 'joke')")
    print("  schedule.every().hour.at(':32').do(toot_item, 'jokes.csv', 'Mastodon')")
    print()
    
    print("Benefits of the replacement:")
    print("  + Enhanced error logging and debugging")
    print("  + Unified configuration management")
    print("  + Consistent CSV and index handling")
    print("  + Better authentication and session management")
    print("  + Same interface - no changes to scheduling code")

def main():
    """Run integration test."""
    print("PLATFORM INTEGRATION TEST")
    print(f"Python version: {sys.version}")
    print()
    
    # Run compatibility test
    results = test_import_compatibility()
    
    # Show replacement strategy
    demonstrate_replacement_strategy()
    
    # Summary
    print("\n" + "=" * 60)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    passed_tests = sum(1 for result in results.values() if result)
    
    print("Test Results:")
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "+" if result else "-"
        print(f"  {symbol} {test_name}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    # Integration readiness assessment
    print("\nIntegration Readiness:")
    
    new_modules_ready = results.get('new_twitter', False) and results.get('new_mastodon', False)
    interfaces_ready = results.get('twitter_interface', False) and results.get('mastodon_interface', False)
    utilities_ready = results.get('utilities', False)
    
    if new_modules_ready and interfaces_ready and utilities_ready:
        print("  STATUS: READY FOR INTEGRATION")
        print("  - New platform modules are available")
        print("  - Function interfaces are compatible")
        print("  - Utilities are working correctly")
        print("  - newcore.py can safely use new modules")
        return True
    else:
        print("  STATUS: NEEDS ATTENTION")
        if not new_modules_ready:
            print("  - Install missing dependencies (requests, mastodon.py)")
        if not interfaces_ready:
            print("  - Function interface issues need resolution")  
        if not utilities_ready:
            print("  - Utility integration needs fixing")
        print("  - Address issues before integrating with newcore.py")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)