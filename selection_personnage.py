import discord
from discord.ui import View, Button
from personnage_db import (
    charger_personnages_base, 
    creer_personnage, 
    personnage_existe,
    get_personnage
)
import os


class SelectionPersonnageView(View):
    """View pour la sélection du personnage de base avec navigation."""
    
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.personnages = charger_personnages_base()
        self.selected_index = 0
        
        # Créer les boutons de navigation
        self.prev_button = Button(label="◀ Précédent", style=discord.ButtonStyle.secondary)
        self.prev_button.callback = self.prev_personnage
        self.add_item(self.prev_button)
        
        self.select_button = Button(label="✅ Choisir ce personnage", style=discord.ButtonStyle.success)
        self.select_button.callback = self.select_personnage
        self.add_item(self.select_button)
        
        self.next_button = Button(label="Suivant ▶", style=discord.ButtonStyle.secondary)
        self.next_button.callback = self.next_personnage
        self.add_item(self.next_button)
        
        self.update_buttons()
    
    def update_buttons(self):
        """Met à jour l'état des boutons de navigation."""
        self.prev_button.disabled = (self.selected_index == 0)
        self.next_button.disabled = (self.selected_index == len(self.personnages) - 1)
    
    def get_current_embed_and_file(self):
        """Crée l'embed et le fichier pour le personnage actuel."""
        perso = self.personnages[self.selected_index]
        
        # Créer l'embed
        embed = discord.Embed(
            title=f"📋 {perso['nom']}",
            description=f"**Race :** {perso['race']}\n\n*Personnage {self.selected_index + 1}/{len(self.personnages)}*",
            color=discord.Color.blue()
        )
        
        # Attacher l'image du personnage
        image_path = perso.get('image', '')
        file = None
        if image_path and os.path.exists(image_path):
            file = discord.File(image_path, filename="personnage.png")
            embed.set_thumbnail(url="attachment://personnage.png")
        
        # Ajouter la description si elle existe
        if perso.get('description'):
            embed.add_field(
                name="📖 Description",
                value=perso['description'],
                inline=False
            )
        
        # Statistiques
        embed.add_field(
            name="📊 Statistiques",
            value=f"💚 **PV:** {perso['pv_max']}/{perso['pv_max']}\n"
                  f"⚔️ **Force:** {perso['force']}\n"
                  f"🔮 **Magie:** {perso['magie']}\n"
                  f"🛡️ **Armure:** {perso['armure']}\n"
                  f"✨ **Armure Magique:** {perso['armure_magique']}\n"
                  f"⚡ **Vitesse:** {perso['vitesse']}",
            inline=False
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
        
        return embed, file
    
    async def prev_personnage(self, interaction: discord.Interaction):
        """Affiche le personnage précédent."""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ Ce n'est pas votre sélection de personnage !",
                ephemeral=True
            )
            return
        
        if self.selected_index > 0:
            self.selected_index -= 1
            self.update_buttons()
            
            embed, file = self.get_current_embed_and_file()
            
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
    
    async def next_personnage(self, interaction: discord.Interaction):
        """Affiche le personnage suivant."""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ Ce n'est pas votre sélection de personnage !",
                ephemeral=True
            )
            return
        
        if self.selected_index < len(self.personnages) - 1:
            self.selected_index += 1
            self.update_buttons()
            
            embed, file = self.get_current_embed_and_file()
            
            if file:
                await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)
    
    async def select_personnage(self, interaction: discord.Interaction):
        """Sélectionne le personnage actuel."""
        if interaction.user.id != int(self.user_id):
            await interaction.response.send_message(
                "❌ Ce n'est pas votre sélection de personnage !",
                ephemeral=True
            )
            return
        
        perso = self.personnages[self.selected_index]
        
        # Créer le personnage dans la base de données
        creer_personnage(self.user_id, perso)
        
        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True
        
        # Créer l'embed de confirmation
        embed = discord.Embed(
            title="✅ Personnage créé !",
            description=f"Vous avez choisi **{perso['nom']}** ({perso['race']})\n\n"
                       f"Utilisez `!mon_personnage` pour voir vos stats\n"
                       f"Utilisez `!combat` pour commencer l'aventure !",
            color=discord.Color.green()
        )
        
        # Attacher l'image du personnage
        image_path = perso.get('image', '')
        file = None
        if image_path and os.path.exists(image_path):
            file = discord.File(image_path, filename="personnage.png")
            embed.set_thumbnail(url="attachment://personnage.png")
        
        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)


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
    embed, file = view.get_current_embed_and_file()
    
    if file:
        await interaction.response.send_message(
            content="🎮 **Choisissez votre personnage**\n"
                   "Utilisez les boutons pour naviguer entre les personnages :",
            embed=embed,
            file=file,
            view=view,
            ephemeral=False
        )
    else:
        await interaction.response.send_message(
            content="🎮 **Choisissez votre personnage**\n"
                   "Utilisez les boutons pour naviguer entre les personnages :",
            embed=embed,
            view=view,
            ephemeral=False
        )