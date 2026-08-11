import discord
from discord.ext import commands

class SayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="say")
    @commands.has_permissions(administrator=True)
    async def say(self, ctx, channel: discord.TextChannel, *, message: str):
        """Envia uma mensagem em um canal específico (Apenas Administradores)."""
        try:
            await ctx.message.delete() # Apaga o comando original para limpar o chat
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass
        
        await channel.send(message)

async def setup(bot):
    await bot.add_cog(SayCog(bot))