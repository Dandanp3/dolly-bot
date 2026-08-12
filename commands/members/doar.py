from datetime import datetime, timezone
import discord
from discord.ext import commands

class TransferCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="doar", aliases=["pay", "transferir"])
    async def doar(self, ctx, member: discord.Member, amount: int):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode doar moedas para si mesmo!")

        if member.bot:
            return await ctx.send("❌ Você não pode doar moedas para um bot!")

        if amount <= 0:
            return await ctx.send("❌ A quantia para doação precisa ser maior que zero!")

        server_id_str = str(ctx.guild.id)
        now = datetime.now(timezone.utc)

        author_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        author_wallet = author_data.get("servers", {}).get(server_id_str, {}).get("wallet", 0)

        if author_wallet < amount:
            return await ctx.send(
                f"❌ Você não tem moedas suficientes na carteira para doação!\n"
                f"• Sua carteira atual: **{author_wallet}** moedas\n"
                f"• Tentou doar: **{amount}** moedas"
            )

        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": -amount},
                "$set": {"updated_at": now}
            }
        )
        await self.db.users.update_one(
            {"discord_id": member.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": amount},
                "$set": {"updated_at": now},
                "$setOnInsert": {
                    "created_at": now,
                    "discord_id": member.id
                }
            },
            upsert=True
        )
        embed = discord.Embed(
            title="🎁 Doação Realizada!",
            description=(
                f"Você transferiu **{amount} moedas** para {member.mention}!\n\n"
                f"<:bone:1386546091306254386> **Saldo restante na sua carteira:** {author_wallet - amount} moedas"
            ),
            color=0x2ecc71
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="🐾 Mundo Animal • Economia")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TransferCog(bot))