from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def analyze_japanese_text(text: str):
    morphemes = tokenizer_obj.tokenize(text, mode)
    extracted_data = []

    # On ajoute "助動詞" (Verbe auxiliaire) qui est souvent pertinent en classique
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for m in morphemes:
        pos = m.part_of_speech()
        major_pos = pos[0]

        if major_pos in targets:
            lemma = m.dictionary_form()
            
            if lemma == "" or lemma.isspace():
                continue

            definitions = []
            try:
                # 1. Recherche standard
                result = jmd.lookup(lemma)
                
                # Priorité aux mots communs (entries)
                if result.entries:
                    for sense in result.entries[0].senses:
                        definitions.extend([g.text for g in sense.gloss])
                
                # 2. Si vide, on regarde les Noms Propres (names)
                elif result.names:
                     # Les noms propres ont une structure différente (traductions dans 'gloss' parfois directes)
                     # Souvent: translation est un objet, on prend .text ou on convertit
                     for name_entity in result.names:
                        if name_entity.senses:
                             for sense in name_entity.senses:
                                 definitions.extend([g.text for g in sense.gloss])

            except Exception as e:
                print(f"Jamdict error for {lemma}: {e}")
            
            extracted_data.append({
                "original": m.surface(),
                "terme": lemma,
                "lecture": m.reading_form(),
                "pos": major_pos,
                "definitions": definitions[:3]
            })

    return extracted_data