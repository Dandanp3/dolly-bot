import discord
from discord.ext import commands
from discord import ui
import json
import os
import asyncio
import string

JSON_FILE = "cache/questions.json"

# --- Funções Auxiliares de JSON ---
def load_questions():
    if not os.path.exists(JSON_FILE):
        return {}
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_questions(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_server_data(guild_id):
    data = load_questions()
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {"nota_minima": 5, "questoes": []} # Padrão
    return data, gid

# VIEW: ADICIONAR QUESTÃO (.addquestion)
class AddQuestionView(ui.View):
    def __init__(self, bot, author, guild_id):
        super().__init__(timeout=600)
        self.bot = bot
        self.author = author
        self.guild_id = guild_id
        
        self.step = "enunciado"
        self.enunciado = ""
        self.alternativas = {}
        self.resposta = ""
        self.letras = list(string.ascii_lowercase) # a, b, c, d...

    def create_embed(self):
        embed = discord.Embed(title="📝 Adicionar Nova Questão", color=discord.Color.green())
        
        if self.enunciado:
            embed.add_field(name="Enunciado", value=self.enunciado, inline=False)
            
        if self.alternativas:
            alts_text = "\n".join([f"**{k})** {v}" for k, v in self.alternativas.items()])
            embed.add_field(name="Alternativas", value=alts_text, inline=False)
            
        if self.resposta:
            embed.add_field(name="Resposta Correta", value=f"Letra **{self.resposta}**", inline=False)

        # Instruções Dinâmicas
        if self.step == "enunciado":
            embed.description = "➡️ **Digite o ENUNCIADO da questão no chat.**"
        elif self.step == "alternativas":
            prox_letra = self.letras[len(self.alternativas)]
            embed.description = f"➡️ **Digite o texto da alternativa [{prox_letra}].**\n*(Se já adicionou opções suficientes, clique no botão para parar)*"
        elif self.step == "resposta":
            embed.description = "➡️ **Qual é a letra correta?** (Ex: `a`, `b`, `c`)"
        elif self.step == "salvo":
            embed.description = "✅ **Questão salva com sucesso no banco de dados!**"
            embed.color = discord.Color.blue()
            
        return embed

    async def update_view(self, message: discord.Message):
        self.clear_items()
        
        # Só mostra o botão de parar quando tiver pelo menos 2 alternativas (A e B)
        if self.step == "alternativas" and len(self.alternativas) >= 2:
            btn_stop = ui.Button(label="Finalizar Alternativas", style=discord.ButtonStyle.primary)
            btn_stop.callback = self.stop_alternatives
            self.add_item(btn_stop)
            
        await message.edit(embed=self.create_embed(), view=self)

    async def stop_alternatives(self, interaction: discord.Interaction):
        self.step = "resposta"
        await self.update_view(message=interaction.message)

    async def wait_for_input(self, message: discord.Message):
        def check(m):
            return m.author == self.author and m.channel == message.channel

        try:
            while self.step in ["enunciado", "alternativas", "resposta"]:
                msg = await self.bot.wait_for('message', check=check, timeout=180.0)
                content = msg.content
                await msg.delete()

                if self.step == "enunciado":
                    self.enunciado = content
                    self.step = "alternativas"
                    
                elif self.step == "alternativas":
                    prox_letra = self.letras[len(self.alternativas)]
                    self.alternativas[prox_letra] = content
                    # Se chegar na letra 'z' (improvável), força ir pra resposta
                    if len(self.alternativas) >= 26: 
                        self.step = "resposta"

                elif self.step == "resposta":
                    resposta_clean = content.lower().strip()
                    if resposta_clean in self.alternativas:
                        self.resposta = resposta_clean
                        self.step = "salvo"
                        self.save_to_json()
                    else:
                        temp = await message.channel.send("❌ Letra inválida! Escolha uma das alternativas cadastradas.")
                        await asyncio.sleep(3)
                        await temp.delete()

                await self.update_view(message=message)

        except asyncio.TimeoutError:
            await message.edit(content="⏳ Tempo esgotado para adicionar questão.", view=None)

    def save_to_json(self):
        data, gid = get_server_data(self.guild_id)
        
        nova_questao = {
            "enunciado": self.enunciado,
            "alternativas": self.alternativas,
            "resposta": self.resposta
        }
        
        data[gid]["questoes"].append(nova_questao)
        save_questions(data)


# VIEW: EDITAR QUESTÃO (.editquestion)
class EditQuestionView(ui.View):
    def __init__(self, bot, author, guild_id, q_index, question_data):
        super().__init__(timeout=600)
        self.bot = bot
        self.author = author
        self.guild_id = guild_id
        self.q_index = q_index
        self.q_data = question_data
        self.letras = list(string.ascii_lowercase)

    def create_embed(self):
        embed = discord.Embed(title=f"✏️ Editando Questão #{self.q_index + 1}", color=discord.Color.gold())
        embed.description = "Clique nos botões abaixo para editar um campo específico."
        
        embed.add_field(name="Enunciado", value=self.q_data["enunciado"], inline=False)
        alts_text = "\n".join([f"**{k})** {v}" for k, v in self.q_data["alternativas"].items()])
        embed.add_field(name="Alternativas", value=alts_text, inline=False)
        embed.add_field(name="Resposta Correta", value=f"Letra **{self.q_data['resposta']}**", inline=False)
        
        return embed

    def build_buttons(self):
        self.clear_items()
        
        # Botão Editar Enunciado
        btn_enunciado = ui.Button(label="Editar Enunciado", style=discord.ButtonStyle.secondary, row=0)
        btn_enunciado.callback = self.edit_enunciado
        self.add_item(btn_enunciado)

        # Botões para cada alternativa existente
        for k in self.q_data["alternativas"].keys():
            btn_alt = ui.Button(label=f"Editar {k.upper()}", style=discord.ButtonStyle.secondary, row=1)
            btn_alt.callback = self.make_edit_alt_callback(k)
            self.add_item(btn_alt)
            
        # Botão Nova Alternativa
        btn_nova_alt = ui.Button(label="+ Nova Alternativa", style=discord.ButtonStyle.primary, row=1)
        btn_nova_alt.callback = self.add_new_alt
        self.add_item(btn_nova_alt)

        # Botões Inferiores
        btn_resposta = ui.Button(label="Mudar Resposta", style=discord.ButtonStyle.secondary, row=2)
        btn_resposta.callback = self.edit_resposta
        self.add_item(btn_resposta)

        btn_save = ui.Button(label="💾 Salvar Alterações", style=discord.ButtonStyle.success, row=2)
        btn_save.callback = self.save_changes
        self.add_item(btn_save)

    # Callbacks Dinâmicos 
    async def get_text_input(self, interaction: discord.Interaction, prompt: str) -> str:
        await interaction.response.send_message(f"➡️ {prompt} (Digite no chat)", ephemeral=True)
        
        def check(m):
            return m.author == self.author and m.channel == interaction.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            await msg.delete()
            return msg.content
        except asyncio.TimeoutError:
            return None

    async def edit_enunciado(self, interaction: discord.Interaction):
        novo_texto = await self.get_text_input(interaction, "Digite o novo ENUNCIADO:")
        if novo_texto:
            self.q_data["enunciado"] = novo_texto
            self.build_buttons()
            await interaction.message.edit(embed=self.create_embed(), view=self)

    def make_edit_alt_callback(self, letra):
        # Closure para guardar a letra certa no botão dinâmico
        async def callback(interaction: discord.Interaction):
            novo_texto = await self.get_text_input(interaction, f"Digite o novo texto para a letra **{letra}**:")
            if novo_texto:
                self.q_data["alternativas"][letra] = novo_texto
                self.build_buttons()
                await interaction.message.edit(embed=self.create_embed(), view=self)
        return callback

    async def add_new_alt(self, interaction: discord.Interaction):
        prox_letra = self.letras[len(self.q_data["alternativas"])]
        novo_texto = await self.get_text_input(interaction, f"Digite o texto para a NOVA alternativa (**{prox_letra}**):")
        if novo_texto:
            self.q_data["alternativas"][prox_letra] = novo_texto
            self.build_buttons()
            await interaction.message.edit(embed=self.create_embed(), view=self)

    async def edit_resposta(self, interaction: discord.Interaction):
        nova_resp = await self.get_text_input(interaction, "Qual é a nova letra correta?")
        if nova_resp:
            nova_resp = nova_resp.lower().strip()
            if nova_resp in self.q_data["alternativas"]:
                self.q_data["resposta"] = nova_resp
                self.build_buttons()
                await interaction.message.edit(embed=self.create_embed(), view=self)
            else:
                await interaction.followup.send("❌ Essa letra não existe nas alternativas!", ephemeral=True)

    async def save_changes(self, interaction: discord.Interaction):
        data, gid = get_server_data(self.guild_id)
        data[gid]["questoes"][self.q_index] = self.q_data
        save_questions(data)
        
        await interaction.response.edit_message(content="✅ **Questão atualizada com sucesso!**", embed=self.create_embed(), view=None)
        self.stop()


class QuestionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="addquestion")
    @commands.has_permissions(manage_roles=True)
    async def cmd_addquestion(self, ctx):
        view = AddQuestionView(self.bot, ctx.author, ctx.guild.id)
        msg = await ctx.send(embed=view.create_embed(), view=view)
        await view.wait_for_input(msg)

    @commands.command(name="questions", aliases=["questoes"])
    @commands.has_permissions(manage_roles=True)
    async def cmd_questions(self, ctx):
        data, gid = get_server_data(ctx.guild.id)
        questoes = data[gid]["questoes"]
        nota_minima = data[gid]["nota_minima"]

        if not questoes:
            return await ctx.send("❌ Nenhuma questão cadastrada para este servidor.")

        embed = discord.Embed(
            title="📋 Banco de Questões do Servidor",
            description=f"Nota Mínima para passar: **{nota_minima}**\nTotal de questões: **{len(questoes)}**",
            color=discord.Color.purple()
        )

        for i, q in enumerate(questoes, 1):
            alts = " | ".join([f"{k}) {v}" for k, v in q["alternativas"].items()])
            # Limite de tamanho de campo (Discord suporta 1024 max)
            texto = f"**{q['enunciado']}**\n*{alts}*\n✅ Resposta: **{q['resposta']}**"
            if len(texto) > 1024:
                texto = texto[:1020] + "..."
            embed.add_field(name=f"Questão #{i}", value=texto, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="editquestion")
    @commands.has_permissions(manage_roles=True)
    async def cmd_editquestion(self, ctx):
        data, gid = get_server_data(ctx.guild.id)
        questoes = data[gid]["questoes"]

        if not questoes:
            return await ctx.send("❌ Nenhuma questão cadastrada para este servidor.")

        # Pede o número da questão primeiro
        await ctx.send("➡️ **Qual o NÚMERO da questão que você deseja editar?** (Ex: `1`, `2`)\n*Dica: Use `.questions` para ver os números.*")
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            q_index = int(msg.content.strip()) - 1 # Subtrai 1 pois array começa em 0
            
            if q_index < 0 or q_index >= len(questoes):
                return await ctx.send("❌ Número de questão inválido!")
                
            q_data = questoes[q_index]
            
            # Abre a view de edição
            view = EditQuestionView(self.bot, ctx.author, ctx.guild.id, q_index, q_data)
            view.build_buttons()
            await ctx.send(embed=view.create_embed(), view=view)

        except ValueError:
            await ctx.send("❌ Você deve digitar um número válido.")
        except asyncio.TimeoutError:
            await ctx.send("⏳ Tempo esgotado.")

    @commands.command(name="editpontuation", aliases=["notaminima", "setnota"])
    @commands.has_permissions(manage_roles=True)
    async def cmd_editpontuation(self, ctx, nota: int):
        if nota < 1:
            return await ctx.send("❌ A nota mínima deve ser pelo menos 1.")
            
        data, gid = get_server_data(ctx.guild.id)
        data[gid]["nota_minima"] = nota
        save_questions(data)
        
        await ctx.send(f"✅ A nota mínima para passar no teste agora é **{nota}**!")

async def setup(bot):
    await bot.add_cog(QuestionsCog(bot))