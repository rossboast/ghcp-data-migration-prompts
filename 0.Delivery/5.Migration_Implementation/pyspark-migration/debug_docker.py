"""Debug script to test DockerOracleManager"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.integration.docker_oracle_manager import DockerOracleManager

# Try to create and run the manager
print("Creating DockerOracleManager...")
manager = DockerOracleManager(
    image="gvenzl/oracle-free:23-slim-faststart",
    container_name="oracle-test",
    port=1521,
    password="pytest_oracle",
    auto_cleanup=False
)

print("\nTrying to ensure Oracle is ready...")
result = manager.ensure_oracle_ready()
print(f"\nResult: {result}")

if result:
    print("\n✓ Success! Oracle is ready")
    details = manager.get_connection_details()
    print(f"Connection details: {details}")
else:
    print("\n✗ Failed to setup Oracle")
