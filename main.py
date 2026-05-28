import os
import sys
import logging
import time
from contextlib import asynccontextmanager
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, HTTPException, Request
# pyrefly: ignore [missing-import]
from fastapi.responses import JSONResponse, StreamingResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import httpx
import json

# Ensure src/ is in the python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# pyrefly: ignore [missing-import]
from text_logic_parser import (
    Proposition, 
    Syllogism, 
    validate_syllogism, 
    AIExtractor, 
    settings, 
    GeminiConfigurationError, 
    GeminiAPIError,
    analyze_text_concepts,
    extract_raw_arguments_local
)

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("text_logic_parser")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup check
    if not settings.gemini_api_key:
        logger.warning(
            "\n"
            "========================================================================\n"
            "⚠️  WARNING: GEMINI_API_KEY environment variable is not configured.     \n"
            "The AI essay extraction feature will fail with a 412 status code        \n"
            "until a valid API key is supplied in the environment or a .env file.   \n"
            "========================================================================\n"
        )
    else:
        logger.info(f"Gemini API key loaded. Using model: {settings.gemini_model}")
    yield

app = FastAPI(
    title="Aristotelian Logic Essay Analyzer",
    description="Analyze student essays for logical validity using Aristotelian syllogistic rules.",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(GeminiConfigurationError)
async def gemini_configuration_error_handler(request: Request, exc: GeminiConfigurationError):
    return JSONResponse(
        status_code=412,
        content={
            "success": False,
            "error": "Gemini API Key Missing",
            "message": str(exc),
            "resolution": "Please set the GEMINI_API_KEY environment variable. You can do this by creating a '.env' file in the project root with 'GEMINI_API_KEY=your_key_here' or by setting it in your shell environment."
        }
    )

@app.exception_handler(GeminiAPIError)
async def gemini_api_error_handler(request: Request, exc: GeminiAPIError):
    # Determine user-friendly messages and appropriate status codes
    status_code = exc.status_code
    
    if status_code == 429:
        message = "Gemini API rate limit or quota exceeded. Please wait a moment before trying again."
        resolution = "Check your Gemini API quota and usage limits on the Google AI Studio console."
    elif status_code == 403:
        message = "Gemini API authorization failed. The configured API key is invalid or unauthorized."
        resolution = "Please verify that the GEMINI_API_KEY environment variable is set to a valid, active API key from Google AI Studio."
    elif status_code == 400:
        message = f"Gemini API Bad Request: {exc.message}"
        resolution = "Ensure the request structure and parameters (including the model name) are valid."
    elif status_code in (503, 504):
        message = exc.message
        resolution = "Check network connectivity and the status of Google Gemini API services."
    else:
        message = exc.message
        resolution = "If this persists, verify your Gemini account standing and internet connection."
        # Map generic upstream errors or 5xx to 502 Bad Gateway
        if status_code >= 500 or status_code not in (400, 401, 403, 404, 429):
            status_code = 502

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": "Gemini API Failure",
            "message": message,
            "status_code": exc.status_code,
            "resolution": resolution
        }
    )

class EssayRequest(BaseModel):
    text: str

async def stream_analysis(text: str):
    """
    Asynchronous generator that segments text into chunks, processes them concurrently
    in an asyncio worker queue with retry capability, deduplicates in real-time using term keys,
    and yields JSON-encoded SSE events.
    """
    if not settings.gemini_api_key:
        raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")

    # 1. Run local spaCy Semantic concept extraction
    try:
        concepts = analyze_text_concepts(text)
    except Exception as e:
        logger.error(f"Error extracting concepts: {e}")
        concepts = {"noun_chunks": [], "entities": [], "key_terms": []}
        
    try:
        raw_spacy_args = extract_raw_arguments_local(text)
    except Exception as e:
        logger.error(f"Error extracting raw spacy arguments: {e}")
        raw_spacy_args = []

    # 2. Chunk text
    from text_logic_parser.parser import chunk_essay_for_extraction
    try:
        chunks = chunk_essay_for_extraction(text)
    except Exception as e:
        logger.error(f"Error chunking essay: {e}")
        chunks = [text]  # Fallback to single chunk of entire text
        
    total_chunks = len(chunks)
    
    # Emit initial metadata and concepts
    metadata = {
        "event": "metadata",
        "total_chunks": total_chunks,
        "concepts": concepts,
        "raw_spacy_arguments": raw_spacy_args
    }
    yield f"event: metadata\ndata: {json.dumps(metadata)}\n\n"
    
    if not chunks:
        yield f"event: completed\ndata: {json.dumps({'success': True, 'arguments_count': 0})}\n\n"
        return
        
    # Queue structure: (chunk_index, chunk_text, attempt_count)
    queue = asyncio.Queue()
    for idx, chunk in enumerate(chunks):
        await queue.put((idx, chunk, 0))
        
    seen_reconstructed = set()
    from text_logic_parser.models import normalize_term
    
    extractor = AIExtractor()
    emitted_count = 0
    
    # Concurrency limit (optimized for performance)
    concurrency_ceiling = 10
    workers_count = min(concurrency_ceiling, total_chunks)
    
    result_queue = asyncio.Queue()
    
    async def worker(worker_id: int, client: httpx.AsyncClient):
        while True:
            try:
                chunk_idx, chunk_text, attempt = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
                
            try:
                args = await extractor.async_extract_arguments_for_chunk(client, chunk_text)
                await result_queue.put({
                    "status": "success",
                    "chunk_index": chunk_idx,
                    "arguments": args
                })
            except Exception as e:
                logger.error(f"Worker {worker_id} failed on chunk {chunk_idx} (attempt {attempt+1}): {e}")
                
                # Check for fatal failures that will never succeed on retry (such as auth/config/quota errors)
                is_fatal = False
                if isinstance(e, GeminiConfigurationError):
                    is_fatal = True
                elif isinstance(e, GeminiAPIError) and e.status_code in (400, 401, 403, 412, 429):
                    is_fatal = True
                    
                if is_fatal:
                    await result_queue.put({
                        "status": "fatal_error",
                        "chunk_index": chunk_idx,
                        "exception": e
                    })
                    break  # Exit worker immediately
                
                next_attempt = attempt + 1
                if next_attempt < 3:
                    # Put back in the queue to retry
                    await queue.put((chunk_idx, chunk_text, next_attempt))
                    await result_queue.put({
                        "status": "requeued",
                        "chunk_index": chunk_idx,
                        "attempt": next_attempt
                    })
                else:
                    await result_queue.put({
                        "status": "failed",
                        "chunk_index": chunk_idx,
                        "error": str(e)
                    })
            finally:
                queue.task_done()
                
    async with httpx.AsyncClient() as client:
        # Launch worker tasks
        worker_tasks = [asyncio.create_task(worker(i, client)) for i in range(workers_count)]
        
        completed_chunks = set()
        
        while len(completed_chunks) < total_chunks:
            # Check if all workers are done and result queue is empty
            if all(t.done() for t in worker_tasks) and result_queue.empty():
                break
                
            try:
                res = await asyncio.wait_for(result_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
                
            status = res["status"]
            
            if status == "fatal_error":
                raise res["exception"]
                
            chunk_idx = res["chunk_index"]
            
            if status == "success":
                completed_chunks.add(chunk_idx)
                extracted_args = res["arguments"]
                chunk_arguments = []
                
                # Reconstruct, deduplicate and validate syllogisms for this chunk
                for arg in extracted_args:
                    orig_text = arg.get("original_text", "")
                    rationale = arg.get("rationale", "Reconstructed from text context.")
                    
                    recon = arg.get("reconstructed_syllogism", {})
                    premise_jsons = recon.get("premises", [])
                    conclusion_json = recon.get("conclusion", {})
                    
                    premises = []
                    for p_json in premise_jsons:
                        premises.append(Proposition(
                            quantifier=p_json.get("quantifier"),
                            subject=p_json.get("subject", ""),
                            copula=p_json.get("copula", ""),
                            predicate=p_json.get("predicate", ""),
                            is_implicit=p_json.get("is_implicit", False)
                        ))
                        
                    conclusion = Proposition(
                        quantifier=conclusion_json.get("quantifier"),
                        subject=conclusion_json.get("subject", ""),
                        copula=conclusion_json.get("copula", ""),
                        predicate=conclusion_json.get("predicate", "")
                    )
                    
                    # Deduplicate based on logical key of normalized premises and conclusion
                    def norm_prop(p):
                        return (
                            p.quantifier if p.quantifier else "",
                            normalize_term(p.subject),
                            p.copula,
                            normalize_term(p.predicate)
                        )
                    p_tuples = tuple(sorted(norm_prop(p) for p in premises))
                    c_tuple = norm_prop(conclusion)
                    arg_key = (p_tuples, c_tuple)
                    
                    if arg_key in seen_reconstructed:
                        continue
                    seen_reconstructed.add(arg_key)
                    
                    # Create Syllogism
                    syll = Syllogism(premises, conclusion)
                    violations = validate_syllogism(syll)
                    is_valid = not any(not v.get("is_warning", False) for v in violations)
                    
                    # Build structured JSON for response
                    formatted_premises = []
                    for p in premises:
                        formatted_premises.append({
                            "quantifier": p.quantifier,
                            "subject": p.subject,
                            "copula": p.copula,
                            "predicate": p.predicate,
                            "is_implicit": p.is_implicit,
                            "type_code": p.type_code,
                            "is_subject_distributed": p.is_subject_distributed,
                            "is_predicate_distributed": p.is_predicate_distributed
                        })
                        
                    formatted_conclusion = {
                        "quantifier": conclusion.quantifier,
                        "subject": conclusion.subject,
                        "copula": conclusion.copula,
                        "predicate": conclusion.predicate,
                        "type_code": conclusion.type_code,
                        "is_subject_distributed": conclusion.is_subject_distributed,
                        "is_predicate_distributed": conclusion.is_predicate_distributed
                    }
                    
                    chunk_arguments.append({
                        "original_text": orig_text,
                        "rationale": rationale,
                        "reconstructed_syllogism": {
                            "premises": formatted_premises,
                            "conclusion": formatted_conclusion
                        },
                        "minor_term": syll.minor_term,
                        "major_term": syll.major_term,
                        "middle_term": syll.middle_term,
                        "violations": violations,
                        "is_valid": is_valid
                    })
                    emitted_count += 1
                
                # Emit success result for this chunk
                chunk_data = {
                    "event": "chunk_result",
                    "chunk_index": chunk_idx,
                    "arguments": chunk_arguments,
                    "status": "success",
                    "total_chunks": total_chunks,
                    "processed_chunks": len(completed_chunks)
                }
                yield f"event: chunk_result\ndata: {json.dumps(chunk_data)}\n\n"
                
            elif status == "requeued":
                # Emit retry notifications
                retry_data = {
                    "event": "chunk_retry",
                    "chunk_index": chunk_idx,
                    "attempt": res["attempt"],
                    "total_chunks": total_chunks
                }
                yield f"event: chunk_retry\ndata: {json.dumps(retry_data)}\n\n"
                
            elif status == "failed":
                completed_chunks.add(chunk_idx)
                # Emit failure notification for this chunk but continue pipeline
                chunk_data = {
                    "event": "chunk_result",
                    "chunk_index": chunk_idx,
                    "arguments": [],
                    "status": "failed",
                    "error": res["error"],
                    "total_chunks": total_chunks,
                    "processed_chunks": len(completed_chunks)
                }
                yield f"event: chunk_result\ndata: {json.dumps(chunk_data)}\n\n"
                
            result_queue.task_done()
            
        # Clean up worker tasks
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        
    completed_payload = {
        "event": "completed",
        "success": True,
        "arguments_count": emitted_count
    }
    yield f"event: completed\ndata: {json.dumps(completed_payload)}\n\n"


@app.post("/api/analyze/stream")
async def analyze_essay_stream(request: EssayRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Essay text cannot be empty.")
        
    return StreamingResponse(
        stream_analysis(request.text),
        media_type="text/event-stream"
    )


@app.post("/api/analyze")
async def analyze_essay(request: EssayRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Essay text cannot be empty.")
        
    start_time = time.perf_counter()
        
    try:
        concepts = {"noun_chunks": [], "entities": [], "key_terms": []}
        raw_spacy_arguments = []
        arguments = []
        
        async for line in stream_analysis(request.text):
            if not line.strip():
                continue
            if line.startswith("event:"):
                # Split at most 2 times to get: event_header, data_header, and empty space
                parts = line.split("\n", 2)
                if len(parts) >= 2:
                    event_type = parts[0].replace("event: ", "").strip()
                    data_line = parts[1].replace("data: ", "").strip()
                    try:
                        data = json.loads(data_line)
                        if event_type == "metadata":
                            concepts = data.get("concepts", concepts)
                            raw_spacy_arguments = data.get("raw_spacy_arguments", raw_spacy_arguments)
                        elif event_type == "chunk_result":
                            arguments.extend(data.get("arguments", []))
                    except json.JSONDecodeError:
                        pass
                        
        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "success": True,
            "concepts": concepts,
            "raw_spacy_arguments": raw_spacy_arguments,
            "arguments": arguments,
            "processing_time_ms": processing_time_ms
        }
        
    except (GeminiConfigurationError, GeminiAPIError):
        raise
    except Exception as e:
        logger.error(f"Error in synchronous analyze: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze essay: {str(e)}")

# Mount static folder for serving frontend
# Ensure 'static' directory exists before running
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    # pyrefly: ignore [missing-import]
    import uvicorn
    port = int(os.environ.get("PORT", 5522))
    # Bind to 0.0.0.0 in production/cloud, 127.0.0.1 for local dev
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    reload = False if "PORT" in os.environ else True
    uvicorn.run("main:app", host=host, port=port, reload=reload)
