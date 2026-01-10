import discord
from discord.ext import commands
from views.battle_view import BattleView

def setup_fight(bot):

    @bot.command()
    async def fight(ctx, opponent: discord.Member):
        if opponent.bot:
            await ctx.send("❌ Impossible de combattre un bot.")
            return

        battle = {
            "current": {"hp": 30, "atk": 8, "def": 4},
            "enemy": {"hp": 30, "atk": 7, "def": 5}
        }

        embed = discord.Embed(
            title="⚔️ Combat lancé !",
            description=f"{ctx.author.mention} vs {opponent.mention}",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed, view=BattleView(battle))
