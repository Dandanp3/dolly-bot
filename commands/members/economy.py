import random
from datetime import datetime, timezone
import discord
from discord.ext import commands

DEFAULTS = {
    "brincar": {"min_coins": 1080, "max_coins": 2880, "cooldown_seconds": 120},
    "dormir": {"min_coins": 2520, "max_coins": 4680, "cooldown_seconds": 300},
    "uivar": {"min_coins": 3960, "max_coins": 7560, "cooldown_seconds": 600}
}

EMBED_VISUALS = {
    "brincar": {
        "title": "🌿",
        "desc": "Você perseguiu insetos ancestrais e correu pelas samambaias gigantes, achando moedas escondidas na lama!\n\n💰 **+{reward} moedas** foram adicionadas à sua carteira!{boost_text}",
        "color": 0x2ecc71 
    },
    "dormir": {
        "title": "💤 Sono na Caverna",
        "desc": "Você se abrigou numa gruta escura para um cochilo seguro e profundo, encontrando moedas sob as pedras.\n\n💰 **+{reward} moedas** foram adicionadas à sua carteira!{boost_text}",
        "color": 0x9b59b6 
    },
    "uivar": {
        "title": "🐺 Eco Ancestral",
        "desc": "Você ergueu a cabeça para o céu primordial e uivou para os vales, ganhando moedas da alcateia!\n\n💰 **+{reward} moedas** foram adicionadas à sua carteira!{boost_text}",
        "color": 0x3498db 
    }
}

class EconomyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def _execute_action(self, ctx: commands.Context, action_name: str):
        server_id_str = str(ctx.guild.id)
        now = datetime.now(timezone.utc)

        # Buscar configurações custom e os boosts do servidor
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        econ_config = server_data.get("economy", {}).get(action_name, DEFAULTS[action_name])
        role_boosts = server_data.get("role_boosts", {}) # 🚀 Puxando a tabela de multiplicadores

        min_coins = econ_config.get("min_coins", DEFAULTS[action_name]["min_coins"])
        max_coins = econ_config.get("max_coins", DEFAULTS[action_name]["max_coins"])
        cooldown_seconds = econ_config.get("cooldown_seconds", DEFAULTS[action_name]["cooldown_seconds"])

        # Verificar o histórico de execuções 
        user_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        server_user_profile = user_data.get("servers", {}).get(server_id_str, {})
        last_action_at = server_user_profile.get("last_actions", {}).get(action_name)

        if last_action_at:
            if last_action_at.tzinfo is None:
                last_action_at = last_action_at.replace(tzinfo=timezone.utc)
            
            elapsed = (now - last_action_at).total_seconds()
            if elapsed < cooldown_seconds:
                remaining = int(cooldown_seconds - elapsed)
                minutes, seconds = divmod(remaining, 60)
                
                embed_cd = discord.Embed(
                    title="⏳ Calma aí, amiguinho!",
                    description=f"Você está muito cansado para fazer isso agora.\nDescanse as patinhas por `{minutes}m {seconds}s` antes de tentar novamente!",
                    color=0xe74c3c 
                )
                return await ctx.send(embed=embed_cd)

        # boost logica
        total_multiplier = 0.0
        
        # Varre todos os cargos que o membro tem no servidor
        for role in ctx.author.roles:
            role_id_str = str(role.id)
            if role_id_str in role_boosts:
                total_multiplier += role_boosts[role_id_str]

        # Se a soma der 0.0, o padrão vira 1x
        if total_multiplier == 0.0:
            total_multiplier = 1.0

        # Sortear as moedas e multiplicar pelo valor final somado
        base_reward = random.randint(min_coins, max_coins)
        reward = int(base_reward * total_multiplier)

        # Atualizar os dados do usuário com a nova quantia (usando o valor numérico não formatado)
        update_query = {
            "$inc": {f"servers.{server_id_str}.wallet": reward},
            "$set": {
                f"servers.{server_id_str}.last_actions.{action_name}": now,
                "updated_at": now
            },
            "$setOnInsert": {
                "created_at": now,
                "discord_id": ctx.author.id
            }
        }

        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            update_query,
            upsert=True
        )

        formatted_reward = await self.bot.server_controller.format_money(ctx.guild.id, reward)

        boost_text = f"\n🚀 *(Boost aplicado: **{total_multiplier}x**)*" if total_multiplier > 1.0 else ""

        # Pegar os dados visuais específicos da ação escolhida
        visuals = EMBED_VISUALS[action_name]
        
        # Criar o Embed de Sucesso (injetando o valor já formatado)
        embed_success = discord.Embed(
            title=visuals["title"],
            description=visuals["desc"].format(reward=formatted_reward, boost_text=boost_text),
            color=visuals["color"]
        )
        
        # Adicionar o avatar do usuário e um rodapé temático
        embed_success.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed_success.set_footer(text="🐾 • Economia")

        await ctx.send(embed=embed_success)

    @commands.command(name="brincar")
    async def brincar(self, ctx):
        await self._execute_action(ctx, "brincar")

    @commands.command(name="dormir")
    async def dormir(self, ctx):
        await self._execute_action(ctx, "dormir")

    @commands.command(name="uivar")
    async def uivar(self, ctx):
        await self._execute_action(ctx, "uivar")

    # COMANDO DE CONFIGURAÇÃO 
    @commands.command(name="seteconomia", aliases=["config_economia"])
    @commands.has_permissions(administrator=True) # Somente administradores
    async def seteconomia(self, ctx, acao: str, min_coins: int, max_coins: int, cooldown_segundos: int):
        """
        Altera os ganhos e o cooldown de uma ação da economia.
        Uso: !seteconomia <brincar|dormir|uivar> <min> <max> <cooldown>
        """
        acao = acao.lower()
        if acao not in ["brincar", "dormir", "uivar"]:
            return await ctx.send("❌ Ação inválida! Escolha entre: `brincar`, `dormir` ou `uivar`.")

        if min_coins < 0 or max_coins < min_coins or cooldown_segundos < 0:
            return await ctx.send("❌ Valores inválidos! O mínimo não pode ser maior que o máximo e não podem ser negativos.")

        server_id_str = str(ctx.guild.id)

        # Atualiza os valores específicos da ação no banco de dados MongoDB
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {
                "$set": {
                    f"economy.{acao}.min_coins": min_coins,
                    f"economy.{acao}.max_coins": max_coins,
                    f"economy.{acao}.cooldown_seconds": cooldown_segundos
                }
            },
            upsert=True
        )

        embed = discord.Embed(
            title="⚙️ Economia Atualizada!",
            description=f"As configurações para a ação **{acao}** foram alteradas com sucesso neste servidor.",
            color=0x2ecc71
        )
        embed.add_field(name="Mínimo", value=f"{min_coins} moedas", inline=True)
        embed.add_field(name="Máximo", value=f"{max_coins} moedas", inline=True)
        embed.add_field(name="Tempo de Espera", value=f"{cooldown_segundos} segundos", inline=True)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(EconomyCog(bot))
