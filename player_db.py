import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
import json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Création de la table avec les colonnes supplémentaires
cur.execute("""
CREATE TABLE IF NOT EXISTS player_stats (
    user_id TEXT PRIMARY KEY,
    personnage_id TEXT,
    nom TEXT,
    pv INTEGER,
    pv_max INTEGER,
    force INTEGER,
    magie INTEGER,
    armure INTEGER,
    armure_magique INTEGER,
    vitesse INTEGER,
    image TEXT,
    attaques JSONB
);
""")
conn.commit()


def get_player(user_id):
    """Récupère le joueur depuis la DB, ou crée un joueur par défaut."""
    cur.execute("SELECT * FROM player_stats WHERE user_id = %s", (user_id,))
    joueur = cur.fetchone()

    if joueur:
        # Sécurité si ancien joueur sans image ou attaques
        if not joueur.get("image"):
            joueur["image"] = "images/personnages/default.png"
            update_player(user_id, image=joueur["image"])
        if not joueur.get("attaques"):
            joueur["attaques"] = []
            update_player(user_id, attaques=joueur["attaques"])
        return joueur

    # Création automatique d'un joueur par défaut
    joueur = {
        "user_id": user_id,
        "personnage_id": None,
        "nom": "Aventurier",
        "pv": 100,
        "pv_max": 100,
        "force": 10,
        "magie": 5,
        "armure": 5,
        "armure_magique": 5,
        "vitesse": 10,
        "image": "images/personnages/default.png",
        "attaques": []
    }

    cur.execute("""
        INSERT INTO player_stats
        (user_id, personnage_id, nom, pv, pv_max, force, magie, armure, armure_magique, vitesse, image, attaques)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, tuple(joueur.values()))
    conn.commit()

    return joueur


def update_player(user_id, **stats):
    """Met à jour le joueur avec les stats passées en kwargs."""
    if not stats:
        return
    fields = ", ".join(f"{k} = %s" for k in stats)
    values = list(stats.values()) + [user_id]
    cur.execute(f"""
        UPDATE player_stats
        SET {fields}
        WHERE user_id = %s
    """, values)
    conn.commit()


def load_characters_json(path="json/personnages.json"):
    """Charge tous les personnages depuis le JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
