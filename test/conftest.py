from pathlib import Path
import pytest

@pytest.fixture
def get_pancreas_ct_data():
    return Path("test/data/input/07-06-2012-NA-PANCREAS-59677/201.000000-PANCREAS DI iDose 3-97846")