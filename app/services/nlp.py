from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def analyze_japanese_text(text: str):
    morphemes = tokenizer_obj.tokenize(text, mode)
    extracted_data = []
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for m in morphemes:
        pos = m.part_of_speech()
        major_pos = pos[0]

        if major_pos in targets:
            lemma = m.dictionary_form()
            if lemma == "" or lemma.isspace():
                continue

            definitions = []
            ent_seq = None  # <--- Initialisation

            try:
                result = jmd.lookup(lemma)
                
                # 1. Recherche standard
                if result.entries:
                    first_entry = result.entries[0] # On cible l'entrée principale
                    ent_seq = first_entry.ent_seq   # <--- CAPTURE DE L'ID UNIQUE
                    
                    for sense in first_entry.senses:
                        definitions.extend([g.text for g in sense.gloss])
                
                # 2. Noms Propres (généralement pas de ent_seq standard, mais des id différents)
                elif result.names:
                     for name_entity in result.names:
                        # Note: les names ont aussi des IDs mais gérés séparément dans JMDict
                        # Pour l'instant on laisse ent_seq à None ou on gère un cas spécifique
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
                "ent_seq": ent_seq, # <--- On le passe au schéma
                "definitions": definitions[:3]
            })

    return extracted_data