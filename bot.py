import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from combat import CombatView

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()


bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")

@bot.command()
async def combat(ctx):
    print("Commande !combat reçue")  # <-- test
    view = CombatView()
    await ctx.send(
        content=f"🧑 {view.joueur['nom']} PV: {view.joueur['pv']} | 👾 {view.ennemi['nom']} PV: {view.ennemi['pv']}\n"
                f"{'C’est votre tour !' if view.tour_joueur else 'C’est au tour de l’ennemi...'}",
        view=view
    )

bot.run(TOKEN)
