import math
import discord
from discord.ext import commands

class ShopView(discord.ui.View):
    def __init__(self, ctx, items, per_page=5):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.items = items
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, math.ceil(len(items) / per_page))
        self.message = None

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🛒 Loja da Tribo Pré-Histórica",
            description="Use `d!info <nome do item>` para ver detalhes e `d!buy <nome>` para comprar.",
            color=0x3498db
        )

        start = (self.current_page - 1) * self.per_page
        end = start + self.per_page
        page_items = self.items[start:end]

        for item in page_items:
            emoji = "🎭" if item.get("type") == "cargo" else "📦"
            
            # Puxamos o preço já formatado que criamos no comando principal
            price = item.get("price_formatted") 
            
            name = item.get("name")
            
            # Checar estoque se for limitado
            if item.get("is_limited"):
                stock = item.get("stock", 0)
                stock_text = f" | Estoque: {stock}" if stock > 0 else " | 🔴 Esgotado"
            else:
                stock_text = " | ♾️ Ilimitado"

            embed.add_field(
                name=f"{emoji} {name}",
                value=f"<:bone:1386546091306254386> Preço: **{price}** moedas{stock_text}",
                inline=False
            )

        embed.set_footer(
            text=f"Página {self.current_page}/{self.total_pages} • Solicitado por {self.ctx.author.display_name}",
            icon_url=self.ctx.author.display_avatar.url
        )
        return embed

    def update_buttons(self):
        self.children[0].disabled = (self.current_page == 1)
        self.children[1].disabled = (self.current_page == self.total_pages)

    @discord.ui.button(label="◀ Anterior", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Apenas quem executou o comando pode mudar de página!", ephemeral=True)
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Próximo ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Apenas quem executou o comando pode mudar de página!", ephemeral=True)
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="shop", aliases=["loja"])
    async def shop(self, ctx):
        server_data = await self.db.servers.find_one({"server_id": ctx.guild.id}) or {}
        items = server_data.get("store", [])

        if not items:
            return await ctx.send("🏜️ A loja deste servidor está vazia no momento!")

        for item in items:
            item["price_formatted"] = await self.bot.server_controller.format_money(
                ctx.guild.id, 
                item.get("price", 0)
            )

        view = ShopView(ctx, items, per_page=5)
        view.update_buttons()
        
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message

async def setup(bot):
    await bot.add_cog(ShopCog(bot))