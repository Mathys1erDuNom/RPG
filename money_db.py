import os
import psycopg2
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table argent
cur.execute("""
CREATE TABLE IF NOT EXISTS argent (
    user_id TEXT PRIMARY KEY,
    balance INTEGER DEFAULT 0
);
""")
conn.commit()


def get_balance(user_id):
    """Récupère le solde d'un utilisateur."""
    cur.execute("SELECT balance FROM argent WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    if result:
        return result[0]
    else:
        # Créer un compte avec 1000 pièces de départ
        cur.execute(
            "INSERT INTO argent (user_id, balance) VALUES (%s, %s)",
            (user_id, 1000)
        )
        conn.commit()
        return 1000


def add_money(user_id, amount):
    """Ajoute de l'argent au solde d'un utilisateur."""
    current = get_balance(user_id)
    new_balance = current + amount
    cur.execute(
        "UPDATE argent SET balance = %s WHERE user_id = %s",
        (new_balance, user_id)
    )
    conn.commit()
    return new_balance


def remove_money(user_id, amount):
    """Retire de l'argent du solde d'un utilisateur."""
    current = get_balance(user_id)
    if current < amount:
        return None  # Pas assez d'argent
    new_balance = current - amount
    cur.execute(
        "UPDATE argent SET balance = %s WHERE user_id = %s",
        (new_balance, user_id)
    )
    conn.commit()
    return new_balance


def has_money(user_id, amount):
    """Vérifie si un utilisateur a assez d'argent."""
    return get_balance(user_id) >= amount