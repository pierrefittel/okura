# On utilise la version exacte définie dans votre pyproject.toml
FROM python:3.13-slim

# Installation des dépendances système minimales (git, curl, build-essential pour compiler certaines libs si besoin)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Installation de Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

# Configuration de Poetry pour ne pas créer de virtualenv (inutile dans un conteneur isolé)
RUN poetry config virtualenvs.create false

WORKDIR /app

# On copie d'abord uniquement les fichiers de dépendances pour profiter du cache Docker
COPY pyproject.toml poetry.lock* ./

# Installation des dépendances (y compris jamdict qui fonctionnera ici)
RUN poetry install --no-root --no-interaction --no-ansi

# Le code source sera monté via le docker-compose, pas besoin de le copier ici pour le dev
# Commande de lancement par défaut (avec reload pour le dev)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]