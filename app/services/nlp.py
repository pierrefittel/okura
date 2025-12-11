import re
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def analyze_japanese_text(text: str):
    # 1. Découpage en phrases (grossier mais efficace pour le contexte)
    # On coupe après 。！？ ou fin de ligne
    sentences = re.split(r'(?<=[。！？\n])', text)
    
    extracted_data = []
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for sentence in sentences:
        if not sentence.strip():
            continue
            
        morphemes = tokenizer_obj.tokenize(sentence, mode)

        for m in morphemes:
            pos = m.part_of_speech()
            major_pos = pos[0]

            if major_pos in targets:
                lemma = m.dictionary_form()
                
                if not lemma or lemma.isspace() or lemma == '%':
                    continue

                definitions = []
                ent_seq = None

                try:
                    result = jmd.lookup(lemma)
                    if result.entries:
                        first_entry = result.entries[0]
                        ent_seq = int(first_entry.idseq) 
                        for sense in first_entry.senses:
                            definitions.extend([g.text for g in sense.gloss])
                    elif result.names:
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
                    "ent_seq": ent_seq,
                    "definitions": definitions[:3],
                    "context": sentence.strip() # <-- On attache la phrase entière ici
                })

    return extracted_data