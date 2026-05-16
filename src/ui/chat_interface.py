from agents.triagem_agent import TriagemAgent
from config.settings import TENTATIVAS_AUTENTICACAO
import re
import streamlit as st


class ChatInterface:
    def __init__(self, app_agente):
        self.app_agente = app_agente
        self.triagem_agent = TriagemAgent()
        self._inicializar_memoria_estavel()

    def _inicializar_memoria_estavel(self):
        if "state_grafo" not in st.session_state:
            st.session_state.state_grafo = {
                "messages": [
                    {
                        "role": "assistant", 
                        "content": "\n\n".join(self.triagem_agent.saudacao())
                    }
                ],
                "cpf_digitado": None,
                "data_digitada": None,
                "tentativas": 0,
                "autenticado": False,
                "dados_cliente": None,
                "agente_atual": "ia_triagem",
                "passo_triagem": "COLETANDO_CPF"
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
                # Se for dicionário comum do Python
                role = msg.get("role", "assistant")
                # Se o LangGraph salvou como 'ai', converte para o visual do Streamlit
                if role == "ai": role = "assistant"

            content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
            with st.chat_message(role):
                st.write(content)

    def gerenciar_fluxo_input(self):
        """Gerencia o fluxo de inputs do usuário, controlando a sequência de perguntas para autenticação e depois liberando para solicitações gerais"""
        fase = st.session_state.state_grafo.get("passo_triagem", "COLETANDO_CPF")
        autenticado = st.session_state.state_grafo.get("autenticado", False)
        tentativas = st.session_state.state_grafo.get("tentativas", 0)

        if tentativas >= TENTATIVAS_AUTENTICACAO and not autenticado:
            placeholder_texto = "🔒 Atendimento encerrado por excesso de tentativas."
            st.chat_input(placeholder_texto, disabled=True) 
            return 

        if not autenticado:
            placeholder_texto = "Digite seu CPF..." if fase == "COLETANDO_CPF" else "Digite sua Data de Nascimento (DD/MM/AAAA)..." 
            max_chars = 11 if fase == "COLETANDO_CPF" else 10
        else:
            dados = st.session_state.state_grafo.get('dados_cliente') or {}
            nome_completo = dados.get('nome', 'Cliente')
            placeholder_texto = f"{nome_completo.split()[0]}, já identifiquei o seu cadastro. Como posso ajuda-lo hoje?"
            max_chars = None

        user_input = st.chat_input(placeholder_texto, max_chars=max_chars)
        
        # Script para focar automaticamente no chat assim que a janela carregar
        st.components.v1.html(
            """
            <script>
                window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]').focus();
            </script>
            """,
            height=0, 
        )

        if user_input:
            with st.chat_message("user"):
                st.write(user_input)
            st.session_state.state_grafo["messages"].append({"role": "user", "content": user_input})
                
            if not autenticado:
                if fase == "COLETANDO_CPF":
                    st.session_state.state_grafo["cpf_digitado"] = user_input.strip()
                    st.session_state.state_grafo["passo_triagem"] = "COLETANDO_DATA_NASCIMENTO"

                    st.session_state.state_grafo["messages"].append({
                        "role": "assistant",
                        "content": "Agora, informe sua **data de nascimento no formato DD/MM/AAAA** (Exemplo: 10/10/1990):"
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

                    st.session_state.state_grafo["data_digitada"] = data_digitada
                    # Reseta o passo caso precise coletar novamente, em caso de falha na autenticação
                    st.session_state.state_grafo["passo_triagem"] = "COLETANDO_CPF" 

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