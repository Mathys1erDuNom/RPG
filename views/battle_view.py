import discord
from discord.ui import View, Button
from game.combat_logic import attack

class BattleView(View):
    def __init__(self, battle):
        super().__init__(timeout=300)
        self.battle = battle

    @discord.ui.button(label="⚔️ Attaquer", style=discord.ButtonStyle.danger)
    async def attack_btn(self, interaction: discord.Interaction, button: Button):
        damage = attack(self.battle["current"], self.battle["enemy"])
        await interaction.response.send_message(
            f"💥 {interaction.user.mention} inflige **{damage} dégâts** !",
            ephemeral=False
        )
