from graph.handlers import WorkflowHandlers
from graph.state import AgentChatContext
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from ui.chat_interface import ChatInterface


handlers = WorkflowHandlers()
workflow = StateGraph(AgentChatContext)

workflow.add_node("autenticacao", handlers.autenticacao_handler)
workflow.add_node("ia_triagem", handlers.interpretacao_solicitacao_handler)

workflow.set_entry_point("autenticacao")

workflow.add_conditional_edges(
    "autenticacao",
    handlers.flow_router,
    {
        "autenticacao": "autenticacao",
        "ia_triagem": "ia_triagem",
        "encerrar": END,
        "__end__": END
    }
)

workflow.add_conditional_edges(
    "ia_triagem",
    handlers.flow_router,
    {
        "ia_triagem": "ia_triagem",
        "agente_credito": END,
        "agente_cambio": END,
        "encerrar": END,
        "__end__": END
    }
)

config_memoria = MemorySaver()
app_agente = workflow.compile(checkpointer=config_memoria)

if __name__ == "__main__":
    chat_interface = ChatInterface(app_agente)
    chat_interface.display_chat()
    chat_interface.gerenciar_fluxo_input()