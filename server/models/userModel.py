from datetime import datetime, timezone
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

class StrikeEntry(BaseModel):
    reason: str
    duration_hours: int
    applied_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    staff_id: int

class ServerProfile(BaseModel):
    # Campos de Economia 
    wallet: int = Field(default=0, description="Saldo de moedas na carteira do usuário")
    bank: int = Field(default=0, description="Saldo de moedas no banco do usuário")

    last_salaries: Dict[str, datetime] = Field(
        default_factory=dict, 
        description="Mapeia o ID do cargo (str) para a data/hora do último recebimento"
    )

    # Campos de Strike 
    has_strike: bool = Field(default=False, description="Indica se o usuário possui strike ativo")
    strike_count: int = Field(default=0, description="Quantidade total de strikes recebidos aqui")
    strike_expires_at: Optional[datetime] = Field(None, description="Data em que o strike atual deve ser removido")
    strike_history: List[StrikeEntry] = Field(default_factory=list, description="Histórico detalhado de strikes")

class UserModel(BaseModel):
    discord_id: int = Field(..., description="ID único de usuário no Discord")
    
    # Dict de servidores 
    servers: Dict[str, ServerProfile] = Field(default_factory=dict, description="Status e dados do usuário em cada servidor")
    
    # Timestamps globais
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_mongo(self) -> dict:
        return self.model_dump(exclude_none=True)
