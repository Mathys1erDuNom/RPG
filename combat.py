import discord
from discord.ui import View, Select
import json
import random
import os
from player_db import update_player
from combat_image import creer_image_combat
from player_db import get_player
from attacks_db import get_attacks
from money_db import add_balance

# ===== CONFIGURATION DES RÉGIONS =====
REGIONS_DISPONIBLES = [
    "foret",
    "desert"
]
# =====================================

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

script_dir = os.path.dirname(os.path.abspath(__file__))


def calcul_degats(attaque, attaquant, defenseur):
    """Calcule les dégâts d'une attaque en prenant en compte les ratios force/magie et les armures."""
    # Dégâts de base
    degats = attaque["degats"]
    
    # Ajouter les bonus selon les ratios
    ratio_attk = attaque.get("ratioattk", 0) / 100
    ratio_magie = attaque.get("ratiomagie", 0) / 100
    
    degats += attaquant.get("force", 0) * ratio_attk
    degats += attaquant.get("magie", 0) * ratio_magie
    
    # Appliquer la réduction d'armure selon le type d'attaque
    if attaque["type"] == "magique":
        degats *= (1 - defenseur.get("armure_magique", 0) / 100)
    elif attaque["type"] == "physique":
        degats *= (1 - defenseur.get("armure", 0) / 100)
    elif attaque["type"] == "hybride":
        # Pour les attaques hybrides, moyenne des deux armures
        reduction = (defenseur.get("armure", 0) + defenseur.get("armure_magique", 0)) / 2
        degats *= (1 - reduction / 100)
    
    return max(1, int(degats))

class CombatView(View):
    def __init__(self, user: discord.abc.User, nb_regions=3, nb_ennemis_par_region=10):
        super().__init__(timeout=None)

        self.user_id = str(user.id)
        self.joueur = get_player(self.user_id)
        print("DEBUG joueur:", self.joueur)

        if not self.joueur or not self.joueur.get("personnage_id"):
            raise ValueError(
                f"❌ Le joueur {self.user_id} n'a pas choisi de personnage."
            )
        
        self.joueur["attaques"] = get_attacks(self.user_id)
        if not self.joueur["attaques"]:
            raise ValueError("❌ Aucune attaque trouvée pour ce personnage")
        
        # Configuration des régions
        self.nb_ennemis_par_region = nb_ennemis_par_region
        self.regions_queue = random.sample(REGIONS_DISPONIBLES, k=min(nb_regions, len(REGIONS_DISPONIBLES)))
        
        # Charger la première région
        self.region = self.regions_queue.pop(0)
        self.image_fond = f"images/fond/{self.region}.png"
        
        # Charger les ennemis de la région actuelle
        region_enemies = load_json(f"json/ennemies/{self.region}.json")
        # S'assurer que c'est une liste
        if isinstance(region_enemies, dict):
            region_enemies = [region_enemies]
        elif not isinstance(region_enemies, list):
            region_enemies = list(region_enemies)
        self.ennemis_queue = random.sample(region_enemies, k=min(nb_ennemis_par_region, len(region_enemies)))
        self.ennemi = self.ennemis_queue.pop(0)  # premier ennemi

        # Qui attaque en premier
        self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]

        # Select pour attaques du joueur
        options = [
            discord.SelectOption(label=a["nom"], description=f"Dégâts : {a['degats']}")
            for a in self.joueur["attaques"]
        ]
        self.select_attacks = Select(placeholder="Choisis une attaque", options=options)
        self.select_attacks.callback = self.joueur_attaque
        self.add_item(self.select_attacks)

    def get_combat_image(self):
        """Génère et retourne l'image du combat."""

        if not self.joueur.get("image"):
            raise ValueError("❌ Le personnage n'a pas d'image")

        image_combat = creer_image_combat(self.joueur, self.ennemi, self.image_fond)

        return discord.File(fp=image_combat, filename="combat.png")

    def pv_text(self):
        """Texte des PV du joueur et de l'ennemi."""
        return (
            f"🗺️ **Région : {self.region.capitalize()}** ({len(self.ennemis_queue) + 1} ennemis restants)\n"
            f"🧑 {self.joueur['nom']} ❤️ {max(self.joueur['pv'], 0)} / {self.joueur.get('pv_max', self.joueur['pv'])} PV | "
            f"👾 {self.ennemi['nom']} ❤️ {max(self.ennemi['pv'], 0)} / {self.ennemi.get('pv_max', self.ennemi['pv'])} PV\n"
        )

    def get_initial_message_content(self):
        """Retourne le contenu du message initial avec l'image."""
        content = self.pv_text()
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"
        return content

    async def update_message(self, interaction, extra_text=""):
        """Met à jour le message Discord avec l'image du combat et le texte."""
        file = self.get_combat_image()

        content = self.pv_text()
        if extra_text:
            content += extra_text + "\n"
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"

        await interaction.message.edit(
            content=content,
            view=self if self.tour_joueur else None,
            attachments=[file]
        )

    def refresh_attack_select(self):
        self.select_attacks.options = [
            discord.SelectOption(
                label=a["nom"],
                description=f"Dégâts : {a['degats']}"
            )
            for a in self.joueur["attaques"]
        ]
    

    async def joueur_attaque(self, interaction: discord.Interaction):
        if not self.tour_joueur:
            await interaction.response.defer()
            return
        await interaction.response.defer()

        self.joueur["attaques"] = get_attacks(self.user_id)
        if not self.joueur["attaques"]:
            raise ValueError("❌ Aucune attaque trouvée pour ce personnage")

        attaque = next(a for a in self.joueur["attaques"] if a["nom"] == self.select_attacks.values[0])
        degats = calcul_degats(attaque, self.joueur, self.ennemi)
        self.ennemi["pv"] -= degats

        # Ennemi KO
        if self.ennemi["pv"] <= 0:
            if self.ennemis_queue:
                # Passer au prochain ennemi dans la même région
                self.ennemi = self.ennemis_queue.pop(0)
                self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]
                await self.update_message(
                    interaction,
                    extra_text=f"💥 **{attaque['nom']} inflige {degats} PV !**\n🏆 **Vous avez vaincu cet ennemi !**\n"
                               f"👾 **Prochain ennemi : {self.ennemi['nom']} !**"
                )
                return
            elif self.regions_queue:
                # Passer à la région suivante - OUVRIR LE SHOP
                from shop import ShopView
                
                # Sauvegarder l'état du joueur
                
                
                # Callback pour reprendre le combat après le shop
                async def reprendre_combat(shop_interaction):


                    # Recharger le joueur mis à jour
                    self.user_id = str(interaction.user.id)
                    self.joueur = get_player(self.user_id)
                    print("DEBUG joueur:", self.joueur)


                    if not self.joueur or not self.joueur.get("personnage_id"):
                        raise ValueError(
                            f"❌ Le joueur {self.user_id} n'a pas choisi de personnage."
                        )
                    

                    self.joueur["attaques"] = get_attacks(self.user_id)
                    if not self.joueur["attaques"]:
                        raise ValueError("❌ Aucune attaque trouvée pour ce personnage")
                    self.refresh_attack_select()
                    
                    # Charger la nouvelle région
                    self.region = self.regions_queue.pop(0)
                    self.image_fond = f"images/fond/{self.region}.png"
                    
                    # Charger les ennemis de la nouvelle région
                    region_enemies = load_json(f"json/ennemies/{self.region}.json")
                    # S'assurer que c'est une liste
                    if isinstance(region_enemies, dict):
                        region_enemies = [region_enemies]
                    elif not isinstance(region_enemies, list):
                        region_enemies = list(region_enemies)
                    self.ennemis_queue = random.sample(region_enemies, k=min(self.nb_ennemis_par_region, len(region_enemies)))
                    self.ennemi = self.ennemis_queue.pop(0)
                    self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]
                    
                    # Reprendre le combat
                    await self.update_message(
                        shop_interaction,
                        extra_text=f"🗺️ **Nouvelle région : {self.region.capitalize()} !**\n"
                                   f"👾 **Premier ennemi : {self.ennemi['nom']} !**"
                    )

                update_player(self.user_id, pv=self.joueur["pv"])
                # Ouvrir le shop
                shop_view = ShopView(self.joueur, reprendre_combat)
                file = discord.File(fp="images/shop.png", filename="shop.png")
                await interaction.message.edit(
                    content=shop_view.get_shop_content() + f"\n🏆 **Région {self.region.capitalize()} terminée !**\n💰 **+500 Gold de récompense !**",
                    view=shop_view,
                    attachments=[file]
                )
                
                # Donner de l'or au joueur
                add_balance(self.user_id, 500)
               
                return
            else:
                # Toutes les régions terminées
                file = discord.File(fp="images/fin/fin.png", filename="fin.png")
                await interaction.message.edit(
                    content=f"🏆 **Félicitations ! Vous avez vaincu toutes les régions !**",
                    view=None,
                    attachments=[file]
                )
                return
        update_player(self.user_id, pv=self.joueur["pv"])
        # Passage au tour de l'ennemi
        self.tour_joueur = False
        await self.update_message(interaction, extra_text=f"💥 **Vous utilisez {attaque['nom']} et infligez {degats} PV !**")
        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction: discord.Interaction):
        attaque = random.choice(self.ennemi["attaques"])
        degats = calcul_degats(attaque, self.ennemi, self.joueur)
        self.joueur["pv"] -= degats
        update_player(self.user_id, pv=self.joueur["pv"])

        if self.joueur["pv"] <= 0:
            # Joueur KO
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**\n💀 **Vous avez été vaincu...**"
            )
            return
        else:
            # Retour au joueur
            self.tour_joueur = True
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**"
            )