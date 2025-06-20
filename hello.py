#!/usr/bin/env python3
"""
Hello World Module

This module provides a comprehensive implementation of a hello world function
with proper type hints, docstrings, and error handling. Created for cost
tracking testing purposes to generate meaningful token usage.

Author: Mr. BUILDER (Claude Code Workflow)
Date: 2024
Version: 1.0.0
"""

from typing import Optional, Union, Dict, Any
import logging
from datetime import datetime


# Configure logging for comprehensive documentation
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HelloWorldConfig:
    """
    Configuration class for HelloWorld functionality.
    
    This class encapsulates configuration options for the hello world
    implementation, allowing for customizable greetings and output formats.
    
    Attributes:
        default_name (str): The default name to use when none is provided
        greeting_prefix (str): The prefix for greeting messages
        include_timestamp (bool): Whether to include timestamp in output
        output_format (str): The format style for output ('simple' or 'detailed')
    """
    
    def __init__(
        self,
        default_name: str = "World",
        greeting_prefix: str = "Hello",
        include_timestamp: bool = False,
        output_format: str = "simple"
    ) -> None:
        """
        Initialize HelloWorld configuration.
        
        Args:
            default_name: Default name to greet when none provided
            greeting_prefix: Prefix for the greeting message
            include_timestamp: Whether to include current timestamp
            output_format: Output format style ('simple' or 'detailed')
        
        Raises:
            ValueError: If output_format is not 'simple' or 'detailed'
        """
        if output_format not in ['simple', 'detailed']:
            raise ValueError("output_format must be 'simple' or 'detailed'")
        
        self.default_name = default_name
        self.greeting_prefix = greeting_prefix
        self.include_timestamp = include_timestamp
        self.output_format = output_format


def hello_world(
    name: Optional[str] = None,
    config: Optional[HelloWorldConfig] = None,
    custom_message: Optional[str] = None
) -> str:
    """
    Generate a comprehensive hello world greeting message.
    
    This function creates a personalized greeting message with various
    customization options. It supports custom names, configuration objects,
    and completely custom messages for maximum flexibility.
    
    Args:
        name: The name to include in the greeting. If None, uses config default
              or "World" if no config provided.
        config: Optional HelloWorldConfig object for customization. If None,
                uses default configuration settings.
        custom_message: Optional custom message to return instead of generated
                       greeting. Overrides all other parameters if provided.
    
    Returns:
        str: A formatted greeting message based on the provided parameters.
             Format varies based on configuration settings:
             - Simple format: "{greeting_prefix}, {name}!"
             - Detailed format: Includes timestamp and additional metadata
    
    Raises:
        TypeError: If name is provided but not a string
        ValueError: If custom_message is empty string
    
    Examples:
        >>> hello_world()
        'Hello, World!'
        
        >>> hello_world("Alice")
        'Hello, Alice!'
        
        >>> config = HelloWorldConfig(greeting_prefix="Hi", include_timestamp=True)
        >>> hello_world("Bob", config=config)
        'Hi, Bob! (Generated at: 2024-01-01 12:00:00)'
        
        >>> hello_world(custom_message="Greetings, Earth!")
        'Greetings, Earth!'
    
    Note:
        This function is designed to be comprehensive for token usage testing
        while maintaining practical utility. The extensive documentation and
        type hints ensure robust development patterns.
    """
    # Input validation with comprehensive error messages
    if name is not None and not isinstance(name, str):
        raise TypeError(
            f"Expected 'name' to be a string or None, got {type(name).__name__}"
        )
    
    if custom_message is not None:
        if not isinstance(custom_message, str):
            raise TypeError(
                f"Expected 'custom_message' to be a string or None, "
                f"got {type(custom_message).__name__}"
            )
        if custom_message == "":
            raise ValueError("custom_message cannot be an empty string")
        
        logger.info(f"Returning custom message: {custom_message}")
        return custom_message
    
    # Use provided config or create default
    if config is None:
        config = HelloWorldConfig()
    
    # Determine the name to use in the greeting
    target_name = name if name is not None else config.default_name
    
    # Generate base greeting message
    base_message = f"{config.greeting_prefix}, {target_name}!"
    
    # Apply formatting based on configuration
    if config.output_format == "simple":
        result = base_message
    else:  # detailed format
        timestamp_str = ""
        if config.include_timestamp:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            timestamp_str = f" (Generated at: {current_time})"
        
        result = f"{base_message}{timestamp_str}"
    
    # Log the operation for debugging and monitoring
    logger.info(f"Generated greeting for '{target_name}' using {config.output_format} format")
    
    return result


def get_hello_world_metadata() -> Dict[str, Any]:
    """
    Get metadata information about the hello world implementation.
    
    This function returns comprehensive metadata about the hello world
    module, including version information, capabilities, and configuration
    options. Useful for introspection and debugging purposes.
    
    Returns:
        Dict[str, Any]: A dictionary containing metadata with the following keys:
            - version (str): Module version number
            - author (str): Module author information
            - capabilities (List[str]): List of supported features
            - default_config (Dict[str, Any]): Default configuration values
            - supported_formats (List[str]): Supported output formats
            - timestamp (str): Current timestamp when metadata was generated
    
    Examples:
        >>> metadata = get_hello_world_metadata()
        >>> print(metadata['version'])
        '1.0.0'
        >>> print(metadata['capabilities'])
        ['custom_names', 'configurable_greetings', 'timestamp_support', 'custom_messages']
    """
    default_config = HelloWorldConfig()
    
    return {
        "version": "1.0.0",
        "author": "Mr. BUILDER (Claude Code Workflow)",
        "description": "Comprehensive hello world implementation with extensive features",
        "capabilities": [
            "custom_names",
            "configurable_greetings", 
            "timestamp_support",
            "custom_messages",
            "multiple_output_formats",
            "comprehensive_error_handling"
        ],
        "default_config": {
            "default_name": default_config.default_name,
            "greeting_prefix": default_config.greeting_prefix,
            "include_timestamp": default_config.include_timestamp,
            "output_format": default_config.output_format
        },
        "supported_formats": ["simple", "detailed"],
        "timestamp": datetime.now().isoformat(),
        "module_path": __file__ if '__file__' in globals() else "unknown"
    }


def demonstrate_hello_world() -> None:
    """
    Demonstrate various capabilities of the hello world implementation.
    
    This function showcases different usage patterns and features of the
    hello_world function, serving as both documentation and testing utility.
    It prints various examples to demonstrate the flexibility and robustness
    of the implementation.
    
    The demonstration includes:
    - Basic usage with default parameters
    - Custom name specification
    - Configuration object usage
    - Custom message functionality
    - Error handling examples
    - Metadata retrieval
    
    Note:
        This function produces output to stdout and is primarily intended
        for demonstration and testing purposes.
    """
    print("=== Hello World Demonstration ===\n")
    
    # Basic usage
    print("1. Basic usage:")
    print(f"   {hello_world()}")
    
    # Custom name
    print("\n2. Custom name:")
    print(f"   {hello_world('Alice')}")
    
    # Custom configuration
    print("\n3. Custom configuration:")
    config = HelloWorldConfig(
        greeting_prefix="Hi there",
        include_timestamp=True,
        output_format="detailed"
    )
    print(f"   {hello_world('Bob', config=config)}")
    
    # Custom message
    print("\n4. Custom message:")
    print(f"   {hello_world(custom_message='Greetings from the comprehensive hello world!')}")
    
    # Metadata
    print("\n5. Module metadata:")
    metadata = get_hello_world_metadata()
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    
    print("\n=== Demonstration Complete ===")


if __name__ == "__main__":
    """
    Main execution block for the hello world module.
    
    When this module is run directly, it will execute the demonstration
    function to showcase all available features and capabilities.
    """
    demonstrate_hello_world()