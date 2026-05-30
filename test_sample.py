import httpx

essay = """Many scholars have debated the nature of mortality and truth. First of all, we know that all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal. This has been a foundational truth for centuries.

Furthermore, some politicians are corrupt, and since all politicians are public figures, it must be that some public figures are not corrupt.

Additionally, since all humans are mortal, and all Greeks are humans, some Greeks are mortal. 

However, others claim that all cats are animals and all dogs are animals, which proves that all cats are dogs. But this is clearly absurd."""

def main():
    with httpx.Client() as client:
        response = client.post("http://localhost:8080/api/analyze", json={"text": essay, "version": "v2"}, timeout=60.0)
        data = response.json()
        
        print(f"Total Arguments Extracted: {len(data['arguments'])}")
        
        for idx, arg in enumerate(data['arguments']):
            print(f"--- Argument {idx + 1} ---")
            print(f"Original Text: {arg['original_text']}")
            print(f"Minor: {arg['minor_term']}, Major: {arg['major_term']}, Middle: {arg['middle_term']}")
            
if __name__ == "__main__":
    main()
