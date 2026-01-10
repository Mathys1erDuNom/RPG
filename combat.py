# combat.py
import discord
from discord.ui import View, Select
import json
import random

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

class CombatView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.joueur = load_json("json/personnage.json")
        self.ennemi = load_json("json/ennemie.json")

        # Détermine qui attaque en premier
        self.tour_joueur = True if self.joueur["vitesse"] >= self.ennemi["vitesse"] else False

        # Création du select pour les attaques
        options = [discord.SelectOption(label=a["nom"], description=f"Dégâts: {a['degats']}") for a in self.joueur["attaques"]]
        self.select_attacks = Select(placeholder="Choisis une attaque", options=options)
        self.select_attacks.callback = self.joueur_attaque
        self.add_item(self.select_attacks)

    async def update_message(self, interaction, content=None):
        if not content:
            content = f"🧑 {self.joueur['nom']} PV: {self.joueur['pv']} | 👾 {self.ennemi['nom']} PV: {self.ennemi['pv']}\n"
            content += "C'est votre tour !" if self.tour_joueur else "C'est au tour de l'ennemi..."
        await interaction.message.edit(content=content, view=self)

    async def joueur_attaque(self, interaction):
        if not self.tour_joueur:
            await interaction.response.defer()
            return

        # Choix attaque
        attaque = next(a for a in self.joueur["attaques"] if a["nom"] == self.select_attacks.values[0])
        self.ennemi["pv"] -= attaque["degats"]

        # Vérifie victoire
        if self.ennemi["pv"] <= 0:
            await interaction.response.edit_message(content=f"🏆 Vous avez vaincu {self.ennemi['nom']} !", view=None)
            return

        self.tour_joueur = False
        await self.update_message(interaction)

        # Ennemi attaque automatiquement
        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction):
        attaque = random.choice(self.ennemi["attaques"])
        self.joueur["pv"] -= attaque["degats"]

        # Vérifie défaite
        if self.joueur["pv"] <= 0:
            await interaction.message.edit(content=f"💀 Vous avez été vaincu par {self.ennemi['nom']}...", view=None)
            return

        self.tour_joueur = True
        await self.update_message(interaction)
