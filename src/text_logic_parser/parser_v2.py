import re
import spacy
from typing import List, Dict, Any, Tuple, Optional
from text_logic_parser.parser import nlp_engine, analyze_text_concepts, _split_coordinate_clauses, _strip_leading_discourse_token

def clean_text_v2(text: str) -> str:
    """
    Cleans up text first, by getting rid of new lines, adding a space to avoid 
    concatenating words, unless the previous word ends with a hyphen.
    We do this even for paragraphs so that we have a long stream of text.
    """
    # Split text into lines
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if cleaned_lines and cleaned_lines[-1].endswith('-'):
            # Remove the hyphen and append the word without space
            cleaned_lines[-1] = cleaned_lines[-1][:-1] + line
        else:
            cleaned_lines.append(line)
            
    # Join with space
    return " ".join(cleaned_lines)

def resolve_pronouns(doc, concepts: Dict[str, Any]) -> Dict[spacy.tokens.Token, str]:
    """
    A lightweight heuristic to resolve pronouns to the most recent matching key term/noun chunk.
    """
    resolved_map = {}
    valid_nouns = []
    for chunk in doc.noun_chunks:
        if chunk.root.pos_ in ("NOUN", "PROPN"):
            valid_nouns.append(chunk.text)
            
    # Include key terms and entities
    for k in concepts.get("key_terms", []):
        if k not in valid_nouns:
            valid_nouns.append(k)
            
    recent_noun = None
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN") and token.text in valid_nouns:
            recent_noun = token.text
        elif token.pos_ == "PRON" and recent_noun:
            # Very basic resolution: map to the most recent noun seen.
            # In a real system, we'd check gender/number matching.
            if token.text.lower() in ("he", "she", "it", "they", "his", "her", "its", "their", "this", "that"):
                resolved_map[token] = recent_noun
                
    return resolved_map

def extract_clauses_v2(text: str, nlp=None) -> List[Dict[str, Any]]:
    """
    With spaCy, we extract all the complete clauses. 
    Examine subjects and predicates using key terms and noun list, matching pronouns.
    Returns a list of clause dictionaries.
    """
    if nlp is None:
        nlp = nlp_engine
        
    text = clean_text_v2(text)
    doc = nlp(text)
    concepts = analyze_text_concepts(text, nlp)
    resolved_pronouns = resolve_pronouns(doc, concepts)
    
    clauses = []
    
    for i, sent in enumerate(doc.sents):
        # We can use the existing _split_coordinate_clauses to get individual clauses from a sentence
        sub_clauses = _split_coordinate_clauses(sent.text, nlp)
        
        for raw_clause in sub_clauses:
            clause_doc = nlp(raw_clause)
            
            # Find root
            root = None
            for t in clause_doc:
                if t.dep_ == "ROOT":
                    root = t
                    break
                    
            if not root:
                continue
                
            subject_term = None
            predicate_term = None
            
            # Find subject
            for child in root.children:
                if child.dep_ in ("nsubj", "nsubjpass", "csubj"):
                    # Check if pronoun to resolve
                    original_subj = child.text
                    resolved_subj = original_subj
                    
                    # Try to map token from original doc to clause doc
                    # (this is approximate based on string match for simplicity)
                    for orig_token, res_val in resolved_pronouns.items():
                        if orig_token.text == child.text:
                            resolved_subj = res_val
                            break
                            
                    subject_term = resolved_subj
                    break
                    
            # Find predicate
            for child in root.children:
                if child.dep_ in ("attr", "acomp", "dobj", "prep", "xcomp"):
                    predicate_term = "".join([t.text + t.whitespace_ for t in child.subtree]).strip()
                    break
                    
            if not subject_term:
                subject_term = "unknown_subject"
            if not predicate_term:
                predicate_term = "unknown_predicate"
                
            # Collect terms
            terms = set()
            if subject_term != "unknown_subject":
                terms.add(subject_term.lower())
            
            # Extract nouns/key terms from predicate to serve as the predicate term match
            for pt in nlp(predicate_term):
                if pt.pos_ in ("NOUN", "PROPN", "ADJ") and len(pt.lemma_) > 2:
                    terms.add(pt.lemma_.lower())
                    
            if not terms:
                # Fallback to key terms in the clause
                for kt in concepts.get("key_terms", []):
                    if kt.lower() in raw_clause.lower():
                        terms.add(kt.lower())
            
            clauses.append({
                "original_text": raw_clause,
                "sentence_index": i,
                "subject": subject_term,
                "predicate": predicate_term,
                "terms": list(terms)
            })
            
    return clauses

def find_candidate_arguments(clauses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Examine each clause -> presume each is a conclusion candidate.
    If a clause has two terms in it that can be found separated in one or more clauses, 
    we have a candidate conclusion, and candidate premises.
    Returns:
      [{
         "conclusion": clause_dict,
         "premises": [clause_dict, ...],
         "type": "syllogism" | "enthymeme" | "assumption",
         "chunk_boundaries": (min_sent_idx, max_sent_idx)
      }]
    """
    candidates = []
    
    for i, conc_clause in enumerate(clauses):
        conc_terms = conc_clause["terms"]
        if len(conc_terms) < 2:
            # Need at least two terms to form S and P
            candidates.append({
                "conclusion": conc_clause,
                "premises": [],
                "type": "assumption",
                "chunk_boundaries": (conc_clause["sentence_index"], conc_clause["sentence_index"])
            })
            continue
            
        found_premises = []
        term_1 = conc_terms[0]
        term_2 = conc_terms[1]
        
        # Look for these terms in other clauses
        # To avoid grabbing clauses from completely different parts of the text,
        # we can prioritize nearby clauses (e.g., within 5 sentences). But user said: 
        # "look for syllogism candidates across the entire text stream before chunking"
        # We will search globally.
        for j, prem_clause in enumerate(clauses):
            if i == j:
                continue # Skip the conclusion itself
                
            prem_terms = prem_clause["terms"]
            if term_1 in prem_terms or term_2 in prem_terms:
                found_premises.append(prem_clause)
                
        # Determine type
        if len(found_premises) >= 2:
            arg_type = "syllogism"
            # Keep only the two best premises (e.g. closest distance)
            found_premises.sort(key=lambda p: abs(p["sentence_index"] - conc_clause["sentence_index"]))
            found_premises = found_premises[:2]
        elif len(found_premises) == 1:
            arg_type = "enthymeme"
        else:
            arg_type = "assumption"
            
        # Calculate boundaries
        indices = [conc_clause["sentence_index"]] + [p["sentence_index"] for p in found_premises]
        min_idx = min(indices)
        max_idx = max(indices)
        
        candidates.append({
            "conclusion": conc_clause,
            "premises": found_premises,
            "type": arg_type,
            "chunk_boundaries": (min_idx, max_idx)
        })
        
    # Deduplicate candidates based on the semantic terms of their conclusions.
    # If we have "All men are mortal" and later "First of all... all men are mortal",
    # their extracted S and P terms should match. We keep only the first occurrence.
    deduped_candidates = []
    seen_term_pairs = set()
    
    for cand in candidates:
        conc_terms = cand["conclusion"]["terms"]
        # Sort terms so order doesn't matter (S-P or P-S)
        term_signature = tuple(sorted(conc_terms[:2]))
        
        if term_signature not in seen_term_pairs:
            seen_term_pairs.add(term_signature)
            deduped_candidates.append(cand)
            
    return deduped_candidates
