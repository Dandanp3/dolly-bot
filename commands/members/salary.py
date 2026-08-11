import discord
from discord.ext import commands

class UserSalaryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="meusalario", aliases=["meussalarios", "mysalary", "salarios"])
    async def meusalario(self, ctx, member: discord.Member = None):
        """
        Exibe todos os cargos com salários ativos do usuário, o valor pago e o intervalo de horas.
        Uso: d!meusalario ou d!meusalario @usuario
        """
        target = member or ctx.author
        server_id = ctx.guild.id

        # Buscar as configurações de salário do servidor no MongoDB
        server_data = await self.db.servers.find_one({"server_id": server_id}) or {}
        role_salaries = server_data.get("role_salaries", {})

        active_salaries = []

        # Verificar todos os cargos que o usuário possui no servidor
        for role in target.roles:
            role_id_str = str(role.id)
            if role_id_str in role_salaries:
                salary_info = role_salaries[role_id_str]
                amount = salary_info.get("amount", 0)
                hours = salary_info.get("interval_hours", 0)
                active_salaries.append(
                    f"• {role.mention} ➔ **{amount} moedas** a cada `{hours}h`"
                )

        # Título e descrições adaptados de acordo com o alvo
        is_self = target == ctx.author
        title_text = "💼 Seus Salários Ativos" if is_self else f"💼 Salários de {target.display_name}"

        embed = discord.Embed(
            title=title_text,
            color=0x2ecc71 # Verde
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)

        # Se o usuário não possuir nenhum cargo com salário
        if not active_salaries:
            embed.add_field(
                name="📜 Cargos com Salário",
                value="*Nenhum cargo com salário ativo equipado no momento.*",
                inline=False
            )
            if is_self:
                embed.set_footer(text="Dica: Adquira cargos da staff ou especiais para receber pagamentos!")
        else:
            # Listagem dos cargos e seus respectivos valores e horários
            embed.add_field(
                name="📜 Pagamentos Programados",
                value="\n".join(active_salaries),
                inline=False
            )
            embed.set_footer(text="ℹ️ Lembre-se: os salários caem direto na sua caverna (banco)!")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(UserSalaryCog(bot))