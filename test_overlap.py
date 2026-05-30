import spacy

nlp_engine = spacy.load("en_core_web_sm")

syllogisms = [
    ("Socrates", "mortal", "man"),
    ("Socrates", "mortal", "human"), # Should this be a duplicate? Yes, probably.
    ("Bob", "happy", "man"),
    ("He", "happy", "is"),
    ("All cats", "felines", "animals"),
    ("A dog", "feline", "creature")
]

seen_argument_lemmas = []

for minor, major, middle in syllogisms:
    combined_terms = f"{minor} {major} {middle}"
    doc_lemmas = nlp_engine(combined_terms)
    current_lemmas = set(t.lemma_.lower() for t in doc_lemmas if not t.is_punct and not t.is_stop)
    
    print(f"Testing: {minor}, {major}, {middle}")
    print(f"Lemmas: {current_lemmas}")
    
    is_duplicate = False
    for seen_lemmas in seen_argument_lemmas:
        if not current_lemmas or not seen_lemmas:
            continue
        intersection = current_lemmas.intersection(seen_lemmas)
        union = current_lemmas.union(seen_lemmas)
        jaccard = len(intersection) / len(union) if union else 0
        
        min_len = min(len(current_lemmas), len(seen_lemmas))
        overlap = len(intersection) / min_len if min_len > 0 else 0
        
        print(f"  vs {seen_lemmas}: intersection={intersection}, jaccard={jaccard:.2f}, overlap={overlap:.2f}")
        if jaccard >= 0.50:
            is_duplicate = True
            print("  -> DUPLICATE (Jaccard)!")
            break
            
    if not is_duplicate:
        seen_argument_lemmas.append(current_lemmas)
