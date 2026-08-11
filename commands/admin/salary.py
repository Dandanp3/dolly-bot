import discord
from discord.ext import commands

class SalaryAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="addsalario")
    @commands.has_permissions(administrator=True)
    async def addsalario(self, ctx, role: discord.Role, amount: int, interval_str: str):
        """
        Configura um salário fixo para um cargo.
        Uso: d!addsalario @Moderador 12000 10h
        """
        if amount <= 0:
            return await ctx.send("❌ O valor do salário deve ser maior que zero!")

        # Tratamento da string de tempo (ex: "10h" -> 10)
        interval_str = interval_str.lower().strip()
        if not interval_str.endswith('h'):
            return await ctx.send("❌ Formato de tempo inválido! Use `h` no final (ex: `10h` para 10 horas).")
        
        try:
            hours = int(interval_str[:-1])
        except ValueError:
            return await ctx.send("❌ Use apenas números antes do 'h' (ex: `10h`).")

        if hours <= 0:
            return await ctx.send("❌ O intervalo de horas deve ser de pelo menos 1h!")

        server_id = ctx.guild.id
        role_id_str = str(role.id)

        # Monta a estrutura que o modelo RoleSalary exige
        salary_data = {
            "amount": amount,
            "interval_hours": hours
        }

        # Atualiza ou cria a configuração no banco
        await self.db.servers.update_one(
            {"server_id": server_id},
            {"$set": {f"role_salaries.{role_id_str}": salary_data}},
            upsert=True
        )

        embed = discord.Embed(
            title="💼 Salário Configurado!",
            description=(
                f"O cargo {role.mention} agora possui um salário ativo!\n\n"
                f"💰 **Quantia:** `{amount}` moedas\n"
                f"⏱️ **Intervalo:** A cada `{hours}h`\n"
                f"*(A quantia será direcionada diretamente para o banco)*"
            ),
            color=0x2ecc71
        )
        embed.set_footer(text=f"ID do Cargo: {role.id}")
        
        await ctx.send(embed=embed)

    @commands.command(name="removesalario")
    @commands.has_permissions(administrator=True)
    async def removesalario(self, ctx, role: discord.Role):
        """
        Remove o salário configurado de um cargo.
        Uso: d!removesalario @Moderador
        """
        server_id = ctx.guild.id
        role_id_str = str(role.id)

        # Apaga o salário do banco de dados
        result = await self.db.servers.update_one(
            {"server_id": server_id},
            {"$unset": {f"role_salaries.{role_id_str}": ""}}
        )

        if result.modified_count > 0:
            await ctx.send(f"✅ O salário do cargo {role.mention} foi removido com sucesso!")
        else:
            await ctx.send(f"⚠️ O cargo {role.mention} não possuía nenhum salário configurado.")

async def setup(bot):
    await bot.add_cog(SalaryAdminCog(bot))