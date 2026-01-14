import discord
from discord.ui import View, Select, Button
import json
from personnage_db import get_personnage, personnage_existe
from money_db import get_balance, remove_money
from psycopg2.extras import Json
import os

# Connexion à la base pour les mises à jour
from personnage_db import conn, cur


def load_shop_data():
    """Charge les données du shop depuis le fichier JSON."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "json/attaques.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def apprendre_attaque(user_id, attaque):
    """Ajoute une nouvelle attaque au personnage."""
    perso = get_personnage(user_id)
    attaques = perso["attaques"]
    
    # Vérifier si l'attaque existe déjà
    if any(a["nom"] == attaque["nom"] for a in attaques):
        return False, "Vous connaissez déjà cette attaque !"
    
    # Limiter à 6 attaques maximum
    if len(attaques) >= 6:
        return False, "Vous avez déjà 6 attaques ! (maximum atteint)"
    
    # Ajouter l'attaque (sans l'id et le prix)
    nouvelle_attaque = {
        "nom": attaque["nom"],
        "degats": attaque["degats"],
        "type": attaque["type"],
        "ratioattk": attaque["ratioattk"],
        "ratiomagie": attaque["ratiomagie"]
    }
    attaques.append(nouvelle_attaque)
    
    # Mettre à jour dans la base
    cur.execute(
        "UPDATE personnages SET attaques = %s WHERE user_id = %s",
        (Json(attaques), user_id)
    )
    conn.commit()
    return True, "Attaque apprise avec succès !"


def augmenter_stat(user_id, stat, bonus):
    """Augmente une statistique du personnage."""
    perso = get_personnage(user_id)
    
    # Vérifier que la stat existe
    if stat not in perso:
        return False, "Statistique invalide !"
    
    # Augmenter la stat
    nouvelle_valeur = perso[stat] + bonus
    
    # Cas spécial pour pv_max : on augmente aussi les pv actuels
    if stat == "pv_max":
        cur.execute(
            "UPDATE personnages SET pv_max = %s, pv = pv + %s WHERE user_id = %s",
            (nouvelle_valeur, bonus, user_id)
        )
    else:
        cur.execute(
            f"UPDATE personnages SET {stat} = %s WHERE user_id = %s",
            (nouvelle_valeur, user_id)
        )
    
    conn.commit()
    return True, f"{stat.replace('_', ' ').title()} augmentée de +{bonus} !"


class ShopView(View):
    """Vue principale du shop avec sélection par catégorie."""
    
    def __init__(self, user_id):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.shop_data = load_shop_data()
        
    @discord.ui.button(label="⚔️ Attaques", style=discord.ButtonStyle.primary, row=0)
    async def btn_attaques(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        view = ShopAttaquesView(self.user_id, self.shop_data["attaques"])
        embed = self.create_shop_embed("attaques")
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📊 Améliorations", style=discord.ButtonStyle.success, row=0)
    async def btn_stats(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        view = ShopStatsView(self.user_id, self.shop_data["objets_stats"])
        embed = self.create_shop_embed("stats")
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="💰 Mon Argent", style=discord.ButtonStyle.secondary, row=1)
    async def btn_balance(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        balance = get_balance(self.user_id)
        await interaction.response.send_message(
            f"💰 Vous avez **{balance}** pièces d'or !",
            ephemeral=True
        )
    
    @discord.ui.button(label="❌ Fermer", style=discord.ButtonStyle.danger, row=1)
    async def btn_close(self, interaction: discord.Interaction, button: Button):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        await interaction.message.delete()
    
    def create_shop_embed(self, category):
        """Crée l'embed du shop selon la catégorie."""
        balance = get_balance(self.user_id)
        
        if category == "attaques":
            embed = discord.Embed(
                title="⚔️ Shop - Attaques",
                description="Sélectionnez une attaque dans le menu déroulant ci-dessous",
                color=discord.Color.red()
            )
            
            # Afficher quelques attaques en exemple
            for atk in self.shop_data["attaques"][:3]:
                embed.add_field(
                    name=f"{atk['nom']} - {atk['prix']}💰",
                    value=f"{atk['description']}\n"
                          f"• Dégâts: {atk['degats']} ({atk['type']})\n"
                          f"• Ratios: ⚔️{atk['ratioattk']}% 🔮{atk['ratiomagie']}%",
                    inline=False
                )
            
            if len(self.shop_data["attaques"]) > 3:
                embed.add_field(
                    name="➕ Et plus encore...",
                    value=f"*{len(self.shop_data['attaques']) - 3} autres attaques disponibles*",
                    inline=False
                )
        
        else:  # stats
            embed = discord.Embed(
                title="📊 Shop - Améliorations de Stats",
                description="Sélectionnez une amélioration dans le menu déroulant ci-dessous",
                color=discord.Color.green()
            )
            
            # Afficher quelques objets en exemple
            for obj in self.shop_data["objets_stats"][:3]:
                embed.add_field(
                    name=f"{obj['emoji']} {obj['nom']} - {obj['prix']}💰",
                    value=f"{obj['description']}",
                    inline=True
                )
            
            if len(self.shop_data["objets_stats"]) > 3:
                embed.add_field(
                    name="➕ Et plus encore...",
                    value=f"*{len(self.shop_data['objets_stats']) - 3} autres objets disponibles*",
                    inline=False
                )
        
        embed.set_footer(text=f"💰 Votre argent : {balance} pièces d'or")
        return embed


class ShopAttaquesView(View):
    """Vue pour acheter des attaques."""
    
    def __init__(self, user_id, attaques):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.attaques = attaques
        
        # Créer les options du select
        options = []
        for atk in attaques:
            desc = f"{atk['prix']}💰 | {atk['degats']} dégâts ({atk['type']})"
            options.append(
                discord.SelectOption(
                    label=atk["nom"],
                    description=desc[:100],
                    value=atk["id"]
                )
            )
        
        self.select = Select(
            placeholder="Choisissez une attaque à acheter",
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
        
        # Bouton retour
        btn_back = Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary)
        btn_back.callback = self.go_back
        self.add_item(btn_back)
    
    async def on_select(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        # Trouver l'attaque sélectionnée
        atk_id = self.select.values[0]
        attaque = next(a for a in self.attaques if a["id"] == atk_id)
        
        # Vérifier l'argent
        if not remove_money(self.user_id, attaque["prix"]):
            balance = get_balance(self.user_id)
            await interaction.response.send_message(
                f"❌ Pas assez d'argent ! Il vous manque **{attaque['prix'] - balance}** pièces.",
                ephemeral=True
            )
            return
        
        # Apprendre l'attaque
        success, message = apprendre_attaque(self.user_id, attaque)
        
        if not success:
            # Rembourser si échec
            from money_db import add_money
            add_money(self.user_id, attaque["prix"])
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Succès !
        balance = get_balance(self.user_id)
        embed = discord.Embed(
            title="✅ Attaque Apprise !",
            description=f"Vous avez appris **{attaque['nom']}** !",
            color=discord.Color.green()
        )
        embed.add_field(
            name="📊 Détails",
            value=f"• Dégâts: {attaque['degats']} ({attaque['type']})\n"
                  f"• Ratio Force: {attaque['ratioattk']}%\n"
                  f"• Ratio Magie: {attaque['ratiomagie']}%",
            inline=False
        )
        embed.set_footer(text=f"💰 Argent restant : {balance} pièces")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    async def go_back(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        view = ShopView(self.user_id)
        shop_data = load_shop_data()
        embed = discord.Embed(
            title="🏪 Boutique",
            description="Bienvenue dans la boutique ! Choisissez une catégorie :",
            color=discord.Color.gold()
        )
        balance = get_balance(self.user_id)
        embed.set_footer(text=f"💰 Votre argent : {balance} pièces d'or")
        
        await interaction.response.edit_message(embed=embed, view=view)


class ShopStatsView(View):
    """Vue pour acheter des améliorations de stats."""
    
    def __init__(self, user_id, objets):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.objets = objets
        
        # Créer les options du select
        options = []
        for obj in objets:
            desc = f"{obj['prix']}💰 | {obj['description']}"
            options.append(
                discord.SelectOption(
                    label=obj["nom"],
                    description=desc[:100],
                    value=obj["id"],
                    emoji=obj["emoji"]
                )
            )
        
        self.select = Select(
            placeholder="Choisissez une amélioration à acheter",
            options=options
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
        
        # Bouton retour
        btn_back = Button(label="⬅️ Retour", style=discord.ButtonStyle.secondary)
        btn_back.callback = self.go_back
        self.add_item(btn_back)
    
    async def on_select(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        # Trouver l'objet sélectionné
        obj_id = self.select.values[0]
        objet = next(o for o in self.objets if o["id"] == obj_id)
        
        # Vérifier l'argent
        if not remove_money(self.user_id, objet["prix"]):
            balance = get_balance(self.user_id)
            await interaction.response.send_message(
                f"❌ Pas assez d'argent ! Il vous manque **{objet['prix'] - balance}** pièces.",
                ephemeral=True
            )
            return
        
        # Augmenter la stat
        success, message = augmenter_stat(self.user_id, objet["stat"], objet["bonus"])
        
        if not success:
            # Rembourser si échec
            from money_db import add_money
            add_money(self.user_id, objet["prix"])
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Succès !
        balance = get_balance(self.user_id)
        perso = get_personnage(self.user_id)
        
        embed = discord.Embed(
            title="✅ Amélioration Achetée !",
            description=f"Vous avez utilisé **{objet['nom']}** !",
            color=discord.Color.green()
        )
        
        stat_display = objet["stat"].replace("_", " ").title()
        stat_value = perso[objet["stat"]]
        
        embed.add_field(
            name="📈 Amélioration",
            value=f"{objet['emoji']} **{stat_display}**: {stat_value - objet['bonus']} → **{stat_value}** (+{objet['bonus']})",
            inline=False
        )
        embed.set_footer(text=f"💰 Argent restant : {balance} pièces")
        
        await interaction.response.send_message(embed=embed, ephemeral=False)
    
    async def go_back(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Ce n'est pas votre shop !", ephemeral=True)
            return
        
        view = ShopView(self.user_id)
        embed = discord.Embed(
            title="🏪 Boutique",
            description="Bienvenue dans la boutique ! Choisissez une catégorie :",
            color=discord.Color.gold()
        )
        balance = get_balance(self.user_id)
        embed.set_footer(text=f"💰 Votre argent : {balance} pièces d'or")
        
        await interaction.response.edit_message(embed=embed, view=view)


async def ouvrir_shop(ctx):
    """Ouvre le shop pour l'utilisateur."""
    user_id = str(ctx.author.id)
    
    # Vérifier que l'utilisateur a un personnage
    if not personnage_existe(user_id):
        await ctx.send(f"❌ {ctx.author.mention} Vous n'avez pas de personnage ! Utilisez `!creer_personnage` d'abord.")
        return
    
    view = ShopView(user_id)
    balance = get_balance(user_id)
    
    embed = discord.Embed(
        title="🏪 Boutique",
        description="Bienvenue dans la boutique ! Choisissez une catégorie :",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="⚔️ Attaques",
        value="Apprenez de nouvelles attaques puissantes !",
        inline=True
    )
    embed.add_field(
        name="📊 Améliorations",
        value="Augmentez vos statistiques !",
        inline=True
    )
    embed.set_footer(text=f"💰 Votre argent : {balance} pièces d'or")
    
    await ctx.send(embed=embed, view=view)