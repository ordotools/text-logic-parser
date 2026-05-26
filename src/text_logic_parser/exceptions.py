class GeminiError(Exception):
    """Base exception for all Gemini-related errors."""
    pass

class GeminiConfigurationError(GeminiError):
    """Raised when the Gemini API key is missing or blank when trying to make a request."""
    pass

class GeminiAPIError(GeminiError):
    """
    Raised when the Gemini API returns a non-200 HTTP status 
    or is unreachable due to networking errors.
    """
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Gemini API error (Status {status_code}): {message}")
