# Test Project: Data Processing Utilities

## Overview

This is a comprehensive test project demonstrating Python programming best practices, including:
- Multiple utility functions for data processing
- Proper documentation and type hints
- Clean code structure and organization
- API testing capabilities

## Features

### 1. Mathematical Operations
- Basic arithmetic calculations
- Statistical computations (mean, median, mode)
- Number validation and formatting

### 2. String Processing
- Text cleaning and normalization
- Word frequency analysis
- String validation utilities

### 3. Data Manipulation
- List processing and filtering
- Dictionary operations
- Data structure transformations

### 4. File Operations
- JSON file reading/writing
- CSV data processing
- Configuration file handling

## Project Structure

```
test-project/
├── README.md           # This file
├── main.py            # Main application with multiple utility functions
├── requirements.txt   # Python dependencies
└── data/              # Sample data files (created at runtime)
```

## Installation

1. Clone or navigate to this project directory
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the main script to see all functions in action:

```bash
python main.py
```

The script will demonstrate:
- Mathematical calculations
- String processing examples
- Data manipulation operations
- File I/O operations
- API response simulation for testing

## API Testing

This project includes utilities that can be used for API testing:
- Data validation functions
- Response parsing utilities  
- Mock data generation
- Error handling demonstrations

## Functions Overview

### Mathematical Functions
- `calculate_statistics(numbers)` - Calculate mean, median, mode
- `is_prime(number)` - Check if a number is prime
- `factorial(n)` - Calculate factorial recursively

### String Functions
- `clean_text(text)` - Clean and normalize text
- `word_frequency(text)` - Count word frequencies
- `validate_email(email)` - Basic email validation

### Data Functions
- `filter_data(data, condition)` - Filter data based on conditions
- `transform_dict(data, key_map)` - Transform dictionary keys
- `merge_datasets(dataset1, dataset2)` - Merge two datasets

### File Functions
- `save_json(data, filename)` - Save data to JSON file
- `load_json(filename)` - Load data from JSON file
- `process_csv_data(data)` - Process CSV-like data structures

## Requirements

- Python 3.8+
- See requirements.txt for package dependencies

## License

This is a test project for demonstration purposes.