import discord
from discord.ext import commands
from datetime import datetime, timezone

class StoreActionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="info")
    async def store_info(self, ctx, *, item_name: str):
        """Mostra todas as informações detalhadas de um item da loja."""
        matched_item = await self.bot.server_controller.find_store_item(ctx.guild.id, item_name)

        if not matched_item:
            return await ctx.send(f"❌ Nenhum item com o nome ou ID **'{item_name}'** foi encontrado na loja.")

        # Montar embed com TODAS as informações
        item_type_str = "🎭 Cargo" if matched_item.get("type") == "cargo" else "📦 Item Normal"
        price = matched_item.get("price")
        desc = matched_item.get("description", "Sem descrição informada.")
        is_limited = matched_item.get("is_limited", False)
        
        if is_limited:
            stock = matched_item.get("stock", 0)
            stock_str = f"Limitado ({stock} unidades restantes)"
        else:
            stock_str = "Ilimitado (♾️)"

        embed = discord.Embed(
            title=f"📋 Detalhes do Item: {matched_item.get('name')}",
            description=desc,
            color=0x9b59b6
        )
        embed.add_field(name="Tipo", value=item_type_str, inline=True)
        embed.add_field(name="Preço", value=f"<:bone:1386546091306254386> {price} moedas", inline=True)
        embed.add_field(name="Estoque", value=stock_str, inline=True)
        
        if matched_item.get("type") == "cargo" and matched_item.get("role_id"):
            role = ctx.guild.get_role(matched_item.get("role_id"))
            role_mention = role.mention if role else "Cargo não encontrado no servidor"
            embed.add_field(name="Cargo Vinculado", value=role_mention, inline=False)

        embed.set_footer(text=f"ID do Item: {matched_item.get('id')}")
        await ctx.send(embed=embed)

    @commands.command(name="buy", aliases=["comprar"])
    async def buy(self, ctx, *, item_name: str):
        """Compra um item da loja usando exclusivamente o saldo da carteira."""
        server_id_str = str(ctx.guild.id)
        
        # 1. Buscar o item usando o método inteligente do controller (ignora maiúsculas e acentos)
        matched_item = await self.bot.server_controller.find_store_item(ctx.guild.id, item_name)

        if not matched_item:
            return await ctx.send(f"❌ O item **'{item_name}'** não existe na loja do servidor.")

        # 2. Verificar estoque se for limitado
        is_limited = matched_item.get("is_limited", False)
        current_stock = matched_item.get("stock", 0)
        
        if is_limited and current_stock <= 0:
            await self.db.servers.update_one(
                {"server_id": ctx.guild.id},
                {"$pull": {"store": {"id": matched_item.get("id")}}}
            )
            return await ctx.send("❌ Sinto muito, este item esgotou no estoque e foi removido da loja!")

        price = matched_item.get("price")

        # 3. Buscar carteira do usuário (desconta APENAS da wallet)
        user_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        server_profile = user_data.get("servers", {}).get(server_id_str, {})
        wallet = server_profile.get("wallet", 0)

        if wallet < price:
            return await ctx.send(
                f"❌ Você não tem moedas suficientes na carteira!\n"
                f"• Preço do item: **{price}** moedas\n"
                f"• Sua carteira atual: **{wallet}** moedas\n"
                f"*(Dica: Use `d!sacar` para puxar dinheiro do banco)*"
            )

        now = datetime.now(timezone.utc)

        # 4. Processar entrega de cargo (se for do tipo cargo)
        if matched_item.get("type") == "cargo":
            role_id = matched_item.get("role_id")
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    try:
                        await ctx.author.add_roles(role, reason=f"Comprou o item {matched_item.get('name')} na loja")
                    except discord.Forbidden:
                        return await ctx.send("❌ Erro interno: Não tenho permissão para entregar este cargo. Avise um Administrador.")

        # 5. Descontar o dinheiro da carteira do usuário no Banco de Dados
        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": -price},
                "$set": {"updated_at": now}
            }
        )

        # 6. Atualizar estoque ou remover se for a última unidade
        if is_limited:
            if current_stock <= 1:
                await self.db.servers.update_one(
                    {"server_id": ctx.guild.id},
                    {"$pull": {"store": {"id": matched_item.get("id")}}}
                )
            else:
                await self.db.servers.update_one(
                    {"server_id": ctx.guild.id, "store.id": matched_item.get("id")},
                    {"$inc": {"store.$.stock": -1}}
                )

        # 7. Mensagem de Sucesso
        embed = discord.Embed(
            title="🛍️ Compra Efetuada com Sucesso!",
            description=f"Você adquiriu **{matched_item.get('name')}** por **{price} moedas** tiradas da sua carteira.",
            color=0x2ecc71
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        if matched_item.get("type") == "cargo":
            embed.add_field(name="Cargo Entregue", value="O cargo foi adicionado ao seu perfil do Discord!", inline=False)
            
        if is_limited and current_stock <= 1:
            embed.set_footer(text="⚠️ Este era o último item no estoque! Ele foi removido da loja.")

        await ctx.send(embed=embed)

    @commands.command(name="comprardodo")
    async def comprardodo(self, ctx):
        server_id_str = str(ctx.guild.id)
        
        # Checa se tem dodo na loja
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        store_items = server_data.get("store", [])
        dodo_info = next((item for item in store_items if item.get("type") == "dodo"), None)
        
        if not dodo_info:
            return await ctx.send("❌ Não há Dodôs à venda na loja no momento!")

        price = dodo_info.get("price", 0)

        # Checa saldo e se o usuário JÁ TEM um Dodô
        user_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        server_profile = user_data.get("servers", {}).get(server_id_str, {})
        
        if server_profile.get("has_dodo", False):
            return await ctx.send("❌ Você já tem um Dodô vivo! Não pode ter dois ao mesmo tempo.")

        user_wallet = server_profile.get("wallet", 0)
        
        if user_wallet < price:
            return await ctx.send(f"❌ Você não tem dinheiro na carteira para comprar um Dodô. (Custa: `{price}` moedas).")

        # Pede o nome do Dodô no chat
        await ctx.send(f"Você está pagando `{price}` por um Dodô. Digite no chat como você quer chamar o seu Dodô (tempo: 60s):")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            dodo_name = msg.content.strip()
            
            # Limita o nome para não ficar gigante no embed da luta
            if len(dodo_name) > 30:
                dodo_name = dodo_name[:30]

        except asyncio.TimeoutError:
            return await ctx.send("⏳ Tempo esgotado! A compra do Dodô foi cancelada.")

        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": -price},
                "$set": {
                    f"servers.{server_id_str}.has_dodo": True,
                    f"servers.{server_id_str}.dodo_name": dodo_name
                }
            }
        )

        await ctx.send(f"🎉 Parabéns! Você acaba de adotar o **🦤 {dodo_name}**. Cuide bem dele e boa sorte nas rinhas!")

async def setup(bot):
    await bot.add_cog(StoreActionsCog(bot))
