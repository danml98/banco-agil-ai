from agents.triagem_agent import TriagemAgent
from config.settings import TENTATIVAS_AUTENTICACAO
from graph.state import AgentChatContext
from langgraph.graph import END


class WorkflowHandlers:
    def __init__(self):
        self.triagem_agent = TriagemAgent()

    def autenticacao_handler(self, state: AgentChatContext) -> dict:
        """Handler responsável por interceptar o contexto e enviar para a autenticação

        Args:
            state (AgentChatContext): Dicionario contendo os dados do chat e a mensagem do cliente
        """
        cpf = state.get("cpf_digitado")
        data_nascimento = state.get("data_nascimento_digitada")
        tentativa_atual = state.get("tentativas", 0)

        resultado = self.triagem_agent.autenticacao(cpf, data_nascimento, tentativa_atual)

        if resultado["status_autenticacao"]:
            return {
                "autenticado": True,
                "dados_cliente": resultado["dados_cliente"],
                "agente_atual": "menu_principal",
                "messages": [{"role": "assistant", "content": resultado["mensagem"]}]
            }
        else:
            nova_tentativa = tentativa_atual + 1
            return {
                "autenticado": False,
                "tentativas": nova_tentativa,
                "messages": [{"role": "assistant", "content": resultado["mensagem"]}]
            }
        
    def interpretacao_solicitacao_handler(self, state: AgentChatContext) -> dict:
        """Handler responsável por acionar o Gemini para interpretar o texto do cliente."""
        ultima_mensagem = state["messages"][-1].content
        
        # Consome o método de IA do seu agente de triagem
        analise = self.triagem_agent.interpretar_solicitacao(ultima_mensagem)
        
        return {
            "agente_atual": analise["intencao"].value
        }

    def flow_router(self, state: AgentChatContext) -> str:
        """Roteador do fluxo. Lê o estado atualizado e decide o próximo passo."""
        if not state["autenticado"]:
            if state.get("tentativas", 0) >= TENTATIVAS_AUTENTICACAO and not state.get("autenticado"):
                return "encerrar"
            
        if not state.get("autenticado"):
            return "__end__"
        
        if state.get("agente_atual") == "menu_principal":
            return "__end__"

        if state["agente_atual"] == "credito":
            return "agente_credito"
        if state["agente_atual"] == "cambio":
            return "agente_cambio"
        if state["agente_atual"] == "encerrar":
            return "encerrar"
            
        return "ia_triagem"
