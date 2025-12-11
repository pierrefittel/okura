import re
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def estimate_jlpt(entry):
    """Essaie de deviner le niveau JLPT basé sur les tags ou la fréquence."""
    # 1. Recherche explicite (si votre DB jamdict contient les tags legacy)
    # Les tags ressemblent parfois à 'jlpt-n5' dans misc
    for sense in entry.senses:
        for m in sense.misc:
            match = re.search(r'jlpt-n(\d)', str(m))
            if match:
                return int(match.group(1))
    
    # 2. Estimation par fréquence (Priorité)
    # news1/ichi1 ~ N5-N3 (Mots très courants)
    # news2/ichi2 ~ N2 (Mots courants)
    # Sans tag ~ N1+ (Mots rares)
    is_common = False
    for k_ele in entry.kanji_forms:
        if any(p in ['news1', 'ichi1', 'spec1', 'gai1'] for p in k_ele.pri):
            is_common = True
            break
    if not is_common:
        for r_ele in entry.kana_forms:
            if any(p in ['news1', 'ichi1', 'spec1', 'gai1'] for p in r_ele.pri):
                is_common = True
                break
                
    # Si c'est un mot très courant ("news1"), on peut le considérer "facile" (approx N4/N5 pour le filtrage)
    if is_common:
        return 4 # On retourne arbitrairement 4 pour les mots courants
        
    return 1 # Par défaut, on considère les mots sans tag comme "Difficiles" (N1)

def analyze_japanese_text(text: str):
    sentences = re.split(r'(?<=[。！？\n])', text)
    extracted_data = []
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for sentence in sentences:
        if not sentence.strip(): continue
        morphemes = tokenizer_obj.tokenize(sentence, mode)

        for m in morphemes:
            pos = m.part_of_speech()
            major_pos = pos[0]

            if major_pos in targets:
                lemma = m.dictionary_form()
                if not lemma or lemma.isspace() or lemma == '%': continue

                definitions = []
                ent_seq = None
                jlpt_level = None # <--

                try:
                    result = jmd.lookup(lemma)
                    if result.entries:
                        first_entry = result.entries[0]
                        ent_seq = int(first_entry.idseq)
                        
                        # --- Estimation du niveau ---
                        jlpt_level = estimate_jlpt(first_entry)
                        
                        for sense in first_entry.senses:
                            definitions.extend([g.text for g in sense.gloss])
                            
                    elif result.names:
                         for name_entity in result.names:
                            if name_entity.senses:
                                 for sense in name_entity.senses:
                                     definitions.extend([g.text for g in sense.gloss])

                except Exception as e:
                    print(f"Error {lemma}: {e}")
                
                extracted_data.append({
                    "original": m.surface(),
                    "terme": lemma,
                    "lecture": m.reading_form(),
                    "pos": major_pos,
                    "ent_seq": ent_seq,
                    "definitions": definitions[:3],
                    "context": sentence.strip(),
                    "jlpt": jlpt_level # <-- On passe le niveau au front
                })

    return extracted_data