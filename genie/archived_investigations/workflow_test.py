#!/usr/bin/env python3
"""
Simple workflow test file to verify the workflow system is functioning.
Includes debug logging to track execution path.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Configure logging for debug tracking
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/workflow_test_debug.log')
    ]
)

logger = logging.getLogger('workflow_test')


def main():
    """Main function to test workflow system and track execution."""
    logger.debug("=== WORKFLOW TEST EXECUTION START ===")
    logger.debug(f"Execution time: {datetime.now().isoformat()}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug(f"Current working directory: {Path.cwd()}")
    logger.debug(f"Script location: {Path(__file__).absolute()}")
    
    try:
        logger.info("Initializing workflow test...")
        
        # Main test message
        message = "Workflow system is working!"
        logger.debug(f"Test message prepared: '{message}'")
        
        # Print the required message
        print(message)
        logger.info(f"Successfully printed message: {message}")
        
        # Additional debugging information
        logger.debug("Testing system environment...")
        logger.debug(f"PATH environment: {sys.path[:3]}...")  # First 3 paths only
        
        logger.info("=== WORKFLOW TEST COMPLETED SUCCESSFULLY ===")
        return 0
        
    except Exception as e:
        logger.error(f"Workflow test failed with exception: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.debug("=== WORKFLOW TEST FAILED ===")
        return 1
    
    finally:
        logger.debug("=== WORKFLOW TEST EXECUTION END ===")


if __name__ == "__main__":
    logger.debug("Script executed directly")
    exit_code = main()
    logger.debug(f"Exiting with code: {exit_code}")
    sys.exit(exit_code)