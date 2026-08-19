import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timezone

class DodoFightCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        
        self.active_challenges = {}

    @commands.command(name="dodofight")
    async def dodofight(self, ctx, oponente: discord.Member, quantia: int):
        if quantia <= 0:
            return await ctx.send("❌ A aposta deve ser maior que zero!")
        
        if oponente == ctx.author:
            return await ctx.send("❌ Você não pode botar o seu Dodô pra brigar com ele mesmo!")

        if oponente.bot:
            return await ctx.send("❌ Bots não têm Dodôs!")

        server_id_str = str(ctx.guild.id)
        desafiante_id = ctx.author.id
        oponente_id = oponente.id

        # 1. Pega os dados dos dois do banco
        user_desafiante = await self.db.users.find_one({"discord_id": desafiante_id}) or {}
        user_oponente = await self.db.users.find_one({"discord_id": oponente_id}) or {}

        prof_desafiante = user_desafiante.get("servers", {}).get(server_id_str, {})
        prof_oponente = user_oponente.get("servers", {}).get(server_id_str, {})

        # 2. Verifica Dodôs
        if not prof_desafiante.get("has_dodo", False):
            return await ctx.send("❌ Você não tem um Dodô para lutar! Compre um na loja primeiro.")
        if not prof_oponente.get("has_dodo", False):
            return await ctx.send(f"❌ O oponente {oponente.mention} não tem um Dodô!")

        dodo_desafiante = prof_desafiante.get("dodo_name", "Dodô Desconhecido")
        dodo_oponente = prof_oponente.get("dodo_name", "Dodô Desconhecido")

        # 3. Verifica Dinheiro no Banco
        if prof_desafiante.get("bank", 0) < quantia:
            return await ctx.send(f"❌ Você não tem `{quantia}` moedas no banco para apostar.")
        
        if prof_oponente.get("bank", 0) < quantia:
            return await ctx.send(f"❌ {oponente.mention} não tem `{quantia}` moedas no banco para cobrir a aposta.")

        challenge_key = (oponente_id, desafiante_id) # Se a chave existir, significa que o outro cara chamou primeiro
        
        if challenge_key in self.active_challenges and self.active_challenges[challenge_key] == quantia:
            # DESAFIO ACEITO! Inicia a luta
            del self.active_challenges[challenge_key]
            await self.start_fight(ctx, oponente, ctx.author, dodo_oponente, dodo_desafiante, quantia)
            return

        new_challenge_key = (desafiante_id, oponente_id)
        self.active_challenges[new_challenge_key] = quantia

        embed_convite = discord.Embed(
            title="⚔️ DESAFIO DE RINHA DE DODÔ!",
            description=(
                f"{ctx.author.mention} desafiou {oponente.mention} para uma rinha sangrenta!\n\n"
                f"🦤 **{dodo_desafiante}** VS **{dodo_oponente}** 🦤\n\n"
                f"💰 **Aposta:** `{quantia}` moedas (Quem perder, o Dodô **MORRE**)\n\n"
                f"Para aceitar, {oponente.mention} deve digitar exatamente o mesmo comando:\n"
                f"`d!dodofight {ctx.author.mention} {quantia}`"
            ),
            color=0xe67e22
        )
        await ctx.send(embed=embed_convite)

        # Limpa o desafio da memória depois de 60 segundos se o outro cara ignorar
        await asyncio.sleep(60)
        if new_challenge_key in self.active_challenges:
            del self.active_challenges[new_challenge_key]

    async def start_fight(self, ctx, j1: discord.Member, j2: discord.Member, dodo1: str, dodo2: str, quantia: int):
        server_id_str = str(ctx.guild.id)

        # Mensagem inicial que vai ser editada
        embed_luta = discord.Embed(
            title="🔥 A RINHA DE DODÔ COMEÇOU!",
            description="Preparando o galpão...",
            color=0xff0000
        )
        msg_luta = await ctx.send(embed=embed_luta)

        # Lista de frases de efeito malucas
        frases = [
            f"💥 **{dodo1}** deu uma bicada voadora no olho de **{dodo2}**!",
            f"🌪️ **{dodo2}** rodopiou e acertou um chute no peito de **{dodo1}**!",
            f"🩸 **{dodo1}** arrastou o bico no chão fazendo faísca e avançou pra cima de **{dodo2}**!",
            f"🪨 **{dodo2}** pegou uma pedra com o bico e atirou na cabeça de **{dodo1}**!",
            f"🔥 **{dodo1}** deu um grito ensurdecedor, deixando **{dodo2}** desnorteado!",
            f"⚔️ **{dodo2}** defendeu um golpe fatal com a asa e revidou com um pisão nas costas de **{dodo1}**!"
        ]

        # Sorteia 3 frases e exibe a cada 3 segundos
        frases_escolhidas = random.sample(frases, 3)
        
        historico_luta = ""
        for frase in frases_escolhidas:
            await asyncio.sleep(3)
            historico_luta += f"{frase}\n\n"
            
            embed_luta.description = historico_luta
            await msg_luta.edit(embed=embed_luta)

        await asyncio.sleep(3) # Pausa dramática para o resultado

        # Sorteio do Vencedor (50/50 puramente aleatório)
        vencedor_is_j1 = random.choice([True, False])
        
        if vencedor_is_j1:
            vencedor, perdedor = j1, j2
            dodo_vencedor, dodo_perdedor = dodo1, dodo2
        else:
            vencedor, perdedor = j2, j1
            dodo_vencedor, dodo_perdedor = dodo2, dodo1
        
        #  Tira do perdedor (tira a grana apostada e deleta o dodô)
        await self.db.users.update_one(
            {"discord_id": perdedor.id},
            {
                "$inc": {f"servers.{server_id_str}.bank": -quantia},
                "$set": {
                    f"servers.{server_id_str}.has_dodo": False,
                    f"servers.{server_id_str}.dodo_name": None
                }
            }
        )

        # Dá o dinheiro da aposta para o vencedor
        await self.db.users.update_one(
            {"discord_id": vencedor.id},
            {
                "$inc": {f"servers.{server_id_str}.bank": quantia}
            }
        )


        historico_luta += f"💀 O impacto final! **{dodo_perdedor}** não resistiu e capotou sem vida no chão da rinha!\n\n"
        
        embed_final = discord.Embed(
            title="🏆 FIM DA RINHA!",
            description=historico_luta,
            color=0xf1c40f
        )
        embed_final.add_field(name="👑 Vencedor", value=f"{vencedor.mention} e seu implacável **{dodo_vencedor}**!\nLevou `+{quantia}` moedas para o banco.", inline=False)
        embed_final.add_field(name="💀 Derrotado", value=f"{perdedor.mention} perdeu `{quantia}` moedas e seu Dodô **{dodo_perdedor}** faleceu nas arenas de batalha.", inline=False)
        
        embed_final.set_thumbnail(url=vencedor.display_avatar.url)

        await msg_luta.edit(embed=embed_final)


async def setup(bot):
    await bot.add_cog(DodoFightCog(bot))
