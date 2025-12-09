from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de connexion : postgresql://user:password@host:port/dbname
# Note : On utilise "localhost" car ton script tourne sur ta machine, 
# et Docker expose le port 5432 sur ta machine.
SQLALCHEMY_DATABASE_URL = "postgresql://landry:secret@localhost:5432/vocab_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Fonction utilitaire pour récupérer la DB dans tes routes (Dependency Injection)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()