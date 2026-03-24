import pytest
from ertimes.io import download_emergency_data


def test_nonexistent_state_raises_error():
    """Test that download_emergency_data raises ValueError for a nonexistent state."""
    with pytest.raises(ValueError, match="State 'texas' is not supported"):
        download_emergency_data(state="texas") 

