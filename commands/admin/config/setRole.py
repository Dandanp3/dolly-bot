import discord
from discord.ext import commands

class SetRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db  # Puxando a conexão do MongoDB injetada no bot

    @commands.command(name="setrole")
    @commands.has_permissions(administrator=True)
    async def set_role(self, ctx, tipo: str, role: discord.Role):
        """Configura os cargos de verificado e strike no servidor."""
        tipo = tipo.lower()
        
        # Validar o tipo de cargo
        if tipo not in ["verificado", "strike"]:
            return await ctx.send("❌ Tipo inválido! Use apenas: `verificado` ou `strike`.")

        # Atualizar a configuração no banco de dados (coleção 'servers')
        field_name = f"{tipo}_role_id"
        
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$set": {field_name: role.id}},
            upsert=True # Cria o documento do servidor caso não exista
        )
        
        await ctx.send(f"✅ O cargo para **{tipo.capitalize()}** foi configurado para {role.mention} com sucesso!")

async def setup(bot):
    await bot.add_cog(SetRole(bot))