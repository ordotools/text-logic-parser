import sys
sys.path.append('src')
from text_logic_parser.parser_v2 import extract_clauses_v2, find_candidate_arguments

text = """
There are exactly 4 classical syllogisms in this text, 2 of which are valid and 2 of which are invalid.

Academic philosophers often spend their careers analyzing historical arguments, which frequently leads to intense departmental debates. All logicians are meticulous thinkers, and some meticulous thinkers are professors; therefore, some logicians are professors. This classic puzzle often trips up undergraduates, who find it incredibly frustrating to untangle during exams.

Furthermore, no politicians are entirely transparent. Since all transparent speakers are trustworthy leaders, it follows that no politicians are trustworthy leaders. When a student successfully identifies this pattern, it proves they understand formal deduction. However, most students prefer studying ethics because they find the material more relatable to daily life.

Consider another case: all reptiles are cold-blooded creatures, and all iguanas are reptiles, so all iguanas are cold-blooded creatures. A professor might present this example to a student while he is grading essays late at night. Finally, all birds can fly, and some insects can fly, which means some birds are insects.
"""

clauses = extract_clauses_v2(text)
for i, c in enumerate(clauses):
    print(f"Clause {i}: {c['original_text']}")
    print(f"  Terms: {c['terms']}")

print("\nFinding Candidates:")
cands = []
for i, conc_clause in enumerate(clauses):
    conc_terms = conc_clause["terms"]
    if len(conc_terms) < 2:
        continue
    cands.append(conc_clause)

seen_term_pairs = set()
for c in cands:
    term_sig = tuple(sorted(c['terms'][:2]))
    print(f"Checking {c['original_text']} with sig {term_sig}")
    if term_sig not in seen_term_pairs:
        seen_term_pairs.add(term_sig)
        print(f"  -> Added {term_sig}")
    else:
        print(f"  -> Eliminated {term_sig} (DUPLICATE)")
