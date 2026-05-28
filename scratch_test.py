import spacy

nlp = spacy.load("en_core_web_sm")

def _strip_leading_discourse_token(token) -> bool:
    if token.is_punct:
        return True
    return token.pos_ in ("ADV", "SCONJ") and token.dep_ in ("advmod", "mark")

text = "thus Socrates is mortal"
doc = nlp(text)
for token in doc:
    print(token.text, token.pos_, token.dep_, _strip_leading_discourse_token(token))
    
print("---")
text2 = "therefore all men are mortal"
doc2 = nlp(text2)
for token in doc2:
    print(token.text, token.pos_, token.dep_, _strip_leading_discourse_token(token))
