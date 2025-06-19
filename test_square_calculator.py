import pytest
from square_calculator import calculate_square


class TestCalculateSquare:
    """Test cases for the calculate_square function."""
    
    def test_positive_integer(self):
        """Test squaring a positive integer."""
        assert calculate_square(5) == 25.0
        
    def test_negative_integer(self):
        """Test squaring a negative integer."""
        assert calculate_square(-3) == 9.0
        
    def test_zero(self):
        """Test squaring zero."""
        assert calculate_square(0) == 0.0
        
    def test_positive_float(self):
        """Test squaring a positive float."""
        assert calculate_square(2.5) == 6.25
        
    def test_negative_float(self):
        """Test squaring a negative float."""
        assert calculate_square(-1.5) == 2.25
        
    def test_string_number(self):
        """Test squaring a string representation of a number."""
        assert calculate_square("4") == 16.0
        assert calculate_square("-2") == 4.0
        assert calculate_square("3.5") == 12.25
        
    def test_invalid_string(self):
        """Test error handling for invalid string input."""
        with pytest.raises(ValueError, match="Invalid input: 'invalid' cannot be converted to a number"):
            calculate_square("invalid")
            
    def test_none_input(self):
        """Test error handling for None input."""
        with pytest.raises(TypeError, match="Input cannot be None"):
            calculate_square(None)
            
    def test_empty_string(self):
        """Test error handling for empty string."""
        with pytest.raises(ValueError):
            calculate_square("")
            
    def test_complex_number(self):
        """Test error handling for complex number input."""
        with pytest.raises(ValueError):
            calculate_square("1+2j")


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])