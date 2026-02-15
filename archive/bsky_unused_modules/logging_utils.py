import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from modules import auth

def run(config):
    module_name = __name__.split('.')[-1]
    print(f"{module_name} started")

    # Authenticate
    session = auth.run(config)
    if not session:
        print(f"{module_name} failed: Authentication error")
        return

    # Module-specific logic here
    print(f"Running {module_name} logic...")

    print(f"{module_name} finished")

if __name__ == "__main__":
    # Standalone testing setup
    import json

    # Load config for testing
    with open("../config.json", "r") as config_file:  # Adjust path as needed
        config = json.load(config_file)

    # Run the module independently
    run(config)
