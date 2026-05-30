import asyncio
import os
import sys

# Ensure src/ is in the python search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from text_logic_parser.parser_v2 import extract_clauses_v2, find_candidate_arguments
from text_logic_parser.ai_extractor_v2 import AIExtractorV2
import httpx
import json

async def main():
    text1 = "First of all, we know that all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal."
    text2 = "all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal."
    
    clauses1 = extract_clauses_v2(text1)
    cands1 = find_candidate_arguments(clauses1)
    
    clauses2 = extract_clauses_v2(text2)
    cands2 = find_candidate_arguments(clauses2)
    
    extractor_v2 = AIExtractorV2()
    
    async with httpx.AsyncClient() as client:
        print("--- TEXT 1 ---")
        for cand in cands1:
            if cand["type"] in ("syllogism", "enthymeme"):
                args = await extractor_v2.async_extract_arguments_for_candidates(client, cand, text1)
                print(json.dumps(args, indent=2))
                
        print("--- TEXT 2 ---")
        for cand in cands2:
            if cand["type"] in ("syllogism", "enthymeme"):
                args = await extractor_v2.async_extract_arguments_for_candidates(client, cand, text2)
                print(json.dumps(args, indent=2))

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
