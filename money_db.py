# money_db.py
import os
import psycopg2
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table argent
cur.execute("""
CREATE TABLE IF NOT EXISTS argent (
    user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0
);
""")
conn.commit()


# ==============================
#        FONCTIONS UTILES
# ==============================

def get_balance(user_id: str) -> int:
    """Retourne l'argent du joueur (0 si inexistant)."""
    cur.execute("SELECT balance FROM argent WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0


def set_balance(user_id: str, amount: int):
    """Fixe directement l'argent du joueur."""
    cur.execute("""
        INSERT INTO argent (user_id, balance)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET balance = EXCLUDED.balance
    """, (user_id, amount))
    conn.commit()


def add_balance(user_id: str, amount: int):
    """Ajoute (ou retire si négatif) de l'argent au joueur."""
    cur.execute("""
        INSERT INTO argent (user_id, balance)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET balance = argent.balance + EXCLUDED.balance
    """, (user_id, amount))
    conn.commit()


def can_afford(user_id: str, cost: int) -> bool:
    """Vérifie si le joueur a assez d'argent."""
    return get_balance(user_id) >= cost
