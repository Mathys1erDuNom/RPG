import discord
from discord.ui import View, Select
import json
from personnage_db import (
    charger_personnages_base, 
    creer_personnage, 
    personnage_existe,
    get_personnage
)

class SelectionPersonnageView(View):
    """View pour la sélection du personnage de base."""
    
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        
        # Charger les personnages disponibles
        with open("json/personnages.json", "r", encoding="utf-8") as f:
            self.personnages_disponibles = json.load(f)
        
        # Créer les options pour le Select
        options = []
        for i, perso in enumerate(self.personnages_disponibles):
            # Créer une description avec les stats principales
            desc = f"⚔️{perso['force']} 🔮{perso['magie']} 🛡️{perso['armure']} ⚡{perso['vitesse']}"
            options.append(
                discord.SelectOption(
                    label=f"{perso['nom']} ({perso['race']})",
                    description=desc,
                    value=str(i)
                )
            )
        
        # Ajouter le Select au View
        self.select = Select(
            placeholder="Choisissez votre personnage",
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
        """Callback quand un personnage est sélectionné."""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ Ce n'est pas votre sélection de personnage !",
                ephemeral=True
            )
            return
        
        # Récupérer le personnage choisi
        index = int(self.select.values[0])
        personnage_choisi = self.personnages_disponibles[index]
        
        # Créer le personnage dans la base de données
        creer_personnage(self.user_id, personnage_choisi)
        
        # Message de confirmation avec embed
        embed = discord.Embed(
            title="✅ Personnage créé !",
            description=f"Vous avez choisi **{personnage_choisi['nom']}** !",
            color=discord.Color.green()
        )
        
        # Ajouter les stats dans l'embed
        embed.add_field(
            name="📊 Statistiques",
            value=f"❤️ PV: {personnage_choisi['pv']}/{personnage_choisi['pv_max']}\n"
                  f"⚔️ Force: {personnage_choisi['force']}\n"
                  f"🔮 Magie: {personnage_choisi['magie']}\n"
                  f"🛡️ Armure: {personnage_choisi['armure']}\n"
                  f"✨ Armure Magique: {personnage_choisi['armure_magique']}\n"
                  f"⚡ Vitesse: {personnage_choisi['vitesse']}",
            inline=True
        )
        
        # Liste des attaques
        attaques_text = "\n".join([
            f"• **{atk['nom']}**: {atk['degats']} dégâts ({atk['type']})"
            for atk in personnage_choisi['attaques']
        ])
        embed.add_field(
            name="⚔️ Attaques",
            value=attaques_text,
            inline=False
        )
        
        # Ajouter l'image si elle existe
        if personnage_choisi.get('image'):
            embed.set_thumbnail(url=f"attachment://{personnage_choisi['image'].split('/')[-1]}")
        
        await interaction.response.edit_message(
            content=None,
            embed=embed,
            view=None
        )


async def afficher_selection_personnage(interaction: discord.Interaction):
    """Affiche le menu de sélection de personnage."""
    user_id = str(interaction.user.id)
    
    # Vérifier si l'utilisateur a déjà un personnage
    if personnage_existe(user_id):
        perso = get_personnage(user_id)
        await interaction.response.send_message(
            f"❌ Vous avez déjà un personnage : **{perso['nom']}** ({perso['race']})\n"
            f"Utilisez `/reset_personnage` pour recommencer.",
            ephemeral=True
        )
        return
    
    # Afficher le menu de sélection
    view = SelectionPersonnageView(user_id)
    await interaction.response.send_message(
        "🎮 **Choisissez votre personnage**\n"
        "Sélectionnez le personnage avec lequel vous voulez jouer :",
        view=view,
        ephemeral=False
    )