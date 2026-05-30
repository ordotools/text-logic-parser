import sys
sys.path.append('src')
from text_logic_parser.parser_v2 import extract_clauses_v2, find_candidate_arguments

text_last_para = """
Consider another case: all reptiles are cold-blooded creatures, and all iguanas are reptiles, so all iguanas are cold-blooded creatures. A professor might present this example to a student while he is grading essays late at night. Finally, all birds can fly, and some insects can fly, which means some birds are insects.
"""

clauses = extract_clauses_v2(text_last_para)
print("CLAUSES:")
for i, c in enumerate(clauses):
    print(f"{i}: {c['original_text']} | Terms: {c['terms']}")

print("\nCANDIDATES:")
cands = find_candidate_arguments(clauses)
for c in cands:
    print(f"TYPE: {c['type']} | CONC: {c['conclusion']['original_text']}")
    for p in c['premises']:
        print(f"  PREM: {p['original_text']}")
