"""Service layer wrapper for room allocation operations."""

from allocation_algorithm import run_allocation_algorithm


def run_allocation():
    """Run the allocation workflow and return a summary payload."""
    return run_allocation_algorithm()
