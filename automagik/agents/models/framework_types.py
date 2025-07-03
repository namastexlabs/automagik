"""Framework type enums for consistent agent framework identification."""

from enum import Enum


class FrameworkType(str, Enum):
    """Supported AI framework types.
    
    This enum ensures consistent framework naming throughout the system
    and prevents issues with mismatched framework type strings.
    """
    
    PYDANTIC_AI = "pydanticai"
    AGNO = "agno"
    CLAUDE_CODE = "claude_code"
    LANGCHAIN = "langchain"
    LANGGRAPH = "langgraph"
    AUTO = "auto"  # Allow auto-selection based on content type
    
    @classmethod
    def default(cls) -> "FrameworkType":
        """Get the default framework type."""
        return cls.PYDANTIC_AI
    
    @classmethod
    def normalize(cls, framework_name: str) -> "FrameworkType":
        """Normalize a framework name to the correct enum value.
        
        Args:
            framework_name: Framework name string (may have inconsistent naming)
            
        Returns:
            Normalized FrameworkType enum
            
        Raises:
            ValueError: If framework name is not recognized
        """
        if not framework_name:
            return cls.default()
        
        # Only normalize for exact known mappings
        name_lower = framework_name.lower()
        
        # Direct string mappings (no legacy pydantic_ai support)
        name_mappings = {
            "pydanticai": cls.PYDANTIC_AI,
            "agno": cls.AGNO,
            "claude": cls.CLAUDE_CODE,  # Allow "claude" as alias for "claude_code"
            "claude_code": cls.CLAUDE_CODE,
            "claude-code": cls.CLAUDE_CODE,
            "langchain": cls.LANGCHAIN,
            "langgraph": cls.LANGGRAPH,
        }
        
        # Check direct mappings first
        if name_lower in name_mappings:
            return name_mappings[name_lower]
        
        # Remove special characters for fuzzy matching (but not for pydantic_ai)
        if "pydantic" in name_lower and "_" in name_lower:
            # Explicitly reject pydantic_ai variations
            raise ValueError("Framework 'pydantic_ai' is no longer supported. Use 'pydanticai' instead.")
        
        # Normalize other framework names (remove underscores/hyphens)
        name_lower.replace("_", "").replace("-", "")
        
        
        normalized = name_mappings.get(name_lower)
        if normalized:
            return normalized
        
        # Only allow direct enum value lookup for exact matches
        for enum_member in cls:
            if enum_member.value == framework_name:
                return enum_member
        
        raise ValueError(f"Unknown framework type: {framework_name}")
    
    def __str__(self) -> str:
        """String representation returns the enum value."""
        return self.value