import pytest
import spacy
from text_logic_parser.parser import (
    split_logical_clauses,
    clean_proposition_text,
    parse_proposition,
    parse_syllogism
)
from text_logic_parser.models import normalize_term

# Load spaCy nlp model once for tests
@pytest.fixture(scope="module")
def nlp():
    return spacy.load("en_core_web_sm")

def test_split_logical_clauses():
    # Split by period and therefore
    premises, conclusion = split_logical_clauses(
        "Socrates is a man. All men are mortal. Therefore Socrates is mortal."
    )
    assert len(premises) == 2
    assert premises[0] == "Socrates is a man"
    assert premises[1] == "All men are mortal"
    assert conclusion == "Therefore Socrates is mortal."

    # Split by comma and thus
    premises, conclusion = split_logical_clauses(
        "Socrates is a man, all men are mortal, thus Socrates is mortal"
    )
    assert len(premises) == 2
    assert premises[0] == "Socrates is a man"
    assert premises[1] == "all men are mortal"
    assert conclusion == "thus Socrates is mortal"

    # Split by semicolon and hence
    premises, conclusion = split_logical_clauses(
        "Some dogs are friendly; all friendly animals make good pets. Hence some dogs make good pets."
    )
    assert len(premises) == 2
    assert premises[0] == "Some dogs are friendly"
    assert premises[1] == "all friendly animals make good pets"
    assert conclusion == "Hence some dogs make good pets."

def test_clean_proposition_text():
    assert clean_proposition_text("Therefore Socrates is mortal.") == "Socrates is mortal"
    assert clean_proposition_text("thus all men are mortal,") == "all men are mortal"
    assert clean_proposition_text("  Hence some cats are black.  ") == "some cats are black"

def test_parse_proposition(nlp):
    # Test Universal Affirmative
    p1 = parse_proposition("All men are mortal", nlp)
    assert p1.quantifier == "all"
    assert normalize_term(p1.subject) == "man"
    assert p1.copula == "are"
    assert p1.predicate == "mortal"
    assert p1.type_code == "A"

    # Test Singular Affirmative
    p2 = parse_proposition("Socrates is a man", nlp)
    assert p2.quantifier is None
    assert p2.subject == "Socrates"
    assert p2.copula == "is"
    assert p2.predicate == "a man"
    assert p2.type_code == "Singular Affirmative"

    # Test Universal Negative
    p3 = parse_proposition("No reptiles are warm-blooded", nlp)
    assert p3.quantifier == "no"
    assert normalize_term(p3.subject) == "reptile"
    assert p3.copula == "are"
    assert p3.predicate == "warm - blooded" or "warm-blooded" in p3.predicate
    assert p3.type_code == "E"

    # Test Particular Negative
    p4 = parse_proposition("Some philosophers are not rich", nlp)
    assert p4.quantifier == "some"
    assert normalize_term(p4.subject) == "philosopher"
    assert p4.copula == "are not"
    assert p4.predicate == "rich"
    assert p4.type_code == "O"

def test_parse_syllogism(nlp):
    text = "Socrates is a man, all men are mortal. Therefore Socrates is mortal."
    syll = parse_syllogism(text, nlp)
    
    assert syll.minor_term == "Socrates"
    assert syll.major_term == "mortal"
    assert normalize_term(syll.middle_term) == "man"
    
    assert syll.conclusion.type_code == "Singular Affirmative"
    assert syll.major_premise.type_code == "A"
    assert syll.minor_premise.type_code == "Singular Affirmative"
