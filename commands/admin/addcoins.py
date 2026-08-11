from datetime import datetime, timezone
import discord
from discord.ext import commands

class AdminEconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="addcoins", aliases=["darmoedas", "givecoins"])
    @commands.has_permissions(administrator=True)
    async def addcoins(self, ctx, member: discord.Member, amount: int):
        """
        Adiciona uma quantia específica de moedas na carteira de um usuário.
        Uso: d!addcoins @usuario 5000
        """
        if amount <= 0:
            return await ctx.send("❌ A quantia de moedas a ser adicionada deve ser maior que zero!")

        if member.bot:
            return await ctx.send("❌ Bots não possuem carteira neste servidor!")

        server_id_str = str(ctx.guild.id)
        now = datetime.now(timezone.utc)

        # Monta a query para incrementar a carteira e atualizar os timestamps
        update_query = {
            "$inc": {f"servers.{server_id_str}.wallet": amount},
            "$set": {"updated_at": now},
            "$setOnInsert": {
                "created_at": now,
                "discord_id": member.id
            }
        }

        # Executa o update (upsert=True garante que a conta seja criada se não existir)
        await self.db.users.update_one(
            {"discord_id": member.id},
            update_query,
            upsert=True
        )

        # Puxa o saldo atualizado apenas para mostrar no Embed
        user_data = await self.db.users.find_one({"discord_id": member.id})
        new_wallet = user_data.get("servers", {}).get(server_id_str, {}).get("wallet", 0)

        # Embed de confirmação
        embed = discord.Embed(
            title="💰 Injeção de Moedas!",
            description=(
                f"Você adicionou **{amount} moedas** na carteira de {member.mention}!\n\n"
                f"🎒 **Novo Saldo na Pata:** `{new_wallet}` moedas"
            ),
            color=0x2ecc71 # Verde de sucesso
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="🐾 Mundo Animal • Economia Admin")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminEconomyCog(bot))