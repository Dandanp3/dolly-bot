import discord
from discord.ext import commands

class BoostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="addboost")
    @commands.has_permissions(administrator=True)
    async def addboost(self, ctx, role: discord.Role, multiplier: float):
        """
        Adiciona um multiplicador de ganhos (boost) a um cargo específico.
        Uso: d!addboost @Cargo 1.25
        """
        if multiplier < 0:
            return await ctx.send("❌ O multiplicador não pode ser negativo!")

        server_id = ctx.guild.id
        role_id_str = str(role.id)

        # Se o adm colocar 1.0 (ou 0), significa que está removendo o boost (multiplicador neutro)
        if multiplier <= 1.0:
            await self.db.servers.update_one(
                {"server_id": server_id},
                {"$unset": {f"role_boosts.{role_id_str}": ""}}
            )
            return await ctx.send(f"✅ O boost do cargo {role.mention} foi removido (voltou ao padrão 1.0x).")

        # Atualiza ou cria o boost no banco de dados usando o ID do cargo como chave
        await self.db.servers.update_one(
            {"server_id": server_id},
            {"$set": {f"role_boosts.{role_id_str}": multiplier}},
            upsert=True
        )

        embed = discord.Embed(
            title="🚀 Boost de Economia Configurado!",
            description=(
                f"O cargo {role.mention} agora possui um bônus ativo!\n\n"
                f"📈 **Multiplicador:** `{multiplier}x`\n"
                f"*(Membros com este cargo receberão este bônus ao usar comandos de economia)*"
            ),
            color=0xe67e22
        )
        embed.set_footer(text=f"ID do Cargo: {role.id}")
        
        await ctx.send(embed=embed)

    @commands.command(name="removeboost")
    @commands.has_permissions(administrator=True)
    async def removeboost(self, ctx, role: discord.Role):
        """
        Remove o multiplicador de ganhos (boost) de um cargo específico.
        Uso: d!removeboost @Cargo
        """
        server_id = ctx.guild.id
        role_id_str = str(role.id)

        # Remove o boost usando $unset no banco de dados
        result = await self.db.servers.update_one(
            {"server_id": server_id},
            {"$unset": {f"role_boosts.{role_id_str}": ""}}
        )

        # Verifica se o banco de dados realmente apagou algo para dar um feedback preciso
        if result.modified_count > 0:
            await ctx.send(f"✅ O boost do cargo {role.mention} foi excluído do banco de dados com sucesso!")
        else:
            await ctx.send(f"⚠️ O cargo {role.mention} não possuía nenhum boost ativo configurado.")

async def setup(bot):
    await bot.add_cog(BoostCog(bot))