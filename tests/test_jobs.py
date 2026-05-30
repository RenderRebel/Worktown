import pytest
from pydantic import ValidationError
from models.schemas import JobCreate, JobType, PartTimeType, PayBasis

# Common template data for creating a job
VALID_BASE_DATA = {
    "title": "Need helper for gardening",
    "description": "Help clean the garden backyard and water plants",
    "category": "household",
    "pin_code": "123456",
    "pay": 250.0
}

def test_part_time_one_time_valid():
    """Verify that a one-time part-time job with hours is valid and gets hourly pay_basis."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time",
        "part_time_type": "one_time",
        "hours": 4.5
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.part_time
    assert job.part_time_type == PartTimeType.one_time
    assert job.hours == 4.5
    assert job.pay_basis == PayBasis.hourly


def test_part_time_one_time_missing_hours():
    """Verify that a one-time part-time job without hours fails validation."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time",
        "part_time_type": "one_time"
        # missing hours
    }
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(**data)
    assert "hours is required and must be greater than 0" in str(exc_info.value)


def test_part_time_one_time_invalid_hours():
    """Verify that a one-time part-time job with zero hours fails validation."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time",
        "part_time_type": "one_time",
        "hours": 0
    }
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(**data)
    assert "hours is required and must be greater than 0" in str(exc_info.value)


def test_part_time_desire_day_valid():
    """Verify that 'desire day' part-time job gets daily pay_basis."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time",
        "part_time_type": "desire_day"
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.part_time
    assert job.part_time_type == PartTimeType.desire_day
    assert job.pay_basis == PayBasis.daily


def test_part_time_monthly_valid():
    """Verify that 'monthly' part-time job gets daily pay_basis."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "part_time",
        "part_time_type": "monthly"
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.part_time
    assert job.part_time_type == PartTimeType.monthly
    assert job.pay_basis == PayBasis.daily


def test_full_day_valid():
    """Verify that full-day jobs get monthly pay_basis automatically."""
    data = {
        **VALID_BASE_DATA,
        "job_type": "full_day"
    }
    job = JobCreate(**data)
    assert job.job_type == JobType.full_day
    assert job.part_time_type is None
    assert job.hours is None
    assert job.pay_basis == PayBasis.monthly


def test_full_day_invalid_fields():
    """Verify that specifying part_time_type or hours on full-day jobs raises validation errors."""
    data_with_pt_type = {
        **VALID_BASE_DATA,
        "job_type": "full_day",
        "part_time_type": "one_time"
    }
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(**data_with_pt_type)
    assert "part_time_type should not be specified for full_day jobs" in str(exc_info.value)

    data_with_hours = {
        **VALID_BASE_DATA,
        "job_type": "full_day",
        "hours": 8.0
    }
    with pytest.raises(ValidationError) as exc_info:
        JobCreate(**data_with_hours)
    assert "hours should not be specified for full_day jobs" in str(exc_info.value)
