import re
import os
import urllib.request
import zipfile
from sudachipy import tokenizer, dictionary
from jamdict import Jamdict
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
import tempfile
import jieba
from pypinyin import pinyin, Style

# --- MOTEUR JAPONAIS ---
print("Init NLP Japonais...")
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

# --- MOTEUR CHINOIS ---
CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"
CEDICT_FILE = "cedict_ts.u8"
cedict_data = {}

def load_cedict():
    """Charge ou télécharge le dictionnaire chinois."""
    if not os.path.exists(CEDICT_FILE):
        print("Téléchargement du dictionnaire Chinois (CC-CEDICT)...")
        try:
            # Ajout d'un User-Agent pour éviter le blocage par mdbg.net
            opener = urllib.request.build_opener()
            opener.addheaders = [('User-agent', 'Mozilla/5.0')]
            urllib.request.install_opener(opener)
            
            zip_path = "cedict.zip"
            urllib.request.urlretrieve(CEDICT_URL, zip_path)
            
            print("Extraction du dictionnaire...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            if os.path.exists(zip_path): os.remove(zip_path)
            print("Dictionnaire Chinois installé.")
        except Exception as e:
            print(f"ERREUR CRITIQUE DICO CHINOIS: {e}")
            return

    if not cedict_data:
        print("Chargement CEDICT en mémoire...")
        try:
            with open(CEDICT_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip(): continue
                    parts = line.split(' ', 2)
                    if len(parts) < 3: continue
                    
                    traditional, simplified, rest = parts
                    
                    # Extraction définitions
                    defs = []
                    if '/' in rest:
                        defs = rest.split('/', 1)[1].strip().strip('/').split('/')
                    
                    entry = {"defs": defs}
                    
                    # On indexe les deux formes
                    if simplified not in cedict_data: cedict_data[simplified] = []
                    cedict_data[simplified].append(entry)
                    if traditional not in cedict_data: cedict_data[traditional] = []
                    cedict_data[traditional].append(entry)
            print(f"CEDICT chargé : {len(cedict_data)} entrées.")
        except Exception as e:
            print(f"Erreur lecture CEDICT: {e}")

# Lancement au démarrage (non bloquant si échec)
try: load_cedict()
except: pass

# --- OUTILS ---
def clean_html_text(html_content: str) -> str:
    soup = BeautifulSoup(html_content, 'html.parser')
    for tag in soup(['rt', 'rp', 'script', 'style']): tag.decompose()
    text = soup.get_text()
    return re.sub(r'［＃.*?］', '', text)

def clean_raw_text(text: str) -> str:
    text = re.sub(r'《.*?》', '', text)
    text = text.replace('｜', '')
    return re.sub(r'［＃.*?］', '', text)

def extract_text_from_epub(file_bytes: bytes) -> str:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name
    try:
        book = epub.read_epub(tmp_path)
        full = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                full.append(clean_html_text(item.get_content().decode('utf-8')))
        return "\n".join(full)
    except: return ""
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

# --- ANALYSE ---
def analyze_text(text: str, lang: str = "jp"):
    result = {}
    if lang == "cn":
        if not cedict_data: load_cedict()
        result = analyze_chinese_text(text)
    else:
        result = analyze_japanese_text(text)
    
    result["raw_text"] = text
    return result

def analyze_chinese_text(text: str):
    lines = text.splitlines()
    sentences = []
    
    for line in lines:
        if not line.strip():
            sentences.append([{"text": "", "is_word": False}])
            continue
            
        words = jieba.cut(line)
        tokens = []
        for w in words:
            # Détection mot (au moins un caractère non-symbole)
            is_word = len(w.strip()) > 0 and not re.match(r'^[^\w\u4e00-\u9fff]+$', w)
            
            token = {"text": w, "is_word": is_word}
            if is_word:
                # Pinyin
                pys = pinyin(w, style=Style.TONE)
                reading = " ".join([x[0] for x in pys])
                
                # Defs
                defs = []
                if w in cedict_data:
                    defs = cedict_data[w][0]['defs'][:4]
                
                token.update({
                    "lemma": w, "reading": reading, "pos": "Mot",
                    "ent_seq": abs(hash(w)) % 100000000, # ID Hash positif
                    "definitions": defs, "jlpt": None
                })
            tokens.append(token)
        sentences.append(tokens)
    return {"sentences": sentences}

def estimate_jlpt(entry):
    # Logique simplifiée pour JMDict
    for s in entry.senses:
        for m in s.misc: 
            if 'jlpt-n' in str(m): return int(str(m)[-1])
    return 4 if any(k.pri for k in entry.kanji_forms) else 1

def analyze_japanese_text(text: str):
    lines = text.splitlines()
    sentences = []
    targets = ["名詞", "動詞", "形容詞", "副詞", "助動詞", "形状詞", "代名詞", "固有名詞"] 

    for line in lines:
        if not line.strip():
            sentences.append([{"text": "", "is_word": False}])
            continue
            
        tokens = []
        for m in tokenizer_obj.tokenize(line, mode):
            w = m.surface()
            try: pos = m.part_of_speech()[0]
            except: pos = "Inconnu"
            
            token = {"text": w, "is_word": False}
            if pos in targets:
                forms = [f for f in [m.dictionary_form(), m.normalized_form(), w] if f]
                found = None
                for f in forms:
                    try:
                        res = jmd.lookup(f)
                        if res.entries: 
                            found = res.entries[0]
                            break
                    except: continue
                
                if found:
                    defs = [g.text for s in found.senses for g in s.gloss]
                    token.update({
                        "is_word": True, "lemma": forms[0], 
                        "reading": m.reading_form(), "pos": pos,
                        "ent_seq": int(found.idseq), "definitions": defs[:4],
                        "jlpt": estimate_jlpt(found)
                    })
            tokens.append(token)
        sentences.append(tokens)
    return {"sentences": sentences}