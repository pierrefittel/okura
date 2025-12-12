import re
import os
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import tempfile

# --- MOTEUR JAPONAIS ---
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

# --- MOTEUR CHINOIS ---
import jieba
from pypinyin import pinyin, Style

# Chargeur simple pour CC-CEDICT (Dictionnaire Chinois)
# Si le fichier 'cedict_ts.u8' est présent à la racine, il sera chargé.
CEDICT_PATH = "cedict_ts.u8"
cedict_data = {}

def load_cedict():
    if not os.path.exists(CEDICT_PATH):
        return
    print("Chargement CC-CEDICT...")
    with open(CEDICT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or not line.strip(): continue
            # Format: Traditional Simplified [pin1 yin1] /meaning/meaning/.../
            parts = line.split(' ', 2)
            if len(parts) < 3: continue
            traditional = parts[0]
            simplified = parts[1]
            rest = parts[2]
            
            pinyin_match = re.search(r'\[(.*?)\]', rest)
            if not pinyin_match: continue
            pinyin_str = pinyin_match.group(1)
            
            defs_raw = rest.split('/', 1)[1].strip('/')
            definitions = defs_raw.split('/')
            
            # On indexe par Simplifié (le plus courant) et Traditionnel
            entry = {"pinyin": pinyin_str, "defs": definitions}
            if simplified not in cedict_data: cedict_data[simplified] = []
            cedict_data[simplified].append(entry)
            if traditional not in cedict_data: cedict_data[traditional] = []
            cedict_data[traditional].append(entry)
    print("CC-CEDICT chargé.")

# Tentative de chargement au démarrage
try: load_cedict()
except: pass

# --- NETTOYAGE (Commun) ---
def clean_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup(['rt', 'rp', 'script', 'style']): tag.decompose()
    text = soup.get_text()
    text = re.sub(r'［＃.*?］', '', text)
    return text

def clean_raw_text(text: str) -> str:
    text = re.sub(r'《.*?》', '', text)
    text = text.replace('｜', '')
    text = re.sub(r'［＃.*?］', '', text)
    return text

def extract_text_from_epub(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        book = epub.read_epub(tmp_path)
        full_text = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full_text.append(clean_html_text(item.get_content().decode('utf-8')))
        return "\n".join(full_text)
    except: return ""

# --- ANALYSEUR DISPATCHER ---
def analyze_text(text: str, lang: str = "jp"):
    if lang == "cn":
        return analyze_chinese_text(text)
    else:
        return analyze_japanese_text(text)

# --- IMPLEMENTATION CHINOISE ---
def analyze_chinese_text(text: str):
    lines = text.splitlines()
    sentences_output = []
    
    for line in lines:
        if not line.strip():
            sentences_output.append([{"text": "", "is_word": False}])
            continue
            
        # Segmentation Jieba
        words = list(jieba.cut(line))
        line_tokens = []
        
        for word in words:
            # Ignorer ponctuation basique (très simplifié)
            is_word = len(word.strip()) > 0 and not re.match(r'[，。？！：；“”‘’（）\s]', word)
            
            token_data = {
                "text": word,
                "is_word": is_word
            }
            
            if is_word:
                # 1. Pinyin (Lecture)
                py_list = pinyin(word, style=Style.TONE)
                reading = " ".join([item[0] for item in py_list])
                
                # 2. Définition (CC-CEDICT)
                defs = []
                if word in cedict_data:
                    # On prend la première entrée
                    entry = cedict_data[word][0]
                    # Si le pinyin du dico est différent, on peut l'afficher aussi
                    defs = entry['defs'][:4]
                elif not cedict_data:
                    defs = ["(Dictionnaire cedict_ts.u8 manquant)"]
                
                token_data.update({
                    "lemma": word,
                    "reading": reading,
                    "pos": "Mot", # Jieba basic n'a pas de POS par défaut, on simplifie
                    "ent_seq": hash(word) % 100000000, # ID temporaire
                    "definitions": defs,
                    "jlpt": None # Pas de HSK implémenté pour l'instant
                })
                
            line_tokens.append(token_data)
        sentences_output.append(line_tokens)
        
    return {"sentences": sentences_output}

# --- IMPLEMENTATION JAPONAISE (Votre version stable V4) ---
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