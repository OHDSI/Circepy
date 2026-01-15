
import pytest

def pytest_addoption(parser):
    parser.addoption(
        "--sample-cohorts", action="store_true", default=True, help="Randomly sample 10 cohorts for testing"
    )
