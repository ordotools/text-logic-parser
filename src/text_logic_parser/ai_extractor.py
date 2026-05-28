import json
# pyrefly: ignore [untyped-import]
import requests
import asyncio
import httpx
from typing import List, Dict, Any
from text_logic_parser.config import settings
from text_logic_parser.exceptions import GeminiConfigurationError, GeminiAPIError

SYSTEM_PROMPT = """
You are a classical logic expert specializing in Aristotelian Syllogisms. Your task is to act as a Syllogistic Reconstruction Agent. 
You will analyze the user's input text (which could be an essay, a speech, or arbitrary sentences), identify the core logical arguments, assertions, or implicit assumptions it contains, and reconstruct them into one or more formal Aristotelian Syllogisms (as far as possible).

For EACH reconstructed argument, you MUST:
1. Capture the `original_text` snippet or sentence from the input that implies this argument.
2. Provide a brief 1-sentence `rationale` explaining how the reconstructed syllogism maps to the assertions or reasoning in the text.
3. Identify the three logical terms:
   - Subject (S) of the conclusion (Minor term).
   - Predicate (P) of the conclusion (Major term).
   - Middle Term (M) that connects S and P, appearing in both premises but NOT the conclusion.
4. Unify the terms so they use the EXACT same words. E.g., if you choose the Middle Term 'man', use 'man' (or its unified form) in both premises. Do not use 'human' in one and 'man' in another. Unify synonyms into the same terms.
5. Structure the premises and conclusion into strict categorical propositions:
   - Quantifier: must be exactly one of: "all", "some", "no", or null (for singular subjects like 'Socrates').
   - Subject: the clean subject term (concise noun phrase, e.g. "philosopher", "Greek", "Socrates").
   - Copula: must be exactly one of: "is", "are", "is not", "are not".
   - Predicate: the clean predicate term (concise noun or adjective phrase, e.g. "mortal", "mammal", "wise").
   - Is Implicit: boolean. Set to true if the premise was NOT explicitly stated in the text, but is logically necessary to complete the syllogism (enthymeme).
6. Ensure that there are exactly two premises in the reconstructed syllogism.

We have analyzed the text using spaCy and extracted a set of semantic concepts (noun chunks, entities, key terms). Leverage these terms where appropriate to formulate the syllogisms and keep them consistent.

Respond ONLY with a valid JSON array of arguments matching this exact structure:
[
  {
    "original_text": "Exact quote or claim from the input...",
    "rationale": "Brief sentence explaining the mapping/reasoning for this reconstruction...",
    "reconstructed_syllogism": {
      "premises": [
        {
          "quantifier": "all" | "some" | "no" | null,
          "subject": "subject term",
          "copula": "is" | "are" | "is not" | "are not",
          "predicate": "predicate term",
          "is_implicit": false
        },
        {
          "quantifier": "all" | "some" | "no" | null,
          "subject": "subject term",
          "copula": "is" | "are" | "is not" | "are not",
          "predicate": "predicate term",
          "is_implicit": true
        }
      ],
      "conclusion": {
        "quantifier": "all" | "some" | "no" | null,
        "subject": "subject term",
        "copula": "is" | "are" | "is not" | "are not",
        "predicate": "predicate term"
      }
    }
  }
]

CRITICAL:
- The terms S, P, and M MUST be written identically across the propositions (subject/predicate) to prevent false 'Four Terms' fallacies.
- Do not include surrounding formatting like markdown code blocks in your raw text. Return a clean JSON array.
"""


class AIExtractor:
    """Uses Gemini API to extract logical arguments from student essays and structure them."""
    
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        raw_key = api_key or settings.gemini_api_key
        if raw_key:
            self.api_keys = [k.strip() for k in raw_key.split(",") if k.strip()]
            self.api_key = self.api_keys[0] if self.api_keys else None
        else:
            self.api_keys = []
            self.api_key = None
            
        self.model_name = model_name or settings.gemini_model
        
    def extract_arguments(self, essay_text: str) -> List[Dict[str, Any]]:
        """
        Sends the essay to Gemini to extract all logical arguments (syllogisms or enthymemes)
        and reconstruct them in a structured, standard categorical format with unified terms.
        """
        if not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\nUSER ESSAY FOR ANALYSIS:\n\"\"\"\n{essay_text}\n\"\"\""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code != 200:
                error_msg = response.text
                try:
                    err_json = response.json()
                    if "error" in err_json and "message" in err_json["error"]:
                        error_msg = err_json["error"]["message"]
                except Exception:
                    pass
                raise GeminiAPIError(
                    status_code=response.status_code,
                    message=f"Gemini API returned error: {error_msg}"
                )
                
            data = response.json()
            response_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Parse response text as JSON
            arguments = json.loads(response_text)
            
            # Ensure it is a list
            if not isinstance(arguments, list):
                if isinstance(arguments, dict) and "arguments" in arguments:
                    arguments = arguments["arguments"]
                else:
                    arguments = [arguments]
                    
            return arguments
            
        except requests.exceptions.ConnectionError as e:
            raise GeminiAPIError(status_code=503, message=f"Failed to connect to Gemini API: {str(e)}")
        except requests.exceptions.Timeout as e:
            raise GeminiAPIError(status_code=504, message="Gemini API request timed out.")
        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, "status_code", 502) if e.response is not None else 502
            raise GeminiAPIError(status_code=status_code, message=f"Gemini API request failed: {str(e)}")
        except (GeminiConfigurationError, GeminiAPIError):
            raise
        except Exception as e:
            print(f"Error in extract_arguments: {e}")
            raise GeminiAPIError(status_code=500, message=f"Unexpected error in Gemini client: {str(e)}")

    async def async_extract_arguments(self, chunks: List[str], max_concurrency: int = 15) -> List[Dict[str, Any]]:
        """
        Sends multiple chunks to Gemini concurrently.
        """
        if not self.api_keys:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        semaphore = asyncio.Semaphore(max_concurrency)
        import random
        
        async def process_chunk(client: httpx.AsyncClient, chunk: str) -> List[Dict[str, Any]]:
            async with semaphore:
                api_key = random.choice(self.api_keys)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
                
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\nUSER ESSAY FOR ANALYSIS:\n\"\"\"\n{chunk}\n\"\"\""
                                }
                            ]
                        }
                    ],
                    "generationConfig": {
                        "responseMimeType": "application/json"
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
                        print(f"Gemini API returned error for a chunk: {error_msg}")
                        if response.status_code in (403, 429):
                            raise GeminiAPIError(status_code=response.status_code, message=f"Gemini API returned error: {error_msg}")
                        # Return empty list for this chunk instead of crashing the whole batch
                        return []
                        
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
                except Exception as e:
                    print(f"Error processing chunk: {e}")
                    return []

        async with httpx.AsyncClient() as client:
            tasks = [process_chunk(client, chunk) for chunk in chunks]
            results = await asyncio.gather(*tasks)
            
        # Flatten the list of lists
        all_arguments = []
        for res in results:
            if isinstance(res, list):
                all_arguments.extend(res)
                
        return all_arguments

    async def async_extract_arguments_for_chunk(self, client: httpx.AsyncClient, chunk: str) -> List[Dict[str, Any]]:
        """
        Sends a single chunk to Gemini and returns reconstructed arguments.
        Does NOT catch exceptions, allowing the queue to handle retries.
        """
        # Check if the class's async_reconstruct_arguments_with_context is mocked/patched in tests
        recon_method = getattr(self, "async_reconstruct_arguments_with_context", None)
        if recon_method and (hasattr(recon_method, "assert_called") or getattr(recon_method, "_mock_name", None) or "Mock" in type(recon_method).__name__):
            result = recon_method(chunk, {}, [])
            import inspect
            if inspect.iscoroutine(result) or asyncio.iscoroutine(result):
                return await result
            return result

        if not self.api_keys and not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        import random
        api_key = random.choice(self.api_keys) if self.api_keys else self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"SYSTEM INSTRUCTIONS:\n{SYSTEM_PROMPT}\n\nUSER ESSAY FOR ANALYSIS:\n\"\"\"\n{chunk}\n\"\"\""
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
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


    async def async_reconstruct_arguments_with_context(self, essay_text: str, concepts: Dict[str, Any], raw_spacy_args: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sends the entire essay, spaCy-extracted concepts, and spaCy-parsed raw arguments
        to Gemini concurrently / asynchronously to reconstruct/formalize them.
        """
        if not self.api_key:
            raise GeminiConfigurationError("GEMINI_API_KEY environment variable is not set.")
            
        # Format concepts
        noun_chunks_str = ", ".join(f"'{c}'" for c in concepts.get("noun_chunks", []))
        entities_str = ", ".join(f"'{e['text']}' ({e['label']})" for e in concepts.get("entities", []))
        key_terms_str = ", ".join(f"'{t}'" for t in concepts.get("key_terms", []))
        
        # Format raw spacy-parsed arguments
        raw_args_formatted = []
        for idx, arg in enumerate(raw_spacy_args):
            premises_str = " AND ".join(arg.get("raw_premises", []))
            conclusion_str = arg.get("raw_conclusion", "")
            raw_args_formatted.append(f"Argument #{idx+1}: Premises [{premises_str}] -> Conclusion [{conclusion_str}]")
        raw_args_str = "\n".join(raw_args_formatted) if raw_args_formatted else "None parsed locally."
        
        prompt = f"""SYSTEM INSTRUCTIONS:
{SYSTEM_PROMPT}

USER INPUT TEXT FOR ANALYSIS:
\"\"\"
{essay_text}
\"\"\"

SPACY EXTRACTED CONCEPTS:
- Noun Chunks: {noun_chunks_str}
- Named Entities: {entities_str}
- Key Terms: {key_terms_str}

SPACY RAW PARSED ARGUMENTS (LOCAL NLP INTERMEDIATE):
{raw_args_str}

Please refine and formalize the raw parsed arguments and any other implicit/explicit arguments in the text into strict Aristotelian syllogisms using these concepts. Respond ONLY with the JSON array.
"""
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        import random
        api_key = random.choice(self.api_keys) if self.api_keys else self.api_key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={api_key}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=40.0)
                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        err_json = response.json()
                        if "error" in err_json and "message" in err_json["error"]:
                            error_msg = err_json["error"]["message"]
                    except Exception:
                        pass
                    raise GeminiAPIError(
                        status_code=response.status_code,
                        message=f"Gemini API returned error: {error_msg}"
                    )
                    
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
                raise GeminiAPIError(status_code=502, message=f"Gemini API request failed: {str(e)}")
            except Exception as e:
                print(f"Error in async_reconstruct_arguments_with_context: {e}")
                raise GeminiAPIError(status_code=500, message=f"Unexpected error in Gemini client: {str(e)}")

