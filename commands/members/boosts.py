import discord
from discord.ext import commands

class UserBoostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="meuboost", aliases=["meusboosts", "myboost", "boosts"])
    async def meuboost(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        server_id = ctx.guild.id

        # Buscar as configurações de boost do servidor no MongoDB
        server_data = await self.db.servers.find_one({"server_id": server_id}) or {}
        role_boosts = server_data.get("role_boosts", {})

        active_boosts = []
        total_multiplier = 0.0

        # Verificar todos os cargos que o usuário possui
        for role in target.roles:
            role_id_str = str(role.id)
            if role_id_str in role_boosts:
                multiplier = role_boosts[role_id_str]
                active_boosts.append(f"• {role.mention} ➔ **{multiplier}x**")
                total_multiplier += multiplier

        # Título e descrições adaptados
        is_self = target == ctx.author
        title_text = "🚀 Seus Multiplicadores de Economia" if is_self else f"🚀 Multiplicadores de {target.display_name}"

        embed = discord.Embed(
            title=title_text,
            color=0xe67e22 # laranja
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)

        # Se o user nao possuir nenhum cargo com boost
        if not active_boosts:
            embed.add_field(
                name="📜 Cargos com Boost",
                value="*Nenhum cargo com multiplicador ativo equipado no momento.*",
                inline=False
            )
            embed.add_field(
                name="📊 Multiplicador Final",
                value="**1.0x** *(Ganhos padrão)*",
                inline=False
            )
            if is_self:
                embed.set_footer(text="Dica: Adquira cargos VIPs ou especiais para aumentar seus ganhos!")
        else:
            # Listagem dos cargos que dão boost
            embed.add_field(
                name="📜 Cargos Ativos",
                value="\n".join(active_boosts),
                inline=False
            )
            # Exibe o total acumulado
            embed.add_field(
                name="📊 Multiplicador Total",
                value=f"🔥 **{total_multiplier}x** de bônus em cada comando de economia!",
                inline=False
            )
            embed.set_footer(text="🐾 Mundo Animal • Economia")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserBoostCog(bot))