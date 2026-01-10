import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
VOICE_CHANNEL_ID = int(os.getenv("CHANNEL_ID_COPAING"))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

    channel = bot.get_channel(VOICE_CHANNEL_ID)

    if channel:
        await channel.send("🟢 **Le bot est connecté et prêt !** 🐊")
    else:
        print("❌ Salon introuvable (ID incorrect ou pas accessible)")

bot.run(TOKEN)
