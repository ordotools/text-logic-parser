import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# Ensure src/ is in the python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from text_logic_parser import Proposition, Syllogism, validate_syllogism, AIExtractor

app = FastAPI(
    title="Aristotelian Logic Essay Analyzer",
    description="Analyze student essays for logical validity using Aristotelian syllogistic rules.",
    version="1.0.0"
)

class EssayRequest(BaseModel):
    text: str

@app.post("/api/analyze")
async def analyze_essay(request: EssayRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Essay text cannot be empty.")
        
    try:
        extractor = AIExtractor()
        extracted_args = extractor.extract_arguments(request.text)
        
        response_arguments = []
        
        for arg in extracted_args:
            orig_text = arg.get("original_text", "")
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
            
        return {
            "success": True,
            "arguments": response_arguments
        }
        
    except Exception as e:
        print(f"Error analyzing essay: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze essay: {str(e)}")

# Mount static folder for serving frontend
# Ensure 'static' directory exists before running
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=5522, reload=True)
