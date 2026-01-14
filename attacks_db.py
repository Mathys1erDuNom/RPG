# attacks_db.py
import os
import psycopg2
import json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS player_attacks (
    user_id TEXT PRIMARY KEY,
    attacks JSONB
);
""")
conn.commit()


def get_attacks(user_id):
    cur.execute("SELECT attacks FROM player_attacks WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else []


def set_attacks(user_id, attacks):
    cur.execute("""
        INSERT INTO player_attacks (user_id, attacks)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET attacks = EXCLUDED.attacks
    """, (user_id, json.dumps(attacks)))
    conn.commit()
