import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from text_logic_parser.exceptions import GeminiAPIError, GeminiConfigurationError
from main import stream_analysis


@pytest.mark.anyio
async def test_stream_analysis_basic_success():
    """Verify that stream_analysis yields metadata, chunk results, and completed events on success."""
    text = "Socrates is a man. All men are mortal. Therefore Socrates is mortal."
    
    mock_extracted_args = [
        {
            "original_text": "Socrates is mortal because he is a man.",
            "rationale": "Socrates is a man, men are mortal, so Socrates is mortal.",
            "reconstructed_syllogism": {
                "premises": [
                    {"quantifier": "all", "subject": "men", "copula": "are", "predicate": "mortal", "is_implicit": False},
                    {"quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "man", "is_implicit": False}
                ],
                "conclusion": {
                    "quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "mortal"
                }
            }
        }
    ]

    with patch("main.settings.gemini_api_key", "valid-key-for-test"):
        with patch("text_logic_parser.ai_extractor.AIExtractor.async_extract_arguments_for_chunk") as mock_extract:
            mock_extract.return_value = mock_extracted_args
            
            events = []
            async for event_line in stream_analysis(text):
                if event_line.strip():
                    events.append(event_line)
            
            # Assert we received at least metadata, chunk_result, and completed events
            assert len(events) >= 3
            assert any("event: metadata" in e for e in events)
            assert any("event: chunk_result" in e for e in events)
            assert any("event: completed" in e for e in events)


@pytest.mark.anyio
async def test_stream_analysis_realtime_deduplication():
    """Verify that stream_analysis culls duplicate syllogisms based on terms in real-time."""
    text = "Socrates is a man. All men are mortal. Socrates is a man. All men are mortal."
    
    mock_args_chunk_1 = [
        {
            "original_text": "Socrates is mortal",
            "reconstructed_syllogism": {
                "premises": [
                    {"quantifier": "all", "subject": "men", "copula": "are", "predicate": "mortal"},
                    {"quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "man"}
                ],
                "conclusion": {"quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "mortal"}
            }
        }
    ]
    
    # Exact same logical syllogism, different original text excerpt
    mock_args_chunk_2 = [
        {
            "original_text": "Socrates is mortal again",
            "reconstructed_syllogism": {
                "premises": [
                    {"quantifier": "all", "subject": "men", "copula": "are", "predicate": "mortal"},
                    {"quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "man"}
                ],
                "conclusion": {"quantifier": None, "subject": "Socrates", "copula": "is", "predicate": "mortal"}
            }
        }
    ]

    with patch("main.settings.gemini_api_key", "valid-key-for-test"):
        with patch("text_logic_parser.ai_extractor.AIExtractor.async_extract_arguments_for_chunk") as mock_extract:
            # Return chunk 1 arguments first, then chunk 2 arguments, and empty for any subsequent chunks
            mock_extract.side_effect = [mock_args_chunk_1, mock_args_chunk_2, []]
            
            import json
            chunk_results = []
            async for event_line in stream_analysis(text):
                if "event: chunk_result" in event_line:
                    data_str = event_line.split("data:")[1].strip()
                    chunk_results.append(json.loads(data_str))
            
            # Total chunk results should equal total chunks (3)
            assert len(chunk_results) == 3
            
            # The total number of arguments emitted should be exactly 1 due to culling
            total_args = sum(len(r["arguments"]) for r in chunk_results)
            assert total_args == 1


@pytest.mark.anyio
async def test_stream_analysis_failed_requeue_retry():
    """Verify that a transiently failed chunk is requeued and retried up to 3 times before failing."""
    text = "Single chunk text"
    
    with patch("main.settings.gemini_api_key", "valid-key-for-test"):
        with patch("text_logic_parser.ai_extractor.AIExtractor.async_extract_arguments_for_chunk") as mock_extract:
            # First and second calls raise transient errors (503 Service Unavailable), third succeeds
            mock_extract.side_effect = [
                GeminiAPIError(status_code=503, message="Unavailable"),
                GeminiAPIError(status_code=503, message="Unavailable"),
                [] # success with no arguments
            ]
            
            events = []
            async for event_line in stream_analysis(text):
                if event_line.strip():
                    events.append(event_line)
            
            # Assert chunk retry events were generated
            assert any("event: chunk_retry" in e for e in events)
            # The execution completed successfully
            assert any("event: completed" in e for e in events)


@pytest.mark.anyio
async def test_stream_analysis_fatal_error_bubbling():
    """Verify that a fatal error (like 403 Forbidden) is bubbled up immediately without retry."""
    text = "Single chunk text"
    
    with patch("main.settings.gemini_api_key", "valid-key-for-test"):
        with patch("text_logic_parser.ai_extractor.AIExtractor.async_extract_arguments_for_chunk") as mock_extract:
            # 403 Forbidden represents fatal key authentication error
            mock_extract.side_effect = GeminiAPIError(status_code=403, message="Forbidden key")
            
            with pytest.raises(GeminiAPIError) as exc_info:
                async for _ in stream_analysis(text):
                    pass
            
            assert exc_info.value.status_code == 403
