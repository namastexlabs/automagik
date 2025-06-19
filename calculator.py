def calculator(num1, num2, operation):
    """
    Simple calculator function that performs basic arithmetic operations.
    
    Args:
        num1 (float): First number
        num2 (float): Second number
        operation (str): Operation to perform ('add', 'subtract', 'multiply', 'divide')
    
    Returns:
        float: Result of the operation
    
    Raises:
        ValueError: If operation is not supported or division by zero
    """
    if operation == 'add':
        return num1 + num2
    elif operation == 'subtract':
        return num1 - num2
    elif operation == 'multiply':
        return num1 * num2
    elif operation == 'divide':
        if num2 == 0:
            raise ValueError("Cannot divide by zero")
        return num1 / num2
    else:
        raise ValueError(f"Unsupported operation: {operation}")


def add(num1, num2):
    """Add two numbers."""
    return num1 + num2


def subtract(num1, num2):
    """Subtract second number from first number."""
    return num1 - num2


def multiply(num1, num2):
    """Multiply two numbers."""
    return num1 * num2


def divide(num1, num2):
    """Divide first number by second number."""
    if num2 == 0:
        raise ValueError("Cannot divide by zero")
    return num1 / num2


if __name__ == "__main__":
    print("Calculator Example Usage:")
    print(f"10 + 5 = {add(10, 5)}")
    print(f"10 - 5 = {subtract(10, 5)}")
    print(f"10 * 5 = {multiply(10, 5)}")
    print(f"10 / 5 = {divide(10, 5)}")
    
    print(f"\nUsing main calculator function:")
    print(f"10 + 5 = {calculator(10, 5, 'add')}")
    print(f"10 - 5 = {calculator(10, 5, 'subtract')}")
    print(f"10 * 5 = {calculator(10, 5, 'multiply')}")
    print(f"10 / 5 = {calculator(10, 5, 'divide')}")