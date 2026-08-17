import discord
from discord.ext import commands

class EconomyAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="resetareconomia", aliases=["zerareconomia", "reset_economy"])
    @commands.has_permissions(administrator=True) # Apenas ADM do servidor pode utilizar
    async def resetareconomia(self, ctx: commands.Context):
        """
        Zera a carteira e o banco de TODOS os usuários cadastrados neste servidor.
        Apenas Administradores do servidor podem executar.
        """
        server_id_str = str(ctx.guild.id)

        aviso = await ctx.send("🔄 **Iniciando o reset da economia...** Aguarde um instante.")

        # Atualiza todos os usuarios
        resultado = await self.db.users.update_many(
            {f"servers.{server_id_str}": {"$exists": True}},
            {
                "$set": {
                    f"servers.{server_id_str}.wallet": 0,
                    f"servers.{server_id_str}.bank": 0
                }
            }
        )

        embed = discord.Embed(
            title="💥 Economia Resetada!",
            description=f"A carteira e a conta bancária de **todos** os usuários foram zeradas no servidor **{ctx.guild.name}**.",
            color=0xe74c3c # Cor vermelha para indicar alteração crítica
        )
        embed.add_field(
            name="📊 Total de Usuários Afetados", 
            value=f"`{resultado.modified_count}` contas foram resetadas.", 
            inline=False
        )
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text=f"Executado por: {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

        await aviso.edit(content=None, embed=embed)

    @resetareconomia.error
    async def resetareconomia_error(self, ctx, error):
        """Tratamento de erro caso um membro sem permissão de ADM tente usar o comando"""
        if isinstance(error, commands.MissingPermissions):
            embed_error = discord.Embed(
                title="🚫 Acesso Negado",
                description="Apenas **Administradores** têm permissão para resetar a economia do servidor!",
                color=0xff0000
            )
            await ctx.send(embed=embed_error)

async def setup(bot):
    await bot.add_cog(EconomyAdminCog(bot))
