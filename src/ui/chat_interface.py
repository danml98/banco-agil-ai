from agents.triagem_agent import TriagemAgent
from config.variables import TENTATIVAS_AUTENTICACAO
import re
import streamlit as st


class ChatInterface:
    def __init__(self, app_agente):
        self.app_agente = app_agente
        self.triagem_agent = TriagemAgent()
        self._inicializar_memoria_estavel()

    def _inicializar_memoria_estavel(self):
        """
        Inicializa o estado do grafo na sessão do Streamlit, garantindo que o histórico de mensagens e os dados de autenticação sejam preservados durante a interação.
        """
        if "state_grafo" not in st.session_state:
            st.session_state.state_grafo = {
                "messages": [
                    {
                        "role": "assistant", 
                        "content": "\n\n".join(self.triagem_agent.saudacao())
                    }
                ],
                "cpf_digitado": None,
                "data_nascimento_digitada": None,
                "tentativas": 0,
                "autenticado": False,
                "dados_cliente": None,
                "agente_atual": "autenticacao",
                "passo_triagem": "COLETANDO_CPF",
                "passo_entrevista": None,
                "respostas_entrevista": {},
                "entrevista_realizada": False
            }

    def display_chat(self):
        """Renderiza o titulo e o histórico de mensagens tratando objetos e dicionários."""
        st.set_page_config(page_title="Banco Ágil - Atendimento Virtual", page_icon="🏦")
        st.title("Atendimento Banco Ágil")

        for msg in st.session_state.state_grafo["messages"]:
            if hasattr(msg, 'type'):
                # Se for objeto nativo do LangGraph (AIMessage, HumanMessage)
                role = "assistant" if msg.type == "ai" else "user"
            elif hasattr(msg, 'role'):
                role = msg.role
            else:
                role = msg.get("role", "assistant")
                if role == "ai": role = "assistant"

            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
            with st.chat_message(role):
                st.write(content)

    def gerenciar_fluxo_input(self):
        """Gerencia o fluxo de inputs do usuário, controlando a sequência de perguntas para autenticação e depois liberando para solicitações gerais"""
        fase = st.session_state.state_grafo.get("passo_triagem", "COLETANDO_CPF")
        autenticado = st.session_state.state_grafo.get("autenticado", False)
        tentativas = st.session_state.state_grafo.get("tentativas", 0)
        agente_atual = st.session_state.state_grafo.get("agente_atual")

        if (tentativas > TENTATIVAS_AUTENTICACAO and not autenticado) or agente_atual == "encerrar":
            if agente_atual == "encerrar":
                placeholder_texto = "Você encerrou este atendimento"
            else:
                placeholder_texto = "Atendimento encerrado por excesso de tentativas de autenticação."
            st.chat_input(placeholder_texto, disabled=True) 
            return 

        if not autenticado:
            placeholder_texto = "Digite seu CPF..." if fase == "COLETANDO_CPF" else "Digite sua Data de Nascimento (DD/MM/AAAA)..." 
            max_chars = 14 if fase == "COLETANDO_CPF" else 10
        else:
            if agente_atual == "credito" or agente_atual == "cambio":
                placeholder_texto = "Digite sua resposta..."
            elif agente_atual == "agente_entrevista":
                placeholder_texto = "Responda à pergunta acima..."
            else:
                placeholder_texto = "Digite sua solicitação (ex: crédito, câmbio)..."
            max_chars = None

        user_input = st.chat_input(placeholder_texto, max_chars=max_chars)
        
        # foca automaticamente no chat assim que a janela carregar
        st.iframe(
            """
            <script>
                window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]').focus();
            </script>
            """,
            height=1, 
        )

        if user_input:
            with st.chat_message("user"):
                st.write(user_input)
            st.session_state.state_grafo["messages"].append({"role": "user", "content": user_input})
                
            # Interceptação global de encerramento 
            if user_input.strip().lower() == "encerrar":
                self._disparar_grafo_agentes()
                return

            if not autenticado:
                if fase == "COLETANDO_CPF":
                    cpf_limpo = "".join(filter(str.isdigit, user_input))

                    if len(cpf_limpo) != 11:
                        st.session_state.state_grafo["messages"].append({
                            "role": "assistant",
                            "content": "O CPF deve conter exatamente 11 números. Por favor, informe seu CPF novamente:"
                        })
                        st.rerun()

                    st.session_state.state_grafo["cpf_digitado"] = cpf_limpo
                    st.session_state.state_grafo["passo_triagem"] = "COLETANDO_DATA_NASCIMENTO"

                    st.session_state.state_grafo["messages"].append({
                        "role": "assistant",
                        "content": "Agora, informe sua data de nascimento no formato DD/MM/AAAA (Exemplo: 10/10/1990):"
                    })
                    st.rerun()
                
                elif fase == "COLETANDO_DATA_NASCIMENTO":
                    data_digitada = user_input.strip()

                    formato_data_valido = re.match(r"^\d{2}/\d{2}/\d{4}$", data_digitada)

                    if not formato_data_valido:
                        st.session_state.state_grafo["messages"].append({
                            "role": "assistant",
                            "content": "Formato de data inválido. Por favor, digite no formato DD/MM/AAAA (Exemplo: 10/10/1990):"
                        })
                        st.rerun()

                    st.session_state.state_grafo["data_nascimento_digitada"] = data_digitada

                    self._disparar_grafo_agentes()
            else:
                self._disparar_grafo_agentes()

    def _disparar_grafo_agentes(self):
        """Chama a execução do LangGraph"""
        try:
            config_agente = {"configurable": {"thread_id": "cliente_banco_agil"}}

            novo_estado = self.app_agente.invoke(
                st.session_state.state_grafo, 
                config=config_agente
            )

            st.session_state.state_grafo = novo_estado
        except Exception as e:
            st.session_state.state_grafo["messages"].append({
                "role": "assistant",
                "content": f"Desculpe-me, enfrentamos uma instabilidade técnica momentânea. Código de erro: {str(e)}"
            })
        st.rerun()