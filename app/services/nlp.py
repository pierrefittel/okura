from sudachipy import tokenizer, dictionary

# On charge le dictionnaire une seule fois au démarrage du module
# SplitMode.C est le mode qui garde les mots composés (ex: "New York" au lieu de "New" + "York")
tokenizer_obj = dictionary.Dictionary().create()
mode = tokenizer.Tokenizer.SplitMode.C

def analyze_japanese_text(text: str):
    """
    Découpe le texte et retourne les lemmes (formes dictionnaire).
    """
    morphemes = tokenizer_obj.tokenize(text, mode)
    extracted_data = []

    # Filtre les catégories grammaticales inintéressantes (particules, ponctuation...)
    # Cibles : Noms, Verbes, Adjectifs, Adverbes
    targets = ["名詞", "動詞", "形容詞", "副詞"]

    for m in morphemes:
        pos = m.part_of_speech() # Renvoie une liste ['Nom', 'Commun', 'Général', ...]
        major_pos = pos[0]

        if major_pos in targets:
            # Petit nettoyage : ignorer les symboles et les espaces qui passeraient le filtre
            if m.dictionary_form() == "" or m.dictionary_form().isspace():
                continue

            extracted_data.append({
                "original": m.surface(),          # Mot tel qu'il est écrit
                "terme": m.dictionary_form(),     # Forme dictionnaire (pour la DB)
                "lecture": m.reading_form(),      # Lecture Katakana (utile pour le tri/recherche)
                "pos": major_pos                  # Nature (Nom, Verbe...)
            })

    return extracted_data