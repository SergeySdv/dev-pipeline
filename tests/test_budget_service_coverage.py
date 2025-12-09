"""
Property-based test for test coverage non-regression.

**Feature: services-architecture-completion, Property 9: Test coverage non-regression**
**Validates: Requirements 5.2**

This test ensures that the BudgetService has comprehensive test coverage
for all its public methods, verifying that moving logic from workers to
services doesn't result in decreased test coverage.
"""

import inspect
import pytest
from tasksgodzilla.services.budget import BudgetService


def test_budget_service_method_coverage():
    """
    Verify that all public methods of BudgetService have corresponding tests.
    
    This is a meta-test that ensures test coverage non-regression by checking
    that every public method in BudgetService has at least one test case.
    """
    # Get all public methods of BudgetService (excluding private and dunder methods)
    service_methods = [
        name for name, method in inspect.getmembers(BudgetService, predicate=inspect.isfunction)
        if not name.startswith('_')
    ]
    
    # Expected public methods that should be tested
    expected_methods = {
        'check_and_track',
        'check_protocol_budget',
        'check_step_budget',
        'record_usage',
    }
    
    # Verify all expected methods exist
    actual_methods = set(service_methods)
    assert expected_methods.issubset(actual_methods), (
        f"Missing expected methods: {expected_methods - actual_methods}"
    )
    
    # Import the test module to verify tests exist
    import tests.test_budget_service as test_module
    
    # Get all test functions
    test_functions = [
        name for name, obj in inspect.getmembers(test_module, predicate=inspect.isfunction)
        if name.startswith('test_')
    ]
    
    # Verify each method has at least one test
    method_test_coverage = {}
    for method in expected_methods:
        # Look for tests that mention this method in their name
        related_tests = [
            test_name for test_name in test_functions
            if method.replace('_', '') in test_name.replace('_', '')
        ]
        method_test_coverage[method] = related_tests
    
    # Verify all methods have tests
    untested_methods = [
        method for method, tests in method_test_coverage.items()
        if not tests
    ]
    
    assert not untested_methods, (
        f"The following BudgetService methods lack test coverage: {untested_methods}. "
        f"This violates the test coverage non-regression property."
    )
    
    # Log coverage summary
    print("\n=== BudgetService Test Coverage Summary ===")
    for method, tests in sorted(method_test_coverage.items()):
        print(f"{method}: {len(tests)} test(s)")
        for test in tests[:3]:  # Show first 3 tests
            print(f"  - {test}")
        if len(tests) > 3:
            print(f"  ... and {len(tests) - 3} more")


def test_budget_service_test_count_minimum():
    """
    Verify that BudgetService has a minimum number of tests.
    
    This ensures that the service has comprehensive test coverage,
    not just one test per method.
    """
    import tests.test_budget_service as test_module
    
    # Get all test functions
    test_functions = [
        name for name, obj in inspect.getmembers(test_module, predicate=inspect.isfunction)
        if name.startswith('test_')
    ]
    
    # We should have at least 20 tests for BudgetService
    # (as of this implementation, we have 23 tests)
    min_tests = 20
    actual_count = len(test_functions)
    
    assert actual_count >= min_tests, (
        f"BudgetService has only {actual_count} tests, expected at least {min_tests}. "
        f"This suggests test coverage may have regressed."
    )


def test_budget_service_critical_scenarios_covered():
    """
    Verify that critical scenarios are covered by tests.
    
    This ensures that important edge cases and integration scenarios
    are tested, not just happy paths.
    """
    import tests.test_budget_service as test_module
    
    # Critical scenarios that must be tested
    critical_scenarios = {
        'strict_mode': ['strict'],
        'warn_mode': ['warn'],
        'off_mode': ['off'],
        'budget_exceeded': ['exceed'],
        'multiple_protocols': ['multiple'],
        'multiple_steps': ['multiple'],
        'cumulative_tracking': ['cumulative'],
        'exact_limit': ['exact'],
        'no_limit': ['no_limit'],
    }
    
    # Get all test functions
    test_functions = [
        name for name, obj in inspect.getmembers(test_module, predicate=inspect.isfunction)
        if name.startswith('test_')
    ]
    
    # Check which scenarios are covered
    scenario_coverage = {}
    for scenario, keywords in critical_scenarios.items():
        covered = any(
            any(keyword in test_name.lower() for keyword in keywords)
            for test_name in test_functions
        )
        scenario_coverage[scenario] = covered
    
    # Verify all critical scenarios are covered
    uncovered_scenarios = [
        scenario for scenario, covered in scenario_coverage.items()
        if not covered
    ]
    
    assert not uncovered_scenarios, (
        f"The following critical scenarios lack test coverage: {uncovered_scenarios}. "
        f"This violates the test coverage non-regression property."
    )
    
    # Log scenario coverage
    print("\n=== Critical Scenario Coverage ===")
    for scenario, covered in sorted(scenario_coverage.items()):
        status = "✓" if covered else "✗"
        print(f"{status} {scenario}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
