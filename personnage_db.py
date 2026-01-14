import os
import psycopg2
import json
from psycopg2.extras import Json
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Connexion globale à la base
conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

# Création de la table personnages
cur.execute("""
CREATE TABLE IF NOT EXISTS personnages (
    user_id TEXT PRIMARY KEY,
    race TEXT NOT NULL,
    nom TEXT NOT NULL,
    pv INTEGER NOT NULL,
    pv_max INTEGER NOT NULL,
    vitesse INTEGER NOT NULL,
    force INTEGER NOT NULL,
    magie INTEGER NOT NULL,
    armure INTEGER NOT NULL,
    armure_magique INTEGER NOT NULL,
    image TEXT NOT NULL,
    attaques JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""")
conn.commit()


def charger_personnages_base():
    """Charge tous les personnages disponibles depuis le fichier JSON."""
    with open("json/personnages.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_personnage(user_id):
    """Récupère le personnage d'un utilisateur depuis la base de données."""
    cur.execute("""
        SELECT race, nom, pv, pv_max, vitesse, force, magie, armure, armure_magique, image, attaques
        FROM personnages
        WHERE user_id = %s
    """, (user_id,))
    
    result = cur.fetchone()
    if result:
        return {
            "race": result[0],
            "nom": result[1],
            "pv": result[2],
            "pv_max": result[3],
            "vitesse": result[4],
            "force": result[5],
            "magie": result[6],
            "armure": result[7],
            "armure_magique": result[8],
            "image": result[9],
            "attaques": result[10]
        }
    return None


def creer_personnage(user_id, personnage_base):
    """Crée un nouveau personnage pour un utilisateur à partir d'un personnage de base."""
    cur.execute("""
        INSERT INTO personnages (
            user_id, race, nom, pv, pv_max, vitesse, force, magie, 
            armure, armure_magique, image, attaques
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """, (
        user_id,
        personnage_base["race"],
        personnage_base["nom"],
        personnage_base["pv"],
        personnage_base["pv_max"],
        personnage_base["vitesse"],
        personnage_base["force"],
        personnage_base["magie"],
        personnage_base["armure"],
        personnage_base["armure_magique"],
        personnage_base["image"],
        Json(personnage_base["attaques"])
    ))
    conn.commit()


def update_personnage_pv(user_id, pv):
    """Met à jour les PV du personnage."""
    cur.execute("""
        UPDATE personnages
        SET pv = %s, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (pv, user_id))
    conn.commit()


def reset_personnage_pv(user_id):
    """Restaure les PV du personnage à leur maximum."""
    cur.execute("""
        UPDATE personnages
        SET pv = pv_max, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = %s
    """, (user_id,))
    conn.commit()


def supprimer_personnage(user_id):
    """Supprime le personnage d'un utilisateur."""
    cur.execute("DELETE FROM personnages WHERE user_id = %s", (user_id,))
    conn.commit()


def personnage_existe(user_id):
    """Vérifie si un utilisateur a déjà un personnage."""
    cur.execute("SELECT 1 FROM personnages WHERE user_id = %s", (user_id,))
    return cur.fetchone() is not None


def get_stats_personnage(user_id):
    """Récupère uniquement les statistiques du personnage (sans les attaques)."""
    cur.execute("""
        SELECT race, nom, pv, pv_max, vitesse, force, magie, armure, armure_magique
        FROM personnages
        WHERE user_id = %s
    """, (user_id,))
    
    result = cur.fetchone()
    if result:
        return {
            "race": result[0],
            "nom": result[1],
            "pv": result[2],
            "pv_max": result[3],
            "vitesse": result[4],
            "force": result[5],
            "magie": result[6],
            "armure": result[7],
            "armure_magique": result[8]
        }
    return None