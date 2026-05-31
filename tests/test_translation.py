import pytest
from unittest.mock import patch
from utils.translation import translate_to_hindi, translate_fields_recursively
from models.schemas import JobCreate, JobType

def test_translate_to_hindi():
    """Test that translate_to_hindi correctly handles successful and failed API responses."""
    # 1. Test successful mock response
    with patch("utils.translation.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [[["नमस्ते", "Hello", None, None, 10]]]
        
        res = translate_to_hindi("Hello")
        assert res == "नमस्ते"

    # 2. Test empty input
    res_empty = translate_to_hindi("")
    assert res_empty == ""

    # 3. Test None input
    res_none = translate_to_hindi(None)
    assert res_none is None

    # 4. Test API error fallback
    with patch("utils.translation.requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        res_fail = translate_to_hindi("Hello")
        assert res_fail == "Hello"


def test_job_create_translation_fields():
    """Verify that JobCreate can accept and validate translation fields."""
    data = {
        "title": "Need gardener",
        "description": "Clean the backyard garden",
        "category": "domestic",
        "pin_code": "110001",
        "pay": 500.0,
        "job_type": "part_time",
        "title_hi": "माली की आवश्यकता है",
        "description_hi": "पिछवाड़े के बगीचे को साफ करें"
    }
    job = JobCreate(**data)
    assert job.title == "Need gardener"
    assert job.title_hi == "माली की आवश्यकता है"
    assert job.description_hi == "पिछवाड़े के बगीचे को साफ करें"


def test_translate_fields_recursively():
    """Verify that translate_fields_recursively correctly translates targeted user-facing fields recursively."""
    nested_response = {
        "user": {
            "name": "John Doe",
            "bio": "Expert in home cleaning and gardening",
            "skills": ["cleaning", "watering plants"],
            "address": "123 Flower Lane",
            "uid": "user-uuid-12345",
            "role": "worker"
        },
        "message": "Welcome back"
    }
    
    # Mock translate_to_hindi to return a mapped value for testing
    with patch("utils.translation.translate_to_hindi", side_effect=lambda x: f"translated_{x}" if x else x):
        translated = translate_fields_recursively(nested_response)
        
        assert translated["user"]["name"] == "translated_John Doe"
        assert translated["user"]["bio"] == "translated_Expert in home cleaning and gardening"
        assert translated["user"]["skills"] == ["translated_cleaning", "translated_watering plants"]
        assert translated["user"]["address"] == "translated_123 Flower Lane"
        assert translated["message"] == "translated_Welcome back"
        
        # System fields are not translated
        assert translated["user"]["uid"] == "user-uuid-12345"
        assert translated["user"]["role"] == "worker"
