import random
import discord
from discord.ext import commands
from datetime import datetime, timezone

class CacarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="caçar", aliases=["cacar"])
    async def cacar(self, ctx, member: discord.Member):
        if member == ctx.author:
            return await ctx.send("❌ Você não pode caçar a si mesmo!")
            
        if member.bot:
            return await ctx.send("❌ Você não pode caçar robôs, as engrenagens não têm gosto bom.")

        server_id_str = str(ctx.guild.id)
        now = datetime.now(timezone.utc)

        # Buscar configurações de cooldown e % do servidor
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        econ_config = server_data.get("economy", {}).get("cacar", {"min_coins": 50, "max_coins": 70, "cooldown_seconds": 3600})
        
        cooldown_seconds = econ_config["cooldown_seconds"]

        # Verificar cooldown do caçador
        user_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        user_profile = user_data.get("servers", {}).get(server_id_str, {})
        last_action_at = user_profile.get("last_actions", {}).get("cacar")

        if last_action_at:
            if last_action_at.tzinfo is None:
                last_action_at = last_action_at.replace(tzinfo=timezone.utc)
            
            elapsed = (now - last_action_at).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                horas, resto = divmod(remaining, 3600)
                minutos, segundos = divmod(resto, 60)
                
                embed_cd = discord.Embed(
                    title="⏳ Fôlego Esgotado",
                    description=f"Você está exausto após sua última caçada.\nDescanse por `{horas}h {minutos}m {segundos}s` antes de caçar novamente!",
                    color=0xe74c3c
                )
                return await ctx.send(embed=embed_cd)

        # Buscar carteira do alvo
        target_data = await self.db.users.find_one({"discord_id": member.id}) or {}
        target_profile = target_data.get("servers", {}).get(server_id_str, {})
        target_wallet = target_profile.get("wallet", 0)

        if target_wallet <= 0:
            return await ctx.send(f"🦴 **{member.display_name}** é só pele e osso. Não há moedas na carteira para roubar!")

        # Calcular o valor roubado 50% ou 70% 
        percent = random.choice([econ_config["min_coins"], econ_config["max_coins"]])
        reward = int(target_wallet * (percent / 100.0))
        
        # Garantir que rouba no mínimo 1 moeda se a matemática jogar para 0
        if reward <= 0:
            reward = 1

        # Atualizar quem atacou 
        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": reward},
                "$set": {
                    f"servers.{server_id_str}.last_actions.cacar": now,
                    "updated_at": now
                },
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        # Atualizar a presa 
        await self.db.users.update_one(
            {"discord_id": member.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": -reward},
                "$set": {"updated_at": now},
                "$setOnInsert": {"created_at": now}
            },
            upsert=True
        )

        # Mensagem final
        embed = discord.Embed(
            title="🩸 Caçada Concluída!",
            description=(
                f"Você achou um animal indefeso e o finalizou, conseguindo achar **{reward} moedas** dentro de seu corpo.\n\n"
                f"{member.mention} perdeu **{reward} moedas** passivamente."
            ),
            color=0x8b0000 # Vermelho 
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Taxa de abate: {percent}%")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(CacarCog(bot))