import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from combat import CombatView

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID_COPAING"))  # <-- ID du salon où envoyer le message

intents = discord.Intents.default()
intents.message_content = True  # nécessaire pour lire et envoyer les messages

bot = commands.Bot(command_prefix="!", intents=intents)

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
async def combat(ctx, nb_regions: int = 3, nb_ennemis: int = 10):
    view = CombatView(
        user=ctx.author,
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
