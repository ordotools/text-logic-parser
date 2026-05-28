import spacy

nlp = spacy.load("en_core_web_sm")

texts = [
    "Because all mammals are warm-blooded, whales are warm-blooded.",
    "Since it is raining, the grass is wet.",
    "The grass is wet as it is raining.",
    "Given that A is B, C is D.",
    "I was tired so I went home early."
]

for text in texts:
    doc = nlp(text)
    print(text)
    for token in doc:
        if token.dep_ in ("mark", "advmod", "cc", "advcl"):
            print("  ", token.text, token.pos_, token.dep_, "head:", token.head.text, token.head.pos_, token.head.dep_)
    print("---")
