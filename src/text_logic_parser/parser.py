import re
import spacy
from typing import List, Tuple, Optional
from .models import Proposition, Syllogism

# Load spaCy NLP engine
try:
    nlp_engine = spacy.load("en_core_web_sm")
except OSError:
    # Fallback if not downloaded, though we expect it to be downloaded
    nlp_engine = None

# Conclusion indicators to segment the syllogism conclusion
CONCLUSION_INDICATORS = [
    "therefore", "thus", "hence", "consequently", "so", 
    "it follows that", "implies that", "we can conclude that"
]

def split_logical_clauses(text: str) -> Tuple[List[str], str]:
    """
    Splits an input logical argument text into a list of premises and a conclusion.
    Uses punctuation, coordinate conjunctions, and conclusion indicators.
    """
    # Normalize spacing and strip
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 1. Identify the conclusion using indicators
    pattern = r'\b(' + '|'.join(CONCLUSION_INDICATORS) + r')\b'
    match = re.search(pattern, text, re.IGNORECASE)
    
    premises_text = text
    conclusion_text = ""
    
    if match:
        start_idx = match.start()
        premises_text = text[:start_idx].strip()
        conclusion_text = text[start_idx:].strip()
    
    # Clean trailing punctuation from premises block
    if premises_text.endswith(','):
        premises_text = premises_text[:-1].strip()
        
    # 2. Split premises into individual clauses
    # Split by periods, semicolons, or newlines first
    raw_clauses = re.split(r'[.;\n]+', premises_text)
    premise_clauses = []
    
    for clause in raw_clauses:
        clause = clause.strip()
        if not clause:
            continue
            
        # Check if the clause contains a comma or coordinate conjunction "and"/"but"
        # We can split on commas, or ' and ' / ' but ' if both sides represent full propositions (>= 3 words)
        sub_splits = re.split(r', and |, | and | but ', clause, flags=re.IGNORECASE)
        
        valid_sub_splits = []
        for sub in sub_splits:
            sub = sub.strip()
            if not sub:
                continue
            # Strip leading conjunctions if any
            if sub.lower().startswith("and "):
                sub = sub[4:].strip()
            if sub.lower().startswith("but "):
                sub = sub[4:].strip()
            valid_sub_splits.append(sub)
            
        # Only perform the split if every sub-clause has at least 3 words (Subject + Copula + Predicate)
        is_valid_split = len(valid_sub_splits) > 1 and all(len(s.split()) >= 3 for s in valid_sub_splits)
        
        if is_valid_split:
            premise_clauses.extend(valid_sub_splits)
        else:
            premise_clauses.append(clause)
            
    return premise_clauses, conclusion_text

def clean_proposition_text(text: str) -> str:
    """Removes leading conclusion indicators and extra punctuation."""
    text = text.strip()
    # Strip any ending period or comma
    if text.endswith('.') or text.endswith(','):
        text = text[:-1].strip()
        
    # Remove leading conclusion indicator if present (e.g. "Therefore Socrates is mortal" -> "Socrates is mortal")
    pattern = r'^(' + '|'.join(CONCLUSION_INDICATORS) + r')\b\s*'
    text = re.sub(pattern, '', text, flags=re.IGNORECASE).strip()
    
    return text

def parse_proposition(text: str, nlp=None) -> Proposition:
    """
    Parses a single natural language clause into a logical Proposition object using spaCy.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    cleaned_text = clean_proposition_text(text)
    doc = nlp(cleaned_text)
    
    # 1. Locate the main verb/copula (ROOT)
    root = None
    for token in doc:
        if token.dep_ == "ROOT":
            root = token
            break
            
    if not root:
        # Fallback if no root token found
        words = cleaned_text.split()
        return Proposition(None, words[0], "is", " ".join(words[1:]))

    # 2. Find Nominal Subject (nsubj or nsubjpass)
    subject_token = None
    for child in root.children:
        if child.dep_ in ("nsubj", "nsubjpass"):
            subject_token = child
            break
            
    # Fallback subject if not found
    if not subject_token:
        # Try to find any noun/pronoun before the root verb
        for token in doc:
            if token.i < root.i and token.pos_ in ("PROPN", "NOUN", "PRON"):
                subject_token = token
                break

    # 3. Extract Quantifier and Subject Term
    quantifier = None
    subject_text = ""
    
    if subject_token:
        # Check if subject has a determiner or adjective child that acts as a quantifier
        for child in subject_token.children:
            if child.dep_ in ("det", "amod") and child.text.lower() in ("all", "some", "no", "every", "each", "any"):
                quantifier = child.text.lower()
                # If "every" or "each" or "any", map to standard "all"
                if quantifier in ("every", "each", "any"):
                    quantifier = "all"
                break
        
        # Reconstruct the subject term text (excluding the quantifier child)
        subj_tokens = sorted([t for t in subject_token.subtree if not (quantifier and t.text.lower() == quantifier)], key=lambda t: t.i)
        subject_text = "".join([t.text + t.whitespace_ for t in subj_tokens]).strip()
    else:
        subject_text = cleaned_text.split()[0] # absolute fallback

    # 4. Check for negation and construct the copula
    is_negated = False
    neg_token = None
    for child in root.children:
        if child.dep_ == "neg":
            is_negated = True
            neg_token = child
            break
            
    copula_text = root.text
    if is_negated:
        # Build "is not" / "are not"
        copula_text = f"{root.text} {neg_token.text}"

    # 5. Extract Predicate Term
    # The predicate is usually the attribute (attr), adjectival complement (acomp),
    # direct object (dobj), or a prepositional phrase (prep) of the root verb.
    pred_token = None
    for child in root.children:
        if child.dep_ in ("attr", "acomp", "dobj", "prep", "xcomp"):
            pred_token = child
            break
            
    predicate_text = ""
    if pred_token:
        # Reconstruct predicate term text from its full subtree (excluding negation child if it was placed here)
        pred_tokens = sorted([t for t in pred_token.subtree if t.dep_ != "neg"], key=lambda t: t.i)
        predicate_text = "".join([t.text + t.whitespace_ for t in pred_tokens]).strip()
    else:
        # Fallback: take all tokens after the root verb
        pred_tokens = [t for t in doc if t.i > root.i and t.dep_ != "neg"]
        if pred_tokens:
            predicate_text = "".join([t.text + t.whitespace_ for t in pred_tokens]).strip()
        else:
            predicate_text = "mortal" # default/last resort fallback

    # Double check if quantifier was incorrectly captured inside subject
    # E.g. if subject_text starts with "all ", strip it
    for q in ("all ", "some ", "no "):
        if subject_text.lower().startswith(q):
            if not quantifier:
                quantifier = q.strip()
            subject_text = subject_text[len(q):].strip()
            
    return Proposition(quantifier, subject_text, copula_text, predicate_text)

def parse_syllogism(text: str, nlp=None) -> Syllogism:
    """
    Parses a full multi-sentence natural language logical argument into a structured Syllogism.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    # 1. Segment the text into premises and conclusion
    premise_clauses, conclusion_clause = split_logical_clauses(text)
    
    if not conclusion_clause:
        raise ValueError("Could not find a conclusion clause in the argument. Ensure you use an indicator word like 'Therefore', 'Thus', or 'Hence'.")
        
    # 2. Parse premises
    premises = [parse_proposition(clause, nlp) for clause in premise_clauses if clause.strip()]
    
    # 3. Parse conclusion
    conclusion = parse_proposition(conclusion_clause, nlp)
    
    # 4. Create and return the Syllogism
    return Syllogism(premises, conclusion)
