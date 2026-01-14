import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
# Curseur qui renvoie des dictionnaires
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Création de la table
cur.execute("""
CREATE TABLE IF NOT EXISTS player_stats (
    user_id TEXT PRIMARY KEY,
    nom TEXT,
    pv INTEGER,
    pv_max INTEGER,
    force INTEGER,
    magie INTEGER,
    armure INTEGER,
    armure_magique INTEGER,
    vitesse INTEGER
);
""")
conn.commit()


def get_player(user_id):
    # 🔹 sélectionner depuis la bonne table
    cur.execute("SELECT * FROM player_stats WHERE user_id = %s", (user_id,))
    joueur = cur.fetchone()

    if joueur:
        return joueur  # déjà un dict grâce à RealDictCursor

    # 🔧 création automatique si inexistant
    joueur = {
        "user_id": user_id,
        "nom": "Aventurier",
        "pv": 100,
        "pv_max": 100,
        "force": 10,
        "magie": 5,
        "armure": 5,
        "armure_magique": 5,
        "vitesse": 10
    }

    cur.execute("""
        INSERT INTO player_stats (user_id, nom, pv, pv_max, force, magie, armure, armure_magique, vitesse)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, tuple(joueur.values()))
    conn.commit()

    return joueur


def update_player(user_id, **stats):
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
