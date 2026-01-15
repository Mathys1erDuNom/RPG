import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from combat import CombatView
from selection_personnage import SelectionPersonnageView
from personnage_db import personnage_existe, get_personnage, reset_personnage_pv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID_COPAING"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        await channel.send("🟢 **Le bot est connecté et prêt !** 🐊")
    else:
        print("❌ Salon introuvable (ID incorrect ou bot n'a pas les permissions)")

@bot.command()
async def choix_personnage(ctx):
    """Permet de choisir et créer son personnage."""
    user_id = str(ctx.author.id)
    
    # Vérifier si l'utilisateur a déjà un personnage
    if personnage_existe(user_id):
        perso = get_personnage(user_id)
        await ctx.send(
            f"❌ {ctx.author.mention} Vous avez déjà un personnage : **{perso['nom']}** ({perso['race']})\n"
            f"Utilisez `!reset_personnage` pour recommencer."
        )
        return
    
    # Afficher le menu de sélection
    view = SelectionPersonnageView(user_id)
    await ctx.send(
        f"🎮 **{ctx.author.mention} Choisissez votre personnage**\n"
        "Sélectionnez le personnage avec lequel vous voulez jouer :",
        view=view
    )

@bot.command()
async def mon_personnage(ctx):
    """Affiche les informations du personnage de l'utilisateur."""
    user_id = str(ctx.author.id)
    
    if not personnage_existe(user_id):
        await ctx.send(f"❌ {ctx.author.mention} Vous n'avez pas de personnage ! Utilisez `!choix_personnage` d'abord.")
        return
    
    perso = get_personnage(user_id)
    
    # Créer un embed avec les infos du personnage
    embed = discord.Embed(
        title=f"📋 {perso['nom']}",
        description=f"**Race :** {perso['race']}",
        color=discord.Color.blue()
    )
    
    # Calculer le pourcentage de PV
    pv_percent = (perso['pv'] / perso['pv_max']) * 100
    if pv_percent > 75:
        pv_emoji = "💚"
    elif pv_percent > 50:
        pv_emoji = "💛"
    elif pv_percent > 25:
        pv_emoji = "🧡"
    else:
        pv_emoji = "❤️"
    
    embed.add_field(
        name="📊 Statistiques",
        value=f"{pv_emoji} **PV:** {perso['pv']}/{perso['pv_max']}\n"
              f"⚔️ **Force:** {perso['force']}\n"
              f"🔮 **Magie:** {perso['magie']}\n"
              f"🛡️ **Armure:** {perso['armure']}\n"
              f"✨ **Armure Magique:** {perso['armure_magique']}\n"
              f"⚡ **Vitesse:** {perso['vitesse']}",
        inline=True
    )
    
    # Liste des attaques
    attaques_text = "\n".join([
        f"• **{atk['nom']}**\n"
        f"  ╰ {atk['degats']} dégâts ({atk['type']})\n"
        f"  ╰ Ratio Force: {atk.get('ratioattk', 0)}% | Magie: {atk.get('ratiomagie', 0)}%"
        for atk in perso['attaques']
    ])
    embed.add_field(
        name="⚔️ Attaques",
        value=attaques_text,
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def combat(ctx, nb_regions: int = 3, nb_ennemis: int = 10):
    """Lance un combat avec des régions et des ennemis."""
    user_id = str(ctx.author.id)
    
    # Vérifier que l'utilisateur a un personnage
    if not personnage_existe(user_id):
        await ctx.send(f"❌ {ctx.author.mention} Vous n'avez pas de personnage ! Utilisez `!creer_personnage` d'abord.")
        return
    
    # Charger le personnage
    joueur = get_personnage(user_id)
    
    # Vérifier que le joueur a des PV
    if joueur["pv"] <= 0:
        await ctx.send(f"❌ {ctx.author.mention} Votre personnage est KO ! Utilisez `!soigner` pour restaurer vos PV.")
        return
    
    # Valider les paramètres
    nb_regions = max(1, min(5, nb_regions))
    nb_ennemis = max(1, min(20, nb_ennemis))
    
    # Créer la vue de combat
    try:
        view = CombatView(user_id, nb_regions=nb_regions, nb_ennemis_par_region=nb_ennemis)
        file = view.get_combat_image()
        
        await ctx.send(
            content=f"⚔️ {ctx.author.mention}\n" + view.get_initial_message_content(),
            file=file,
            view=view
        )
    except ValueError as e:
        await ctx.send(f"❌ Erreur : {str(e)}")


@bot.command()
async def reset_personnage(ctx):
    """Supprime le personnage de l'utilisateur."""
    from personnage_db import supprimer_personnage
    
    user_id = str(ctx.author.id)
    
    if not personnage_existe(user_id):
        await ctx.send(f"❌ {ctx.author.mention} Vous n'avez pas de personnage à supprimer.")
        return
    
    perso = get_personnage(user_id)
    supprimer_personnage(user_id)
    
    await ctx.send(
        f"🗑️ {ctx.author.mention} Votre personnage **{perso['nom']}** a été supprimé.\n"
        f"Utilisez `!creer_personnage` pour en créer un nouveau !"
    )

@bot.command()
async def aide(ctx):
    """Affiche la liste des commandes disponibles."""
    embed = discord.Embed(
        title="📖 Guide des Commandes",
        description="Voici toutes les commandes disponibles :",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="!choix_personnage",
        value="Choisissez votre personnage en choisissant parmi les personnages disponibles.",
        inline=False
    )
    
    embed.add_field(
        name="!mon_personnage",
        value="Afficher les statistiques et attaques de votre personnage.",
        inline=False
    )
    
    embed.add_field(
        name="!combat [regions] [ennemis]",
        value="Lancer un combat !\n"
              "• `regions`: Nombre de régions (1-5, défaut: 3)\n"
              "• `ennemis`: Ennemis par région (1-20, défaut: 10)\n"
              "Exemple: `!combat 2 5`",
        inline=False
    )
    
    
    embed.add_field(
        name="!reset_personnage",
        value="Supprimer votre personnage actuel pour en selectionner un nouveau.",
        inline=False
    )
    
    embed.add_field(
        name="!aide",
        value="Afficher cette aide.",
        inline=False
    )
    
    embed.set_footer(text="💡 Astuce : Les PV sont sauvegardés automatiquement après chaque combat !")
    
    await ctx.send(embed=embed)

bot.run(TOKEN)