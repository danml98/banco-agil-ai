from config.variables import TENTATIVAS_AUTENTICACAO
from typing import TypedDict, Annotated, Optional
from langgraph.graph.message import add_messages

class AgentChatContext(TypedDict):
    """Esquema de dados que trafega entre os agentes"""
    messages: Annotated[list, add_messages] # Historico do chat
    cpf_digitado: Optional[str]
    data_nascimento_digitada: Optional[str]
    tentativas: int
    autenticado: bool
    passo_triagem: Optional[str]
    dados_cliente: Optional[dict]
    agente_atual: str
    intencao_aumento: bool
    passo_credito: Optional[str]
    valor_solicitado: Optional[float]
    passo_entrevista: Optional[str]
    respostas_entrevista: Optional[dict]
    entrevista_realizada: bool

def encerramento_node(state: AgentChatContext) -> dict:
    """Handler final que envia a mensagem de despedida.
    O conteúdo da mensagem varia dependendo se o cliente escolheu encerrar ou se foi forçado a encerrar após falha de autenticação.
    Args:
        state (AgentChatContext): O estado atual do chat, contendo o histórico de mensagens e informações do cliente.
    Returns:
        dict: Um dicionário contendo a mensagem de despedida e a indicação de que o agente atual é "encerrar".
    """
    # Acesso seguro à última mensagem
    msg = state["messages"][-1] if state.get("messages") else None
    content = ""
    if msg:
        content = (msg.content if hasattr(msg, 'content') else msg.get('content', '')).lower().strip()

    if state.get("agente_atual") == "encerrar" or content == "encerrar":
        msg_despedida = "Ok, você decidiu encerrar este atendimento!\n\nSaiba que estou à disposição sempre que precisar. \n\nO Banco Ágil agradece o seu contato. \n\nAté logo!"
    else:
        msg_despedida = "Atendimento encerrado. O Banco Ágil agradece o seu contato."

    return {
        "messages": [{"role": "assistant", "content": msg_despedida}],
        "agente_atual": "encerrar"
    }

def flow_router(state: AgentChatContext) -> str:
    """Roteador do fluxo. Lê o estado atualizado e decide o próximo passo.
    Args:
        state (AgentChatContext): O estado atual do chat, contendo o histórico de mensagens, informações do cliente e o agente atual.
    Returns:
        str: O nome do próximo nó a ser executado, ou END para finalizar o fluxo."""
    msg = state["messages"][-1]
    
    # Acesso seguro: Objetos do LangGraph usam atributos, dicionários (Streamlit) usam .get()
    if hasattr(msg, 'content'):
        role = getattr(msg, 'type', 'ai')
        content = msg.content.lower().strip()
    else:
        role = msg.get('role', 'user')
        content = msg.get('content', '').lower().strip()
    
    agente = state.get("agente_atual")

    if role in ["ai", "assistant"]:
        if agente == "credito" and not state.get("passo_credito") and state.get("valor_solicitado"):
            return "agente_credito"
        return "__end__"

    if content == "encerrar" or agente == "encerrar":
        return "encerrar"
        
    if not state.get("autenticado"):
        return "encerrar" if state.get("tentativas", 0) >= TENTATIVAS_AUTENTICACAO else "__end__"
    
    if agente == "menu_principal":
        return "ia_triagem"

    # Mapeamento simples de intenção para nome de nó
    mapping = {"credito": "agente_credito", "cambio": "agente_cambio"}
    return mapping.get(agente, agente)
