class AutomagikAgentsDependencies:
    def __init__(
        self,
        # ... existing parameters ...
        test_mode: bool = False  # Add test mode flag
    ):
        # ... existing initialization ...
        self.test_mode = test_mode
        
        # Skip memory operations in test mode
        if not test_mode:
            # Initialize memory operations
            pass
        else:
            # Mock or skip memory operations for testing
            pass 