import re
import io
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

# --- NETTOYAGE AOZORA ---

def clean_html_text(html_content: str) -> str:
    """Retire les balises ruby (<rt>) pour ne garder que le texte brut."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # On supprime les balises de prononciation (<rt>) et les parenthèses (<rp>)
    for tag in soup(['rt', 'rp']):
        tag.decompose()
        
    # On récupère le texte nettoyé
    text = soup.get_text()
    
    # Nettoyage supplémentaire pour les notes de bas de page Aozora textuelles
    # ex: [＃ここから...]
    text = re.sub(r'［＃.*?］', '', text)
    return text

def clean_raw_text(text: str) -> str:
    """Nettoie le format texte Aozora Bunko (ex: 漢字《かんじ》)."""
    # Retire les lectures entre 《 》
    text = re.sub(r'《.*?》', '', text)
    # Retire les marqueurs de début de ruby ｜
    text = text.replace('｜', '')
    # Retire les notes de l'éditeur ［＃...］
    text = re.sub(r'［＃.*?］', '', text)
    return text

def extract_text_from_epub(file_bytes: bytes) -> str:
    """Extrait le texte de tous les chapitres d'un EPUB."""
    # On écrit les bytes dans un fichier temporaire en mémoire car ebooklib attend un fichier
    # Note: ebooklib est un peu capricieux avec les bytes directs, on utilise une astuce
    import tempfile
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    book = epub.read_epub(tmp_path)
    full_text = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Chaque chapitre est du HTML (XHTML)
            content = item.get_content().decode('utf-8')
            full_text.append(clean_html_text(content))

    return "\n".join(full_text)

# --- ANALYSE ---

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
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞", "形状詞", "代名詞", "固有名詞"] 

    for line in lines:
        if not line.strip(): 
            sentences_output.append([{"text": "", "is_word": False}])
            continue

        morphemes = tokenizer_obj.tokenize(line, mode)
        line_tokens = []

        for m in morphemes:
            token_text = m.surface()
            pos_info = m.part_of_speech()
            major_pos = pos_info[0]
            
            token_data = {"text": token_text, "is_word": False}

            if major_pos in targets:
                # Stratégie de recherche (Lemme -> Normalisé -> Surface)
                forms_to_try = []
                lemma = m.dictionary_form()
                if lemma: forms_to_try.append(lemma)
                normalized = m.normalized_form()
                if normalized and normalized not in forms_to_try: forms_to_try.append(normalized)
                if token_text and token_text not in forms_to_try: forms_to_try.append(token_text)

                found_entry = None
                for form in forms_to_try:
                    if not form or form.isspace() or form == '%': continue
                    try:
                        res = jmd.lookup(form)
                        if res.entries:
                            found_entry = res.entries[0]
                            break
                    except: continue
                
                if found_entry:
                    definitions = []
                    ent_seq = int(found_entry.idseq)
                    jlpt = estimate_jlpt(found_entry)
                    for s in found_entry.senses:
                        definitions.extend([g.text for g in s.gloss])
                    
                    token_data.update({
                        "is_word": True,
                        "lemma": forms_to_try[0],
                        "reading": m.reading_form(),
                        "pos": major_pos,
                        "ent_seq": ent_seq,
                        "definitions": definitions[:4],
                        "jlpt": jlpt
                    })
            
            line_tokens.append(token_data)
        
        sentences_output.append(line_tokens)

    return {"sentences": sentences_output}