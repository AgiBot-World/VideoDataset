import os
from pathlib import Path

import pytest


@pytest.fixture
def parent_dir(request):
    """Get the parent directory for test data.

    Priority:
    1. Use directory specified by TEST_DATA_DIR environment variable
    2. Fallback to the parent directory of the test file
    """
    parent_dir = os.environ.get("TEST_DATA_DIR")
    if parent_dir:
        return Path(parent_dir)
    return Path(__file__).parent
