import os
import pytest
import sys
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import requests

# Ensure src/ is in the python search path for the test suite
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from text_logic_parser.config import Settings
from text_logic_parser.exceptions import GeminiConfigurationError, GeminiAPIError
from text_logic_parser.ai_extractor import AIExtractor
from main import app


client = TestClient(app)

def test_settings_default_values():
    """Verify that settings has the correct default values."""
    settings = Settings(gemini_api_key=None)
    assert settings.gemini_model == "gemini-3.1-flash-lite"
    assert settings.gemini_api_key is None

def test_settings_env_override():
    """Verify that settings can be overridden by environment variables."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123", "GEMINI_MODEL": "gemini-custom"}):
        settings = Settings()
        assert settings.gemini_api_key == "test-key-123"
        assert settings.gemini_model == "gemini-custom"

def test_ai_extractor_missing_key_raises_exception():
    """Verify that AIExtractor raises GeminiConfigurationError when no key is set."""
    with patch("text_logic_parser.ai_extractor.settings.gemini_api_key", None):
        extractor = AIExtractor(api_key=None)
        with pytest.raises(GeminiConfigurationError) as exc_info:
            extractor.extract_arguments("All men are mortal. Socrates is a man.")
        assert "GEMINI_API_KEY environment variable is not set" in str(exc_info.value)


@patch("requests.post")
def test_ai_extractor_api_success(mock_post):
    """Verify that AIExtractor handles successful requests correctly."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '[{"original_text": "Socrates is mortal", "reconstructed_syllogism": {"premises": [], "conclusion": {}}}]'
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_response

    extractor = AIExtractor(api_key="valid-key")
    args = extractor.extract_arguments("Socrates is mortal")
    assert len(args) == 1
    assert args[0]["original_text"] == "Socrates is mortal"

@patch("requests.post")
def test_ai_extractor_api_rate_limit(mock_post):
    """Verify that AIExtractor raises GeminiAPIError on rate limits (429)."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Quota exceeded"
    mock_response.json.return_value = {"error": {"message": "Resource has been exhausted (e.g. queries per minute)."}}
    mock_post.return_value = mock_response

    extractor = AIExtractor(api_key="valid-key")
    with pytest.raises(GeminiAPIError) as exc_info:
        extractor.extract_arguments("Socrates is mortal")
    assert exc_info.value.status_code == 429
    assert "Resource has been exhausted" in str(exc_info.value)

@patch("requests.post")
def test_ai_extractor_api_connection_error(mock_post):
    """Verify that AIExtractor raises GeminiAPIError on connection error."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

    extractor = AIExtractor(api_key="valid-key")
    with pytest.raises(GeminiAPIError) as exc_info:
        extractor.extract_arguments("Socrates is mortal")
    assert exc_info.value.status_code == 503
    assert "Failed to connect" in str(exc_info.value)

def test_api_endpoint_missing_api_key():
    """Verify that the /api/analyze endpoint returns 412 when the API key is missing."""
    with patch("text_logic_parser.ai_extractor.settings.gemini_api_key", None):
        # We also need to patch it in the active extractor instance if it pulls from settings
        with patch("main.settings.gemini_api_key", None):
            response = client.post("/api/analyze", json={"text": "All men are mortal."})
            assert response.status_code == 412
            json_data = response.json()
            assert json_data["success"] is False
            assert json_data["error"] == "Gemini API Key Missing"
            assert "resolution" in json_data
            assert "GEMINI_API_KEY" in json_data["resolution"]

@patch("text_logic_parser.ai_extractor.AIExtractor.async_reconstruct_arguments_with_context")
def test_api_endpoint_rate_limit(mock_async_reconstruct):
    """Verify that the /api/analyze endpoint handles 429 rate limit errors from Gemini API."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    
    from text_logic_parser.exceptions import GeminiAPIError
    import pytest
    from unittest.mock import AsyncMock
    
    mock_async_reconstruct.side_effect = GeminiAPIError(status_code=429, message="Rate limit exceeded")

    # Force a key to be present so it doesn't trigger the 412 error
    with patch("main.settings.gemini_api_key", "test-key-active"):
        with patch("text_logic_parser.ai_extractor.settings.gemini_api_key", "test-key-active"):
            response = client.post("/api/analyze", json={"text": "All men are mortal... it doesn't parse locally"})
            assert response.status_code == 429
            json_data = response.json()
            assert json_data["success"] is False
            assert json_data["error"] == "Gemini API Failure"
            assert "rate limit" in json_data["message"].lower()

@patch("text_logic_parser.ai_extractor.AIExtractor.async_reconstruct_arguments_with_context")
def test_api_endpoint_forbidden(mock_async_reconstruct):
    """Verify that the /api/analyze endpoint handles 403 authorization failures from Gemini API."""
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    
    from text_logic_parser.exceptions import GeminiAPIError
    
    mock_async_reconstruct.side_effect = GeminiAPIError(status_code=403, message="API key not valid.")

    with patch("main.settings.gemini_api_key", "invalid-key-active"):
        with patch("text_logic_parser.ai_extractor.settings.gemini_api_key", "invalid-key-active"):
            response = client.post("/api/analyze", json={"text": "All men are mortal... it doesn't parse locally"})
            assert response.status_code == 403
            json_data = response.json()
            assert json_data["success"] is False
            assert json_data["error"] == "Gemini API Failure"
            assert "authorization failed" in json_data["message"].lower()
            assert "resolution" in json_data
            assert "active API key" in json_data["resolution"]
