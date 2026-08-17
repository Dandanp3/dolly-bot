import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta

class SalaryAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.salary_loop.start() # Inicia o loop quando a Cog é carregada

    def cog_unload(self):
        self.salary_loop.cancel() # Cancela o loop se a Cog for descarregada

    @commands.command(name="addsalario")
    @commands.has_permissions(administrator=True)
    async def addsalario(self, ctx, role: discord.Role, amount: int, interval_str: str):
        """
        Configura um salário fixo para um cargo.
        Uso: d!addsalario @Moderador 12000 10h
        """
        if amount <= 0:
            return await ctx.send("❌ O valor do salário deve ser maior que zero!")

        # Tratamento da string de tempo 
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


    # PAGAMENTO
    @tasks.loop(minutes=5) # Verifica a cada 5 minutos
    async def salary_loop(self):
        # Evita que a task rode antes do bot estar pronto
        await self.bot.wait_until_ready()
        now = datetime.now(timezone.utc)

        # Pega todos os servidores que têm a chave 'role_salaries' configurada
        cursor_servers = self.db.servers.find({"role_salaries": {"$exists": True, "$ne": {}}})
        
        async for server_data in cursor_servers:
            server_id_int = server_data.get("server_id")
            server_id_str = str(server_id_int)
            guild = self.bot.get_guild(server_id_int)
            
            if not guild:
                continue # O bot não está nesse servidor, pula para o próximo

            salaries_config = server_data.get("role_salaries", {})

            for role_id_str, config in salaries_config.items():
                role_id_int = int(role_id_str)
                role = guild.get_role(role_id_int)
                
                if not role:
                    continue # Cargo não existe mais no discord, pula

                amount = config.get("amount", 0)
                interval_hours = config.get("interval_hours", 1)
                
                cursor_users = self.db.users.find({f"servers.{server_id_str}": {"$exists": True}})
                
                async for user_data in cursor_users:
                    discord_id = user_data.get("discord_id")
                    
                    # Checa se o membro está no servidor e se ele tem o cargo
                    member = guild.get_member(discord_id)
                    if not member or role not in member.roles:
                        continue
                    
                    server_profile = user_data.get("servers", {}).get(server_id_str, {})
                    last_salaries = server_profile.get("last_salaries", {})
                    
                    last_paid_at = last_salaries.get(role_id_str)

                    # Se a data do banco for offset-naive, converte para UTC
                    if last_paid_at and last_paid_at.tzinfo is None:
                        last_paid_at = last_paid_at.replace(tzinfo=timezone.utc)

                    if last_paid_at is None or (now - last_paid_at) >= timedelta(hours=interval_hours):
                        
                        # Realiza o pagamento
                        await self.db.users.update_one(
                            {"discord_id": discord_id},
                            {
                                "$inc": {f"servers.{server_id_str}.bank": amount},
                                "$set": {
                                    f"servers.{server_id_str}.last_salaries.{role_id_str}": now,
                                    "updated_at": now
                                }
                            }
                        )

async def setup(bot):
    await bot.add_cog(SalaryAdminCog(bot))
