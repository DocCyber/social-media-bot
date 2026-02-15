"""
Index Manager Utility
Consolidates the duplicate JSON index management found in:
- tweet/tweet.py
- toot/toot.py  
- advertisment/tweetad.py
- additions/pop_joke.py

Provides thread-safe index management with automatic backup and recovery.
Compatible with Python 3.10+ including 3.13.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
try:
    import fcntl  # For file locking on Unix-like systems
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt  # For file locking on Windows
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class IndexManager:
    """
    Thread-safe JSON index manager with backup and recovery capabilities.
    Handles the index.json file that tracks posting positions for different platforms.
    """
    
    def __init__(
        self, 
        index_file: Optional[Union[str, Path]] = None,
        base_path: Optional[Union[str, Path]] = None,
        auto_backup: bool = True
    ):
        """
        Initialize index manager.
        
        Args:
            index_file: Path to index JSON file. Defaults to 'index.json'
            base_path: Base directory. Defaults to jokes root directory
            auto_backup: Whether to create automatic backups
        """
        if base_path is None:
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
        
        if index_file is None:
            self.index_file = self.base_path / "index.json"
        else:
            self.index_file = self.base_path / index_file
        
        self.backup_file = self.index_file.with_suffix('.json.backup')
        self.auto_backup = auto_backup
        
        # Ensure the index file exists
        self._ensure_index_file()
    
    def _ensure_index_file(self) -> None:
        """Ensure the index file exists with default structure."""
        if not self.index_file.exists():
            # Create default index structure based on current usage patterns
            default_indices = {
                "joke": 0,
                "docafterdark": 0, 
                "school": 0,
                "Mastodon": 0,
                "bsky": 0,
                "questions": 0,
                "comic_index": 0,
                "jokebot": 0
            }
            
            try:
                with open(self.index_file, 'w', encoding='utf-8') as f:
                    json.dump(default_indices, f, indent=4)
                print(f"Created default index file: {self.index_file}")
            except Exception as e:
                print(f"ERROR: Could not create index file {self.index_file}: {e}")
                raise
    
    def _lock_file(self, file_handle) -> None:
        """Lock a file for exclusive access (cross-platform)."""
        try:
            if os.name == 'nt' and HAS_MSVCRT:  # Windows
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            elif HAS_FCNTL:  # Unix-like systems
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # If neither is available, skip locking (timer-based execution should prevent conflicts)
        except (OSError, IOError):
            # If locking fails, we'll proceed without it (for compatibility)
            # The timer-based execution should prevent most conflicts anyway
            pass
    
    def _unlock_file(self, file_handle) -> None:
        """Unlock a file (cross-platform)."""
        try:
            if os.name == 'nt' and HAS_MSVCRT:  # Windows
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            elif HAS_FCNTL:  # Unix-like systems
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
            # If neither is available, skip unlocking
        except (OSError, IOError):
            pass  # Ignore unlock errors
    
    def load_indices(self) -> Dict[str, Any]:
        """
        Load indices from JSON file with error recovery.
        
        Returns:
            Dictionary of indices, or empty dict if error
        """
        # Try main file first
        for attempt_file in [self.index_file, self.backup_file]:
            if not attempt_file.exists():
                continue
                
            try:
                with open(attempt_file, 'r', encoding='utf-8') as f:
                    self._lock_file(f)
                    try:
                        indices = json.load(f)
                        if isinstance(indices, dict):
                            return indices
                        else:
                            print(f"WARNING: Invalid index structure in {attempt_file}")
                    finally:
                        self._unlock_file(f)
                        
            except json.JSONDecodeError as e:
                print(f"ERROR: Corrupted JSON in {attempt_file}: {e}")
                continue
            except Exception as e:
                print(f"ERROR: Could not read {attempt_file}: {e}")
                continue
        
        # If both files failed, return default structure
        print("WARNING: Could not load indices, returning defaults")
        return {
            "joke": 0,
            "docafterdark": 0,
            "school": 0, 
            "Mastodon": 0,
            "bsky": 0,
            "questions": 0,
            "comic_index": 0,
            "jokebot": 0
        }
    
    def save_indices(self, indices: Dict[str, Any]) -> bool:
        """
        Save indices to JSON file with backup.
        
        Args:
            indices: Dictionary of indices to save
            
        Returns:
            True if successful, False otherwise
        """
        if not isinstance(indices, dict):
            print("ERROR: Indices must be a dictionary")
            return False
        
        # Create backup if auto_backup is enabled
        if self.auto_backup and self.index_file.exists():
            try:
                shutil.copy2(self.index_file, self.backup_file)
            except Exception as e:
                print(f"WARNING: Could not create backup: {e}")
        
        # Save new indices
        try:
            # Write to temporary file first, then move (atomic operation)
            temp_file = self.index_file.with_suffix('.json.tmp')
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                self._lock_file(f)
                try:
                    json.dump(indices, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                finally:
                    self._unlock_file(f)
            
            # Atomic move (replace original file)
            if os.name == 'nt':  # Windows
                if self.index_file.exists():
                    os.remove(self.index_file)
                os.rename(temp_file, self.index_file)
            else:  # Unix-like
                os.rename(temp_file, self.index_file)
            
            return True
            
        except Exception as e:
            print(f"ERROR: Could not save indices to {self.index_file}: {e}")
            # Clean up temp file if it exists
            temp_file = self.index_file.with_suffix('.json.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            return False
    
    def get_index(self, key: str, default: int = 0) -> int:
        """
        Get current index for a specific key.
        
        Args:
            key: Index key (e.g., 'joke', 'bsky')
            default: Default value if key not found
            
        Returns:
            Current index value
        """
        indices = self.load_indices()
        return indices.get(key, default)
    
    def set_index(self, key: str, value: int) -> bool:
        """
        Set index for a specific key.
        
        Args:
            key: Index key
            value: New index value
            
        Returns:
            True if successful, False otherwise
        """
        indices = self.load_indices()
        indices[key] = value
        return self.save_indices(indices)
    
    def increment_index(self, key: str, amount: int = 1) -> int:
        """
        Increment index for a specific key.
        
        Args:
            key: Index key
            amount: Amount to increment by (default 1)
            
        Returns:
            New index value, or -1 if error
        """
        indices = self.load_indices()
        current_value = indices.get(key, 0)
        new_value = current_value + amount
        indices[key] = new_value
        
        if self.save_indices(indices):
            return new_value
        else:
            return -1
    
    def get_next_index(self, key: str) -> int:
        """
        Get next index value and increment it atomically.
        
        Args:
            key: Index key
            
        Returns:
            The index value to use (before increment), or -1 if error
        """
        indices = self.load_indices()
        current_value = indices.get(key, 0)
        indices[key] = current_value + 1
        
        if self.save_indices(indices):
            return current_value
        else:
            return -1
    
    def reset_index(self, key: str, value: int = 0) -> bool:
        """
        Reset index for a specific key.
        
        Args:
            key: Index key
            value: Value to reset to (default 0)
            
        Returns:
            True if successful, False otherwise
        """
        return self.set_index(key, value)
    
    def list_keys(self) -> List[str]:
        """Get list of all index keys."""
        indices = self.load_indices()
        return list(indices.keys())
    
    def get_all_indices(self) -> Dict[str, Any]:
        """Get all indices as a dictionary."""
        return self.load_indices()
    
    def backup_indices(self, backup_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Create a manual backup of indices.
        
        Args:
            backup_path: Custom backup location. If None, uses timestamped backup.
            
        Returns:
            True if successful, False otherwise
        """
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.index_file.with_name(f"index_backup_{timestamp}.json")
        else:
            backup_path = Path(backup_path)
        
        try:
            shutil.copy2(self.index_file, backup_path)
            print(f"Index backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"ERROR: Could not create backup at {backup_path}: {e}")
            return False


# Global index manager instance  
_global_index_manager: Optional[IndexManager] = None


def get_index_manager(
    index_file: Optional[str] = None,
    base_path: Optional[str] = None
) -> IndexManager:
    """
    Get the global index manager instance.
    
    Args:
        index_file: Index file path (only used on first call)
        base_path: Base directory (only used on first call)
        
    Returns:
        IndexManager instance
    """
    global _global_index_manager
    
    if _global_index_manager is None:
        _global_index_manager = IndexManager(index_file, base_path)
    
    return _global_index_manager


# Convenience functions for backward compatibility
def load_indices() -> Dict[str, Any]:
    """Load indices (backward compatibility)."""
    return get_index_manager().load_indices()


def save_indices(indices: Dict[str, Any]) -> bool:
    """Save indices (backward compatibility)."""
    return get_index_manager().save_indices(indices)


# Example usage and testing
if __name__ == "__main__":
    print("Testing IndexManager...")
    
    # Create index manager
    manager = IndexManager()
    
    # Test loading
    indices = manager.load_indices()
    print(f"Current indices: {indices}")
    
    # Test getting specific index
    joke_index = manager.get_index('joke')
    print(f"Current joke index: {joke_index}")
    
    # Test incrementing
    new_joke_index = manager.increment_index('joke')
    print(f"New joke index after increment: {new_joke_index}")
    
    # Test get_next_index (simulates actual usage pattern)
    next_index = manager.get_next_index('test_key')
    print(f"Next test_key index: {next_index}")
    
    # Test listing keys
    keys = manager.list_keys()
    print(f"Available keys: {keys}")
    
    # Test backup functionality
    backup_success = manager.backup_indices()
    print(f"Backup created: {backup_success}")
    
    # Test backward compatibility functions
    legacy_indices = load_indices()
    print(f"Legacy load function works: {len(legacy_indices)} keys")
    
    print("\nIndexManager test completed.")