import re
import io
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import tempfile

# Initialisation
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

# --- NETTOYAGE ---
def clean_html_text(html_content: str) -> str:
    """Retire les balises ruby (<rt>) pour ne garder que le texte brut."""
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup(['rt', 'rp']): # Retire prononciations
        tag.decompose()
    text = soup.get_text()
    text = re.sub(r'［＃.*?］', '', text) # Retire notes éditeur Aozora
    return text

def clean_raw_text(text: str) -> str:
    """Nettoie le format texte Aozora Bunko (ex: 漢字《かんじ》)."""
    text = re.sub(r'《.*?》', '', text) # Retire furigana
    text = text.replace('｜', '') # Retire séparateurs
    text = re.sub(r'［＃.*?］', '', text)
    return text

def extract_text_from_epub(file_bytes: bytes) -> str:
    """Extrait le texte des chapitres d'un EPUB."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    
    try:
        book = epub.read_epub(tmp_path)
        full_text = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8')
                full_text.append(clean_html_text(content))
        return "\n".join(full_text)
    except:
        return ""

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
            pos = m.part_of_speech()[0]
            token_data = {"text": token_text, "is_word": False}

            if pos in targets:
                # Stratégie de recherche: Lemme -> Normalisé -> Surface (pour trouver "芳烈")
                forms = []
                if m.dictionary_form(): forms.append(m.dictionary_form())
                if m.normalized_form() and m.normalized_form() not in forms: forms.append(m.normalized_form())
                if token_text not in forms: forms.append(token_text)

                found = None
                for f in forms:
                    if not f or f.isspace() or f == '%': continue
                    try:
                        res = jmd.lookup(f)
                        if res.entries:
                            found = res.entries[0]
                            break
                    except: continue
                
                if found:
                    defs = []
                    for s in found.senses: defs.extend([g.text for g in s.gloss])
                    token_data.update({
                        "is_word": True,
                        "lemma": forms[0],
                        "reading": m.reading_form(),
                        "pos": pos,
                        "ent_seq": int(found.idseq),
                        "definitions": defs[:4],
                        "jlpt": estimate_jlpt(found)
                    })
            
            line_tokens.append(token_data)
        sentences_output.append(line_tokens)

    return {"sentences": sentences_output}