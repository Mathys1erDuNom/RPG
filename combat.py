# combat.py
import discord
from discord.ui import View, Select
import json
import random
import asyncio


def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)


class CombatView(View):
    def __init__(self):
        super().__init__(timeout=None)

        self.joueur = load_json("json/personnage.json")
        self.ennemi = load_json("json/ennemie.json")

        # Détermine qui attaque en premier
        self.tour_joueur = self.joueur["vitesse"] >= self.ennemi["vitesse"]

        # Création du select pour les attaques
        options = [
            discord.SelectOption(
                label=a["nom"],
                description=f"Dégâts : {a['degats']}"
            )
            for a in self.joueur["attaques"]
        ]

        self.select_attacks = Select(
            placeholder="Choisis une attaque",
            options=options
        )
        self.select_attacks.callback = self.joueur_attaque
        self.add_item(self.select_attacks)

    def pv_text(self):
        return (
            f"🧑 {self.joueur['nom']} ❤️ {max(self.joueur['pv'], 0)} PV | "
            f"👾 {self.ennemi['nom']} ❤️ {max(self.ennemi['pv'], 0)} PV\n"
        )

    async def update_message(self, interaction, extra_text=""):
        content = self.pv_text()
        if extra_text:
            content += extra_text + "\n"

        content += "🟢 **C'est votre tour !**" if self.tour_joueur else "🔴 **Tour de l'ennemi...**"

        await interaction.message.edit(
            content=content,
            view=self if self.tour_joueur else None
        )

    async def joueur_attaque(self, interaction: discord.Interaction):
        if not self.tour_joueur:
            await interaction.response.defer()
            return

        # ACK interaction
        await interaction.response.defer()

        attaque = next(
            a for a in self.joueur["attaques"]
            if a["nom"] == self.select_attacks.values[0]
        )

        degats = attaque["degats"]
        self.ennemi["pv"] -= degats

        # Victoire joueur
        if self.ennemi["pv"] <= 0:
            await interaction.message.edit(
                content=(
                    self.pv_text() +
                    f"💥 **{attaque['nom']} inflige {degats} PV !**\n"
                    f"🏆 **Vous avez vaincu {self.ennemi['nom']} !**"
                ),
                view=None
            )
            return

        # Passage au tour ennemi
        self.tour_joueur = False
        await self.update_message(
            interaction,
            extra_text=f"💥 **Vous utilisez {attaque['nom']} et infligez {degats} PV !**"
        )

        await self.ennemi_attaque(interaction)

    async def ennemi_attaque(self, interaction: discord.Interaction):
        attaque = random.choice(self.ennemi["attaques"])
        degats = attaque["degats"]

        # Annonce attaque ennemie
        await interaction.message.edit(
            content=(
                self.pv_text() +
                f"👾 **{self.ennemi['nom']} utilise {attaque['nom']}...**"
            ),
            view=None
        )

        # Pause
        await asyncio.sleep(1.5)

        # Application des dégâts
        self.joueur["pv"] -= degats

        # Défaite joueur
        if self.joueur["pv"] <= 0:
            await interaction.message.edit(
                content=(
                    self.pv_text() +
                    f"💥 **{self.ennemi['nom']} inflige {degats} PV !**\n"
                    f"💀 **Vous avez été vaincu...**"
                ),
                view=None
            )
            return

        # Retour au joueur
        self.tour_joueur = True
        await self.update_message(
            interaction,
            extra_text=f"💥 **{self.ennemi['nom']} inflige {degats} PV !**"
        )
