from datetime import datetime, timezone
from typing import Optional, List, Dict
import uuid
from pydantic import BaseModel, Field

class ActionConfig(BaseModel):
    min_coins: int
    max_coins: int
    cooldown_seconds: int

class EconomyConfig(BaseModel):
    brincar: ActionConfig = Field(
        default_factory=lambda: ActionConfig(min_coins=1080, max_coins=2880, cooldown_seconds=120)
    )
    dormir: ActionConfig = Field(
        default_factory=lambda: ActionConfig(min_coins=2520, max_coins=4680, cooldown_seconds=300)
    )
    uivar: ActionConfig = Field(
        default_factory=lambda: ActionConfig(min_coins=3960, max_coins=7560, cooldown_seconds=600)
    )
    cacar: ActionConfig = Field(
        default_factory=lambda: ActionConfig(min_coins=50, max_coins=70, cooldown_seconds=3600)
    )

class StoreItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8], description="ID único curto gerado automaticamente")
    type: str = Field(..., description="Tipo do item: 'cargo' ou 'item'")
    name: str = Field(..., description="Nome do item ou nome do cargo")
    role_id: Optional[int] = Field(None, description="ID do cargo (se o tipo for cargo)")
    price: int = Field(..., description="Preço do item")
    description: Optional[str] = Field(None, description="Descrição do item")
    is_limited: bool = Field(default=False, description="Se possui limite de estoque")
    stock: Optional[int] = Field(None, description="Quantidade disponível no estoque")

# Sorteio
class GiveawayModel(BaseModel):
    prize_type: str = Field(..., description="'cargo' ou 'coins'")
    prize_name: str = Field(..., description="Nome do cargo ou descrição da quantidade de moedas")
    reward_value: int = Field(..., description="ID do cargo ou quantidade de moedas")
    winners_count: int = Field(..., description="Quantidade de vencedores")
    duration_seconds: int = Field(..., description="Duração total em segundos")
    emoji: str = Field(..., description="Emoji usado para reagir")
    channel_id: int = Field(..., description="Canal onde o sorteio foi postado")
    message_id: int = Field(..., description="ID da mensagem do sorteio")
    ends_at: datetime = Field(..., description="Data/Hora em que o sorteio expira")

# Modelo de Salário 
class RoleSalary(BaseModel):
    amount: int = Field(..., description="Quantidade de moedas do salário")
    interval_hours: int = Field(..., description="Intervalo de horas para receber")

class ServerModel(BaseModel):
    server_id: int = Field(..., description="ID do servidor do Discord")
    
    # Cargos do Servidor 
    verified_role_id: Optional[int] = Field(None, description="ID do cargo de Verificado")
    strike_role_id: Optional[int] = Field(None, description="ID do cargo de Strike para punições")
    
    # Canais de log 
    log_channel_id: Optional[int] = Field(None, description="Canal onde os strikes serão logados")

    # Configuração de Economia
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    
    # Loja do Servidor
    store: List[StoreItem] = Field(default_factory=list, description="Lista de itens à venda no servidor")

    # Sorteio Ativo
    giveaway: Optional[GiveawayModel] = Field(None, description="Dados do sorteio ativo no momento")

    # Multiplicadores de Economia por Cargo 
    role_boosts: Dict[str, float] = Field(
        default_factory=dict, 
        description="Mapeia o ID do cargo (em string) para o multiplicador de moedas"
    )

    # Salários por Cargo 
    role_salaries: Dict[str, RoleSalary] = Field(
        default_factory=dict,
        description="Mapeia o ID do cargo (em string) para a configuração de salário daquele cargo"
    )

    def to_mongo(self) -> dict:
        return self.model_dump(exclude_none=True)