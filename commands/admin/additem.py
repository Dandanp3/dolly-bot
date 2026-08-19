import asyncio
import uuid
import unicodedata
import discord
from discord.ext import commands

def normalize_text(text: str) -> str:
    """Remove acentos, joga para minúsculo e tira espaços extras."""
    if not text:
        return ""
    nfkd_form = unicodedata.normalize('NFKD', text)
    only_ascii = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    return only_ascii.lower().strip()

class TypeChoiceView(discord.ui.View):
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

    @discord.ui.button(label="Item Normal", style=discord.ButtonStyle.secondary, emoji="📦")
    async def btn_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.value = "item"
        await interaction.response.defer()
        self.stop()

class SkipDescView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.skipped = False

    @discord.ui.button(label="Pular Descrição", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def btn_skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.skipped = True
        await interaction.response.defer()
        self.stop()

class LimitChoiceView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.is_limited = None

    @discord.ui.button(label="Ilimitado", style=discord.ButtonStyle.success, emoji="♾️")
    async def btn_inf(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.is_limited = False
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Limitado", style=discord.ButtonStyle.danger, emoji="📉")
    async def btn_lim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return
        self.is_limited = True
        await interaction.response.defer()
        self.stop()

class StoreAdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="additem")
    @commands.has_permissions(administrator=True)
    async def additem(self, ctx):
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        # -- PASSO 1: Criar o Embed base vazio --
        embed = discord.Embed(title="🛒 Criação de Item", color=0x2b2d31)
        embed.add_field(name="Tipo", value="*Aguardando...*", inline=False)
        embed.add_field(name="Nome", value="*Aguardando...*", inline=False)
        embed.add_field(name="Alvo / Cargo ID", value="*Aguardando...*", inline=False)
        embed.add_field(name="Preço", value="*Aguardando...*", inline=False)
        embed.add_field(name="Descrição", value="*Aguardando...*", inline=False)
        embed.add_field(name="Estoque", value="*Aguardando...*", inline=False)
        
        embed.description = "Selecione o **TIPO** de item que deseja criar usando os botões."
        
        type_view = TypeChoiceView(ctx)
        msg = await ctx.send(embed=embed, view=type_view)
        
        await type_view.wait()
        if type_view.value is None:
            return await msg.edit(content="❌ Tempo esgotado. Tente novamente.", embed=None, view=None)
            
        item_type = type_view.value
        embed.set_field_at(0, name="Tipo", value="🎭 Cargo" if item_type == "cargo" else "📦 Item Normal", inline=False)

        # -- PASSO 2: Pegar o NOME do item --
        embed.description = "Envie no chat o **nome** que aparecerá para este item na loja."
        await msg.edit(embed=embed, view=None)

        resp_msg = await self.bot.wait_for('message', check=check)
        await resp_msg.delete()
        item_name = resp_msg.content

        embed.set_field_at(1, name="Nome", value=item_name, inline=False)

        # -- PASSO 3: Pegar o ID do Cargo (se for cargo) ou pular --
        role_id = None
        if item_type == "cargo":
            embed.description = f"Envie no chat o **ID do cargo** do Discord que será entregue ao comprar **{item_name}**."
            await msg.edit(embed=embed)

            while True:
                resp_msg = await self.bot.wait_for('message', check=check)
                await resp_msg.delete()
                try:
                    role_id = int(resp_msg.content)
                    role = ctx.guild.get_role(role_id)
                    if not role:
                        temp = await ctx.send("❌ Cargo não encontrado! Mande um ID válido.")
                        await asyncio.sleep(3)
                        await temp.delete()
                        continue
                    break
                except ValueError:
                    temp = await ctx.send("❌ ID inválido. Mande apenas os números do ID do cargo.")
                    await asyncio.sleep(3)
                    await temp.delete()
            
            embed.set_field_at(2, name="Alvo / Cargo ID", value=f"ID: {role_id}", inline=False)
        else:
            embed.set_field_at(2, name="Alvo / Cargo ID", value="N/A (Item Físico/Normal)", inline=False)

        # -- PASSO 4: Preço --
        embed.description = "Envie no chat o **valor numérico** (preço) em moedas deste item."
        await msg.edit(embed=embed)
        
        while True:
            resp_msg = await self.bot.wait_for('message', check=check)
            await resp_msg.delete()
            try:
                item_price = int(resp_msg.content)
                if item_price <= 0: raise ValueError
                break
            except ValueError:
                temp = await ctx.send("❌ Valor inválido. Digite apenas números maiores que zero.")
                await asyncio.sleep(3)
                await temp.delete()

        embed.set_field_at(3, name="Preço", value=f"💰 {item_price} moedas", inline=False)

        # -- PASSO 5: Descrição (Com corrida de Task para Chat vs Botão) --
        embed.description = "Envie no chat uma **descrição** para o item OU clique no botão para pular."
        skip_view = SkipDescView(ctx)
        await msg.edit(embed=embed, view=skip_view)

        message_task = asyncio.create_task(self.bot.wait_for('message', check=check))
        view_task = asyncio.create_task(skip_view.wait())
        
        done, pending = await asyncio.wait(
            [message_task, view_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        item_desc = "Sem descrição."
        if message_task in done:
            resp_msg = message_task.result()
            item_desc = resp_msg.content
            await resp_msg.delete()
        elif skip_view.skipped:
            item_desc = "Sem descrição."

        for task in pending: task.cancel()

        embed.set_field_at(4, name="Descrição", value=f"📝 {item_desc}", inline=False)

        # -- PASSO 6: Estoque --
        embed.description = "Este item tem limite de estoque?"
        lim_view = LimitChoiceView(ctx)
        await msg.edit(embed=embed, view=lim_view)
        
        await lim_view.wait()
        is_limited = lim_view.is_limited

        if is_limited:
            embed.description = "Envie no chat a **quantidade máxima** deste item."
            await msg.edit(embed=embed, view=None)
            while True:
                resp_msg = await self.bot.wait_for('message', check=check)
                await resp_msg.delete()
                try:
                    item_stock = int(resp_msg.content)
                    if item_stock <= 0: raise ValueError
                    break
                except ValueError:
                    temp = await ctx.send("❌ Quantidade inválida. Digite apenas números maiores que zero.")
                    await asyncio.sleep(3)
                    await temp.delete()
            embed.set_field_at(5, name="Estoque", value=f"📉 {item_stock} unidades", inline=False)
        else:
            item_stock = None
            embed.set_field_at(5, name="Estoque", value="♾️ Ilimitado", inline=False)

        # -- PASSO 7: Salvar no Banco --
        embed.description = "✅ **Item adicionado com sucesso à loja do servidor!**"
        embed.color = 0x2ecc71
        await msg.edit(embed=embed, view=None)

        new_item = {
            "id": uuid.uuid4().hex[:8],
            "type": item_type,
            "name": item_name,
            "role_id": role_id,
            "price": item_price,
            "description": item_desc if item_desc != "Sem descrição." else None,
            "is_limited": is_limited,
            "stock": item_stock
        }

        # Atualiza a estrutura do servidor empurrando o item novo pro array 'store'
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$push": {"store": new_item}},
            upsert=True
        )

    @commands.command(name="removeitem", aliases=["delitem", "removeritem"])
    @commands.has_permissions(administrator=True)
    async def removeitem(self, ctx, *, item_query: str):
        """
        Remove um item da loja do servidor.
        Aceita tanto o nome do item quanto o ID único de 8 caracteres.
        Uso: d!removeitem VIP Gold  ou  d!removeitem a1b2c3d4
        """
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        items = server_data.get("store", [])

        normalized_query = normalize_text(item_query)
        target_item = None

        # Busca tanto por coincidência no nome normalizado quanto pelo ID do item
        for item in items:
            item_name_norm = normalize_text(item.get("name", ""))
            item_id = str(item.get("id", "")).strip()

            if item_name_norm == normalized_query or item_id == item_query.strip():
                target_item = item
                break

        if not target_item:
            return await ctx.send(f"❌ Nenhum item com nome ou ID **'{item_query}'** foi encontrado na loja.")

        # Remove o item do banco de dados utilizando a chave única 'id'
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$pull": {"store": {"id": target_item.get("id")}}}
        )

        embed = discord.Embed(
            title="🗑️ Item Removido da Loja",
            description=(
                f"O item **{target_item.get('name')}** foi excluído com sucesso da loja!\n\n"
                f"• **ID do Item:** `{target_item.get('id')}`\n"
                f"• **Tipo:** {'🎭 Cargo' if target_item.get('type') == 'cargo' else '📦 Item Normal'}\n"
                f"• **Preço:** 💰 {target_item.get('price')} moedas"
            ),
            color=0xe74c3c
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="🐾 Mundo Animal • Administração da Loja")

        await ctx.send(embed=embed)

    @commands.command(name="adddodo")
    @commands.has_permissions(administrator=True)
    async def adddodo(self, ctx, price: int):
        """Adiciona o Dodô à venda na loja."""
        if price <= 0:
            return await ctx.send("❌ O preço do Dodô deve ser maior que zero!")

        dodo_item = {
            "id": "dodo", 
            "type": "dodo",
            "name": "🦤 Dodô de Combate",
            "price": price,
            "description": "Compre este Dodô para participar das famosas Rinhas! Se você perder uma luta, ele morre.",
            "is_limited": False,
            "stock": None,
            "role_id": None # Preenchendo com None para bater certinho com seu modelo
        }
        
        # Removemos qualquer dodô antigo para não duplicar
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$pull": {"store": {"type": "dodo"}}}
        )

        # Adicionamos ele no topo da loja
        await self.db.servers.update_one(
            {"server_id": ctx.guild.id},
            {"$push": {
                "store": {
                    "$each": [dodo_item],
                    "$position": 0
                }
            }},
            upsert=True
        )

        await ctx.send(f"✅ O **🦤 Dodô de Combate** foi adicionado à loja por **{price}** moedas!\n*(Os jogadores já podem usar `d!buy dodo`)*")

async def setup(bot):
    await bot.add_cog(StoreAdminCog(bot))
