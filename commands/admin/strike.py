import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta

class StrikeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Puxando a conexão do MongoDB injetada no bot

    @commands.command(name="strike")
    @commands.has_permissions(manage_roles=True)
    async def apply_strike(self, ctx, member: discord.Member, duration_hours: int, *, reason: str):
        """Aplica um strike a um usuário, remove o cargo de verificado e salva no banco."""
        server_id_str = str(ctx.guild.id) # O model usa string como chave para o dict de servidores

        # 1. Buscar configurações de cargo do servidor
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id})
        
        if not server_data or not server_data.get("strike_role_id"):
            return await ctx.send("❌ O cargo de Strike não está configurado neste servidor! Use `!setrole strike @cargo`.")

        strike_role = ctx.guild.get_role(server_data["strike_role_id"])
        verified_role = ctx.guild.get_role(server_data.get("verified_role_id")) if server_data.get("verified_role_id") else None

        if not strike_role:
            return await ctx.send("❌ O cargo de Strike configurado no banco não existe mais no Discord.")

        # 2. Atualizar os cargos do membro
        try:
            if strike_role not in member.roles:
                await member.add_roles(strike_role, reason=f"Strike aplicado por {ctx.author}: {reason}")
            
            if verified_role and verified_role in member.roles:
                await member.remove_roles(verified_role, reason="Usuário recebeu um Strike")
        except discord.Forbidden:
            return await ctx.send("❌ Não tenho permissão para alterar os cargos. Verifique a ordem dos cargos nas configurações do servidor!")

        # 3. Preparar dados para o banco de dados
        expires_at = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
        
        strike_entry = {
            "reason": reason,
            "duration_hours": duration_hours,
            "applied_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
            "staff_id": ctx.author.id
        }

        # 4. Atualizar (ou criar) o documento do usuário
        update_query = {
            "$set": {
                f"servers.{server_id_str}.has_strike": True,
                f"servers.{server_id_str}.strike_expires_at": expires_at,
                "updated_at": datetime.now(timezone.utc)
            },
            "$inc": {
                f"servers.{server_id_str}.strike_count": 1
            },
            "$push": {
                f"servers.{server_id_str}.strike_history": strike_entry
            },
            "$setOnInsert": {
                "created_at": datetime.now(timezone.utc),
                f"servers.{server_id_str}.coins": 0 # Inicializa coins se for usuário novo
            }
        }
        
        await self.db.users.update_one(
            {"discord_id": member.id}, 
            update_query, 
            upsert=True
        )

        await ctx.send(f"⚠️ **Strike Aplicado!**\nO usuário {member.mention} recebeu um strike de `{duration_hours}h`.\n**Motivo:** {reason}\n*O cargo de verificado foi removido.*")

    @commands.command(name="unstrike")
    @commands.has_permissions(manage_roles=True)
    async def remove_strike(self, ctx, member: discord.Member):
        """Remove o strike de um usuário antes do prazo e devolve o cargo de verificado."""
        server_id_str = str(ctx.guild.id)
        
        # 1. Buscar configurações de cargo do servidor
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id})
        if not server_data:
            return await ctx.send("❌ Servidor não configurado no banco de dados.")

        strike_role = ctx.guild.get_role(server_data.get("strike_role_id"))
        verified_role = ctx.guild.get_role(server_data.get("verified_role_id"))

        # 2. Atualizar os cargos do membro
        try:
            if strike_role and strike_role in member.roles:
                await member.remove_roles(strike_role, reason=f"Strike removido por {ctx.author}")
            
            if verified_role and verified_role not in member.roles:
                await member.add_roles(verified_role, reason="Strike removido, restaurando verificação")
        except discord.Forbidden:
            return await ctx.send("❌ Não tenho permissão para alterar os cargos deste usuário.")

        # 3. Atualizar o banco de dados
        await self.db.users.update_one(
            {"discord_id": member.id},
            {"$set": {
                f"servers.{server_id_str}.has_strike": False,
                f"servers.{server_id_str}.strike_expires_at": None,
                "updated_at": datetime.now(timezone.utc)
            }}
        )

        await ctx.send(f"✅ **Strike Removido!** O usuário {member.mention} teve o strike perdoado e o cargo de verificado restaurado.")

async def setup(bot):
    await bot.add_cog(StrikeCog(bot))