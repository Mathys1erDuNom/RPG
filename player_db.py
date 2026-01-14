# player_db.py
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

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
    cur.execute("SELECT * FROM player_stats WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return None

    keys = [
        "user_id", "nom", "pv", "pv_max",
        "force", "magie", "armure",
        "armure_magique", "vitesse"
    ]
    return dict(zip(keys, row))


def update_player(user_id, **stats):
    fields = ", ".join(f"{k} = %s" for k in stats)
    values = list(stats.values()) + [user_id]
    cur.execute(f"""
        UPDATE player_stats
        SET {fields}
        WHERE user_id = %s
    """, values)
    conn.commit()
