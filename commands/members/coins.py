import discord
from discord.ext import commands

class CoinsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="coins", aliases=["saldo", "moedas", "money"])
    async def coins(self, ctx, member: discord.Member = None):
        # Se um membro for mencionado, define ele como alvo
        target = member or ctx.author
        server_id_str = str(ctx.guild.id)

        # Buscar dados do alvo no MongoDB
        user_data = await self.db.users.find_one({"discord_id": target.id}) or {}
        server_profile = user_data.get("servers", {}).get(server_id_str, {})
        
        wallet = server_profile.get("wallet", 0)
        bank = server_profile.get("bank", 0)
        total = wallet + bank


        formatted_wallet = await self.bot.server_controller.format_money(ctx.guild.id, wallet)
        formatted_bank = await self.bot.server_controller.format_money(ctx.guild.id, bank)
        formatted_total = await self.bot.server_controller.format_money(ctx.guild.id, total)


        is_self = target == ctx.author
        title_text = "🌿 Seus Suprimentos Acumulados" if is_self else f"🌿 Suprimentos de {target.display_name}"

        # Embed
        embed = discord.Embed(
            title=title_text,
            color=0xf1c40f # Amarelo/Dourado
        )
        embed.set_author(name=target.display_name, icon_url=target.display_avatar.url)
        
        # Colunas com os dados de carteira e banco (usando as variáveis formatadas)
        embed.add_field(name="🐾 Na Pata", value=f"**{formatted_wallet}** moedas", inline=True)
        embed.add_field(name="<:cave:1386546110092279818> Na Caverna", value=f"**{formatted_bank}** moedas", inline=True)
        
        # Separador visual
        embed.add_field(name="", value="", inline=False)
        
        embed.add_field(name="<:bone:1386546091306254386> Patrimônio Total", value=f"**{formatted_total}** moedas", inline=True)

        # Footer adaptativo (continua usando a variável int 'wallet' para a matemática)
        if is_self and wallet > 0:
            embed.set_footer(text="Dica: Guarde suas moedas na caverna (banco) para não ser caçado!")
        else:
            embed.set_footer(text="🐾 • Economia")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CoinsCog(bot))