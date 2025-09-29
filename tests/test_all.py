#!/usr/bin/env python3
"""
Test script to verify all MCP AI Foundation tools are working correctly.
Run this after installation to ensure everything is set up properly.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_notebook():
    """Test Notebook v6.2.0 imports and basic functionality"""
    print("Testing Notebook v6.2.0...")
    try:
        # Test three-file architecture
        import notebook_shared
        import notebook_storage
        import notebook_main
        
        # Verify version
        assert notebook_shared.VERSION == "6.2.0", f"Version mismatch: {notebook_shared.VERSION}"
        
        # Test that key functions exist
        assert hasattr(notebook_main, 'remember')
        assert hasattr(notebook_main, 'recall')
        assert hasattr(notebook_main, 'get_status')
        assert hasattr(notebook_main, 'pin_note')
        assert hasattr(notebook_main, 'compact')  # New in v6.2
        assert hasattr(notebook_main, 'recent_dirs')  # New in v6.2
        
        print("✓ Notebook v6.2.0 - All tests passed")
        return True
    except Exception as e:
        print(f"✗ Notebook failed: {e}")
        return False

def test_task_manager():
    """Test Task Manager v3.1.0 imports and basic functionality"""
    print("Testing Task Manager v3.1.0...")
    try:
        import task_manager_mcp
        
        # Verify version
        assert task_manager_mcp.VERSION == "3.1.0", f"Version mismatch: {task_manager_mcp.VERSION}"
        
        # Test that key functions exist
        assert hasattr(task_manager_mcp, 'add_task')
        assert hasattr(task_manager_mcp, 'list_tasks')
        assert hasattr(task_manager_mcp, 'complete_task')
        assert hasattr(task_manager_mcp, 'task_stats')
        assert hasattr(task_manager_mcp, 'batch')
        
        print("✓ Task Manager v3.1.0 - All tests passed")
        return True
    except Exception as e:
        print(f"✗ Task Manager failed: {e}")
        return False

def test_teambook():
    """Test Teambook v7.0.0 imports and basic functionality"""
    print("Testing Teambook v7.0.0...")
    try:
        # Test four-module architecture
        import teambook_shared_mcp
        import teambook_storage_mcp
        import teambook_api_mcp
        import teambook_main_mcp
        
        # Verify version
        assert teambook_shared_mcp.VERSION == "7.0.0", f"Version mismatch: {teambook_shared_mcp.VERSION}"
        
        # Test that key functions exist in API module
        assert hasattr(teambook_api_mcp, 'write')
        assert hasattr(teambook_api_mcp, 'read')
        assert hasattr(teambook_api_mcp, 'create_teambook')
        assert hasattr(teambook_api_mcp, 'claim')
        assert hasattr(teambook_api_mcp, 'release')
        assert hasattr(teambook_api_mcp, 'evolve')  # Evolution system
        assert hasattr(teambook_api_mcp, 'attempt')
        assert hasattr(teambook_api_mcp, 'combine')
        
        print("✓ Teambook v7.0.0 - All tests passed")
        return True
    except Exception as e:
        print(f"✗ Teambook failed: {e}")
        return False

def test_world():
    """Test World v3.0.0 imports and basic functionality"""
    print("Testing World v3.0.0...")
    try:
        import world_mcp
        
        # Verify version
        assert world_mcp.VERSION == "3.0.0", f"Version mismatch: {world_mcp.VERSION}"
        
        # Test that key functions exist
        assert hasattr(world_mcp, 'world_command')
        assert hasattr(world_mcp, 'datetime_command')
        assert hasattr(world_mcp, 'weather_command')
        assert hasattr(world_mcp, 'context_command')
        assert hasattr(world_mcp, 'batch')
        
        print("✓ World v3.0.0 - All tests passed")
        return True
    except Exception as e:
        print(f"✗ World failed: {e}")
        return False

def test_environment_setup():
    """Test that environment variables can be set"""
    print("Testing environment configuration...")
    try:
        # Test setting environment variables
        os.environ['NOTEBOOK_FORMAT'] = 'pipe'
        os.environ['TASKS_FORMAT'] = 'pipe'
        os.environ['TEAMBOOK_FORMAT'] = 'pipe'
        os.environ['WORLD_FORMAT'] = 'pipe'
        os.environ['AI_ID'] = 'Test-Agent-001'
        
        # Verify they're accessible
        import notebook_shared
        import teambook_shared_mcp
        
        assert notebook_shared.OUTPUT_FORMAT in ['pipe', 'json']
        assert teambook_shared_mcp.OUTPUT_FORMAT in ['pipe', 'json']
        
        print("✓ Environment configuration - All tests passed")
        return True
    except Exception as e:
        print(f"✗ Environment setup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MCP AI Foundation - Tool Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Notebook v6.2.0", test_notebook()))
    results.append(("Task Manager v3.1.0", test_task_manager()))
    results.append(("Teambook v7.0.0", test_teambook()))
    results.append(("World v3.0.0", test_world()))
    results.append(("Environment Setup", test_environment_setup()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name:25} {status}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    # Return exit code
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
