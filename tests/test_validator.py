from text_logic_parser.models import Proposition, Syllogism
from text_logic_parser.validator import validate_syllogism

def test_valid_syllogism_barbara():
    # Socrates is a man. All men are mortal. Therefore Socrates is mortal.
    p1 = Proposition(None, "Socrates", "is", "a man")
    p2 = Proposition("all", "men", "are", "mortal")
    conc = Proposition(None, "Socrates", "is", "mortal")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    # Fully valid, should have no violations
    assert len(violations) == 0

def test_valid_syllogism_celarent():
    # No reptiles are warm-blooded. All snakes are reptiles. Therefore no snakes are warm-blooded.
    p1 = Proposition("no", "reptiles", "are", "warm-blooded")
    p2 = Proposition("all", "snakes", "are", "reptiles")
    conc = Proposition("no", "snakes", "are", "warm-blooded")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    assert len(violations) == 0

def test_undistributed_middle():
    # All dogs are animals. All cats are animals. Therefore all cats are dogs.
    p1 = Proposition("all", "dogs", "are", "animals")
    p2 = Proposition("all", "cats", "are", "animals")
    conc = Proposition("all", "cats", "are", "dogs")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "undistributed_middle" in codes

def test_illicit_major():
    # All dogs are mammals. No cats are dogs. Therefore no cats are mammals.
    p1 = Proposition("all", "dogs", "are", "mammals")
    p2 = Proposition("no", "cats", "are", "dogs")
    conc = Proposition("no", "cats", "are", "mammals")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "illicit_major" in codes

def test_illicit_minor():
    # All men are mortal. All men are wise. Therefore all wise are mortal.
    p1 = Proposition("all", "men", "are", "mortal")
    p2 = Proposition("all", "men", "are", "wise")
    conc = Proposition("all", "wise", "are", "mortal")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "illicit_minor" in codes

def test_exclusive_premises():
    # No politicians are honest. Some actors are not politicians. Therefore some actors are not honest.
    p1 = Proposition("no", "politicians", "are", "honest")
    p2 = Proposition("some", "actors", "are not", "politicians")
    conc = Proposition("some", "actors", "are not", "honest")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "exclusive_premises" in codes

def test_affirmative_from_negative():
    # No thieves are trustworthy. Socrates is a thief. Therefore Socrates is trustworthy.
    p1 = Proposition("no", "thief", "is", "trustworthy")
    p2 = Proposition(None, "Socrates", "is", "a thief")
    conc = Proposition(None, "Socrates", "is", "trustworthy")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "affirmative_from_negative" in codes

def test_negative_from_affirmative():
    # All cats are mammals. All mammals are warm-blooded. Therefore no cats are warm-blooded.
    p1 = Proposition("all", "cats", "are", "mammals")
    p2 = Proposition("all", "mammals", "are", "warm-blooded")
    conc = Proposition("no", "cats", "are", "warm-blooded")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "negative_from_affirmative" in codes

def test_existential_fallacy():
    # All humans are mortal. All Greeks are humans. Therefore some Greeks are mortal.
    p1 = Proposition("all", "humans", "are", "mortal")
    p2 = Proposition("all", "Greeks", "are", "humans")
    conc = Proposition("some", "Greeks", "are", "mortal")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    # Existential fallacy is flagged as a warning
    assert len(violations) == 1
    assert violations[0]["code"] == "existential_fallacy"
    assert violations[0]["is_warning"] is True

def test_four_terms_fallacy():
    # All cats are furry. Socrates is a man. Therefore Socrates is furry.
    p1 = Proposition("all", "cats", "are", "furry")
    p2 = Proposition(None, "Socrates", "is", "a man")
    conc = Proposition(None, "Socrates", "is", "furry")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    codes = [v["code"] for v in violations]
    assert "four_terms" in codes

def test_four_terms_resolved_with_spacy():
    # Test that plural vs singular "warm-blooded reptiles" vs "warm-blooded reptile" unifies correctly
    # and does NOT trigger four terms fallacy.
    # Premise 1: All warm-blooded reptiles are active.
    # Premise 2: This animal is a warm-blooded reptile.
    # Conclusion: Therefore this animal is active.
    p1 = Proposition("all", "warm-blooded reptiles", "are", "active")
    p2 = Proposition(None, "this animal", "is", "a warm-blooded reptile")
    conc = Proposition(None, "this animal", "is", "active")
    
    syll = Syllogism([p1, p2], conc)
    violations = validate_syllogism(syll)
    
    # Check that there are no four terms fallacy violations
    codes = [v["code"] for v in violations]
    assert "four_terms" not in codes
    assert len(violations) == 0

