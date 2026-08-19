import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio 

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
        if matched_item.get("type") == "cargo":
            item_type_str = "🎭 Cargo"
        elif matched_item.get("type") == "dodo":
            item_type_str = "🦤 Dodô de Combate"
        else:
            item_type_str = "📦 Item Normal"

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
        
        # 1. Buscar o item
        matched_item = await self.bot.server_controller.find_store_item(ctx.guild.id, item_name)

        if not matched_item:
            return await ctx.send(f"❌ O item **'{item_name}'** não existe na loja do servidor.")

        price = matched_item.get("price")

        # 2. Buscar carteira do usuário no banco 
        user_data = await self.db.users.find_one({"discord_id": ctx.author.id}) or {}
        server_profile = user_data.get("servers", {}).get(server_id_str, {})
        wallet = server_profile.get("wallet", 0)

        # Checagem de saldo que vale tanto para dodo quanto para itens normais
        if wallet < price:
            return await ctx.send(
                f"❌ Você não tem moedas suficientes na carteira!\n"
                f"• Preço do item: **{price}** moedas\n"
                f"• Sua carteira atual: **{wallet}** moedas\n"
                f"*(Dica: Use `d!sacar` para puxar dinheiro do banco)*"
            )

        now = datetime.now(timezone.utc)

        if matched_item.get("type") == "dodo":
            if server_profile.get("has_dodo", False):
                return await ctx.send("❌ Você já tem um Dodô vivo! Não pode ter dois ao mesmo tempo.")

            await ctx.send(f"Você está pagando `{price}` moedas por um Dodô. **Digite no chat como você quer chamar o seu Dodô** (tempo: 60s):")

            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel

            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                dodo_name = msg.content.strip()
                
                if len(dodo_name) > 30:
                    dodo_name = dodo_name[:30]

            except asyncio.TimeoutError:
                return await ctx.send("⏳ Tempo esgotado! A compra do Dodô foi cancelada e seu dinheiro não foi descontado.")

            # Desconta o dinheiro e salva o dodô
            await self.db.users.update_one(
                {"discord_id": ctx.author.id},
                {
                    "$inc": {f"servers.{server_id_str}.wallet": -price},
                    "$set": {
                        f"servers.{server_id_str}.has_dodo": True,
                        f"servers.{server_id_str}.dodo_name": dodo_name,
                        "updated_at": now
                    }
                }
            )

            # Para a execução do comando aqui, já que o dodô foi comprado com sucesso
            return await ctx.send(f"🎉 Parabéns! Você acaba de adotar o **🦤 {dodo_name}**. Cuide bem dele e boa sorte nas rinhas!")
        
        
        # Verificar estoque se for limitado
        is_limited = matched_item.get("is_limited", False)
        current_stock = matched_item.get("stock", 0)
        
        if is_limited and current_stock <= 0:
            await self.db.servers.update_one(
                {"server_id": ctx.guild.id},
                {"$pull": {"store": {"id": matched_item.get("id")}}}
            )
            return await ctx.send("❌ Sinto muito, este item esgotou no estoque e foi removido da loja!")

        # Processar entrega de cargo 
        if matched_item.get("type") == "cargo":
            role_id = matched_item.get("role_id")
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    try:
                        await ctx.author.add_roles(role, reason=f"Comprou o item {matched_item.get('name')} na loja")
                    except discord.Forbidden:
                        return await ctx.send("❌ Erro interno: Não tenho permissão para entregar este cargo. Avise um Administrador.")

        # Descontar o dinheiro da carteira
        await self.db.users.update_one(
            {"discord_id": ctx.author.id},
            {
                "$inc": {f"servers.{server_id_str}.wallet": -price},
                "$set": {"updated_at": now}
            }
        )

        # Atualizar estoque
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

        # Mensagem de Sucesso
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


async def setup(bot):
    await bot.add_cog(StoreActionsCog(bot))
