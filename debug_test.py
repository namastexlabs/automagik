from src.mcp.security import validate_server_name, ValidationError

test_names = [
    "",  # Empty
    "a" * 65,  # Too long
    "test server",  # Spaces
    "test@server",  # Special chars
    "123test",  # Start with number
    "system",  # Reserved name
    "admin"   # Reserved name
]

for name in test_names:
    try:
        result = validate_server_name(name)
        print(f"PASS: '{name}' -> {result}")
    except ValidationError as e:
        print(f"FAIL: '{name}' -> {e}")
    except Exception as e:
        print(f"ERROR: '{name}' -> {e}") 