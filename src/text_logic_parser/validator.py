from typing import List, Dict, Any, Optional
from .models import Proposition, Syllogism, normalize_term

class FallacyViolation:
    """Represents a specific logic rule violation in a syllogism."""
    def __init__(self, code: str, title: str, description: str, details: str, is_warning: bool = False):
        self.code = code
        self.title = title
        self.description = description
        self.details = details
        self.is_warning = is_warning # If True, it's flagged as a caveat (like modern existential fallacy) rather than absolute invalidity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "is_warning": self.is_warning
        }

def validate_syllogism(syll: Syllogism) -> List[Dict[str, Any]]:
    """
    Validates a syllogism against the classical rules of Aristotelian syllogistic logic.
    Returns a list of detailed fallacy violations (empty list means the argument is fully valid).
    """
    violations = []
    
    # 0. Structural check: make sure we have exactly two premises and a conclusion
    if not syll.premises or len(syll.premises) != 2:
        return [FallacyViolation(
            code="incomplete_syllogism",
            title="Incomplete Syllogism",
            description="A categorical syllogism must contain exactly two premises.",
            details=f"Found {len(syll.premises)} premise(s)."
        ).to_dict()]
        
    major_p = syll.major_premise
    minor_p = syll.minor_premise
    conclusion = syll.conclusion
    
    # If we couldn't separate them because terms didn't align
    if not major_p or not minor_p:
        return [FallacyViolation(
            code="term_matching_error",
            title="Term Alignment Failure",
            description="The terms in the premises could not be aligned with the conclusion.",
            details="Ensure the major term (conclusion predicate) appears in one premise, and the minor term (conclusion subject) appears in the other."
        ).to_dict()]

    S_norm = normalize_term(syll.minor_term)
    P_norm = normalize_term(syll.major_term)
    M_norm = normalize_term(syll.middle_term)
    
    # --- Rule 1: Four Terms Fallacy (Quaternio Terminorum) ---
    # In a standard syllogism, there must be exactly three terms, each used twice.
    # Collect all terms in the premises and conclusion
    terms_in_syllogism = set()
    for prop in [major_p, minor_p, conclusion]:
        terms_in_syllogism.add(normalize_term(prop.subject))
        terms_in_syllogism.add(normalize_term(prop.predicate))
        
    # Remove empty terms if any
    terms_in_syllogism.discard("")
    
    # Check if there are exactly 3 unique normalized terms
    is_four_terms = False
    details_four_terms = ""
    if len(terms_in_syllogism) != 3:
        is_four_terms = True
        details_four_terms = f"Found {len(terms_in_syllogism)} unique terms: " + ", ".join(f"'{t}'" for t in terms_in_syllogism)
    else:
        # Check that the terms present are exactly S_norm, P_norm, M_norm
        expected_terms = {S_norm, P_norm, M_norm}
        if terms_in_syllogism != expected_terms:
            is_four_terms = True
            details_four_terms = f"Expected terms: " + ", ".join(expected_terms) + f". Got: " + ", ".join(terms_in_syllogism)

    if is_four_terms:
        violations.append(FallacyViolation(
            code="four_terms",
            title="Fallacy of Four Terms (Quaternio Terminorum)",
            description="A valid syllogism must contain exactly three distinct logical terms, each used in the same sense throughout the argument.",
            details=details_four_terms
        ).to_dict())
        # If we have a four-term fallacy, other distribution rules cannot be computed reliably, so return early
        return violations

    # Helper function to check if a specific term (by normalized name) is distributed in a proposition
    def is_term_distributed_in_prop(term_norm: str, prop: Proposition) -> bool:
        if normalize_term(prop.subject) == term_norm:
            return prop.is_subject_distributed
        if normalize_term(prop.predicate) == term_norm:
            return prop.is_predicate_distributed
        return False

    # --- Rule 2: Undistributed Middle ---
    # The middle term (M) must be distributed in at least one premise.
    m_in_major = is_term_distributed_in_prop(M_norm, major_p)
    m_in_minor = is_term_distributed_in_prop(M_norm, minor_p)
    
    if not m_in_major and not m_in_minor:
        violations.append(FallacyViolation(
            code="undistributed_middle",
            title="Fallacy of the Undistributed Middle",
            description="The middle term (the term appearing in both premises but not in the conclusion) must be distributed in at least one premise.",
            details=f"The middle term '{syll.middle_term}' is undistributed in both the Major Premise ('{major_p}') and Minor Premise ('{minor_p}')."
        ).to_dict())

    # --- Rule 3: Illicit Major ---
    # If the major term (P) is distributed in the conclusion, it must be distributed in the major premise.
    p_in_conclusion = conclusion.is_predicate_distributed # P is predicate in conclusion
    if p_in_conclusion:
        p_in_major = is_term_distributed_in_prop(P_norm, major_p)
        if not p_in_major:
            violations.append(FallacyViolation(
                code="illicit_major",
                title="Fallacy of Illicit Major",
                description="The major term (the predicate of the conclusion) cannot be distributed in the conclusion unless it is also distributed in the major premise.",
                details=f"The major term '{syll.major_term}' is distributed in the conclusion ('{conclusion}') but not distributed in the major premise ('{major_p}')."
            ).to_dict())

    # --- Rule 4: Illicit Minor ---
    # If the minor term (S) is distributed in the conclusion, it must be distributed in the minor premise.
    s_in_conclusion = conclusion.is_subject_distributed # S is subject in conclusion
    if s_in_conclusion:
        s_in_minor = is_term_distributed_in_prop(S_norm, minor_p)
        if not s_in_minor:
            violations.append(FallacyViolation(
                code="illicit_minor",
                title="Fallacy of Illicit Minor",
                description="The minor term (the subject of the conclusion) cannot be distributed in the conclusion unless it is also distributed in the minor premise.",
                details=f"The minor term '{syll.minor_term}' is distributed in the conclusion ('{conclusion}') but not distributed in the minor premise ('{minor_p}')."
            ).to_dict())

    # --- Rule 5: Exclusive Premises ---
    # A syllogism cannot have two negative premises.
    if major_p.is_negative and minor_p.is_negative:
        violations.append(FallacyViolation(
            code="exclusive_premises",
            title="Fallacy of Exclusive Premises",
            description="A valid syllogism cannot have two negative premises. If both premises are negative, no logical connection can be made.",
            details=f"Both Major Premise ('{major_p}') and Minor Premise ('{minor_p}') are negative."
        ).to_dict())

    # --- Rule 6: Affirmative Conclusion from a Negative Premise ---
    # If either premise is negative, the conclusion must be negative.
    if (major_p.is_negative or minor_p.is_negative) and not conclusion.is_negative:
        violations.append(FallacyViolation(
            code="affirmative_from_negative",
            title="Affirmative Conclusion from a Negative Premise",
            description="If either premise is negative, the conclusion must also be negative. An affirmative conclusion cannot follow from negative premises.",
            details=f"One or both premises are negative, but the conclusion ('{conclusion}') is affirmative."
        ).to_dict())

    # --- Rule 7: Negative Conclusion from Affirmative Premises ---
    # If the conclusion is negative, one of the premises must be negative.
    if conclusion.is_negative and not major_p.is_negative and not minor_p.is_negative:
        violations.append(FallacyViolation(
            code="negative_from_affirmative",
            title="Negative Conclusion from Affirmative Premises",
            description="If both premises are affirmative, the conclusion must also be affirmative. A negative conclusion cannot be drawn from positive premises.",
            details=f"Both premises are affirmative, but the conclusion ('{conclusion}') is negative."
        ).to_dict())

    # --- Rule 8: Existential Fallacy (Modern Logic Caveat) ---
    # Drawing a particular conclusion from two universal premises.
    # Universal premises: A or E
    # Particular conclusion: I or O, or Singular
    # Let's check if both premises are universal, and the conclusion is not universal
    if major_p.is_universal and minor_p.is_universal and (conclusion.is_particular or conclusion.is_singular):
        violations.append(FallacyViolation(
            code="existential_fallacy",
            title="Existential Fallacy (Modern Logic)",
            description="Drawing a particular conclusion from universal premises. Universal statements in modern logic do not assume the existence of their subjects, whereas particular statements do.",
            details=f"Both premises are universal ('{major_p}' and '{minor_p}'), but the conclusion ('{conclusion}') is particular/singular, assuming the existence of '{syll.minor_term}'.",
            is_warning=True
        ).to_dict())

    return violations
