import pytest
from pydantic import ValidationError
from models.schemas import JobCreate, JobType

# Common template data for creating a job
VALID_BASE_DATA = {
    "title": "Need helper for gardening",
    "description": "Help clean the garden backyard and water plants",
    "category": "household",
    "pin_code": "123456",
    "pay": 250.0
}

def test_part_time_job_valid():
    """Verify that a part-time job is valid."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time"
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.part_time


def test_full_time_job_valid():
    """Verify that a full-time job is valid."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "full_time"
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.full_time


def test_invalid_job_type():
    """Verify that specifying an invalid job type raises a validation error."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "invalid_type"
    }
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(**data)
    assert "Input should be 'part_time' or 'full_time'" in str(exc_info.value)
