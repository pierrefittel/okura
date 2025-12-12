import re
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation
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

def analyze_japanese_text(text: str):
    lines = text.splitlines()
    sentences_output = []
    
    # On élargit un peu les cibles pour ne rien rater
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞", "形状詞"] 

    for line in lines:
        if not line: 
            sentences_output.append([{"text": "", "is_word": False}])
            continue

        morphemes = tokenizer_obj.tokenize(line, mode)
        line_tokens = []

        for m in morphemes:
            token_text = m.surface()
            pos_info = m.part_of_speech()
            major_pos = pos_info[0]
            
            token_data = {
                "text": token_text,
                "is_word": False
            }

            if major_pos in targets:
                # 1. On récupère toutes les formes possibles
                forms_to_try = []
                
                # La forme dictionnaire (ex: 食べる pour 食べます)
                lemma = m.dictionary_form()
                if lemma: forms_to_try.append(lemma)
                
                # La forme normalisée (ex: utile pour les variantes graphiques)
                normalized = m.normalized_form()
                if normalized and normalized not in forms_to_try: forms_to_try.append(normalized)
                
                # La forme de surface (ex: 芳烈 tel qu'écrit)
                if token_text and token_text not in forms_to_try: forms_to_try.append(token_text)

                found_entry = None
                
                # 2. On cherche dans Jamdict par ordre de priorité
                for form in forms_to_try:
                    if not form or form.isspace() or form == '%': continue
                    try:
                        # Recherche exacte d'abord
                        res = jmd.lookup(form)
                        if res.entries:
                            found_entry = res.entries[0]
                            break # Trouvé !
                    except:
                        continue
                
                # 3. Si on a trouvé une entrée, on hydrate le token
                if found_entry:
                    definitions = []
                    ent_seq = int(found_entry.idseq)
                    jlpt = estimate_jlpt(found_entry)
                    for s in found_entry.senses:
                        definitions.extend([g.text for g in s.gloss])
                    
                    token_data.update({
                        "is_word": True,
                        "lemma": forms_to_try[0], # On garde la forme la plus "propre" (lemme) pour l'affichage titre
                        "reading": m.reading_form(),
                        "pos": major_pos,
                        "ent_seq": ent_seq,
                        "definitions": definitions[:4],
                        "jlpt": jlpt
                    })
            
            line_tokens.append(token_data)
        
        sentences_output.append(line_tokens)

    return {"sentences": sentences_output}