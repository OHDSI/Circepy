

def pytest_addoption(parser):
    parser.addoption(
        "--sample-cohorts", action="store_true", default=False, help="Randomly sample 10 cohorts for testing"
    )
    parser.addoption(
        "--cohort-filter", action="store", default=None, help="Comma-separated list of specific cohort files to test (e.g. '532.json,932.json')"
    )
