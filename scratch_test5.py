import spacy

nlp = spacy.load("en_core_web_sm")

def is_coordinator(t) -> bool:
    return t.text in (",", ";") or t.pos_ == "CCONJ" or t.text.lower() in ("and", "but", "or", "yet")

def is_content_token(t) -> bool:
    return not is_coordinator(t) and not t.is_punct

def test_split(text):
    print("=" * 60)
    print(f"TEXT: {text}")
    doc = nlp(text)
    
    clause_heads = []
    for token in doc:
        if token.pos_ not in ("VERB", "AUX"):
            continue
        has_subject = any(
            child.dep_ in ("nsubj", "nsubjpass", "csubj", "csubjpass")
            for child in token.children
        )
        if not has_subject:
            continue
        if token.dep_ not in ("ROOT", "conj", "parataxis", "ccomp"):
            continue
        clause_heads.append(token)
        
    print(f"Heads: {[t.text for t in clause_heads]}")
    
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
                
    results = []
    for tokens in merged_clauses:
        reconstructed = "".join([t.text + t.whitespace_ for t in tokens]).strip()
        results.append(reconstructed)
    print(f"SPLIT PARTS: {results}")

test_split("I was tired so I went home early.")
test_split("Socrates is a man, and all men are mortal.")
test_split("Socrates is a man, all men are mortal, thus Socrates is mortal.")
test_split("I like apples, oranges, and bananas.")
