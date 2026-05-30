import spacy

nlp = spacy.load("en_core_web_sm")

text1 = "First of all, we know that all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal."
text2 = "all men are mortal, and we also know that Socrates is a man. Consequently, Socrates is mortal."

doc1 = nlp(text1)
doc2 = nlp(text2)

print("Similarity:", doc1.similarity(doc2))

# Let's also try extracting lemmas and seeing Jaccard similarity
lemmas1 = set(t.lemma_.lower() for t in doc1 if not t.is_punct and not t.is_stop)
lemmas2 = set(t.lemma_.lower() for t in doc2 if not t.is_punct and not t.is_stop)

intersection = lemmas1.intersection(lemmas2)
union = lemmas1.union(lemmas2)
jaccard = len(intersection) / len(union) if union else 0

print("Jaccard similarity of non-stop lemmas:", jaccard)
