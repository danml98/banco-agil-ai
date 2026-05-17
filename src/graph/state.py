from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentChatContext(TypedDict):
    """Esquema de dados que trafega entre os agentes."""
    messages: Annotated[list, add_messages] # Histórico de chat automático
    cpf_digitado: Optional[str]
    data_nascimento_digitada: Optional[str]
    tentativas: int
    autenticado: bool
    dados_cliente: Optional[dict]
    agente_atual: str