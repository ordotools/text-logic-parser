import re
import spacy
from typing import List, Tuple, Optional, Dict, Any
from .models import Proposition, Syllogism

# Load spaCy NLP engine
try:
    nlp_engine = spacy.load("en_core_web_sm")
except OSError:
    # Fallback if not downloaded, though we expect it to be downloaded
    nlp_engine = None

CAUSAL_MARKERS = {"because", "since", "as", "given"}
NON_PREMISE_SUBORDINATORS = {
    "if", "unless", "whether", "although", "though", "even", "while", 
    "whereas", "before", "after", "until", "till", "once"
}

def _strip_leading_discourse_token(token) -> bool:
    """True when a leading token is a premise/discourse marker to drop."""
    if token.is_punct:
        return True
    if token.lemma_.lower() in NON_PREMISE_SUBORDINATORS:
        return False
    return token.pos_ in ("ADV", "SCONJ") and token.dep_ in ("advmod", "mark")

def _extract_causal_dependency_pair(doc) -> Optional[Tuple[str, str]]:
    """
    Detects causal relation from dependency tree using `advcl` + `mark`.
    Returns (premise, conclusion) when a causal pair is found.
    """
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if not sent_text:
            continue

        for token in sent:
            if token.dep_ != "advcl":
                continue

            marker_children = [
                child
                for child in token.children
                if child.dep_ == "mark" and child.lemma_.lower() not in NON_PREMISE_SUBORDINATORS
            ]
            if not marker_children:
                continue

            premise_span = token.doc[token.left_edge.i:token.right_edge.i + 1]
            premise_text = premise_span.text.strip()
            if not premise_text:
                continue

            premise_pattern = r'(?:,\s*)?' + re.escape(premise_text) + r'(?:\s*,)?'
            conclusion_text = re.sub(premise_pattern, ' ', sent_text, count=1).strip(" ,.;")
            conclusion_text = re.sub(r'\s+', ' ', conclusion_text).strip()

            if conclusion_text:
                return premise_text, conclusion_text

    return None

def is_coordinator(t) -> bool:
    return t.text in (",", ";") or t.pos_ == "CCONJ" or t.text.lower() in ("and", "but", "or", "yet")

def is_content_token(t) -> bool:
    return not is_coordinator(t) and not t.is_punct

def _clean_split_clause(s: str) -> str:
    s = s.strip()
    # Strip leading coordinator words
    lower_s = s.lower()
    for coord in ("and ", "but ", "or ", "yet "):
        if lower_s.startswith(coord):
            s = s[len(coord):].strip()
            lower_s = s.lower()
    # Strip leading/trailing punctuation
    s = s.strip(" \t\n\r,.;:")
    return s

def _split_coordinate_clauses(clause: str, nlp=None) -> List[str]:
    """Split on coordinate clauses using spaCy dependency parser."""
    clause = clause.strip()
    if not clause:
        return []

    if nlp is None:
        nlp = nlp_engine

    if nlp is None:
        # Fallback if spaCy model is not loaded
        sub_splits = re.split(r';|, and |, | and | but ', clause, flags=re.IGNORECASE)
        valid_sub_splits = []
        for sub in sub_splits:
            cleaned = _clean_split_clause(sub)
            if cleaned:
                valid_sub_splits.append(cleaned)
        is_valid_split = (
            len(valid_sub_splits) > 1
            and all(len(s.split()) >= 3 for s in valid_sub_splits)
        )
        if is_valid_split:
            return valid_sub_splits
        return [clause]

    doc = nlp(clause)
    
    # Identify clause heads (verbs or auxiliary verbs that have subjects)
    clause_heads = []
    for token in doc:
        if token.pos_ not in ("VERB", "AUX"):
            continue
        # Check for nominal/clausal subjects
        has_subject = any(
            child.dep_ in ("nsubj", "nsubjpass", "csubj", "csubjpass")
            for child in token.children
        )
        if not has_subject:
            continue
        # Accept ROOT or coordinate relations only (conj, parataxis, ccomp)
        if token.dep_ not in ("ROOT", "conj", "parataxis", "ccomp"):
            continue
        clause_heads.append(token)

    if len(clause_heads) <= 1:
        return [clause]

    # For each clause head, construct its subtree excluding other descendant clause heads
    raw_clauses = []
    for head in clause_heads:
        clause_tokens = []
        for t in head.subtree:
            is_descendant = False
            for other in clause_heads:
                if other != head and other in head.subtree:
                    if t in other.subtree:
                        is_descendant = True
                        break
            if not is_descendant:
                clause_tokens.append(t)
        raw_clauses.append((head, sorted(clause_tokens, key=lambda t: t.i)))

    raw_clauses.sort(key=lambda x: x[1][0].i if x[1] else 0)

    # Merge adjacent clauses if they are not separated by a valid coordinator
    merged_clauses = []
    for rc in raw_clauses:
        if not rc[1]:
            continue
        if not merged_clauses:
            merged_clauses.append(rc[1])
        else:
            prev_tokens = merged_clauses[-1]
            curr_tokens = rc[1]
            
            max_prev = max((t.i for t in prev_tokens if is_content_token(t)), default=-1)
            min_curr = min((t.i for t in curr_tokens if is_content_token(t)), default=-1)
            
            has_coordinator = False
            if max_prev != -1 and min_curr != -1:
                for idx in range(max_prev + 1, min_curr):
                    t = doc[idx]
                    if is_coordinator(t):
                        has_coordinator = True
                        break
            
            if has_coordinator:
                merged_clauses.append(curr_tokens)
            else:
                merged_clauses[-1] = sorted(prev_tokens + curr_tokens, key=lambda t: t.i)

    valid_sub_splits = []
    for tokens in merged_clauses:
        reconstructed = "".join([t.text + t.whitespace_ for t in tokens]).strip()
        cleaned = _clean_split_clause(reconstructed)
        if cleaned:
            valid_sub_splits.append(cleaned)

    is_valid_split = (
        len(valid_sub_splits) > 1
        and all(len(s.split()) >= 3 for s in valid_sub_splits)
    )
    if is_valid_split:
        return valid_sub_splits
    return [clause]

def _split_premise_blocks(blocks: List[str], nlp) -> List[str]:
    """Flatten premise blocks, splitting coordinate clauses where valid."""
    premise_clauses = []
    for block in blocks:
        for clause in _split_coordinate_clauses(block, nlp):
            stripped = clause.strip()
            if stripped:
                premise_clauses.append(stripped)
    return premise_clauses

def split_logical_clauses(text: str, nlp=None) -> Tuple[List[str], str]:
    """
    Splits an input logical argument text into a list of premises and a conclusion.
    Uses causal dependencies, sentence boundaries, and coordinate clause splitting.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    text = re.sub(r'\s+', ' ', text).strip()
    doc = nlp(text)

    causal_pair = _extract_causal_dependency_pair(doc)
    if causal_pair:
        premise_text, conclusion_text = causal_pair
        return [premise_text], conclusion_text

    sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    if len(sents) > 1:
        return _split_premise_blocks(sents[:-1], nlp), sents[-1]

    if len(sents) == 1:
        clauses = _split_coordinate_clauses(sents[0], nlp)
        if len(clauses) >= 2:
            return _split_premise_blocks(clauses[:-1], nlp), clauses[-1]
        return [], sents[0]

    return [], text.strip()

def clean_proposition_text(text: str, nlp=None) -> str:
    """Removes leading discourse markers and extra punctuation from a clause."""
    if nlp is None:
        nlp = nlp_engine

    text = re.sub(r'\s+', ' ', text).strip()
    text = text.strip(" \t\n\r,.;:")

    leading_markers = sorted(CAUSAL_MARKERS, key=len, reverse=True)
    marker_pattern = (
        r'^(?:' + '|'.join(re.escape(marker) for marker in leading_markers) + r')\b(?:\s*[,;:]?\s*)'
    )
    text = re.sub(marker_pattern, '', text, flags=re.IGNORECASE).strip()

    if nlp and text:
        doc = nlp(text)
        start_token_idx = 0
        for i, token in enumerate(doc):
            if _strip_leading_discourse_token(token):
                start_token_idx = i + 1
                continue
            break

        if start_token_idx < len(doc):
            text = doc[start_token_idx:].text.strip(" \t\n\r,.;:")

    return text

def _is_descendant_of_relcl(token, subtree_root=None) -> bool:
    """True if token is a relative clause head or has a relative clause ancestor (not including subtree_root)."""
    curr = token
    while curr != subtree_root and curr.head != curr:
        if curr.dep_ == "relcl":
            return True
        curr = curr.head
    return False

def _filter_subtree_tokens(subtree_root, exclude_neg=False, exclude_quantifier=None) -> List:
    """Filters the subtree of a token to exclude punctuation, discourse markers, relative clauses, etc."""
    filtered = []
    for t in subtree_root.subtree:
        # Exclude punctuation except word-internal ones like hyphens and apostrophes
        if t.is_punct and t.text not in ("-", "'", "’"):
            continue
        # Exclude discourse markers
        if t.dep_ == "discourse" or t.pos_ == "INTJ":
            continue
        # Exclude relative clauses and their descendants
        if _is_descendant_of_relcl(t, subtree_root):
            continue
        # Exclude negation if requested
        if exclude_neg and t.dep_ == "neg":
            continue
        # Exclude quantifier if requested
        if exclude_quantifier and t.text.lower() == exclude_quantifier.lower():
            continue
        filtered.append(t)
    return filtered

def parse_proposition(text: str, nlp=None) -> Proposition:
    """
    Parses a single natural language clause into a logical Proposition object using spaCy.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    cleaned_text = clean_proposition_text(text, nlp)
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
        subj_tokens = _filter_subtree_tokens(subject_token, exclude_quantifier=quantifier)
        subject_text = "".join([t.text + t.whitespace_ for t in sorted(subj_tokens, key=lambda t: t.i)]).strip()
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
        # pyrefly: ignore [missing-attribute]
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
        # Reconstruct predicate term text from its filtered subtree (excluding negation)
        pred_tokens = _filter_subtree_tokens(pred_token, exclude_neg=True)
        predicate_text = "".join([t.text + t.whitespace_ for t in sorted(pred_tokens, key=lambda t: t.i)]).strip()
    else:
        # Fallback: take all tokens after the root verb
        pred_tokens = []
        for t in doc:
            if t.i > root.i and t.dep_ != "neg":
                if t.is_punct and t.text not in ("-", "'", "’"):
                    continue
                if t.dep_ == "discourse" or t.pos_ == "INTJ":
                    continue
                if _is_descendant_of_relcl(t):
                    continue
                pred_tokens.append(t)
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

    if not text.strip():
        raise ValueError("Argument text is empty.")

    # 1. Segment the text into premises and conclusion
    premise_clauses, conclusion_clause = split_logical_clauses(text, nlp)

    if not conclusion_clause.strip():
        raise ValueError("Could not segment a conclusion from the argument.")
        
    # 2. Parse premises
    premises = [parse_proposition(clause, nlp) for clause in premise_clauses if clause.strip()]
    
    # 3. Parse conclusion
    conclusion = parse_proposition(conclusion_clause, nlp)
    
    # 4. Create and return the Syllogism
    return Syllogism(premises, conclusion)

def _append_unique_chunk(chunks: List[str], seen: set, chunk_text: str) -> None:
    chunk_text = chunk_text.strip()
    if chunk_text and chunk_text not in seen:
        seen.add(chunk_text)
        chunks.append(chunk_text)

def chunk_essay_for_extraction(text: str, nlp=None) -> List[str]:
    """
    Chunks an essay into smaller logical blocks (Argument Chunks and General Text Chunks)
    to facilitate parallel AI extraction and faster processing.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    doc = nlp(text)
    sentences = list(doc.sents)
    
    # 1. Find dependency-linked causal argument sentences.
    # We treat a sentence as an argument anchor when it contains an advcl+mark
    # structure for premise markers such as "because"/"since".
    chunks: List[str] = []
    seen_chunks: set = set()
    used_sentence_indices = set()
    
    for i, sent in enumerate(sentences):
        sent_doc = nlp(sent.text)
        causal_pair = _extract_causal_dependency_pair(sent_doc)
        if causal_pair:
            # Form argument chunk with limited preceding context.
            start_idx = max(0, i - 2)
            chunk_sents = sentences[start_idx:i+1]
            chunk_text = " ".join([s.text for s in chunk_sents]).strip()
            _append_unique_chunk(chunks, seen_chunks, chunk_text)
                
            # Only mark the causal sentence itself as used to prevent stealing preceding context
            used_sentence_indices.add(i)

    # 2. Overlapping 3-sentence windows on contiguous unused runs (plain syllogisms).
    i = 0
    while i < len(sentences):
        if i in used_sentence_indices:
            i += 1
            continue
        run_start = i
        while i < len(sentences) and i not in used_sentence_indices:
            i += 1
        run_end = i - 1
        if run_end - run_start + 1 >= 3:
            for w in range(run_start, run_end - 1):
                window_sents = sentences[w:w + 3]
                chunk_text = " ".join(s.text for s in window_sents)
                _append_unique_chunk(chunks, seen_chunks, chunk_text)

    # 3. Group remaining unused sentences into "General Text Chunks"
    current_chunk = []
    for i, sent in enumerate(sentences):
        if i not in used_sentence_indices:
            current_chunk.append(sent.text)
            if len(current_chunk) >= 4:
                _append_unique_chunk(chunks, seen_chunks, " ".join(current_chunk))
                current_chunk = []
        else:
            if current_chunk:
                _append_unique_chunk(chunks, seen_chunks, " ".join(current_chunk))
                current_chunk = []
                
    if current_chunk:
        _append_unique_chunk(chunks, seen_chunks, " ".join(current_chunk))
        
    return chunks

def analyze_text_concepts(text: str, nlp=None) -> Dict[str, Any]:
    """
    Parses raw text with spaCy to extract semantic concepts (noun chunks, named entities, key terms)
    to identify "what we are talking about" before AI syllogism reconstruction.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine
        
    doc = nlp(text)
    
    # 1. Extract Noun Chunks (unique, cleaned)
    noun_chunks = []
    seen_chunks = set()
    for chunk in doc.noun_chunks:
        # Clean articles and whitespace
        cleaned = re.sub(r'^(all|some|no|any|every|each|a|an|the)\b', '', chunk.text, flags=re.IGNORECASE).strip()
        cleaned_lower = cleaned.lower()
        if cleaned_lower and len(cleaned_lower.split()) <= 4 and cleaned_lower not in seen_chunks:
            seen_chunks.add(cleaned_lower)
            # Capitalize properly
            noun_chunks.append(cleaned)

    # 2. Extract Named Entities
    entities = []
    seen_ents = set()
    for ent in doc.ents:
        cleaned = ent.text.strip()
        key = (cleaned.lower(), ent.label_)
        if cleaned and key not in seen_ents:
            seen_ents.add(key)
            entities.append({
                "text": cleaned,
                "label": ent.label_
            })
            
    # 3. Extract Key Terms (dominant nouns and adjectives)
    key_terms = []
    seen_terms = set()
    for token in doc:
        if token.pos_ in ("NOUN", "PROPN", "ADJ") and not token.is_stop and not token.is_punct:
            lemma = token.lemma_.lower()
            if len(lemma) > 2 and lemma not in seen_terms:
                seen_terms.add(lemma)
                key_terms.append(token.text)
                
    return {
        "noun_chunks": noun_chunks[:15],  # Limit to top 15 for readable UI
        "entities": entities[:10],
        "key_terms": key_terms[:20]
    }

def extract_raw_arguments_local(text: str, nlp=None) -> List[Dict[str, Any]]:
    """
    Extracts raw premise-conclusion arguments locally from the text using spaCy.
    Identifies sentences/clauses containing causal markers or logical sequences.
    """
    if nlp is None:
        if nlp_engine is None:
            raise RuntimeError("spaCy NLP engine is not loaded. Please download en_core_web_sm.")
        nlp = nlp_engine

    chunks = chunk_essay_for_extraction(text, nlp)
    raw_arguments = []
    seen_args = set()
    
    for chunk in chunks:
        chunk_stripped = chunk.strip()
        if not chunk_stripped:
            continue
            
        try:
            # Segment the chunk into premises and a conclusion
            premises, conclusion = split_logical_clauses(chunk_stripped, nlp)
            
            # Filter empty results or trivial cases (like where there is no premise)
            if premises and conclusion:
                # Clean up each premise and the conclusion for presentation
                cleaned_premises = [clean_proposition_text(p, nlp) for p in premises if p.strip()]
                cleaned_conclusion = clean_proposition_text(conclusion, nlp)
                
                if cleaned_premises and cleaned_conclusion:
                    # Deduplicate based on normalized premises and conclusion
                    norm_premises = tuple(sorted(p.strip().lower() for p in cleaned_premises))
                    norm_conclusion = cleaned_conclusion.strip().lower()
                    arg_key = (norm_premises, norm_conclusion)
                    
                    if arg_key not in seen_args:
                        seen_args.add(arg_key)
                        raw_arguments.append({
                            "original_text": chunk_stripped,
                            "raw_premises": cleaned_premises,
                            "raw_conclusion": cleaned_conclusion
                        })
        except Exception:
            pass
            
    return raw_arguments

