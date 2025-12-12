import re
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def estimate_jlpt(entry):
    for sense in entry.senses:
        for m in sense.misc:
            match = re.search(r'jlpt-n(\d)', str(m))
            if match: return int(match.group(1))
    is_common = False
    for k_ele in entry.kanji_forms:
        if any(p in ['news1', 'ichi1', 'spec1', 'gai1'] for p in k_ele.pri): is_common = True
    if not is_common:
        for r_ele in entry.kana_forms:
            if any(p in ['news1', 'ichi1', 'spec1', 'gai1'] for p in r_ele.pri): is_common = True
    return 4 if is_common else 1

def lookup_word(word_to_find):
    """Cherche un mot avec plusieurs stratégies."""
    # 1. Recherche exacte
    result = jmd.lookup(word_to_find)
    if result.entries: return result.entries[0]
    
    # 2. Si c'est un verbe/adj, parfois Sudachi donne la forme neutre, mais JMDict préfère une variante.
    # On pourrait ajouter ici des heuristiques si besoin.
    return None

def analyze_japanese_text(text: str):
    lines = text.splitlines()
    sentences_output = []
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for line in lines:
        if not line: 
            sentences_output.append([{"text": "", "is_word": False}])
            continue

        morphemes = tokenizer_obj.tokenize(line, mode)
        line_tokens = []

        for m in morphemes:
            token_text = m.surface()
            pos = m.part_of_speech()
            major_pos = pos[0]
            
            token_data = {"text": token_text, "is_word": False}

            if major_pos in targets:
                lemma = m.dictionary_form()
                
                # --- AMÉLIORATION DE LA RECHERCHE ---
                # On essaie le lemme (forme dico), sinon la forme de surface (ce qui est écrit)
                entry = None
                try:
                    # Stratégie 1 : Lemme
                    if lemma and not lemma.isspace():
                         res = jmd.lookup(lemma)
                         if res.entries: entry = res.entries[0]

                    # Stratégie 2 : Surface (pour 芳烈 par exemple si le lemme est faux)
                    if not entry:
                        res = jmd.lookup(token_text)
                        if res.entries: entry = res.entries[0]

                    # Extraction des données si trouvé
                    if entry:
                        definitions = []
                        ent_seq = int(entry.idseq)
                        jlpt = estimate_jlpt(entry)
                        for s in entry.senses:
                            definitions.extend([g.text for g in s.gloss])
                        
                        token_data.update({
                            "is_word": True,
                            "lemma": lemma, # On garde le lemme pour la base, même si on a cherché la surface
                            "reading": m.reading_form(),
                            "pos": major_pos,
                            "ent_seq": ent_seq,
                            "definitions": definitions[:4],
                            "jlpt": jlpt
                        })
                except:
                    pass
            
            line_tokens.append(token_data)
        sentences_output.append(line_tokens)

    return {"sentences": sentences_output}