import os
from jamdict import Jamdict

# 1. On définit le chemin exact (D:\repos\okura\data\jamdict.db)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "jamdict.db")

# 2. On s'assure que le dossier 'data' existe
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    print(f"Dossier créé : {DATA_DIR}")

print(f"installation du dictionnaire vers : {DB_PATH} ...")
print("Cela peut prendre quelques minutes (téléchargement + conversion).")

# 3. On lance l'importation en forçant le chemin
try:
    jmd = Jamdict(db_file=DB_PATH)
    jmd.import_data()
    print("Succès ! Dictionnaire installé.")
except Exception as e:
    print(f"Erreur lors de l'installation : {e}")