import sys
sys.path.append('src')
import spacy
from text_logic_parser.parser_v2 import extract_clauses_v2, find_candidate_arguments

nlp = spacy.load('en_core_web_sm')
text = """
There are exactly 4 classical syllogisms in this text, 2 of which are valid and 2 of which are invalid.

Academic philosophers often spend their careers analyzing historical arguments, which frequently leads to intense departmental debates. All logicians are meticulous thinkers, and some meticulous thinkers are professors; therefore, some logicians are professors. This classic puzzle often trips up undergraduates, who find it incredibly frustrating to untangle during exams.

Furthermore, no politicians are entirely transparent. Since all transparent speakers are trustworthy leaders, it follows that no politicians are trustworthy leaders. When a student successfully identifies this pattern, it proves they understand formal deduction. However, most students prefer studying ethics because they find the material more relatable to daily life.

Consider another case: all reptiles are cold-blooded creatures, and all iguanas are reptiles, so all iguanas are cold-blooded creatures. A professor might present this example to a student while he is grading essays late at night. Finally, all birds can fly, and some insects can fly, which means some birds are insects.
"""
clauses = extract_clauses_v2(text, nlp)
cands = find_candidate_arguments(clauses)
for c in cands:
    conc_terms = c['conclusion']['terms']
    if 'birds' in conc_terms or 'insects' in conc_terms or 'fly' in conc_terms:
        print(f"TYPE: {c['type']} | CONC: {c['conclusion']['original_text']}")
        print(f"  Conc Terms: {conc_terms}")
        for p in c['premises']:
            print(f"  Premise: {p['original_text']} | Terms: {p['terms']}")
