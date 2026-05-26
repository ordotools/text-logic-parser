from text_logic_parser.models import Proposition, Syllogism, normalize_term

def test_normalize_term():
    assert normalize_term("Socrates") == "socrates"
    assert normalize_term("a man") == "man"
    assert normalize_term("the mortal") == "mortal"
    assert normalize_term("cats") == "cat"
    assert normalize_term("dogs") == "dog"
    assert normalize_term("men") == "man"
    assert normalize_term("women") == "woman"
    assert normalize_term("  An apple  ") == "apple"

def test_proposition_properties():
    # A: Universal Affirmative
    p1 = Proposition("all", "men", "are", "mortal")
    assert p1.quantifier == "all"
    assert p1.subject == "men"
    assert p1.copula == "are"
    assert p1.predicate == "mortal"
    assert p1.is_universal is True
    assert p1.is_particular is False
    assert p1.is_negative is False
    assert p1.is_singular is False
    assert p1.type_code == "A"
    assert p1.is_subject_distributed is True
    assert p1.is_predicate_distributed is False

    # E: Universal Negative
    p2 = Proposition("no", "reptiles", "have", "fur")
    # Copula logic checks 'not' or quantifier 'no'
    assert p2.is_universal is True
    assert p2.is_negative is True
    assert p2.type_code == "E"
    assert p2.is_subject_distributed is True
    assert p2.is_predicate_distributed is True

    # I: Particular Affirmative
    p3 = Proposition("some", "philosophers", "are", "wise")
    assert p3.is_particular is True
    assert p3.is_negative is False
    assert p3.type_code == "I"
    assert p3.is_subject_distributed is False
    assert p3.is_predicate_distributed is False

    # O: Particular Negative
    p4 = Proposition("some", "politicians", "are not", "honest")
    assert p4.is_particular is True
    assert p4.is_negative is True
    assert p4.type_code == "O"
    assert p4.is_subject_distributed is False
    assert p4.is_predicate_distributed is True

    # Singular Affirmative
    p5 = Proposition(None, "Socrates", "is", "a man")
    assert p5.is_singular is True
    assert p5.is_negative is False
    assert p5.type_code == "Singular Affirmative"
    assert p5.is_subject_distributed is True
    assert p5.is_predicate_distributed is False

    # Singular Negative
    p6 = Proposition(None, "Plato", "is not", "foolish")
    assert p6.is_singular is True
    assert p6.is_negative is True
    assert p6.type_code == "Singular Negative"
    assert p6.is_subject_distributed is True
    assert p6.is_predicate_distributed is True

def test_syllogism_term_deduction():
    premise1 = Proposition(None, "Socrates", "is", "a man")
    premise2 = Proposition("all", "men", "are", "mortal")
    conclusion = Proposition(None, "Socrates", "is", "mortal")
    
    syll = Syllogism([premise1, premise2], conclusion)
    
    # Check term deduction
    # S = Socrates, P = mortal, M = man/men (since normalize_term("a man") == "man" == normalize_term("men"))
    assert syll.minor_term == "Socrates"
    assert syll.major_term == "mortal"
    assert normalize_term(syll.middle_term) == "man"
    
    # Check major vs minor premise mapping
    # Major premise contains major term "mortal" -> premise2
    # Minor premise contains minor term "Socrates" -> premise1
    assert syll.major_premise == premise2
    assert syll.minor_premise == premise1
