import discord
from discord.ui import View, Button, Select
import json
import os

def load_shop_items(region):
    """Charge les items disponibles dans la boutique d'une région."""
    try:
        with open(f"json/shops/{region}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Si pas de shop spécifique, charger le shop par défaut
        with open("json/shops/default.json", "r", encoding="utf-8") as f:
            return json.load(f)


class ShopView(View):
    """Vue pour le shop de fin de région."""
    
    def __init__(self, user_id, region, joueur, on_continue_callback):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.region = region
        self.joueur = joueur
        self.on_continue_callback = on_continue_callback
        self.gold = 100  # Or gagné à la fin de la région
        self.shop_message = None  # Référence au message du shop
        self.channel = None  # Référence au canal
        
        # Charger les items du shop
        self.shop_items = load_shop_items(region)
        
        # Créer le select pour les items
        self.create_shop_select()
        
        # Bouton pour continuer
        self.continue_button = Button(
            label="➡️ Continuer l'aventure",
            style=discord.ButtonStyle.success,
            row=1
        )
        self.continue_button.callback = self.continue_adventure
        self.add_item(self.continue_button)
    
    def create_shop_select(self):
        """Crée le menu de sélection des items."""
        options = []
        
        for item in self.shop_items:
            # Créer la description de l'item
            description = f"💰 {item['prix']}G"
            if item['type'] == 'attaque':
                description += f" | ⚔️ {item['data']['degats']} dégâts"
            elif item['type'] == 'stat':
                stat_names = {
                    'force': '⚔️ Force',
                    'magie': '🔮 Magie',
                    'armure': '🛡️ Armure',
                    'armure_magique': '✨ Armure Mag',
                    'vitesse': '⚡ Vitesse',
                    'pv_max': '💚 PV Max'
                }
                stat = item['data']['stat']
                value = item['data']['value']
                description += f" | {stat_names.get(stat, stat)} +{value}"
            
            options.append(
                discord.SelectOption(
                    label=item['nom'],
                    description=description[:100],  # Discord limite à 100 caractères
                    value=str(item['id']),
                    emoji=item.get('emoji', '🎁')
                )
            )
        
        self.shop_select = Select(
            placeholder="🛒 Choisir un item à acheter",
            options=options,
            row=0
        )
        self.shop_select.callback = self.acheter_item
        self.add_item(self.shop_select)
    
    def get_shop_embed(self):
        """Crée l'embed du shop."""
        embed = discord.Embed(
            title=f"🏪 Boutique de {self.region.capitalize()}",
            description=f"Vous avez terminé la région **{self.region.capitalize()}** !\n"
                       f"Vous avez gagné **{self.gold} 💰 Or**\n\n"
                       f"Choisissez des améliorations avant de continuer :",
            color=discord.Color.gold()
        )
        
        # Ajouter les items disponibles
        for item in self.shop_items:
            if item['type'] == 'attaque':
                atk = item['data']
                value = (
                    f"💰 Prix : **{item['prix']}G**\n"
                    f"⚔️ Dégâts : **{atk['degats']}**\n"
                    f"🎯 Type : **{atk['type']}**\n"
                    f"📊 Ratio Force : **{atk.get('ratioattk', 0)}%** | "
                    f"Magie : **{atk.get('ratiomagie', 0)}%**"
                )
            elif item['type'] == 'stat':
                stat_display = {
                    'force': '⚔️ Force',
                    'magie': '🔮 Magie',
                    'armure': '🛡️ Armure',
                    'armure_magique': '✨ Armure Magique',
                    'vitesse': '⚡ Vitesse',
                    'pv_max': '💚 PV Maximum'
                }
                stat = item['data']['stat']
                value = (
                    f"💰 Prix : **{item['prix']}G**\n"
                    f"{stat_display.get(stat, stat)} : **+{item['data']['value']}**"
                )
            
            embed.add_field(
                name=f"{item.get('emoji', '🎁')} {item['nom']}",
                value=value,
                inline=True
            )
        
        # Ajouter les stats actuelles du joueur
        embed.add_field(
            name="📊 Vos statistiques",
            value=(
                f"💚 PV : **{self.joueur['pv']}/{self.joueur['pv_max']}**\n"
                f"⚔️ Force : **{self.joueur['force']}**\n"
                f"🔮 Magie : **{self.joueur['magie']}**\n"
                f"🛡️ Armure : **{self.joueur['armure']}**\n"
                f"✨ Armure Mag : **{self.joueur['armure_magique']}**\n"
                f"⚡ Vitesse : **{self.joueur['vitesse']}**"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"💰 Or restant : {self.gold}G")
        
        return embed
    
    async def acheter_item(self, interaction: discord.Interaction):
        """Gère l'achat d'un item."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas votre boutique !",
                ephemeral=True
            )
            return
        
        # Trouver l'item sélectionné
        item_id = int(self.shop_select.values[0])
        item = next((i for i in self.shop_items if i['id'] == item_id), None)
        
        if not item:
            await interaction.response.send_message(
                "❌ Item introuvable !",
                ephemeral=True
            )
            return
        
        # Vérifier si le joueur a assez d'or
        if self.gold < item['prix']:
            await interaction.response.send_message(
                f"❌ Pas assez d'or ! Il vous faut **{item['prix']}G** mais vous n'avez que **{self.gold}G**.",
                ephemeral=True
            )
            return
        
        # Acheter l'item
        self.gold -= item['prix']
        
        # Appliquer l'effet de l'item
        if item['type'] == 'attaque':
            # Ajouter la nouvelle attaque
            self.joueur['attaques'].append(item['data'])
            message = f"✅ Vous avez appris **{item['nom']}** !"
        
        elif item['type'] == 'stat':
            # Augmenter la stat
            stat = item['data']['stat']
            value = item['data']['value']
            self.joueur[stat] += value
            
            # Si c'est pv_max, restaurer aussi les PV
            if stat == 'pv_max':
                self.joueur['pv'] += value
            
            stat_names = {
                'force': 'Force',
                'magie': 'Magie',
                'armure': 'Armure',
                'armure_magique': 'Armure Magique',
                'vitesse': 'Vitesse',
                'pv_max': 'PV Maximum'
            }
            message = f"✅ Votre **{stat_names.get(stat, stat)}** augmente de **+{value}** !"
        
        # Retirer l'item acheté de la liste
        self.shop_items.remove(item)
        
        # Recréer le select sans l'item acheté
        self.remove_item(self.shop_select)
        if self.shop_items:  # S'il reste des items
            self.create_shop_select()
        
        # Mettre à jour l'affichage
        await interaction.response.edit_message(
            content=message,
            embed=self.get_shop_embed(),
            view=self
        )
        
        # Mettre à jour la référence du message
        self.shop_message = await interaction.original_response()
    
    async def continue_adventure(self, interaction: discord.Interaction):
        """Continue l'aventure vers la prochaine région."""
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Ce n'est pas votre aventure !",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        # Supprimer le message du shop
        if self.shop_message:
            await self.shop_message.delete()
        
        # Appeler le callback pour continuer le combat
        await self.on_continue_callback(interaction, self.channel)


async def afficher_shop(interaction, user_id, region, joueur, on_continue_callback):
    """Affiche le shop de fin de région."""
    print(f"DEBUG SHOP: Début afficher_shop pour région={region}, user_id={user_id}")
    
    try:
        print("DEBUG SHOP: Création de ShopView...")
        view = ShopView(user_id, region, joueur, on_continue_callback)
        view.channel = interaction.channel  # Garder la référence du canal
        print(f"DEBUG SHOP: ShopView créée, channel={view.channel}")
        
        # Essayer de charger une image de fond pour le shop
        shop_image_path = f"images/shops/{region}.png"
        file = None
        if os.path.exists(shop_image_path):
            print(f"DEBUG SHOP: Image trouvée: {shop_image_path}")
            file = discord.File(shop_image_path, filename="shop.png")
        else:
            print(f"DEBUG SHOP: Pas d'image pour {shop_image_path}")
        
        print("DEBUG SHOP: Création de l'embed...")
        embed = view.get_shop_embed()
        print(f"DEBUG SHOP: Embed créé: {embed.title}")
        
        # Envoyer un NOUVEAU message pour le shop
        print("DEBUG SHOP: Envoi du message shop...")
        if file:
            view.shop_message = await interaction.channel.send(
                content="",
                embed=embed,
                view=view,
                file=file
            )
        else:
            view.shop_message = await interaction.channel.send(
                content="",
                embed=embed,
                view=view
            )
        print(f"DEBUG SHOP: Message shop envoyé! ID={view.shop_message.id}")
        
    except Exception as e:
        print(f"❌ ERREUR DANS AFFICHER_SHOP: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise