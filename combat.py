# combat.py
import discord
from discord.ui import View, Select
import json
import random
import asyncio

from combat_image import creer_image_combat  # doit retourner un fichier BytesIO ou chemin vers l'image


def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


def calcul_degats(attaque, attaquant, defenseur):
    """
    Calcule les dégâts d'une attaque en prenant en compte :
    - type de l'attaque (physique/magique)
    - magie de l'attaquant
    - armure ou armure magique du défenseur en %
    """
    degats = attaque["degats"]

    if attaque["type"] == "magique":
        degats += attaquant.get("magie", 0)
        degats *= (1 - defenseur.get("armure_magique", 0) / 100)
    else:
        degats *= (1 - defenseur.get("armure", 0) / 100)

    return max(1, int(degats))  # Toujours au moins 1 PV


class CombatView(View):
    def __init__(self):
        super().__init__(timeout=None)

        # Charger joueur et ennemi
        self.joueur = load_json("json/personnage.json")
        self.ennemi = load_json("json/ennemie.json")

        # Détermine qui attaque en premier
        self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]

        # Création du select pour les attaques du joueur
        options = [
            discord.SelectOption(label=a["nom"], description=f"Dégâts : {a['degats']}")
            for a in self.joueur["attaques"]
        ]
        self.select_attacks = Select(placeholder="Choisis une attaque", options=options)
        self.select_attacks.callback = self.joueur_attaque
        self.add_item(self.select_attacks)

    def pv_text(self):
        """Retourne le texte des PV"""
        return (
            f"🧑 {self.joueur['nom']} ❤️ {max(self.joueur['pv'], 0)} / {self.joueur.get('pv_max', self.joueur['pv'])} PV | "
            f"👾 {self.ennemi['nom']} ❤️ {max(self.ennemi['pv'], 0)} / {self.ennemi.get('pv_max', self.ennemi['pv'])} PV\n"
        )

    async def update_message(self, interaction, extra_text=""):
        """Met à jour le message avec l'image du combat et le texte"""
        # Générer l'image du combat
        image_combat = creer_image_combat(self.joueur, self.ennemi)
        file = discord.File(fp=image_combat, filename="combat.png")

        # Contenu texte
        content = self.pv_text()
        if extra_text:
            content += extra_text + "\n"
        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"

        # Modifier le message Discord
        await interaction.message.edit(
            content=content,
            view=self if self.tour_joueur else None,
            attachments=[file]
        )

    async def joueur_attaque(self, interaction: discord.Interaction):
        if not self.tour_joueur:
            await interaction.response.defer()
            return

        await interaction.response.defer()  # ACK interaction

        attaque = next(a for a in self.joueur["attaques"] if a["nom"] == self.select_attacks.values[0])

        # Calcul des dégâts
        degats = calcul_degats(attaque, self.joueur, self.ennemi)
        self.ennemi["pv"] -= degats

        # Victoire joueur
        if self.ennemi["pv"] <= 0:
            await self.update_message(
                interaction,
                extra_text=f"💥 **{attaque['nom']} inflige {degats} PV !**\n🏆 **Vous avez vaincu {self.ennemi['nom']} !**"
            )
            return

        # Passage au tour ennemi
        self.tour_joueur = False
        await self.update_message(interaction, extra_text=f"💥 **Vous utilisez {attaque['nom']} et infligez {degats} PV !**")

        # Lancer l'attaque ennemie
        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction: discord.Interaction):
        # Choix de l'attaque
        attaque = random.choice(self.ennemi["attaques"])
        
        # 1️⃣ Annonce de l'attaque ennemie
        await self.update_message(interaction, extra_text=f"👾 **{self.ennemi['nom']} utilise {attaque['nom']}...**")
        
      
        
        # 2️⃣ Calcul des dégâts et application
        degats = calcul_degats(attaque, self.ennemi, self.joueur)
        self.joueur["pv"] -= degats

        # Affichage des dégâts infligés
        if self.joueur["pv"] <= 0:
            # Joueur KO
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**\n💀 **Vous avez été vaincu...**"
            )
            return
        else:
            # Retour au tour du joueur
            self.tour_joueur = True
            await self.update_message(
                interaction,
                extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV avec {attaque['nom']} !**"
            )
