import pytest
import spacy
from text_logic_parser.parser import (
    split_logical_clauses,
    clean_proposition_text,
    parse_proposition,
    parse_syllogism,
    chunk_essay_for_extraction,
    analyze_text_concepts,
    extract_raw_arguments_local
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
    assert premises[0] == "Socrates is a man."
    assert premises[1] == "All men are mortal."
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

def test_split_logical_clauses_fallback_last_sentence():
    premises, conclusion = split_logical_clauses(
        "All mammals are warm-blooded. Whales are mammals. Whales are warm-blooded."
    )
    assert premises == ["All mammals are warm-blooded.", "Whales are mammals."]
    assert conclusion == "Whales are warm-blooded."

def test_split_logical_clauses_no_indicator_single_sentence():
    premises, conclusion = split_logical_clauses("Whales are warm-blooded.")
    assert premises == []
    assert conclusion == "Whales are warm-blooded."

def test_split_logical_clauses_causal_because():
    premises, conclusion = split_logical_clauses(
        "Because all mammals are warm-blooded, whales are warm-blooded."
    )
    assert premises == ["Because all mammals are warm-blooded"]
    assert conclusion == "whales are warm-blooded"

def test_split_logical_clauses_causal_since():
    premises, conclusion = split_logical_clauses(
        "Since all metals conduct electricity, copper conducts electricity."
    )
    assert premises == ["Since all metals conduct electricity"]
    assert conclusion == "copper conducts electricity"


def test_split_logical_clauses_single_sentence_commas():
    premises, conclusion = split_logical_clauses(
        "Socrates is a man, all men are mortal, thus Socrates is mortal"
    )
    assert len(premises) == 2
    assert premises[0] == "Socrates is a man"
    assert premises[1] == "all men are mortal"
    assert conclusion == "thus Socrates is mortal"


def test_parse_syllogism_no_indicators(nlp):
    text = (
        "All humans are mortal. "
        "Socrates is human. "
        "Socrates is mortal."
    )
    syll = parse_syllogism(text, nlp)

    assert len(syll.premises) == 2
    # pyrefly: ignore [missing-attribute]
    assert syll.major_premise.type_code == "A"
    # pyrefly: ignore [missing-attribute]
    assert syll.minor_premise.type_code == "Singular Affirmative"
    assert syll.conclusion.type_code == "Singular Affirmative"
    assert normalize_term(syll.middle_term) == "human"
    assert syll.major_term == "mortal"
    assert syll.minor_term == "Socrates"


def test_parse_syllogism_no_false_positive_so():
    text = (
        "I was tired so I went home early. "
        "All mammals are warm-blooded. "
        "Whales are mammals. "
        "Whales are warm-blooded."
    )
    premises, conclusion = split_logical_clauses(text)

    assert premises == [
        "I was tired so I went home early.",
        "All mammals are warm-blooded.",
        "Whales are mammals.",
    ]
    assert conclusion == "Whales are warm-blooded."


def test_clean_proposition_text():
    assert clean_proposition_text("Therefore Socrates is mortal.") == "Socrates is mortal"
    assert clean_proposition_text("thus all men are mortal,") == "all men are mortal"
    assert clean_proposition_text("  Hence some cats are black.  ") == "some cats are black"
    assert clean_proposition_text("Because all mammals are warm-blooded,") == "all mammals are warm-blooded"
    assert clean_proposition_text("Since copper is a metal") == "copper is a metal"
    assert clean_proposition_text("Whales are warm-blooded.") == "Whales are warm-blooded"

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
    # pyrefly: ignore [missing-attribute]
    assert syll.major_premise.type_code == "A"
    # pyrefly: ignore [missing-attribute]
    assert syll.minor_premise.type_code == "Singular Affirmative"


def test_chunk_essay_for_extraction_dependency_causal(nlp):
    text = (
        "The city expanded rapidly over the decade. "
        "Since roads were widened, traffic moved faster. "
        "Parks also became more accessible."
    )
    chunks = chunk_essay_for_extraction(text, nlp)

    assert any("Since roads were widened, traffic moved faster." in chunk for chunk in chunks)
    assert any("Parks also became more accessible." in chunk for chunk in chunks)


def test_chunk_essay_for_extraction_fallback_general_chunks(nlp):
    text = (
        "A1 sentence here. "
        "A2 sentence here. "
        "A3 sentence here. "
        "A4 sentence here. "
        "A5 sentence here."
    )
    chunks = chunk_essay_for_extraction(text, nlp)

    # No causal dependency markers: 3-sentence windows plus 4-pack general chunks.
    assert any(
        "A1 sentence here." in c and "A4 sentence here." in c for c in chunks
    )
    assert any(c.strip() == "A5 sentence here." for c in chunks)
    assert any(
        "A1 sentence here." in c and "A3 sentence here." in c for c in chunks
    )


def test_chunk_essay_three_sentence_syllogism(nlp):
    text = (
        "All humans are mortal. "
        "Socrates is human. "
        "Socrates is mortal."
    )
    chunks = chunk_essay_for_extraction(text, nlp)

    assert any(
        "All humans are mortal" in c
        and "Socrates is human" in c
        and "Socrates is mortal" in c
        for c in chunks
    )


def test_coordinate_clause_split_does_not_split_lists(nlp):
    # Lists should not be split
    text = "I like apples, oranges, and bananas."
    premises, conclusion = split_logical_clauses(text, nlp)
    assert len(premises) == 0
    assert conclusion == "I like apples, oranges, and bananas."


def test_parse_proposition_excludes_relative_clauses(nlp):
    # Relative clause 'who are tall' should be excluded from subject term
    p = parse_proposition("All men who are tall are mortal", nlp)
    assert p.quantifier == "all"
    assert normalize_term(p.subject) == "man"
    assert p.copula == "are"
    assert p.predicate == "mortal"


def test_parse_proposition_excludes_discourse_and_punctuation(nlp):
    # Trailing/leading punctuation and discourse markers should be excluded
    p = parse_proposition("Oh, indeed Socrates is mortal...", nlp)
    assert p.quantifier is None
    assert p.subject == "Socrates"
    assert p.copula == "is"
    assert p.predicate == "mortal"


def test_flexible_causal_premise_marker(nlp):
    # Adverbial clauses with causal meaning should be parsed using non-disallowed SCONJs
    premises, conclusion = split_logical_clauses(
        "As all mammals are warm-blooded, whales are warm-blooded.", nlp
    )
    assert premises == ["As all mammals are warm-blooded"]
    assert conclusion == "whales are warm-blooded"


def test_analyze_text_concepts(nlp):
    text = "Socrates is a smart philosopher who lives in Athens. He argues about truth."
    concepts = analyze_text_concepts(text, nlp)
    
    assert "noun_chunks" in concepts
    assert "entities" in concepts
    assert "key_terms" in concepts
    
    # Should identify Socrates
    assert any("Socrates" in chunk for chunk in concepts["noun_chunks"])
    # Should identify Athens as an entity
    assert any(ent["text"] == "Athens" for ent in concepts["entities"])
    # Key terms should contain content words
    assert any(t.lower() == "philosopher" for t in concepts["key_terms"])


def test_extract_raw_arguments_local(nlp):
    text = "Since all men are mortal, and Socrates is a man, Socrates is mortal."
    raw_args = extract_raw_arguments_local(text, nlp)
    
    assert len(raw_args) > 0
    assert "raw_premises" in raw_args[0]
    assert "raw_conclusion" in raw_args[0]
    
    # Verify that the causal premises and conclusion were parsed out
    assert any("mortal" in p for p in raw_args[0]["raw_premises"])
    assert "Socrates is mortal" in raw_args[0]["raw_conclusion"]


