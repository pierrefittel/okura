from sudachipy import tokenizer, dictionary
from jamdict import Jamdict

# Initialisation des moteurs (Sudachi + Jamdict)
# Cela peut prendre quelques secondes au démarrage du serveur
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C
jmd = Jamdict()

def analyze_japanese_text(text: str):
    """
    Découpe le texte, lemmatise et cherche les définitions.
    """
    morphemes = tokenizer_obj.tokenize(text, mode)
    extracted_data = []

    targets = ["名詞", "動詞", "形容詞", "副詞"]

    for m in morphemes:
        pos = m.part_of_speech()
        major_pos = pos[0]

        if major_pos in targets:
            lemma = m.dictionary_form()
            
            # Nettoyage basique
            if lemma == "" or lemma.isspace():
                continue

            # --- PARTIE JAMDICT ---
            # On cherche le mot dans le dictionnaire
            definitions = []
            try:
                # lookup retourne un objet complexe, on simplifie
                result = jmd.lookup(text=lemma)
                if result.entries:
                    # On prend la première entrée trouvée (souvent la plus pertinente)
                    # et on extrait les sens (gloss)
                    for sense in result.entries[0].senses:
                        definitions.extend([g.text for g in sense.gloss])
            except Exception:
                # Si Jamdict plante ou ne trouve rien, on continue sans définition
                pass
            
            # On limite à 3 définitions pour ne pas surcharger la réponse
            definitions = definitions[:3]
            # ----------------------

            extracted_data.append({
                "original": m.surface(),
                "terme": lemma,
                "lecture": m.reading_form(),
                "pos": major_pos,
                "definitions": definitions  # Nouveau champ
            })

    return extracted_data