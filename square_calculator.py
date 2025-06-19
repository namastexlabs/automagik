def calculate_square(number):
    """
    Calculate the square of a number with proper error handling.
    
    Args:
        number: The number to square (int, float, or string representation of a number)
        
    Returns:
        float: The square of the input number
        
    Raises:
        TypeError: If the input cannot be converted to a number
        ValueError: If the input is not a valid number
    """
    try:
        # Convert input to float to handle both int and float inputs
        num = float(number)
        return num ** 2
    except (TypeError, ValueError) as e:
        if number is None:
            raise TypeError("Input cannot be None")
        raise ValueError(f"Invalid input: '{number}' cannot be converted to a number")


if __name__ == "__main__":
    # Basic usage examples
    print(f"Square of 5: {calculate_square(5)}")
    print(f"Square of 3.5: {calculate_square(3.5)}")
    print(f"Square of '4': {calculate_square('4')}")
    
    # Error handling examples
    try:
        calculate_square("invalid")
    except ValueError as e:
        print(f"Error: {e}")
        
    try:
        calculate_square(None)
    except TypeError as e:
        print(f"Error: {e}")