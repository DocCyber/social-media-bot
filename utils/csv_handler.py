"""
CSV Handler Utility
Consolidates the duplicate CSV reading logic found in:
- tweet/tweet.py
- toot/toot.py  
- bsky/bsky.py
- advertisment/tweetad.py

Provides unified CSV reading with multiple encoding support and error handling.
Compatible with Python 3.10+ including 3.13.
"""

import os
import csv
import logging
from typing import List, Optional, Union
from pathlib import Path


class CSVHandler:
    """Unified CSV handler with encoding detection and error handling."""
    
    # Standard encodings to try, in order of preference
    DEFAULT_ENCODINGS = ['utf-8', 'latin-1', 'cp1252', 'windows-1252']
    
    def __init__(self, base_path: Optional[Union[str, Path]] = None):
        """
        Initialize CSV handler.
        
        Args:
            base_path: Base directory for relative file paths. 
                      Defaults to parent directory of this script.
        """
        if base_path is None:
            # Default to jokes root directory (parent of utils)
            self.base_path = Path(__file__).parent.parent
        else:
            self.base_path = Path(base_path)
    
    def read_csv_with_encodings(
        self, 
        filename: Union[str, Path],
        encodings: Optional[List[str]] = None,
        error_callback: Optional[callable] = None
    ) -> Optional[List[List[str]]]:
        """
        Read CSV file trying multiple encodings until successful.
        
        Args:
            filename: CSV file name or path (relative to base_path)
            encodings: List of encodings to try. Uses DEFAULT_ENCODINGS if None.
            error_callback: Function to call on errors (filename, encoding, error)
            
        Returns:
            List of CSV rows as lists of strings, or None if all encodings fail.
        """
        if encodings is None:
            encodings = self.DEFAULT_ENCODINGS.copy()
        
        # Convert to Path and resolve relative to base_path
        filepath = self.base_path / filename
        
        if not filepath.exists():
            if error_callback:
                error_callback(str(filepath), "N/A", f"File not found: {filepath}")
            logging.error(f"CSV file not found: {filepath}")
            return None
        
        # Try each encoding until one works
        for encoding in encodings:
            try:
                with open(filepath, mode='r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    logging.debug(f"Successfully read {filepath} with encoding {encoding}")
                    return rows
                    
            except UnicodeDecodeError as e:
                logging.debug(f"UnicodeDecodeError with encoding {encoding}: {e}")
                if error_callback:
                    error_callback(str(filepath), f"Encoding error: {encoding}", e)
                continue
                
            except Exception as e:
                logging.error(f"Unexpected error reading {filepath} with {encoding}: {e}")
                if error_callback:
                    error_callback(str(filepath), "Unknown error", e)
                continue
        
        # All encodings failed
        error_msg = f"Failed to read {filepath} with all attempted encodings: {encodings}"
        logging.error(error_msg)
        if error_callback:
            error_callback(str(filepath), "All encodings failed", error_msg)
        
        return None
    
    def get_item_by_index(
        self,
        filename: Union[str, Path],
        index: int,
        encodings: Optional[List[str]] = None,
        error_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Get a specific item from CSV by index (0-based).
        
        Args:
            filename: CSV file name or path
            index: Row index (0-based)
            encodings: List of encodings to try
            error_callback: Function to call on errors
            
        Returns:
            First column of the specified row, or None if not found/error.
        """
        rows = self.read_csv_with_encodings(filename, encodings, error_callback)
        
        if rows is None:
            return None
            
        if not rows:  # Empty file
            logging.warning(f"CSV file {filename} is empty")
            return None
            
        if index < 0 or index >= len(rows):
            logging.warning(f"Index {index} out of range for {filename} (has {len(rows)} rows)")
            return None
            
        row = rows[index]
        if not row:  # Empty row
            logging.warning(f"Row {index} in {filename} is empty")
            return None
            
        # Return first column (joke/content text)
        return row[0]
    
    def get_random_item(
        self,
        filename: Union[str, Path],
        encodings: Optional[List[str]] = None,
        error_callback: Optional[callable] = None
    ) -> Optional[str]:
        """
        Get a random item from CSV file.
        
        Args:
            filename: CSV file name or path
            encodings: List of encodings to try
            error_callback: Function to call on errors
            
        Returns:
            Random item from first column, or None if error.
        """
        import random
        
        rows = self.read_csv_with_encodings(filename, encodings, error_callback)
        
        if not rows:
            return None
            
        # Filter out empty rows
        non_empty_rows = [row for row in rows if row and row[0].strip()]
        
        if not non_empty_rows:
            logging.warning(f"No non-empty rows found in {filename}")
            return None
            
        # Return random first column
        return random.choice(non_empty_rows)[0]
    
    def count_rows(
        self,
        filename: Union[str, Path],
        encodings: Optional[List[str]] = None,
        error_callback: Optional[callable] = None
    ) -> int:
        """
        Count total rows in CSV file.
        
        Returns:
            Number of rows, or 0 if error/empty.
        """
        rows = self.read_csv_with_encodings(filename, encodings, error_callback)
        return len(rows) if rows else 0


# Convenience function for backward compatibility
def create_csv_handler(base_path: Optional[str] = None) -> CSVHandler:
    """Create a CSV handler instance with specified base path."""
    return CSVHandler(base_path)


# Example usage for testing
if __name__ == "__main__":
    # Test with actual jokes file
    handler = CSVHandler()
    
    # Test basic reading
    print("Testing CSV reading...")
    rows = handler.read_csv_with_encodings("jokes.csv")
    if rows:
        print(f"Successfully read {len(rows)} rows from jokes.csv")
        print(f"First joke: {rows[0][0][:100]}..." if rows[0] else "Empty first row")
    
    # Test index access
    print("\nTesting index access...")
    joke = handler.get_item_by_index("jokes.csv", 0)
    if joke:
        print(f"Joke at index 0: {joke[:100]}...")
    
    # Test random access
    print("\nTesting random access...")
    random_joke = handler.get_random_item("jokes.csv")
    if random_joke:
        print(f"Random joke: {random_joke[:100]}...")
    
    # Test row counting
    print(f"\nTotal jokes: {handler.count_rows('jokes.csv')}")