import os

def check_file_exists(file_path):
    if os.path.exists(file_path):
        print(f"✓ File '{file_path}' exists")
    else:
        print(f"✗ File '{file_path}' does not exist")

if __name__ == "__main__":
    test_files = [
        "CLAUDE.md",
        "nonexistent_file.txt",
        "test_file_check.py"
    ]
    
    print("File existence check:")
    for file_path in test_files:
        check_file_exists(file_path)