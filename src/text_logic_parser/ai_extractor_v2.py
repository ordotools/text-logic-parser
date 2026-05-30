import json
import httpx
from typing import List, Dict, Any
from text_logic_parser.config import settings
from text_logic_parser.exceptions import GeminiConfigurationError, GeminiAPIError
from text_logic_parser.ai_extractor import SYSTEM_PROMPT

SYSTEM_PROMPT_V2 = """
You are a strict classical logic expert specializing in Aristotelian Syllogisms. 
You are given a CANDIDATE logical argument extracted locally via NLP, along with the text chunk it came from.
Your task is to determine whether this candidate is IN FACT a logical syllogism (or enthymeme) in the context of the text.

If the candidate is NOT a logical argument (e.g. it's just a descriptive sentence, a false positive term match, or unrelated facts), you must disregard it by returning an empty array: []

If it IS a logical argument:
1. If it has only one premise (an enthymeme), derive the necessary implicit premise.
2. Structure it into strict categorical propositions with unified terms (Subject, Predicate, Middle).
3. Ensure there are exactly two premises.

Respond ONLY with a valid JSON array of arguments matching this structure:
[
  {
    "original_text": "Exact quote...",
    "rationale": "Brief rationale...",
    "reconstructed_syllogism": {
      "premises": [
        {"quantifier": "all", "subject": "S", "copula": "is", "predicate": "P", "is_implicit": false},
        {"quantifier": "all", "subject": "S", "copula": "is", "predicate": "P", "is_implicit": true}
      ],
      "conclusion": {"quantifier": "all", "subject": "S", "copula": "is", "predicate": "P"}
    }
  }
]
"""

class AIExtractorV2:
    """Uses Gemini API to verify and reconstruct candidate syllogisms with temperature=0.0."""
    
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        raw_key = api_key or settings.gemini_api_key
        if raw_key:
            self.api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
            self.api_key = self.api_keys[0] if self.api_keys else None
        else:
            self.api_keys = []
            self.api_key = None
            
        self.model_name = model_name or settings.gemini_model
        
    async def async_extract_arguments_for_candidates(self, client: httpx.AsyncClient, candidate: Dict[str, Any], text_chunk: str) -> List[Dict[str, Any]]:
        """
        Sends a candidate and its context chunk to Gemini. 
        Temperature explicitly set to 0.0.
        """
        if not self.api_keys and not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        import random
        api_key = random.choice(self.api_keys) if self.api_keys else self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        # Format the candidate to present to the AI
        candidate_str = f"Candidate Conclusion: {candidate['conclusion']['original_text']}\n"
        candidate_str += f"Candidate Premises: {', '.join([p['original_text'] for p in candidate['premises']])}\n"
        
        prompt = f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT_V2}\n\n"
        prompt += f"CONTEXT CHUNK:\n\"\"\"{text_chunk}\"\"\"\n\n"
        prompt += f"CANDIDATE ARGUMENT:\n{candidate_str}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0  # Force deterministic behavior
            }
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            if response.status_code != 200:
                error_msg = response.text
                try:
                    err_json = response.json()
                    if "error" in err_json and "message" in err_json["error"]:
                        error_msg = err_json["error"]["message"]
                except Exception:
                    pass
                raise GeminiAPIError(status_code=response.status_code, message=f"Gemini API returned error: {error_msg}")
                
            data = response.json()
            if "candidates" not in data or not data["candidates"]:
                return []
                
            response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            arguments = json.loads(response_text)
            
            if not isinstance(arguments, list):
                if isinstance(arguments, dict) and "arguments" in arguments:
                    arguments = arguments["arguments"]
                else:
                    arguments = [arguments]
            return arguments
        except httpx.RequestError as e:
            raise GeminiAPIError(status_code=502, message=f"Network request to Gemini failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise GeminiAPIError(status_code=502, message=f"Failed to parse Gemini JSON response: {str(e)}")
        except Exception as e:
            if isinstance(e, (GeminiConfigurationError, GeminiAPIError)):
                raise
            raise GeminiAPIError(status_code=500, message=f"Unexpected error in Gemini client: {str(e)}")

    async def async_check_statement_of_fact(self, client: httpx.AsyncClient, statement: str) -> bool:
        """
        Uses Gemini API to determine if a statement is a mere statement of fact/observation,
        or a genuine philosophical/logical assumption.
        Returns True if it's a statement of fact, False otherwise.
        """
        if not self.api_keys and not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        import random
        api_key = random.choice(self.api_keys) if self.api_keys else self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        prompt = (
            "Determine whether the following statement is merely a statement of fact/observation, "
            "or a true philosophical/logical assumption. "
            "A statement of fact is an empirical observation or a descriptive statement about the world (e.g. 'The sky is blue', 'Socrates is a man', 'Dogs bark'). "
            "A true assumption is a foundational premise, a normative claim, or a theoretical postulate used to build an argument (e.g. 'All men are mortal', 'Justice is the highest good').\n\n"
            f"Statement: \"{statement}\"\n\n"
            "Respond ONLY with a JSON object containing a single boolean field 'is_statement_of_fact'."
        )
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    result = json.loads(response_text)
                    return result.get("is_statement_of_fact", False)
            return False
        except Exception:
            # If it fails, default to False to keep the assumption
            return False

    async def async_resolve_ambiguous_pronoun(self, client: httpx.AsyncClient, sentence: str, pronoun: str, candidates: List[str]) -> str:
        """
        Uses Gemini API to resolve an ambiguous pronoun to its most likely antecedent from a list of candidates.
        """
        if not self.api_keys and not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        import random
        api_key = random.choice(self.api_keys) if self.api_keys else self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        prompt = (
            "You are an expert coreference resolution AI. Given a sentence containing a pronoun and a list of candidate antecedents, "
            "select the correct antecedent that the pronoun refers to based on the context.\n\n"
            f"Sentence: \"{sentence}\"\n"
            f"Pronoun to resolve: \"{pronoun}\"\n"
            f"Candidates: {json.dumps(candidates)}\n\n"
            "Respond ONLY with a JSON object containing a single string field 'resolved_antecedent' with your exact choice from the Candidates list. "
            "If none fit, pick the most plausible one or return the original pronoun."
        )
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.0
            }
        }
        headers = {"Content-Type": "application/json"}
        
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and data["candidates"]:
                    response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    result = json.loads(response_text)
                    return result.get("resolved_antecedent", candidates[0] if candidates else pronoun)
            return candidates[0] if candidates else pronoun
        except Exception:
            # Fallback to the top heuristic candidate
            return candidates[0] if candidates else pronoun
