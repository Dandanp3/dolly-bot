import math
import discord
from discord.ext import commands

class LeaderboardView(discord.ui.View):
    def __init__(self, ctx, leaderboard_data, per_page=10):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.data = leaderboard_data
        self.per_page = per_page
        self.current_page = 1
        self.total_pages = max(1, math.ceil(len(leaderboard_data) / per_page))
        self.message = None

    def create_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🏆 Ranking dos Mais Ricos da Tribo",
            color=0xf1c40f
        )

        start = (self.current_page - 1) * self.per_page
        end = start + self.per_page
        page_data = self.data[start:end]

        if not page_data:
            embed.description = "Nenhum registro de moedas encontrado neste servidor."
            return embed

        description = []
        for idx, user in enumerate(page_data, start=start + 1):
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"`#{idx}`"

            member = self.ctx.guild.get_member(user["discord_id"])
            name = member.display_name if member else f"Usuário ({user['discord_id']})"
            
            # Aqui pegamos o valor já formatado que foi preparado no comando principal
            total_formatado = user["total_formatado"] 

            description.append(f"{medal} **{name}** — <:bone:1386546091306254386> **{total_formatado}** moedas")

        embed.description = "\n".join(description)
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


class TopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command(name="top", aliases=["leaderboard", "ricos", "palanque"])
    async def top(self, ctx):
        """Exibe o ranking dos usuários com mais moedas (total)."""
        server_id_str = str(ctx.guild.id)

        pipeline = [
            {"$match": {f"servers.{server_id_str}": {"$exists": True}}},
            {
                "$project": {
                    "discord_id": 1,
                    "total": {
                        "$add": [
                            {"$ifNull": [f"$servers.{server_id_str}.wallet", 0]},
                            {"$ifNull": [f"$servers.{server_id_str}.bank", 0]}
                        ]
                    }
                }
            },
            {"$match": {"total": {"$gt": 0}}},
            {"$sort": {"total": -1}}
        ]

        results = await self.db.users.aggregate(pipeline).to_list(length=None)

        if not results:
            return await ctx.send("🏝️ Nenhum animal acumulou riquezas neste servidor ainda!")

        for user in results:
            # Chama a função centralizada do seu controller e salva em uma nova chave
            user["total_formatado"] = await self.bot.server_controller.format_money(
                ctx.guild.id, 
                user["total"]
            )

        view = LeaderboardView(ctx, results, per_page=10)
        view.update_buttons()
        
        embed = view.create_embed()
        message = await ctx.send(embed=embed, view=view)
        view.message = message


async def setup(bot):
    await bot.add_cog(TopCog(bot))