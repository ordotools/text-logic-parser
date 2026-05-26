import os
import json
import requests
from typing import List, Dict, Any

class AIExtractor:
    """Uses Gemini API to extract logical arguments from student essays and structure them."""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.model_name = "gemini-2.5-flash"
        
    def extract_arguments(self, essay_text: str) -> List[Dict[str, Any]]:
        """
        Sends the essay to Gemini to extract all logical arguments (syllogisms or enthymemes)
        and reconstruct them in a structured, standard categorical format with unified terms.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        system_prompt = """
You are a classical logic expert specializing in Aristotelian Syllogisms. Your task is to analyze student essays and extract all logical arguments (syllogisms) they contain. 

Essays often contain:
1. Complete Syllogisms: e.g., "All humans are mortal. Socrates is a human. Therefore Socrates is mortal."
2. Enthymemes (incomplete syllogisms with an unstated/implicit premise): e.g., "Socrates is mortal because he is a man" (Implicit premise: "All men are mortal").

For EACH logical argument found in the essay, you MUST:
1. Capture the exact original text snippet where the student makes this argument.
2. Identify the three logical terms:
   - Subject (S) of the conclusion (Minor term).
   - Predicate (P) of the conclusion (Major term).
   - Middle Term (M) that connects S and P, appearing in both premises but NOT the conclusion.
3. Unify the terms so they use the EXACT same words. E.g., if you choose the Middle Term 'man', use 'man' (or 'men') in both premises. Do not use 'human' in one and 'man' in another. Unify synonyms into the same terms.
4. Structure the premises and conclusion into strict categorical propositions:
   - Quantifier: must be exactly one of: "all", "some", "no", or null (for singular subjects like 'Socrates').
   - Subject: the clean subject term (concise noun phrase, e.g. "philosopher", "Greek", "Socrates").
   - Copula: must be exactly one of: "is", "are", "is not", "are not".
   - Predicate: the clean predicate term (concise noun or adjective phrase, e.g. "mortal", "mammal", "wise").
   - Is Implicit: boolean. Set to true if the premise was NOT explicitly stated in the essay, but is logically necessary to complete the syllogism (enthymeme).
5. Ensure that there are exactly two premises in the reconstructed syllogism.

Respond ONLY with a valid JSON array of arguments matching this exact structure:
[
  {
    "original_text": "Exact quote from the essay making this argument...",
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
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER ESSAY FOR ANALYSIS:\n\"\"\"\n{essay_text}\n\"\"\""
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
                raise RuntimeError(f"Gemini API returned error {response.status_code}: {response.text}")
                
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
            
        except Exception as e:
            # Return an empty list or bubble up the exception
            print(f"Error in extract_arguments: {e}")
            raise e
