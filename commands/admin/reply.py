import discord
from discord.ext import commands

class ReplyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="r")
    async def reply(self, ctx, message_id: int, *, message: str):
        """Responde a uma mensagem específica informando o ID dela no chat atual."""
        try:
            target_message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("❌ Mensagem não encontrada neste canal! Verifique se o ID está correto.")
        except discord.HTTPException:
            return await ctx.send("❌ ID de mensagem inválido.")

        # Tenta apagar a mensagem do comando para manter a imersão limpa
        try:
            await ctx.message.delete()
        except Exception:
            pass

        # Responde marcando a mensagem de destino
        await target_message.reply(message)

async def setup(bot):
    await bot.add_cog(ReplyCog(bot))