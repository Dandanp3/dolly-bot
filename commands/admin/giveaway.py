import asyncio
import random
import re
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands, tasks

class GiveawayTypeView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.value = None

    @discord.ui.button(label="Cargo", style=discord.ButtonStyle.primary, emoji="🎭")
    async def btn_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.value = "cargo"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Coins", style=discord.ButtonStyle.success, emoji="🪙")
    async def btn_coins(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.value = "coins"
        await interaction.response.defer()
        self.stop()

def parse_duration(duration_str: str) -> int:
    """Converte strings como 10s, 5m, 2h, 1d em segundos."""
    match = re.match(r"^(\d+)([smhd])$", duration_str.lower().strip())
    if not match:
        return None
    val, unit = match.groups()
    val = int(val)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return val * multipliers[unit]

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.check_giveaways.start()

    def cog_unload(self):
        self.check_giveaways.cancel()

    @commands.command(name="sorteiosetup", aliases=["giveawaysetup"])
    @commands.has_permissions(administrator=True)
    async def sorteiosetup(self, ctx):
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        if server_data.get("giveaway"):
            return await ctx.send("❌ Já existe um sorteio ativo neste servidor! Espere ele terminar ou use outro servidor.")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # -- PASSO 1: Escolher Tipo (Cargo ou Coins) --
        embed = discord.Embed(title="🎉 Configuração de Sorteio", color=0x3498db)
        embed.add_field(name="Prêmio", value="*Aguardando...*", inline=False)
        embed.add_field(name="Vencedores", value="*Aguardando...*", inline=False)
        embed.add_field(name="Duração", value="*Aguardando...*", inline=False)
        embed.add_field(name="Emoji", value="*Aguardando...*", inline=False)
        embed.add_field(name="Canal", value="*Aguardando...*", inline=False)
        
        embed.description = "O que você deseja sortear? Escolha usando os botões abaixo."
        
        type_view = GiveawayTypeView(ctx)
        msg = await ctx.send(embed=embed, view=type_view)
        
        await type_view.wait()
        if type_view.value is None:
            return await msg.edit(content="❌ Tempo esgotado.", embed=None, view=None)

        prize_type = type_view.value

        # -- PASSO 2: Pegar o valor do prêmio (ID do cargo ou quantidade de moedas) --
        if prize_type == "cargo":
            embed.description = "Envie no chat o **ID do cargo** que será sorteado."
        else:
            embed.description = "Envie no chat a **quantidade de moedas** que serão sorteadas."
        
        await msg.edit(embed=embed, view=None)

        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            try:
                reward_value = int(resp_msg.content)
                if prize_type == "cargo":
                    role = ctx.guild.get_role(reward_value)
                    if not role:
                        temp = await ctx.send("❌ Cargo não encontrado! Digite um ID válido.")
                        await asyncio.sleep(3)
                        await temp.delete()
                        continue
                    prize_name = role.name
                else:
                    if reward_value <= 0: raise ValueError
                    prize_name = f"{reward_value} moedas"
                break
            except ValueError:
                temp = await ctx.send("❌ Valor inválido. Digite apenas números inteiros maiores que zero.")
                await asyncio.sleep(3)
                await temp.delete()

        embed.set_field_at(0, name="Prêmio", value=f"🎁 {prize_name}", inline=False)

        # -- PASSO 3: Quantidade de Vencedores --
        embed.description = "Envie no chat a **quantidade de vencedores** para este sorteio."
        await msg.edit(embed=embed)

        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            try:
                winners_count = int(resp_msg.content)
                if winners_count <= 0: raise ValueError
                break
            except ValueError:
                temp = await ctx.send("❌ Quantidade inválida. Digite um número maior que zero.")
                await asyncio.sleep(3)
                await temp.delete()

        embed.set_field_at(1, name="Vencedores", value=f"👑 {winners_count} pessoa(s)", inline=False)

        # -- PASSO 4: Duração do Sorteio --
        embed.description = "Envie no chat a **duração** do sorteio (Ex: `30s`, `10m`, `2h`, `1d`)."
        await msg.edit(embed=embed)

        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            duration_seconds = parse_duration(resp_msg.content)
            if not duration_seconds:
                temp = await ctx.send("❌ Formato inválido! Use números seguidos de `s`, `m`, `h` ou `d` (Ex: `10m`).")
                await asyncio.sleep(3)
                await temp.delete()
                continue
            break

        embed.set_field_at(2, name="Duração", value=f"⏳ {resp_msg.content}", inline=False)

        # -- PASSO 5: Emoji --
        embed.description = "Envie no chat o **emoji** que os membros usarão para reagir."
        await msg.edit(embed=embed)

        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            emoji_input = resp_msg.content.strip()
            # Validação simples de emoji personalizado ou unicode
            try:
                test_msg = await ctx.send("🔄 Testando emoji...")
                await test_msg.add_reaction(emoji_input)
                await test_msg.delete()
                break
            except Exception:
                temp = await ctx.send("❌ Emoji inválido ou inacessível pelo bot. Tente outro.")
                await asyncio.sleep(3)
                await temp.delete()

        embed.set_field_at(3, name="Emoji", value=emoji_input, inline=False)

        # -- PASSO 6: Canal do Sorteio --
        embed.description = "Mencione ou envie o **ID do canal** onde o sorteio será publicado."
        await msg.edit(embed=embed)

        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            channel_id = None
            if resp_msg.channel_mentions:
                channel_id = resp_msg.channel_mentions[0].id
            else:
                try:
                    channel_id = int(resp_msg.content.strip())
                except ValueError:
                    pass
            
            target_channel = ctx.guild.get_channel(channel_id)
            if not target_channel:
                temp = await ctx.send("❌ Canal inválido! Mencione um canal existente.")
                await asyncio.sleep(3)
                await temp.delete()
                continue
            break

        embed.set_field_at(4, name="Canal", value=target_channel.mention, inline=False)

        # -- Finalização e Disparo --
        now = datetime.now(timezone.utc)
        ends_at = now + timedelta(seconds=duration_seconds)
        timestamp_discord = int(ends_at.timestamp())

        # Montar embed bonitinho do Sorteio para enviar no canal alvo
        giveaway_embed = discord.Embed(
            title="🎉 **NOVO SORTEIO NA TRIBO!** 🎉",
            description=(
                f"Prêmio: **{prize_name}**\n"
                f"Vencedores: **{winners_count}**\n"
                f"Término: <t:{timestamp_discord}:R> (<t:{timestamp_discord}:F>)\n\n"
                f"Reaja com {emoji_input} para participar!"
            ),
            color=0xf1c40f
        )
        giveaway_embed.set_footer(text=f"Organizado por {ctx.author.display_name}")

        giveaway_msg = await target_channel.send(embed=giveaway_embed)
        await giveaway_msg.add_reaction(emoji_input)

        # Salvar no Banco de Dados
        giveaway_data = {
            "prize_type": prize_type,
            "prize_name": prize_name,
            "reward_value": reward_value,
            "winners_count": winners_count,
            "duration_seconds": duration_seconds,
            "emoji": emoji_input,
            "channel_id": target_channel.id,
            "message_id": giveaway_msg.id,
            "ends_at": ends_at
        }

        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$set": {"giveaway": giveaway_data}},
            upsert=True
        )

        await msg.edit(content="✅ Sorteio configurado e iniciado com sucesso!", embed=None, view=None)

    # ---------------- BACKGROUND TASK (A CADA 1 MINUTO) ---------------- #
    @tasks.loop(minutes=1)
    async def check_giveaways(self):
        now = datetime.now(timezone.utc)
        
        # Buscar todos os servers que possuem sorteio ativo expirado
        cursor = self.db.servers.find({"giveaway.ends_at": {"$lte": now}})
        servers_to_finish = await cursor.to_list(length=None)

        for server_doc in servers_to_finish:
            guild_id = server_doc["server_id"]
            giveaway = server_doc.get("giveaway")
            if not giveaway:
                continue

            guild = self.bot.get_guild(guild_id)
            if not guild:
                # Se o bot saiu do servidor, limpa o sorteio do banco
                await self.db.servers.update_one({"server_id": guild_id}, {"$unset": {"giveaway": ""}})
                continue

            channel = guild.get_channel(giveaway["channel_id"])
            if not channel:
                await self.db.servers.update_one({"server_id": guild_id}, {"$unset": {"giveaway": ""}})
                continue

            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except Exception:
                await self.db.servers.update_one({"server_id": guild_id}, {"$unset": {"giveaway": ""}})
                continue

            # Coletar participantes que reagiram com o emoji
            valid_users = []
            for reaction in message.reactions:
                if str(reaction.emoji) == giveaway["emoji"]:
                    async for user in reaction.users():
                        if not user.bot:
                            valid_users.append(user)
                    break

            winners_count = giveaway["winners_count"]
            winners = []
            if valid_users:
                winners = random.sample(valid_users, min(len(valid_users), winners_count))

            # Distribuir os prêmios
            prize_type = giveaway["prize_type"]
            reward_value = giveaway["reward_value"]
            server_id_str = str(guild_id)

            winners_mentions = []
            for winner in winners:
                winners_mentions.append(winner.mention)
                if prize_type == "cargo":
                    role = guild.get_role(reward_value)
                    if role:
                        try:
                            await winner.add_roles(role, reason="Vencedor de sorteio na tribo")
                        except Exception:
                            pass
                elif prize_type == "coins":
                    # Deposita direto no banco da pessoa
                    await self.db.users.update_one(
                        {"discord_id": winner.id},
                        {
                            "$inc": {f"servers.{server_id_str}.bank": reward_value},
                            "$set": {"updated_at": now},
                            "$setOnInsert": {"created_at": now}
                        },
                        upsert=True
                    )

            # Apagar o giveaway do banco do servidor
            await self.db.servers.update_one({"server_id": guild_id}, {"$unset": {"giveaway": ""}})

            # Enviar mensagem informando os vencedores
            if winners:
                winners_text = ", ".join(winners_mentions)
                end_embed = discord.Embed(
                    title="🎉 Sorteio Finalizado!",
                    description=f"Prêmio: **{giveaway['prize_name']}**\n\n🏆 Vencedores: {winners_text}",
                    color=0x2ecc71
                )
                await channel.send(content=f"Parabéns {winners_text}!", embed=end_embed)
            else:
                await channel.send("❌ O sorteio terminou, mas ninguém reagiu a tempo para concorrer.")

    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))