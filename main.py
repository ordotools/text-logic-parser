import os
import sys
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# Ensure src/ is in the python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

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

@app.post("/api/analyze")
async def analyze_essay(request: EssayRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Essay text cannot be empty.")
        
    start_time = time.perf_counter()
        
    try:
        # 1. Run local spaCy Semantic concept extraction
        concepts = analyze_text_concepts(request.text)
        
        # 2. Run local spaCy Argument structure extraction (Show intermediate work)
        raw_spacy_args = extract_raw_arguments_local(request.text)
        
        # 3. Call AI Syllogistic Reconstruction Agent
        extractor = AIExtractor()
        extracted_args = await extractor.async_reconstruct_arguments_with_context(
            request.text, concepts, raw_spacy_args
        )
        
        response_arguments = []
        seen_reconstructed = set()
        from text_logic_parser.models import normalize_term
        
        for arg in extracted_args:
            orig_text = arg.get("original_text", "")
            rationale = arg.get("rationale", "Reconstructed from text context.")
            
            recon = arg.get("reconstructed_syllogism", {})
            premise_jsons = recon.get("premises", [])
            conclusion_json = recon.get("conclusion", {})
            
            # Reconstruct Proposition objects
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
            
            # Validate Syllogism
            violations = validate_syllogism(syll)
            
            # Determine overall validity (ignores warning-only violations)
            is_valid = not any(not v.get("is_warning", False) for v in violations)
            
            # Build structured JSON for this argument
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
            
            response_arguments.append({
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
            
        processing_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "success": True,
            "concepts": concepts,
            "raw_spacy_arguments": raw_spacy_args,
            "arguments": response_arguments,
            "processing_time_ms": processing_time_ms
        }
        
    except (GeminiConfigurationError, GeminiAPIError):
        raise
    except Exception as e:
        print(f"Error analyzing essay: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze essay: {str(e)}")

# Mount static folder for serving frontend
# Ensure 'static' directory exists before running
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 5522))
    # Bind to 0.0.0.0 in production/cloud, 127.0.0.1 for local dev
    host = "0.0.0.0" if "PORT" in os.environ else "127.0.0.1"
    reload = False if "PORT" in os.environ else True
    uvicorn.run("main:app", host=host, port=port, reload=reload)
