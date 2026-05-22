from agents.triagem_agent import TriagemAgent
from agents.credito_agent import CreditoAgent
from agents.entrevista_agent import EntrevistaAgent
from agents.cambio_agent import CambioAgent
from graph.nodes import AgentChatContext, encerramento_node, flow_router
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from ui.chat_interface import ChatInterface

triagem_agent = TriagemAgent()
credito_agent = CreditoAgent()
entrevista_agent = EntrevistaAgent()
cambio_agent = CambioAgent()

workflow = StateGraph(AgentChatContext)

# Registro de Nós
workflow.add_node("autenticacao", triagem_agent.autenticar_node)
workflow.add_node("ia_triagem", triagem_agent.triagem_node)
workflow.add_node("encerrar", encerramento_node)
workflow.add_node("agente_credito", credito_agent.node)
workflow.add_node("agente_entrevista", entrevista_agent.node)
workflow.add_node("agente_cambio", cambio_agent.node)

workflow.set_entry_point("autenticacao")

# Configuração de Roteamento 
routing_nodes = ["autenticacao", "ia_triagem", "agente_credito", "agente_entrevista", "agente_cambio"]
destinations = {n: n for n in routing_nodes}
destinations.update({"encerrar": "encerrar", "__end__": END})

for node_name in routing_nodes:
    workflow.add_conditional_edges(node_name, flow_router, destinations)

workflow.add_edge("encerrar", END)

config_memoria = MemorySaver()
app_agente = workflow.compile(checkpointer=config_memoria)

if __name__ == "__main__":
    chat_interface = ChatInterface(app_agente)
    chat_interface.display_chat()
    chat_interface.gerenciar_fluxo_input()