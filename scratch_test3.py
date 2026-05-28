import spacy

nlp = spacy.load("en_core_web_sm")

texts = [
    "Socrates is a man, all men are mortal, thus Socrates is mortal.",
    "I like apples, oranges, and bananas, and I eat them every day."
]

for text in texts:
    doc = nlp(text)
    print(text)
    for token in doc:
        if token.dep_ == "conj":
            print("  ", token.text, token.pos_, token.dep_, "head:", token.head.text)
    print("---")
