import pytest
import spacy
from text_logic_parser.parser_v2 import clean_text_v2, extract_clauses_v2, find_candidate_arguments

@pytest.fixture(scope="module")
def nlp():
    return spacy.load("en_core_web_sm")

def test_clean_text_v2():
    text = "This is a sen-\ntence with a line break.\nAnd a new paragraph."
    cleaned = clean_text_v2(text)
    assert cleaned == "This is a sentence with a line break. And a new paragraph."
    
def test_clean_text_v2_normal_lines():
    text = "First line.\nSecond line."
    assert clean_text_v2(text) == "First line. Second line."

def test_extract_clauses_v2(nlp):
    text = "Socrates is a man, and all men are mortal."
    clauses = extract_clauses_v2(text, nlp)
    
    assert len(clauses) >= 2
    subjects = [c["subject"].lower() for c in clauses]
    assert "socrates" in subjects

def test_find_candidate_arguments():
    # Mocking clauses output
    clauses = [
        {"original_text": "all men are mortal", "sentence_index": 0, "subject": "men", "predicate": "mortal", "terms": ["men", "mortal"]},
        {"original_text": "Socrates is a man", "sentence_index": 1, "subject": "Socrates", "predicate": "man", "terms": ["socrates", "man"]},
        {"original_text": "Socrates is mortal", "sentence_index": 2, "subject": "Socrates", "predicate": "mortal", "terms": ["socrates", "mortal"]}
    ]
    
    candidates = find_candidate_arguments(clauses)
    
    # The conclusion "Socrates is mortal" has terms "socrates" and "mortal"
    # Both terms appear in previous clauses.
    # So we expect a syllogism candidate.
    
    # So we expect a syllogism candidate.
    
    assert len(candidates) > 0
    # The last one is the syllogism conclusion
    syl = candidates[-1]
    assert syl["conclusion"]["original_text"] == "Socrates is mortal"
    assert syl["type"] == "syllogism"
    assert len(syl["premises"]) == 2
    
    # The first one "all men are mortal" has terms "men" and "mortal".
    # Only "mortal" appears elsewhere, so it might be an enthymeme or assumption depending on match
    # Since "mortal" appears in clause 2 ("Socrates is mortal"), it finds 1 premise.
    # Therefore, enthymeme.

def test_full_text_syllogism_extraction(nlp):
    text = """
    There are exactly 4 classical syllogisms in this text, 2 of which are valid and 2 of which are invalid.

    Academic philosophers often spend their careers analyzing historical arguments, which frequently leads to intense departmental debates. All logicians are meticulous thinkers, and some meticulous thinkers are professors; therefore, some logicians are professors. This classic puzzle often trips up undergraduates, who find it incredibly frustrating to untangle during exams.

    Furthermore, no politicians are entirely transparent. Since all transparent speakers are trustworthy leaders, it follows that no politicians are trustworthy leaders. When a student successfully identifies this pattern, it proves they understand formal deduction. However, most students prefer studying ethics because they find the material more relatable to daily life.

    Consider another case: all reptiles are cold-blooded creatures, and all iguanas are reptiles, so all iguanas are cold-blooded creatures. A professor might present this example to a student while he is grading essays late at night. Finally, all birds can fly, and some insects can fly, which means some birds are insects.
    """
    clauses = extract_clauses_v2(text, nlp)
    
    # Assert that none of the clauses have "unknown" or "predicate" in their terms
    # unless they are actually in the text
    for c in clauses:
        if c["predicate"] == "unknown_predicate":
            assert "unknown" not in c["terms"]
            assert "predicate" not in c["terms"]
            
    cands = find_candidate_arguments(clauses)
    
    # We should have a candidate for the bird/insect syllogism
    bird_candidate_found = False
    for cand in cands:
        if cand["type"] in ("syllogism", "enthymeme"):
            # Check if it has the bird and insect terms
            conc_terms = cand["conclusion"]["terms"]
            if "insects" in conc_terms or "birds" in conc_terms:
                bird_candidate_found = True
                
    assert bird_candidate_found, "The bird/insect syllogism candidate was not found!"
