import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from combat import CombatView
import json

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID_COPAING"))  # <-- ID du salon où envoyer le message

intents = discord.Intents.default()
intents.message_content = True  # nécessaire pour lire et envoyer les messages

bot = commands.Bot(command_prefix="!", intents=intents)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHAR_FILE = os.path.join(BASE_DIR, "json", "personnages.json")


def load_characters():
    if not os.path.exists(CHAR_FILE):
        return {}
    with open(CHAR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_characters(data):
    with open(CHAR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    # Récupérer le salon par son ID
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🟢 **Le bot est connecté et prêt !** 🐊")
    else:
        print("❌ Salon introuvable (ID incorrect ou bot n'a pas les permissions)")



@bot.command()
async def personnage(ctx, choix: str):
    """
    Choix du personnage avant le combat
    Ex: !personnage guerrier
    """

    choix = choix.lower()
    personnages_valides = ["guerrier", "mage", "archer"]

    if choix not in personnages_valides:
        await ctx.send(
            f"❌ Personnage invalide.\n"
            f"Choisis parmi : {', '.join(personnages_valides)}"
        )
        return

    data = load_characters()
    data[str(ctx.author.id)] = choix
    save_characters(data)

    await ctx.send(
        f"✅ {ctx.author.mention} a choisi le personnage **{choix.capitalize()}** ⚔️"
    )




@bot.command()
async def combat(ctx, nb_regions: int = 3, nb_ennemis: int = 10):
    data = load_characters()
    user_id = str(ctx.author.id)

    if user_id not in data:
        await ctx.send(
            "❌ Tu dois d'abord choisir un personnage avec `!personnage <nom>`"
        )
        return

    personnage = data[user_id]

    view = CombatView(
        user=ctx.author,
        personnage=personnage,  # <-- tu le passes ici
        nb_regions=nb_regions,
        nb_ennemis_par_region=nb_ennemis
    )

    file = view.get_combat_image()
    await ctx.send(
        content=view.get_initial_message_content(),
        file=file,
        view=view
    )


bot.run(TOKEN)
