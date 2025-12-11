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
            
            # FILTRE DE SÉCURITÉ : On ignore les lemmes vides ou le joker '%' qui fait planter Jamdict
            if not lemma or lemma.isspace() or lemma == '%':
                continue

            definitions = []
            ent_seq = None

            try:
                # On utilise strict_lookup=True pour éviter que "hashi" ne renvoie des variantes trop éloignées,
                # mais le comportement par défaut est souvent suffisant.
                result = jmd.lookup(lemma)
                
                # 1. Recherche standard
                if result.entries:
                    first_entry = result.entries[0]
                    # --- CORRECTION ICI ---
                    # L'attribut dans l'objet Python est 'idseq', pas 'ent_seq'
                    ent_seq = int(first_entry.idseq) 
                    
                    for sense in first_entry.senses:
                        definitions.extend([g.text for g in sense.gloss])
                
                # 2. Noms Propres (names)
                elif result.names:
                     for name_entity in result.names:
                        # Les noms propres n'ont pas toujours de idseq standard dans cette librairie
                        # On récupère surtout les sens ici
                        if name_entity.senses:
                             for sense in name_entity.senses:
                                 definitions.extend([g.text for g in sense.gloss])

            except Exception as e:
                # On log l'erreur mais on ne bloque pas l'extraction des autres mots
                print(f"Jamdict error for {lemma}: {e}")
            
            extracted_data.append({
                "original": m.surface(),
                "terme": lemma,
                "lecture": m.reading_form(),
                "pos": major_pos,
                "ent_seq": ent_seq,
                "definitions": definitions[:3]
            })

    return extracted_data