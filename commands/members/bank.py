import discord
from discord.ext import commands
from datetime import datetime, timezone

class BankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def get_user_balances(self, discord_id: int, server_id: str):
        user_data = await self.db.users.find_one({"discord_id": discord_id}) or {}
        server_profile = user_data.get("servers", {}).get(server_id, {})
        wallet = server_profile.get("wallet", 0)
        bank = server_profile.get("bank", 0)
        return wallet, bank

    def parse_amount(self, valor: str, max_amount: int) -> int:
        valor = valor.lower()
        if valor in ["all", "tudo"]:
            return max_amount
        try:
            val = int(valor)
            if val <= 0:
                return -1 
            return val
        except ValueError:
            return -2 

    @commands.command(name="depositar", aliases=["dep"])
    async def depositar(self, ctx, valor: str):
        server_id_str = str(ctx.guild.id)
        wallet, bank = await self.get_user_balances(ctx.author.id, server_id_str)
        
        if wallet <= 0:
            return await ctx.send("❌ Você não tem moedas na sua carteira para depositar!")

        amount = self.parse_amount(valor, wallet)
        
        if amount == -1:
            return await ctx.send("❌ Você deve informar um valor maior que zero!")
        if amount == -2:
            return await ctx.send("❌ Valor inválido! Use um número, `all` ou `tudo`.")
        
        if amount > wallet:
            # Formatamos o valor da carteira apenas para exibir o erro bonitinho
            formatted_wallet = await self.bot.server_controller.format_money(ctx.guild.id, wallet)
            return await ctx.send(f"❌ Você não tem moedas suficientes! Sua carteira atual: **{formatted_wallet} moedas**.")

        now = datetime.now(timezone.utc)
        
        # Atualiza banco (+amount) e carteira (-amount) com os valores inteiros reais
        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {
                    f"servers.{server_id_str}.wallet": -amount,
                    f"servers.{server_id_str}.bank": amount
                },
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        
        # ---------------------------------------------------------
        # NOVIDADE AQUI: Formatamos o valor exato que foi depositado
        # ---------------------------------------------------------
        formatted_amount = await self.bot.server_controller.format_money(ctx.guild.id, amount)
        # ---------------------------------------------------------

        embed = discord.Embed(
            title="<:cave:1386546110092279818> Depósito Realizado!",
            description=f"Você guardou **{formatted_amount} moedas** com segurança na sua caverna (banco)!",
            color=0x2ecc71
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="sacar")
    async def sacar(self, ctx, valor: str):
        server_id_str = str(ctx.guild.id)
        wallet, bank = await self.get_user_balances(ctx.author.id, server_id_str)
        
        if bank <= 0:
            return await ctx.send("❌ O seu banco está completamente vazio!")

        amount = self.parse_amount(valor, bank)
        
        if amount == -1:
            return await ctx.send("❌ Você deve informar um valor maior que zero!")
        if amount == -2:
            return await ctx.send("❌ Valor inválido! Use um número, `all` ou `tudo`.")
        
        if amount > bank:
            # Formatamos o valor do banco apenas para exibir o erro bonitinho
            formatted_bank = await self.bot.server_controller.format_money(ctx.guild.id, bank)
            return await ctx.send(f"❌ Você não tem tudo isso guardado! Seu saldo no banco é: **{formatted_bank} moedas**.")

        now = datetime.now(timezone.utc)
        
        # Atualiza banco (-amount) e carteira (+amount) com os valores inteiros reais
        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {
                    f"servers.{server_id_str}.bank": -amount,
                    f"servers.{server_id_str}.wallet": amount
                },
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )
        
        # ---------------------------------------------------------
        # NOVIDADE AQUI: Formatamos o valor exato que foi sacado
        # ---------------------------------------------------------
        formatted_amount = await self.bot.server_controller.format_money(ctx.guild.id, amount)
        # ---------------------------------------------------------

        embed = discord.Embed(
            title="<:bone:1386546091306254386> Saque Realizado!",
            description=f"Você retirou **{formatted_amount} moedas** do seu esconderijo e colocou na carteira.",
            color=0xf1c40f
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BankCog(bot))