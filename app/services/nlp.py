import re
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def estimate_jlpt(entry):
    # (Même logique que précédemment)
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
    # On découpe par lignes pour préserver les paragraphes
    lines = text.splitlines()
    sentences_output = []
    
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞"] 

    for line in lines:
        if not line: 
            # Conserver les sauts de ligne vides
            sentences_output.append([{"text": "", "is_word": False}])
            continue

        # Tokenization de la ligne
        morphemes = tokenizer_obj.tokenize(line, mode)
        line_tokens = []

        for m in morphemes:
            token_text = m.surface()
            pos = m.part_of_speech()
            major_pos = pos[0]
            
            # Objet de base
            token_data = {
                "text": token_text,
                "is_word": False
            }

            # Si c'est un mot intéressant, on l'enrichit
            if major_pos in targets:
                lemma = m.dictionary_form()
                
                # Petit nettoyage
                if lemma and not lemma.isspace() and lemma != '%':
                    definitions = []
                    ent_seq = None
                    jlpt = None

                    try:
                        result = jmd.lookup(lemma)
                        if result.entries:
                            entry = result.entries[0]
                            ent_seq = int(entry.idseq)
                            jlpt = estimate_jlpt(entry)
                            for s in entry.senses:
                                definitions.extend([g.text for g in s.gloss])
                        elif result.names:
                             # On traite les noms propres mais sans JLPT
                             for n in result.names:
                                if n.senses:
                                     for s in n.senses:
                                         definitions.extend([g.text for g in s.gloss])
                    except:
                        pass
                    
                    # Si on a trouvé quelque chose dans le dico
                    if definitions:
                        token_data.update({
                            "is_word": True,
                            "lemma": lemma,
                            "reading": m.reading_form(),
                            "pos": major_pos,
                            "ent_seq": ent_seq,
                            "definitions": definitions[:4], # Limite à 4 sens
                            "jlpt": jlpt
                        })
            
            line_tokens.append(token_data)
        
        sentences_output.append(line_tokens)

    return {"sentences": sentences_output}