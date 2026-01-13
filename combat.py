import discord
from discord.ui import View, Select
import json
import random
import os

from combat_image import creer_image_combat

# ===== CONFIGURATION DES RÉGIONS =====
REGIONS_DISPONIBLES = [
    "foret",
    "desert"
]
# =====================================

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

script_dir = os.path.dirname(os.path.abspath(__file__))
personnage = load_json(os.path.join(script_dir, "json/personnage.json"))

def calcul_degats(attaque, attaquant, defenseur):
    """Calcule les dégâts d'une attaque en prenant en compte physique/magique et armures."""
    degats = attaque["degats"]
    if attaque["type"] == "magique":
        degats += attaquant.get("magie", 0)
        degats *= (1 - defenseur.get("armure_magique", 0) / 100)
    else:
        degats *= (1 - defenseur.get("armure", 0) / 100)
    return max(1, int(degats))

class CombatView(View):
    def __init__(self, nb_regions=3, nb_ennemis_par_region=10):
        super().__init__(timeout=None)

        # Charger joueur
        self.joueur = load_json("json/personnage.json")
        
        # Configuration des régions
        self.nb_ennemis_par_region = nb_ennemis_par_region
        self.regions_queue = random.sample(REGIONS_DISPONIBLES, k=min(nb_regions, len(REGIONS_DISPONIBLES)))
        
        # Charger la première région
        self.region = self.regions_queue.pop(0)
        self.image_fond = f"images/fond/{self.region}.png"
        
        # Charger les ennemis de la région actuelle
        region_enemies = load_json(f"json/ennemies/{self.region}.json")
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

    def pv_text(self):
        """Texte des PV du joueur et de l'ennemi."""
        return (
            f"🗺️ **Région : {self.region.capitalize()}** ({len(self.ennemis_queue) + 1} ennemis restants)\n"
            f"🧑 {self.joueur['nom']} ❤️ {max(self.joueur['pv'], 0)} / {self.joueur.get('pv_max', self.joueur['pv'])} PV | "
            f"👾 {self.ennemi['nom']} ❤️ {max(self.ennemi['pv'], 0)} / {self.ennemi.get('pv_max', self.ennemi['pv'])} PV\n"
        )

    async def update_message(self, interaction, extra_text=""):
        """Met à jour le message Discord avec l'image du combat et le texte."""
        image_combat = creer_image_combat(self.joueur, self.ennemi, self.image_fond)
        file = discord.File(fp=image_combat, filename="combat.png")

        content = self.pv_text()
        if extra_text:
            content += extra_text + "\n"
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"

        await interaction.message.edit(
            content=content,
            view=self if self.tour_joueur else None,
            attachments=[file]
        )

    async def joueur_attaque(self, interaction: discord.Interaction):
        if not self.tour_joueur:
            await interaction.response.defer()
            return
        await interaction.response.defer()

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
                # Passer à la région suivante
                self.region = self.regions_queue.pop(0)
                self.image_fond = f"images/fond/{self.region}.png"
                
                # Charger les ennemis de la nouvelle région
                region_enemies = load_json(f"json/ennemies/{self.region}.json")
                self.ennemis_queue = random.sample(region_enemies, k=min(self.nb_ennemis_par_region, len(region_enemies)))
                self.ennemi = self.ennemis_queue.pop(0)
                self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]
                
                await self.update_message(
                    interaction,
                    extra_text=f"💥 **{attaque['nom']} inflige {degats} PV !**\n🏆 **Région terminée !**\n"
                               f"🗺️ **Nouvelle région : {self.region.capitalize()} !**\n"
                               f"👾 **Premier ennemi : {self.ennemi['nom']} !**"
                )
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

        # Passage au tour de l'ennemi
        self.tour_joueur = False
        await self.update_message(interaction, extra_text=f"💥 **Vous utilisez {attaque['nom']} et infligez {degats} PV !**")
        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction: discord.Interaction):
        attaque = random.choice(self.ennemi["attaques"])
        degats = calcul_degats(attaque, self.ennemi, self.joueur)
        self.joueur["pv"] -= degats

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