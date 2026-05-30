import spacy

nlp_engine = spacy.load("en_core_web_sm")

syllogisms = [
    ("Socrates", "mortal", "man"),
    ("Socrates", "mortal", "is"), # 2 lemmas: socrates, mortal
    ("He", "mortal", "is"), # 1 lemma: mortal
    ("Bob", "happy", "man"),
    ("He", "happy", "is"), # 1 lemma: happy
    ("Bob", "happy", "guy"), # 2 lemmas: bob, happy (guy -> guy, man -> man, jaccard?)
]

seen_argument_lemmas = []

for minor, major, middle in syllogisms:
    combined_terms = f"{minor} {major} {middle}"
    doc_lemmas = nlp_engine(combined_terms)
    current_lemmas = set(t.lemma_.lower() for t in doc_lemmas if not t.is_punct and not t.is_stop)
    
    print(f"\nTesting: {minor}, {major}, {middle}")
    print(f"Lemmas: {current_lemmas}")
    
    is_duplicate = False
    for seen_lemmas in seen_argument_lemmas:
        if not current_lemmas or not seen_lemmas:
            continue
        intersection = current_lemmas.intersection(seen_lemmas)
        intersection_len = len(intersection)
        min_len = min(len(current_lemmas), len(seen_lemmas))
        union_len = len(current_lemmas.union(seen_lemmas))
        
        jaccard = intersection_len / union_len if union_len > 0 else 0
        overlap = intersection_len / min_len if min_len > 0 else 0
        
        print(f"  vs {seen_lemmas}: intersection={intersection_len}, jaccard={jaccard:.2f}, overlap={overlap:.2f}")
        
        # New proposed logic
        if (intersection_len >= 2 and overlap >= 0.80) or jaccard >= 0.50:
            is_duplicate = True
            print("  -> DUPLICATE!")
            break
            
    if not is_duplicate:
        seen_argument_lemmas.append(current_lemmas)
