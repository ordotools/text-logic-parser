import re
import spacy
from typing import List, Optional

# Load spaCy NLP engine for lemmatization
try:
    nlp_engine = spacy.load("en_core_web_sm")
except OSError:
    nlp_engine = None

def normalize_term(term: str) -> str:
    """
    Utility to normalize terms for matching.
    Lowercases, strips whitespace, removes leading articles,
    and handles advanced lemmatization with spaCy (with rule-based fallback).
    """
    if not term:
        return ""
    
    term_stripped = term.strip()
    
    # Check if the last word of the term starts with a capital letter to identify proper nouns
    words = term_stripped.split()
    is_proper = False
    if words:
        last_word = words[-1]
        last_word_clean = last_word.strip(".,;:!?")
        if last_word_clean and last_word_clean[0].isupper():
            is_proper = True
            
    term_lower = term_stripped.lower()
    
    # Remove leading articles
    for article in ["a ", "an ", "the "]:
        if term_lower.startswith(article):
            term_stripped = term_stripped[len(article):].strip()
            term_lower = term_stripped.lower()
            break

    if is_proper:
        return term_lower

    if nlp_engine is not None:
        doc = nlp_engine(term_stripped)
        normalized_tokens = []
        protected_nouns = {"socrates", "athens"}
        for t in doc:
            lemma = t.lemma_.lower()
            if t.text.lower() in protected_nouns:
                lemma = t.text.lower()
            normalized_tokens.append(lemma + t.whitespace_)
        return "".join(normalized_tokens).strip()
        
    # --- FALLBACK RULE-BASED LOGIC ---
    # Strip trailing 's' or 'es' for simple plural matching
    irregular = {
        "men": "man",
        "women": "woman",
        "children": "child",
        "people": "person"
    }
    if term_lower in irregular:
        return irregular[term_lower]
        
    if term_lower.endswith("es") and len(term_lower) > 4:
        stem = term_lower[:-2]
        if stem.endswith(("s", "x", "z", "ch", "sh")):
            return stem
        else:
            return term_lower[:-1] # E.g., "reptiles" -> "reptile"
            
    if term_lower.endswith("s") and not term_lower.endswith("ss") and len(term_lower) > 3:
        return term_lower[:-1]
        
    return term_lower



class Proposition:
    """
    Represents a categorical or singular logical proposition.
    E.g., "All men are mortal", "Socrates is a man".
    """
    def __init__(self, quantifier: Optional[str], subject: str, copula: str, predicate: str, is_implicit: bool = False):
        self.quantifier = quantifier.strip().lower() if quantifier else None
        self.subject = subject.strip()
        self.copula = copula.strip().lower()
        self.predicate = predicate.strip()
        self.is_implicit = is_implicit

    @property
    def is_negative(self) -> bool:
        """True if the proposition is negative (contains 'not' or quantifier is 'no')."""
        if self.quantifier == "no":
            return True
        # Check if copula contains negation (e.g. "is not", "are not")
        return "not" in self.copula

    @property
    def is_universal(self) -> bool:
        """True if the proposition is universal ("all" or "no")."""
        return self.quantifier in ["all", "no"]

    @property
    def is_particular(self) -> bool:
        """True if the proposition is particular ("some")."""
        return self.quantifier == "some"

    @property
    def is_singular(self) -> bool:
        """True if the proposition is singular (quantifier is None, e.g., "Socrates is a man")."""
        return self.quantifier is None

    @property
    def type_code(self) -> str:
        """
        Returns the standard logical code:
        - A: Universal Affirmative ("All S are P")
        - E: Universal Negative ("No S are P" or "All S are not P")
        - I: Particular Affirmative ("Some S are P")
        - O: Particular Negative ("Some S are not P")
        - Singular Affirmative: "Singular Affirmative"
        - Singular Negative: "Singular Negative"
        """
        if self.is_singular:
            return "Singular Negative" if self.is_negative else "Singular Affirmative"
        
        if self.is_universal:
            return "E" if self.is_negative else "A"
        else: # particular
            return "O" if self.is_negative else "I"

    @property
    def is_subject_distributed(self) -> bool:
        """
        Subject is distributed in Universal (A, E) and Singular propositions.
        Subject is undistributed in Particular (I, O) propositions.
        """
        return self.is_universal or self.is_singular

    @property
    def is_predicate_distributed(self) -> bool:
        """
        Predicate is distributed in Negative (E, O, Singular Negative) propositions.
        Predicate is undistributed in Affirmative (A, I, Singular Affirmative) propositions.
        """
        return self.is_negative

    def __repr__(self) -> str:
        q_str = f"{self.quantifier.capitalize()} " if self.quantifier else ""
        return f"{q_str}{self.subject} {self.copula} {self.predicate} [{self.type_code}]"

    def __str__(self) -> str:
        return self.__repr__()


class Syllogism:
    """
    Represents a categorical syllogism with two premises and a conclusion.
    """
    def __init__(self, premises: List[Proposition], conclusion: Proposition):
        self.premises = premises
        self.conclusion = conclusion
        
        self.minor_term = ""  # Subject of conclusion (S)
        self.major_term = ""  # Predicate of conclusion (P)
        self.middle_term = "" # Shared term in premises (M)
        
        self._deduce_terms()

    def _terms_match(self, term1: str, term2: str) -> bool:
        """Check if two terms match after normalization."""
        return normalize_term(term1) == normalize_term(term2)

    def _deduce_terms(self):
        """Deduces the Major, Minor, and Middle terms of the syllogism."""
        # 1. Minor term (S) is the subject of the conclusion
        self.minor_term = self.conclusion.subject
        
        # 2. Major term (P) is the predicate of the conclusion
        self.major_term = self.conclusion.predicate
        
        # 3. Middle term (M) is the term appearing in premises but not in the conclusion
        # Look at the subjects and predicates of premises
        premise_terms = []
        for p in self.premises:
            premise_terms.extend([p.subject, p.predicate])
            
        # Find which term in premises does not match minor or major terms
        for term in premise_terms:
            if not self._terms_match(term, self.minor_term) and not self._terms_match(term, self.major_term):
                self.middle_term = term
                break

    @property
    def major_premise(self) -> Optional[Proposition]:
        """The premise containing the Major Term (P)."""
        for p in self.premises:
            if self._terms_match(p.subject, self.major_term) or self._terms_match(p.predicate, self.major_term):
                return p
        return None

    @property
    def minor_premise(self) -> Optional[Proposition]:
        """The premise containing the Minor Term (S)."""
        for p in self.premises:
            if self._terms_match(p.subject, self.minor_term) or self._terms_match(p.predicate, self.minor_term):
                return p
        return None

    def format_details(self) -> str:
        """Returns a beautiful, formatted string of the syllogism details."""
        lines = []
        lines.append("Parsed Syllogism:")
        lines.append("-----------------")
        
        minor_p = self.minor_premise
        major_p = self.major_premise
        
        # Format Minor Premise
        if minor_p:
            subj_label = "S" if self._terms_match(minor_p.subject, self.minor_term) else "M"
            pred_label = "M" if subj_label == "S" else "S"
            lines.append(f"Minor Premise: {minor_p.quantifier.capitalize() + ' ' if minor_p.quantifier else ''}{minor_p.subject} ({subj_label}) {minor_p.copula} {minor_p.predicate} ({pred_label}) [{minor_p.type_code}]")
        else:
            lines.append("Minor Premise: [Could not identify]")
            
        # Format Major Premise
        if major_p:
            subj_label = "P" if self._terms_match(major_p.subject, self.major_term) else "M"
            pred_label = "M" if subj_label == "P" else "P"
            lines.append(f"Major Premise: {major_p.quantifier.capitalize() + ' ' if major_p.quantifier else ''}{major_p.subject} ({subj_label}) {major_p.copula} {major_p.predicate} ({pred_label}) [{major_p.type_code}]")
        else:
            lines.append("Major Premise: [Could not identify]")
            
        # Format Conclusion
        lines.append(f"Conclusion:    Therefore {self.conclusion.subject} (S) {self.conclusion.copula} {self.conclusion.predicate} (P) [{self.conclusion.type_code}]")
        lines.append("")
        lines.append(f"Middle Term (M): {self.middle_term}")
        lines.append(f"Minor Term  (S): {self.minor_term}")
        lines.append(f"Major Term  (P): {self.major_term}")
        
        return "\n".join(lines)
