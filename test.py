import os
import sys

# Ensure src/ is in the Python search path when running test.py directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from text_logic_parser.parser import parse_syllogism

def main():
    # Demonstration categorical syllogism
    text = "Socrates is a man, all men are mortal. Therefore Socrates is mortal."
    
    print("Input Text:")
    print(f'  "{text}"')
    print()
    
    try:
        syll = parse_syllogism(text)
        print(syll.format_details())
    except Exception as e:
        print(f"Error parsing syllogism: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
