import spacy
nlp = spacy.load("en_core_web_sm")
doc = nlp("Socrates is a man, all men are mortal, thus Socrates is mortal.")
for token in doc:
    print(token.text, token.pos_, token.dep_, token.head.text)
