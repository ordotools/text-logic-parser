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

def get_pronoun_candidates(pronoun_token: spacy.tokens.Token, history: List[Dict[str, Any]]) -> List[str]:
    """
    A heuristic to find probable antecedents based on morphology (Number/Gender) and recent clauses.
    """
    candidates = []
    
    pron_text = pronoun_token.text.lower()
    morph = pronoun_token.morph
    p_gender = morph.get("Gender")
    p_gender = p_gender[0] if p_gender else None
    p_number = morph.get("Number")
    p_number = p_number[0] if p_number else None
    
    is_masc = pron_text in ("he", "him", "his") or p_gender == "Masc"
    is_fem = pron_text in ("she", "her", "hers") or p_gender == "Fem"
    is_neut = pron_text in ("it", "its") or p_gender == "Neut"
    is_plur = pron_text in ("they", "them", "their") or p_number == "Plur"
    is_dem = pron_text in ("this", "that", "these", "those")
    
    scored = []
    for item in reversed(history):
        score = 0
        if item["type"] == "CLAUSE":
            if is_dem or is_neut:
                score += 5
            else:
                continue
        else:
            i_number = item.get("number")
            i_gender = item.get("gender")
            i_entity = item.get("entity_label")
            
            if is_plur:
                if i_number == "Plur": score += 3
                elif i_number == "Sing": score -= 5
            elif p_number == "Sing":
                if i_number == "Sing": score += 1
                elif i_number == "Plur": score -= 5
                
            if is_masc:
                if i_gender == "Masc": score += 3
                elif i_gender in ("Fem", "Neut"): score -= 5
                elif i_entity == "PERSON": score += 1
            elif is_fem:
                if i_gender == "Fem": score += 3
                elif i_gender in ("Masc", "Neut"): score -= 5
                elif i_entity == "PERSON": score += 1
            elif is_neut:
                if i_gender == "Neut": score += 3
                elif i_gender in ("Masc", "Fem"): score -= 5
                elif i_entity not in ("PERSON", None): score += 1
                elif i_entity == "PERSON": score -= 5
                
        scored.append((score, item["text"]))
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    seen = set()
    for score, text in scored:
        if score > -3 and text not in seen:
            seen.add(text)
            candidates.append(text)
            if len(candidates) >= 3:
                break
                
    if not candidates:
        if history:
            return [history[-1]["text"]]
        return [pron_text]
        
    return candidates

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
    
    clauses = []
    history = []
    
    for i, sent in enumerate(doc.sents):
        sent_entities = {ent.text: ent.label_ for ent in sent.ents}
        
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
            subject_candidates = []
            predicate_candidates = []
            original_subj_pronoun = None
            original_pred_pronoun = None
            
            # Find subject
            for child in root.children:
                if child.dep_ in ("nsubj", "nsubjpass", "csubj"):
                    subject_term = child.text
                    if child.pos_ == "PRON":
                        original_subj_pronoun = child.text
                        subject_candidates = get_pronoun_candidates(child, history)
                        subject_term = subject_candidates[0] if subject_candidates else child.text
                    break
                    
            # Find predicate
            for child in root.children:
                if child.dep_ in ("attr", "acomp", "dobj", "prep", "xcomp"):
                    if child.pos_ == "PRON":
                        original_pred_pronoun = child.text
                        predicate_candidates = get_pronoun_candidates(child, history)
                        predicate_term = predicate_candidates[0] if predicate_candidates else child.text
                    else:
                        predicate_term = "".join([t.text + t.whitespace_ for t in child.subtree]).strip()
                    break
                    
            if not subject_term:
                subject_term = "unknown_subject"
            if not predicate_term:
                predicate_term = "unknown_predicate"
                
            # Add current nouns and clause to history
            for token in clause_doc:
                if token.pos_ in ("NOUN", "PROPN"):
                    morph = token.morph
                    history.append({
                        "text": token.text,
                        "type": "NOUN",
                        "number": morph.get("Number")[0] if morph.get("Number") else None,
                        "gender": morph.get("Gender")[0] if morph.get("Gender") else None,
                        "entity_label": sent_entities.get(token.text)
                    })
            
            history.append({
                "text": f'[Clause: "{raw_clause}"]',
                "type": "CLAUSE"
            })
            
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
                "subject_candidates": subject_candidates,
                "predicate_candidates": predicate_candidates,
                "original_subj_pronoun": original_subj_pronoun,
                "original_pred_pronoun": original_pred_pronoun,
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
            
    # 1. Gather all premise term signatures from syllogisms and enthymemes
    valid_premise_signatures = []
    for cand in deduped_candidates:
        if cand["type"] in ("syllogism", "enthymeme"):
            for p in cand["premises"]:
                p_terms = p["terms"]
                p_signature = tuple(sorted(p_terms[:2]))
                valid_premise_signatures.append(p_signature)

    final_candidates = []
    for cand in deduped_candidates:
        if cand["type"] == "assumption":
            conc_terms = cand["conclusion"]["terms"]
            term_signature = tuple(sorted(conc_terms[:2]))
            
            # An assumption must be used as a premise elsewhere
            is_used_as_premise = False
            for p_sig in valid_premise_signatures:
                if term_signature == p_sig:
                    is_used_as_premise = True
                    break
                    
            if not is_used_as_premise:
                continue
                
        final_candidates.append(cand)

    return final_candidates
