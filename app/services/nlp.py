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
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

# --- MOTEUR CHINOIS (CC-CEDICT) ---
CEDICT_URL = "https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.zip"
CEDICT_FILE = "cedict_ts.u8"
cedict_data = {}

def load_cedict():
    """Charge le dictionnaire chinois. Le télécharge si nécessaire."""
    # 1. Téléchargement automatique
    if not os.path.exists(CEDICT_FILE):
        print("Dictionnaire chinois introuvable. Téléchargement de CC-CEDICT...")
        try:
            zip_path = "cedict.zip"
            # Téléchargement (peut prendre quelques secondes)
            urllib.request.urlretrieve(CEDICT_URL, zip_path)
            # Extraction
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            # Nettoyage
            if os.path.exists(zip_path):
                os.remove(zip_path)
            print("Dictionnaire chinois installé avec succès.")
        except Exception as e:
            print(f"Erreur critique téléchargement CEDICT: {e}")
            return

    # 2. Parsing et chargement en mémoire
    if not cedict_data: # Évite de recharger si déjà en mémoire
        print("Chargement de CEDICT en mémoire...")
        try:
            with open(CEDICT_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('#') or not line.strip(): continue
                    
                    # Format: Traditionnel Simplifié [pin1 yin1] /sens 1/sens 2/.../
                    # ex: 漢語 汉语 [Han4 yu3] /Chinese language/
                    parts = line.split(' ', 2)
                    if len(parts) < 3: continue
                    
                    traditional = parts[0]
                    simplified = parts[1]
                    rest = parts[2]
                    
                    # Extraction des définitions
                    if '/' in rest:
                        # On prend tout ce qu'il y a après le premier /
                        defs_raw = rest.split('/', 1)[1].strip().strip('/')
                        definitions = defs_raw.split('/')
                    else:
                        definitions = []

                    entry = {"defs": definitions}
                    
                    # Indexation par Simplifié (standard) et Traditionnel
                    if simplified not in cedict_data: cedict_data[simplified] = []
                    cedict_data[simplified].append(entry)
                    
                    if traditional not in cedict_data: cedict_data[traditional] = []
                    cedict_data[traditional].append(entry)
            print(f"CEDICT chargé : {len(cedict_data)} entrées.")
        except Exception as e:
            print(f"Erreur lecture CEDICT: {e}")

# Initialisation au démarrage du serveur
try: load_cedict()
except Exception as e: print(f"Erreur init NLP Chinois: {e}")


# --- NETTOYAGE COMMUN ---
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
    result = {}
    if lang == "cn":
        if not cedict_data: load_cedict()
        result = analyze_chinese_text(text)
    else:
        result = analyze_japanese_text(text)
    
    # ON AJOUTE LE TEXTE BRUT À LA RÉPONSE
    result["raw_text"] = text 
    return result

# --- ANALYSEUR CHINOIS ---
def analyze_chinese_text(text: str):
    lines = text.splitlines()
    sentences_output = []
    
    for line in lines:
        if not line.strip():
            sentences_output.append([{"text": "", "is_word": False}])
            continue
        words = list(jieba.cut(line))
        line_tokens = []
        for word in words:
            is_word = len(word.strip()) > 0 and not re.match(r'^[，。？！：；“”‘’（）\s\d]+$', word)
            token_data = {"text": word, "is_word": is_word}
            if is_word:
                py_list = pinyin(word, style=Style.TONE)
                reading = " ".join([item[0] for item in py_list])
                defs = []
                if word in cedict_data: defs = cedict_data[word][0]['defs'][:5]
                elif not cedict_data: defs = ["(Dictionnaire non chargé)"]
                token_data.update({
                    "lemma": word, "reading": reading, "pos": "Mot", 
                    "ent_seq": hash(word) % 100000000, "definitions": defs, "jlpt": None
                })
            line_tokens.append(token_data)
        sentences_output.append(line_tokens)
    return {"sentences": sentences_output}
        
    return {"sentences": sentences_output}

# --- ANALYSEUR JAPONAIS ---
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
            try: pos = m.part_of_speech()[0]
            except: pos = "Inconnu"
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
                        if res.entries: found = res.entries[0]; break
                    except: continue
                if found:
                    defs = []
                    for s in found.senses: defs.extend([g.text for g in s.gloss])
                    token_data.update({
                        "is_word": True, "lemma": forms[0], "reading": m.reading_form(),
                        "pos": pos, "ent_seq": int(found.idseq), "definitions": defs[:4], "jlpt": estimate_jlpt(found)
                    })
            line_tokens.append(token_data)
        sentences_output.append(line_tokens)
    return {"sentences": sentences_output}