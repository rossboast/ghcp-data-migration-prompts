"""
Integration test configuration and fixtures.

These tests require real Oracle and Cosmos DB instances.
Set RUN_INTEGRATION_TESTS=true to enable.

Setup Option 1 (Automatic Docker):
    1. Install Docker
    2. Set USE_DOCKER_ORACLE=true
    3. Set RUN_INTEGRATION_TESTS=true
    4. Run: pytest tests/integration/ -v -m integration
    
Setup Option 2 (Manual):
    1. Install Oracle manually or use existing instance
    2. Configure .env with connection details
    3. Set RUN_INTEGRATION_TESTS=true
    4. Run: pytest tests/integration/ -v -m integration

Environment Variables:
    - RUN_INTEGRATION_TESTS: Enable integration tests (default: false)
    - USE_DOCKER_ORACLE: Auto-manage Oracle via Docker (default: false)
    - ORACLE_AUTO_CLEANUP: Remove container after tests (default: false)
    - ORACLE_DOCKER_IMAGE: Docker image to use (default: gvenzl/oracle-free:23-slim)
    - ORACLE_CONTAINER_NAME: Container name (default: pytest-oracle-integration)
    - ORACLE_PORT: Host port mapping (default: 1521)
"""

import pytest
import os
from dotenv import load_dotenv

from extractors.oracle_extractor import OracleExtractor
from loaders.cosmos_loader import CosmosLoader
from config.connections import get_oracle_config, get_cosmos_config, OracleConnectionConfig
from utils.spark_session import SparkSessionManager

# Import Docker Oracle manager
try:
    from .docker_oracle_manager import DockerOracleManager
    DOCKER_MANAGER_AVAILABLE = True
except ImportError:
    DOCKER_MANAGER_AVAILABLE = False


# Load environment variables
load_dotenv()


def integration_tests_enabled():
    """Check if integration tests are enabled via environment variable."""
    return os.getenv("RUN_INTEGRATION_TESTS", "false").lower() == "true"


def use_docker_oracle():
    """Check if Docker Oracle management is enabled."""
    return os.getenv("USE_DOCKER_ORACLE", "false").lower() == "true"


@pytest.fixture(scope="session")
def skip_if_disabled():
    """Skip integration tests if not explicitly enabled."""
    if not integration_tests_enabled():
        pytest.skip(
            "Integration tests disabled. Set RUN_INTEGRATION_TESTS=true to enable."
        )


@pytest.fixture(scope="session")
def spark_session(skip_if_disabled):
    """Create Spark session for integration tests."""
    spark = SparkSessionManager.get_session()
    yield spark
    # Cleanup handled by SparkSessionManager


@pytest.fixture(scope="session")
def docker_oracle(skip_if_disabled):
    """
    Manage Oracle Docker container for integration tests.
    
    Only active when USE_DOCKER_ORACLE=true.
    Automatically pulls image, starts container, waits for ready state,
    and verifies HR schema.
    
    Container is reused between test runs for speed.
    Set ORACLE_AUTO_CLEANUP=true to remove container after tests.
    """
    if not use_docker_oracle():
        pytest.skip("Docker Oracle management disabled. Set USE_DOCKER_ORACLE=true to enable.")
    
    if not DOCKER_MANAGER_AVAILABLE:
        pytest.skip("DockerOracleManager not available. Check docker_oracle_manager.py exists.")
    
    # Create manager with optional customization from environment
    manager = DockerOracleManager(
        image=os.getenv("ORACLE_DOCKER_IMAGE"),
        container_name=os.getenv("ORACLE_CONTAINER_NAME"),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        password=os.getenv("ORACLE_PASSWORD"),
        auto_cleanup=os.getenv("ORACLE_AUTO_CLEANUP", "false").lower() == "true"
    )
    
    # Ensure Oracle is ready (pull, start, wait, verify)
    print("\n" + "="*80)
    print("🐳 Setting up Oracle Docker container for integration tests...")
    print("="*80)
    
    if not manager.ensure_oracle_ready():
        pytest.skip("Failed to setup Oracle Docker container. Check Docker installation and logs.")
    
    print("\n" + "="*80)
    print("✅ Oracle Docker container ready for testing!")
    print("="*80 + "\n")
    
    yield manager
    
    # Cleanup (only if auto_cleanup=true)
    if manager.auto_cleanup:
        print("\n" + "="*80)
        print("🧹 Cleaning up Oracle Docker container...")
        print("="*80)
        manager.cleanup()
        print("✅ Cleanup complete!\n")
    else:
        print("\n" + "="*80)
        print("ℹ️  Oracle container left running for fast reruns.")
        print(f"   To stop: docker stop {manager.container_name}")
        print(f"   To remove: docker rm {manager.container_name}")
        print(f"   To auto-cleanup: Set ORACLE_AUTO_CLEANUP=true")
        print("="*80 + "\n")


@pytest.fixture(scope="session")
def oracle_config(skip_if_disabled, request):
    """
    Get Oracle configuration from Docker or environment.
    
    Priority:
        1. Docker Oracle (if USE_DOCKER_ORACLE=true)
        2. Manual configuration from environment variables
    """
    # Try Docker Oracle first
    if use_docker_oracle():
        if not DOCKER_MANAGER_AVAILABLE:
            pytest.skip("Docker Oracle requested but DockerOracleManager not available")
        
        # Get docker_oracle fixture
        try:
            docker_mgr = request.getfixturevalue('docker_oracle')
            conn_details = docker_mgr.get_connection_details()
            
            return OracleConnectionConfig(
                host=conn_details["host"],
                port=conn_details["port"],
                service=conn_details["service_name"],
                user=conn_details["username"],
                password=conn_details["password"]
            )
        except Exception as e:
            pytest.skip(f"Failed to get Docker Oracle configuration: {e}")
    
    # Fall back to manual configuration
    try:
        config = get_oracle_config()
        return config
    except Exception as e:
        pytest.skip(f"Oracle configuration not available: {e}")


@pytest.fixture(scope="session")
def cosmos_config(skip_if_disabled):
    """Get Cosmos DB configuration from environment."""
    try:
        config = get_cosmos_config()
        return config
    except Exception as e:
        pytest.skip(f"Cosmos DB configuration not available: {e}")


@pytest.fixture(scope="session")
def oracle_extractor(oracle_config, spark_session):
    """Create Oracle extractor for integration tests."""
    extractor = OracleExtractor(oracle_config)
    
    # Validate connection
    try:
        if not extractor.validate_connection():
            pytest.skip("Oracle database not accessible")
    except Exception as e:
        pytest.skip(f"Oracle connection failed: {e}")
    
    return extractor


@pytest.fixture(scope="session")
def cosmos_loader(cosmos_config, spark_session):
    """Create Cosmos DB loader for integration tests."""
    loader = CosmosLoader(
        cosmos_config,
        container="integration_test_data",
        batch_size=100
    )
    
    # Validate connection
    try:
        if not loader.validate_target_connection():
            pytest.skip("Cosmos DB not accessible")
    except Exception as e:
        pytest.skip(f"Cosmos DB connection failed: {e}")
    
    return loader


@pytest.fixture(scope="function")
def test_container_name():
    """Generate unique container name for each test."""
    import uuid
    return f"test_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="function")
def cleanup_cosmos_container(cosmos_config, test_container_name):
    """Cleanup Cosmos DB test container after test."""
    yield
    
    # Cleanup logic here (delete test container)
    # This would require Cosmos SDK client
    try:
        from azure.cosmos import CosmosClient
        client = CosmosClient(cosmos_config.endpoint, cosmos_config.key)
        database = client.get_database_client(cosmos_config.database)
        
        try:
            container = database.get_container_client(test_container_name)
            database.delete_container(test_container_name)
        except:
            pass  # Container might not exist
    except ImportError:
        # Cosmos SDK not available, skip cleanup
        pass


# Markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real databases)"
    )
    config.addinivalue_line(
        "markers", "oracle: mark test as requiring Oracle database"
    )
    config.addinivalue_line(
        "markers", "cosmos: mark test as requiring Cosmos DB"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Known test data from HR schema
EXPECTED_COUNTS = {
    "regions": 4,
    "countries": 25,
    "locations": 23,
    "departments": 27,
    "jobs": 19,
    "employees": 107,
    "job_history": 10
}


EXPECTED_REGION_NAMES = [
    "Europe",
    "Americas",
    "Asia",
    "Middle East and Africa"
]


EXPECTED_EMPLOYEE_COLUMNS = [
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "phone_number",
    "hire_date",
    "job_id",
    "salary",
    "commission_pct",
    "manager_id",
    "department_id"
]
