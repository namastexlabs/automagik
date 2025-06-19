#!/usr/bin/env python3
"""
Data Processing Utilities - Test Project

This module demonstrates various Python programming concepts including:
- Mathematical operations and calculations
- String processing and text analysis
- Data manipulation and transformations
- File I/O operations
- Error handling and validation

Author: Test Project
Date: 2025-06-18
Version: 1.0.0
"""

import json
import re
import statistics
import csv
import os
from typing import List, Dict, Any, Union, Optional
from collections import Counter
import math


class MathUtils:
    """Mathematical utility functions for calculations and analysis."""
    
    @staticmethod
    def calculate_statistics(numbers: List[Union[int, float]]) -> Dict[str, float]:
        """
        Calculate comprehensive statistics for a list of numbers.
        
        Args:
            numbers: List of numeric values
            
        Returns:
            Dictionary containing mean, median, mode, and other statistics
            
        Raises:
            ValueError: If the input list is empty or contains non-numeric values
        """
        if not numbers:
            raise ValueError("Cannot calculate statistics for empty list")
        
        if not all(isinstance(n, (int, float)) for n in numbers):
            raise ValueError("All elements must be numeric")
        
        try:
            return {
                'mean': statistics.mean(numbers),
                'median': statistics.median(numbers),
                'mode': statistics.mode(numbers) if len(set(numbers)) < len(numbers) else numbers[0],
                'std_dev': statistics.stdev(numbers) if len(numbers) > 1 else 0,
                'min': min(numbers),
                'max': max(numbers),
                'count': len(numbers),
                'sum': sum(numbers)
            }
        except Exception as e:
            raise ValueError(f"Error calculating statistics: {str(e)}")
    
    @staticmethod
    def is_prime(number: int) -> bool:
        """
        Check if a number is prime using optimized algorithm.
        
        Args:
            number: Integer to check for primality
            
        Returns:
            True if number is prime, False otherwise
        """
        if not isinstance(number, int):
            return False
        
        if number < 2:
            return False
        if number == 2:
            return True
        if number % 2 == 0:
            return False
        
        # Check odd divisors up to sqrt(number)
        for i in range(3, int(math.sqrt(number)) + 1, 2):
            if number % i == 0:
                return False
        return True
    
    @staticmethod
    def factorial(n: int) -> int:
        """
        Calculate factorial of a number using recursion.
        
        Args:
            n: Non-negative integer
            
        Returns:
            Factorial of n
            
        Raises:
            ValueError: If n is negative or not an integer
        """
        if not isinstance(n, int) or n < 0:
            raise ValueError("Factorial is only defined for non-negative integers")
        
        if n <= 1:
            return 1
        return n * MathUtils.factorial(n - 1)


class StringUtils:
    """String processing and text analysis utilities."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text by removing extra whitespace and special characters.
        
        Args:
            text: Input text string
            
        Returns:
            Cleaned and normalized text
        """
        if not isinstance(text, str):
            return str(text)
        
        # Remove extra whitespaces and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        # Remove special characters but keep basic punctuation
        cleaned = re.sub(r'[^\w\s\.\,\!\?\-]', '', cleaned)
        return cleaned
    
    @staticmethod
    def word_frequency(text: str) -> Dict[str, int]:
        """
        Calculate word frequency in text.
        
        Args:
            text: Input text string
            
        Returns:
            Dictionary with words as keys and frequencies as values
        """
        if not isinstance(text, str):
            return {}
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        return dict(Counter(words))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Basic email validation using regex pattern.
        
        Args:
            email: Email string to validate
            
        Returns:
            True if email format is valid, False otherwise
        """
        if not isinstance(email, str):
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))


class DataUtils:
    """Data manipulation and transformation utilities."""
    
    @staticmethod
    def filter_data(data: List[Dict[str, Any]], condition: callable) -> List[Dict[str, Any]]:
        """
        Filter data based on a custom condition function.
        
        Args:
            data: List of dictionaries to filter
            condition: Function that returns True for items to keep
            
        Returns:
            Filtered list of dictionaries
        """
        if not isinstance(data, list):
            return []
        
        try:
            return [item for item in data if condition(item)]
        except Exception:
            return []
    
    @staticmethod
    def transform_dict(data: Dict[str, Any], key_map: Dict[str, str]) -> Dict[str, Any]:
        """
        Transform dictionary keys according to a mapping.
        
        Args:
            data: Original dictionary
            key_map: Mapping of old_key -> new_key
            
        Returns:
            Dictionary with transformed keys
        """
        if not isinstance(data, dict) or not isinstance(key_map, dict):
            return data
        
        transformed = {}
        for old_key, value in data.items():
            new_key = key_map.get(old_key, old_key)
            transformed[new_key] = value
        
        return transformed
    
    @staticmethod
    def merge_datasets(dataset1: List[Dict], dataset2: List[Dict], 
                      merge_key: str = 'id') -> List[Dict]:
        """
        Merge two datasets based on a common key.
        
        Args:
            dataset1: First dataset
            dataset2: Second dataset
            merge_key: Key to merge on
            
        Returns:
            Merged dataset
        """
        if not all(isinstance(ds, list) for ds in [dataset1, dataset2]):
            return []
        
        merged = []
        
        # Create lookup dictionary for dataset2
        lookup = {item.get(merge_key): item for item in dataset2 
                 if isinstance(item, dict) and merge_key in item}
        
        # Merge datasets
        for item1 in dataset1:
            if isinstance(item1, dict) and merge_key in item1:
                merged_item = item1.copy()
                if item1[merge_key] in lookup:
                    # Merge with matching item from dataset2
                    item2 = lookup[item1[merge_key]]
                    for key, value in item2.items():
                        if key not in merged_item:
                            merged_item[key] = value
                merged.append(merged_item)
        
        return merged


class FileUtils:
    """File I/O operations and data persistence utilities."""
    
    @staticmethod
    def save_json(data: Any, filename: str, indent: int = 2) -> bool:
        """
        Save data to JSON file with error handling.
        
        Args:
            data: Data to save
            filename: Target file path
            indent: JSON indentation for readability
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving JSON file {filename}: {e}")
            return False
    
    @staticmethod
    def load_json(filename: str) -> Optional[Any]:
        """
        Load data from JSON file with error handling.
        
        Args:
            filename: Source file path
            
        Returns:
            Loaded data or None if error occurred
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File not found: {filename}")
            return None
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in file {filename}: {e}")
            return None
        except Exception as e:
            print(f"Error loading JSON file {filename}: {e}")
            return None
    
    @staticmethod
    def process_csv_data(data: List[List[str]], has_header: bool = True) -> List[Dict[str, str]]:
        """
        Process CSV-like data structures into list of dictionaries.
        
        Args:
            data: List of lists representing CSV rows
            has_header: Whether first row contains headers
            
        Returns:
            List of dictionaries with column names as keys
        """
        if not data or not isinstance(data, list):
            return []
        
        if has_header and len(data) > 1:
            headers = data[0]
            rows = data[1:]
            return [dict(zip(headers, row)) for row in rows if len(row) == len(headers)]
        else:
            # Generate generic headers if no header row
            if data:
                headers = [f'col_{i}' for i in range(len(data[0]))]
                return [dict(zip(headers, row)) for row in data if len(row) == len(headers)]
        
        return []


def demonstrate_functionality():
    """
    Demonstrate all utility functions with sample data.
    This function serves as both a test suite and usage example.
    """
    print("=" * 60)
    print("DATA PROCESSING UTILITIES - DEMONSTRATION")
    print("=" * 60)
    
    # Mathematical operations demonstration
    print("\n1. MATHEMATICAL OPERATIONS:")
    print("-" * 30)
    
    sample_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 2, 3, 3]
    try:
        stats = MathUtils.calculate_statistics(sample_numbers)
        print(f"Numbers: {sample_numbers}")
        print(f"Statistics: {stats}")
        
        # Prime number checking
        test_numbers = [17, 18, 19, 20, 97]
        print(f"\nPrime number check:")
        for num in test_numbers:
            print(f"  {num} is prime: {MathUtils.is_prime(num)}")
        
        # Factorial calculation
        print(f"\nFactorials:")
        for n in [5, 7, 10]:
            print(f"  {n}! = {MathUtils.factorial(n)}")
            
    except Exception as e:
        print(f"Error in math operations: {e}")
    
    # String processing demonstration
    print("\n2. STRING PROCESSING:")
    print("-" * 30)
    
    sample_text = "  Hello, World!  This is a TEST string with  extra   spaces!  "
    cleaned = StringUtils.clean_text(sample_text)
    print(f"Original: '{sample_text}'")
    print(f"Cleaned:  '{cleaned}'")
    
    # Word frequency analysis
    text_for_analysis = "the quick brown fox jumps over the lazy dog the fox is quick"
    frequencies = StringUtils.word_frequency(text_for_analysis)
    print(f"\nWord frequencies in: '{text_for_analysis}'")
    for word, count in sorted(frequencies.items()):
        print(f"  '{word}': {count}")
    
    # Email validation
    test_emails = ["test@example.com", "invalid.email", "user@domain.co.uk", "not-an-email"]
    print(f"\nEmail validation:")
    for email in test_emails:
        print(f"  '{email}' is valid: {StringUtils.validate_email(email)}")
    
    # Data manipulation demonstration
    print("\n3. DATA MANIPULATION:")
    print("-" * 30)
    
    sample_data = [
        {"id": 1, "name": "Alice", "age": 30, "city": "New York"},
        {"id": 2, "name": "Bob", "age": 25, "city": "London"},
        {"id": 3, "name": "Charlie", "age": 35, "city": "Paris"},
        {"id": 4, "name": "Diana", "age": 28, "city": "Tokyo"}
    ]
    
    # Filter data
    adults_over_30 = DataUtils.filter_data(sample_data, lambda x: x.get('age', 0) > 30)
    print(f"People over 30: {adults_over_30}")
    
    # Transform dictionary keys
    key_mapping = {"name": "full_name", "age": "years_old"}
    transformed = DataUtils.transform_dict(sample_data[0], key_mapping)
    print(f"Transformed keys: {transformed}")
    
    # Merge datasets
    additional_data = [
        {"id": 1, "salary": 50000, "department": "Engineering"},
        {"id": 2, "salary": 45000, "department": "Marketing"},
        {"id": 3, "salary": 60000, "department": "Sales"}
    ]
    
    merged_data = DataUtils.merge_datasets(sample_data, additional_data)
    print(f"Merged dataset sample: {merged_data[0] if merged_data else 'No data'}")
    
    # File operations demonstration
    print("\n4. FILE OPERATIONS:")
    print("-" * 30)
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    # Save and load JSON
    test_data = {
        "project": "Test Project",
        "version": "1.0.0",
        "features": ["math", "strings", "data", "files"],
        "sample_numbers": sample_numbers,
        "statistics": stats
    }
    
    json_file = "data/test_data.json"
    if FileUtils.save_json(test_data, json_file):
        print(f"Successfully saved data to {json_file}")
        
        loaded_data = FileUtils.load_json(json_file)
        if loaded_data:
            print(f"Successfully loaded data: {loaded_data['project']} v{loaded_data['version']}")
    
    # Process CSV-like data
    csv_data = [
        ["Name", "Age", "City"],
        ["Alice", "30", "New York"],
        ["Bob", "25", "London"],
        ["Charlie", "35", "Paris"]
    ]
    
    processed_csv = FileUtils.process_csv_data(csv_data)
    print(f"Processed CSV data: {processed_csv[0] if processed_csv else 'No data'}")
    
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)


def api_testing_utilities():
    """
    Additional utilities specifically useful for API testing scenarios.
    These functions can be used to validate API responses and test data.
    """
    print("\n" + "=" * 60)
    print("API TESTING UTILITIES")
    print("=" * 60)
    
    # Mock API response validation
    mock_api_response = {
        "status": "success",
        "data": {
            "users": [
                {"id": 1, "email": "user1@test.com", "active": True},
                {"id": 2, "email": "invalid-email", "active": False},
                {"id": 3, "email": "user3@test.com", "active": True}
            ]
        },
        "metadata": {
            "total": 3,
            "page": 1,
            "per_page": 10
        }
    }
    
    print("Mock API Response Validation:")
    print(f"Response structure: {list(mock_api_response.keys())}")
    
    # Validate email addresses in response
    if 'data' in mock_api_response and 'users' in mock_api_response['data']:
        users = mock_api_response['data']['users']
        print("\nEmail validation in API response:")
        for user in users:
            email = user.get('email', '')
            is_valid = StringUtils.validate_email(email)
            print(f"  User {user['id']}: {email} - {'Valid' if is_valid else 'Invalid'}")
    
    # Calculate statistics on API data
    if 'data' in mock_api_response and 'users' in mock_api_response['data']:
        user_ids = [user['id'] for user in mock_api_response['data']['users']]
        if user_ids:
            id_stats = MathUtils.calculate_statistics(user_ids)
            print(f"\nUser ID statistics: {id_stats}")
    
    print("\nAPI Testing utilities ready for use!")


if __name__ == "__main__":
    """
    Main execution block - runs all demonstrations when script is executed directly.
    """
    try:
        demonstrate_functionality()
        api_testing_utilities()
        
        print(f"\n🎉 All functions executed successfully!")
        print(f"✅ Ready for API testing and data processing tasks!")
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        raise