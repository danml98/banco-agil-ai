from agents.credito_agent import CreditoAgent
from services.gemini_service import GeminiService
from tools.utils import formatar_moeda
from agents.triagem_agent import TriagemAgent
from pydantic import BaseModel, Field
from typing import Optional, List
from tools.logger import log

class DadosEntrevista(BaseModel):
    renda_mensal: Optional[float] = Field(None, description="Renda mensal bruta do cliente")
    tipo_emprego: Optional[str] = Field(None, description="Tipo de emprego: formal, autônomo ou desempregado")
    despesas_mensais: Optional[float] = Field(None, description="Valor total de despesas fixas")
    num_dependentes: Optional[int] = Field(None, description="Quantidade de dependentes")
    tem_dividas: Optional[str] = Field(None, description="Se possui dívidas (sim/não)")
    pergunta_seguinte: Optional[str] = Field(None, description="A próxima pergunta natural para coletar o que falta, ou uma mensagem de encerramento se tudo estiver preenchido.")
    entrevista_completa: bool = Field(False, description="Define como True apenas quando todos os campos acima foram coletados.")

class EntrevistaAgent:
    def __init__(self):
        self.credito_agent = CreditoAgent()
        self.triagem = TriagemAgent() # Instantiate TriagemAgent
        self.gemini = GeminiService()
        self.instrucao = (
            "Você é um entrevistador de crédito do Banco Ágil. Seu objetivo é preencher o schema DadosEntrevista.",
            "Analise o histórico e extraia os dados já fornecidos.",
            "Se faltar alguma informação, crie uma pergunta educada no campo 'pergunta_seguinte'.",
            "Se o usuário fornecer várias informações de uma vez, capture todas.",
            "Quando tiver todos os dados, defina 'entrevista_completa' como True."
        )

    def node(self, state: dict) -> dict:
        """Nó que encapsula a lógica da entrevista e a interpretação de IA"""
        msg = state["messages"][-1]
        ultima_msg = (msg.content if hasattr(msg, 'content') else msg.get('content', '')).strip()
        contexto_anterior = state["messages"][-2].content if len(state["messages"]) >= 2 else ""
        analise_ia = self.triagem.interpretar_solicitacao(ultima_msg, contexto_anterior)
        return self.executar_fluxo(state, analise_ia)

    def executar_fluxo(self, state: dict, analise_ia: dict) -> dict:
        cpf = state["cpf_digitado"]
        respostas = state.get("respostas_entrevista") or {}
        
        # Acessa as mensagens como objetos (m.type e m.content) em vez de dicionários
        historico_lista = []
        for m in state["messages"][-10:]:
            role = getattr(m, 'type', 'user')
            content = getattr(m, 'content', '')
            historico_lista.append(f"{role}: {content}")
        historico = "\n".join(historico_lista)
        
        dados_confirmados = ", ".join([f"{k}: {v}" for k, v in respostas.items() if v is not None])
        
        resultado_ia = self.gemini.gerar_resposta(
            prompt=f"Dados já coletados: {dados_confirmados}\n\nHistórico recente:\n{historico}\n\nExtraia novos dados e decida o próximo passo.",
            system_instruction="\n".join(self.instrucao),
            schema=DadosEntrevista
        )

        if not resultado_ia:
            return {"messages": [{"role": "assistant", "content": "Desculpe, não consegui compreender. Pode repetir?"}]}

        respostas.update(resultado_ia.model_dump(exclude_none=True))

        if resultado_ia.entrevista_completa:
            novo_score = self.credito_agent.calcular_score(cpf, respostas)
            valor_pendente = state.get("valor_solicitado")
            msg_final = f"Score atualizado para **{novo_score} pontos**."
            if valor_pendente and novo_score > 0:
                msg_final += f"\n\nCom base nesse novo perfil, vou reprocessar seu pedido de {formatar_moeda(valor_pendente)} agora mesmo..."
            
            return {
                "messages": [{"role": "assistant", "content": msg_final}],
                "agente_atual": "credito",
                "entrevista_realizada": True,
                "respostas_entrevista": respostas
            }

        return {
            "messages": [{"role": "assistant", "content": resultado_ia.pergunta_seguinte}],
            "respostas_entrevista": respostas
        }