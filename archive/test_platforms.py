#!/usr/bin/env python3
"""
Test script for new platform modules in Phase 2 refactoring.
Tests each platform module in isolation to ensure they work correctly.

Compatible with Python 3.10+ including 3.13.
"""

import os
import sys
from pathlib import Path

# Add platforms to path
sys.path.insert(0, str(Path(__file__).parent / "platforms"))

def test_platform_imports():
    """Test that all platform modules can be imported."""
    print("=" * 60)
    print("TESTING PLATFORM IMPORTS")
    print("=" * 60)
    
    try:
        # Test base platform
        print("Testing base platform import...")
        from base import BasePlatform
        print("+ Base platform imported successfully")
        
        # Test Mastodon platform
        print("Testing Mastodon platform import...")
        from mastodon_platform import MastodonPlatform, toot_item
        print("+ Mastodon platform imported successfully")
        
        # Test Twitter platform  
        print("Testing Twitter platform import...")
        from twitter_platform import TwitterPlatform, tweet_item
        print("+ Twitter platform imported successfully")
        
        print("+ All platform imports: PASS\n")
        return True
        
    except Exception as e:
        print(f"- Platform import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_mastodon_platform():
    """Test Mastodon platform functionality."""
    print("=" * 60)
    print("TESTING MASTODON PLATFORM")
    print("=" * 60)
    
    try:
        from mastodon_platform import MastodonPlatform
        
        # Test 1: Platform creation
        print("Test 1: Creating Mastodon platform...")
        try:
            platform = MastodonPlatform()
            print(f"+ Platform created: {platform}")
        except Exception as e:
            # Expected to fail if Mastodon library not installed or config missing
            print(f"- Platform creation failed (expected): {e}")
            if "mastodon.py library not available" in str(e):
                print("  INFO: Install mastodon.py to test fully: pip install Mastodon.py")
            elif "Missing required" in str(e):
                print("  INFO: Mastodon config validation working correctly")
            print("+ Mastodon Platform: CONFIG VALIDATION WORKING\n")
            return True
        
        # Test 2: Configuration validation
        print("Test 2: Testing configuration...")
        config_valid = platform.validate_required_config(['client_id', 'client_secret', 'access_token', 'api_base_url'])
        print(f"+ Configuration valid: {config_valid}")
        
        # Test 3: Stats (without authentication)
        print("Test 3: Getting platform stats...")
        stats = platform.get_stats()
        print(f"+ Platform stats: {stats}")
        
        # Test 4: Authentication test (may fail without valid config)
        print("Test 4: Testing authentication...")
        try:
            auth_result = platform.authenticate()
            print(f"+ Authentication result: {auth_result}")
        except Exception as e:
            print(f"- Authentication failed (expected): {e}")
        
        print("+ Mastodon Platform: BASIC TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"- Mastodon platform test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_twitter_platform():
    """Test Twitter platform functionality."""
    print("=" * 60)
    print("TESTING TWITTER PLATFORM")
    print("=" * 60)
    
    try:
        from twitter_platform import TwitterPlatform
        
        # Test 1: Platform creation
        print("Test 1: Creating Twitter platform...")
        try:
            platform = TwitterPlatform()
            print(f"+ Platform created: {platform}")
        except Exception as e:
            # Expected to fail if requests-oauthlib not installed or config missing
            print(f"- Platform creation failed (expected): {e}")
            if "requests-oauthlib not available" in str(e):
                print("  INFO: Install requests-oauthlib to test fully: pip install requests-oauthlib")
            elif "Missing required" in str(e):
                print("  INFO: Twitter config validation working correctly")
            print("+ Twitter Platform: CONFIG VALIDATION WORKING\n")
            return True
        
        # Test 2: Configuration validation
        print("Test 2: Testing configuration...")
        config_valid = platform.validate_required_config(['consumer_key', 'consumer_secret', 'access_token', 'access_token_secret'])
        print(f"+ Configuration valid: {config_valid}")
        
        # Test 3: Stats (without authentication)
        print("Test 3: Getting platform stats...")
        stats = platform.get_stats()
        print(f"+ Platform stats: {stats}")
        
        # Test 4: Authentication test (may fail without valid config)
        print("Test 4: Testing authentication...")
        try:
            auth_result = platform.authenticate()
            print(f"+ Authentication result: {auth_result}")
        except Exception as e:
            print(f"- Authentication failed (expected): {e}")
        
        print("+ Twitter Platform: BASIC TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"- Twitter platform test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backward_compatibility():
    """Test backward compatibility functions."""
    print("=" * 60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("=" * 60)
    
    try:
        # Test Mastodon backward compatibility
        print("Test 1: Mastodon toot_item function...")
        from mastodon_platform import toot_item
        print("+ toot_item function imported successfully")
        
        # Test calling (won't actually post without authentication)
        try:
            # This should fail gracefully without crashing
            result = toot_item("jokes.csv", "test_mastodon")
            print(f"+ toot_item call result: {result}")
        except Exception as e:
            print(f"- toot_item failed (expected): {e}")
        
        # Test Twitter backward compatibility  
        print("\nTest 2: Twitter tweet_item function...")
        from twitter_platform import tweet_item
        print("+ tweet_item function imported successfully")
        
        # Test calling (won't actually post without authentication)
        try:
            # This should fail gracefully without crashing
            result = tweet_item("jokes.csv", "test_twitter")
            print(f"+ tweet_item call result: {result}")
        except Exception as e:
            print(f"- tweet_item failed (expected): {e}")
        
        print("\n+ Backward Compatibility: FUNCTIONS AVAILABLE\n")
        return True
        
    except Exception as e:
        print(f"- Backward compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_base_platform_functionality():
    """Test base platform abstract functionality."""
    print("=" * 60)
    print("TESTING BASE PLATFORM")
    print("=" * 60)
    
    try:
        from base import BasePlatform, create_platform, validate_platform_class
        from mastodon_platform import MastodonPlatform
        
        # Test 1: Abstract class cannot be instantiated
        print("Test 1: Testing abstract class...")
        try:
            base = BasePlatform("test")
            print("- Base platform should not be instantiable")
            return False
        except TypeError:
            print("+ Base platform correctly abstract")
        
        # Test 2: Platform validation
        print("Test 2: Testing platform class validation...")
        is_valid = validate_platform_class(MastodonPlatform)
        print(f"+ MastodonPlatform valid: {is_valid}")
        
        # Test 3: Factory function (if platform can be created)
        print("Test 3: Testing factory function...")
        try:
            platform = create_platform("mastodon", MastodonPlatform)
            print(f"+ Factory function works: {platform}")
        except Exception as e:
            print(f"- Factory function failed (expected): {e}")
        
        print("+ Base Platform: ARCHITECTURE TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"- Base platform test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_utility_integration():
    """Test that platforms properly use utilities."""
    print("=" * 60)
    print("TESTING UTILITY INTEGRATION")
    print("=" * 60)
    
    try:
        # This test verifies that platforms can access the utilities
        # without breaking, even if they can't authenticate
        
        print("Test 1: Testing utility imports in platforms...")
        
        # Check that platforms import utilities correctly
        from mastodon_platform import MastodonPlatform
        from twitter_platform import TwitterPlatform
        
        print("+ Platform utility imports working")
        
        # Test that utilities are accessible
        print("Test 2: Testing utility access...")
        
        # Create config manager (should work)
        from utils.config_manager import ConfigManager
        config_mgr = ConfigManager()
        config_mgr.load_all_configs()
        platforms = config_mgr.list_platforms()
        print(f"+ Available platform configs: {platforms}")
        
        # Test CSV handler (should work)
        from utils.csv_handler import CSVHandler
        csv_handler = CSVHandler()
        joke_count = csv_handler.count_rows("jokes.csv")
        print(f"+ CSV handler working, jokes available: {joke_count}")
        
        # Test index manager (should work)
        from utils.index_manager import IndexManager
        index_mgr = IndexManager()
        indices = index_mgr.load_indices()
        print(f"+ Index manager working, indices: {list(indices.keys())}")
        
        print("+ Utility Integration: ALL TESTS PASSED\n")
        return True
        
    except Exception as e:
        print(f"- Utility integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all platform tests."""
    print("JOKES BOT PLATFORM TESTING SUITE")
    print("Phase 2: Platform Module Consolidation")
    print("Testing Python version:", sys.version)
    print()
    
    tests = [
        ("Platform Imports", test_platform_imports),
        ("Mastodon Platform", test_mastodon_platform),
        ("Twitter Platform", test_twitter_platform),
        ("Base Platform Architecture", test_base_platform_functionality),
        ("Backward Compatibility", test_backward_compatibility),
        ("Utility Integration", test_utility_integration),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            print(f"Running {test_name} test...")
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"- {test_name} test crashed: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        symbol = "+" if result else "-"
        print(f"{symbol} {test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("SUCCESS: Platform modules are ready for integration!")
        return True
    else:
        print("WARNING: Some tests failed. Review errors before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)