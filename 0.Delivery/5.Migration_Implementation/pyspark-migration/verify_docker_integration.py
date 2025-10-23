#!/usr/bin/env python3
"""
Quick verification script for Docker Oracle integration.

Tests that all components are properly installed and can be imported.
Does NOT start Docker containers - just verifies code structure.

Usage:
    python verify_docker_integration.py
"""

import sys
import os

def print_header(text):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def check_file_exists(filepath, description):
    """Check if a file exists."""
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    exists = os.path.exists(full_path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists

def check_import(module_path, description):
    """Check if a module can be imported."""
    try:
        parts = module_path.split(".")
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        print(f"✅ {description}: {module_path}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_path}")
        print(f"   Error: {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: {module_path}")
        print(f"   Warning: {e}")
        return True  # Count as success if import worked but other error

def check_class_methods(module_path, class_name, expected_methods, description):
    """Check if a class has expected methods."""
    try:
        parts = module_path.split(".")
        module = __import__(module_path)
        for part in parts[1:]:
            module = getattr(module, part)
        
        cls = getattr(module, class_name)
        missing_methods = []
        
        for method in expected_methods:
            if not hasattr(cls, method):
                missing_methods.append(method)
        
        if not missing_methods:
            print(f"✅ {description}: {class_name} has all {len(expected_methods)} methods")
            return True
        else:
            print(f"❌ {description}: {class_name} missing methods: {', '.join(missing_methods)}")
            return False
    except Exception as e:
        print(f"❌ {description}: Failed to check {class_name}")
        print(f"   Error: {e}")
        return False

def check_environment_vars():
    """Check environment variable configuration."""
    print("\n📋 Environment Variables (current values):")
    
    env_vars = [
        ("RUN_INTEGRATION_TESTS", "false", "Enable integration tests"),
        ("USE_DOCKER_ORACLE", "false", "Enable Docker Oracle management"),
        ("ORACLE_AUTO_CLEANUP", "false", "Remove container after tests"),
        ("ORACLE_DOCKER_IMAGE", "gvenzl/oracle-free:23-slim", "Oracle Docker image"),
        ("ORACLE_CONTAINER_NAME", "pytest-oracle-integration", "Container name"),
        ("ORACLE_PORT", "1521", "Host port mapping"),
    ]
    
    for var_name, default, description in env_vars:
        value = os.getenv(var_name, default)
        is_default = (value == default)
        marker = "⚙️" if not is_default else "  "
        print(f"{marker} {var_name}={value}")
        if not is_default:
            print(f"   ({description})")
    
    return True

def main():
    """Run all verification checks."""
    print_header("Docker Oracle Integration Verification")
    print("This script verifies the Docker Oracle integration components.")
    print("It does NOT start Docker containers or run tests.")
    
    all_passed = True
    
    # Check files exist
    print_header("1. File Existence Checks")
    files_to_check = [
        ("tests/integration/docker_oracle_manager.py", "Docker Oracle Manager"),
        ("tests/integration/conftest.py", "Integration Test Fixtures"),
        ("pytest.ini", "Pytest Configuration"),
        ("tests/README.md", "Test Documentation"),
        ("tests/DOCKER_INTEGRATION_SUMMARY.md", "Docker Integration Summary"),
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_passed = False
    
    # Check imports (may fail if dependencies not installed)
    print_header("2. Import Checks")
    print("Note: Import errors for pytest, PySpark, etc. are expected if not installed.")
    print("Only docker_oracle_manager.py import is critical.\n")
    
    # Critical import
    if not check_import(
        "tests.integration.docker_oracle_manager",
        "Docker Oracle Manager module"
    ):
        all_passed = False
        print("\n⚠️  CRITICAL: docker_oracle_manager.py cannot be imported!")
    
    # Optional imports (won't fail verification)
    check_import("pytest", "pytest framework (optional)")
    
    # Check class methods
    print_header("3. DockerOracleManager Class Checks")
    expected_methods = [
        "is_docker_available",
        "is_container_running",
        "is_container_exists",
        "pull_image",
        "start_container",
        "wait_for_healthy",
        "verify_hr_schema",
        "ensure_oracle_ready",
        "cleanup",
        "get_connection_details"
    ]
    
    if not check_class_methods(
        "tests.integration.docker_oracle_manager",
        "DockerOracleManager",
        expected_methods,
        "DockerOracleManager methods"
    ):
        all_passed = False
    
    # Check environment configuration
    print_header("4. Environment Configuration")
    check_environment_vars()
    
    # Summary
    print_header("Verification Summary")
    if all_passed:
        print("✅ All critical checks passed!")
        print("\nNext Steps:")
        print("1. Install Docker: https://docs.docker.com/get-docker/")
        print("2. Set environment variables:")
        print("   export USE_DOCKER_ORACLE=true")
        print("   export RUN_INTEGRATION_TESTS=true")
        print("3. Run integration tests:")
        print("   pytest tests/integration/ -v -m oracle")
        return 0
    else:
        print("❌ Some checks failed!")
        print("\nPlease review the errors above and ensure:")
        print("- All files are present in the correct locations")
        print("- docker_oracle_manager.py can be imported")
        print("- DockerOracleManager class has all required methods")
        return 1

if __name__ == "__main__":
    sys.exit(main())
