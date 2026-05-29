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
