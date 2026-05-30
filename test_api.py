import httpx
import json

essay = """First of all, we know that all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal.

all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal."""

def main():
    with httpx.Client() as client:
        response = client.post("http://localhost:8080/api/analyze", json={"text": essay, "version": "v2"}, timeout=60.0)
        data = response.json()
        
        print(f"Success: {data['success']}")
        print(f"Total Arguments Extracted: {len(data['arguments'])}")
        
        for idx, arg in enumerate(data['arguments']):
            print(f"--- Argument {idx + 1} ---")
            print(f"Original Text: {arg['original_text']}")
            print(f"Minor: {arg['minor_term']}, Major: {arg['major_term']}, Middle: {arg['middle_term']}")
            
if __name__ == "__main__":
    main()
