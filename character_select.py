# character_select.py
import json
import discord
from discord.ui import View, Button
from player_db import update_player

def load_personnages():
    with open("json/personnages.json", "r", encoding="utf-8") as f:
        return json.load(f)

class CharacterSelectView(View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user
        self.personnages = load_personnages()

        for perso in self.personnages:
            self.add_item(CharacterButton(perso, user))


class CharacterButton(Button):
    def __init__(self, perso, user):
        super().__init__(
            label=perso["nom"],
            style=discord.ButtonStyle.primary
        )
        self.perso = perso
        self.user = user

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Ce n'est pas ton choix.", ephemeral=True)
            return

        # Sauvegarder le personnage choisi
        update_player(
            str(self.user.id),
            personnage_id=self.perso["id"],
            nom=self.perso["nom"],
            pv=self.perso["pv"],
            pv_max=self.perso["pv_max"],
            force=self.perso["force"],
            magie=self.perso["magie"],
            armure=self.perso["armure"],
            armure_magique=self.perso["armure_magique"],
            vitesse=self.perso["vitesse"],
            image=self.perso["image"]
        )

        await interaction.response.send_message(
            f"✅ **{self.perso['nom']} sélectionné !**\nTu peux lancer le combat.",
            ephemeral=True
        )
