from datetime import datetime
import enum
from typing import Optional
from pydantic import BaseModel, Field
from config.variables import TENTATIVAS_AUTENTICACAO, CAMINHO_BASE_CLIENTES
from services.gemini_service import GeminiService
from tools.logger import log
from tools.utils import ler_csv

class Intencao(str, enum.Enum):
    CREDITO = "credito"
    CAMBIO = "cambio"
    ENCERRAR = "encerrar"
    OUTRO = "outro"

class AnaliseMensagem(BaseModel):
    intencao: Intencao = Field(description="A intenção principal do cliente baseada na mensagem.")
    detalhes: str = Field(description="Breve explicação de por que você tomou essa decisão.")
    valor_extraido: Optional[float] = Field(None, description="O valor numérico solicitado pelo cliente, se mencionado (ex: 5000).")
    deseja_aumento: bool = Field(False, description="Define como True se o cliente expressou explicitamente o desejo de aumentar o limite, mesmo sem citar valores.")

class TriagemAgent:
    INSTRUCOES = (
        "Você é o motor de triagem do Banco Ágil. Categorize a mensagem em: credito, cambio, encerrar ou outro.\n"
        "Extraia valores numéricos e identifique se há desejo de aumento de limite.\n"
        "Se o cliente aceitar um valor oferecido (ex: 'aceito os 6'), extraia o valor total (ex: 6000)."
    )

    def __init__(self):
        self._gemini_service = GeminiService()

    def _normalizar_data(self, data: str):
        for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"]:
            try: return datetime.strptime(data, fmt).date()
            except (ValueError, TypeError): continue
        return None

    def saudacao(self):
        return [
            "Olá, seja muito bem vindo ao atendimento do banco Agil!",
            "Sou Agilia, assistente virtual do Banco Ágil.",
            'Para encerrar o atendimento, basta digitar "encerrar" a qualquer momento.',
            "Para começarmos o atendimento com segurança, por favor, digite o seu CPF:"
        ]

    def autenticar_node(self, state: dict) -> dict:
        if state.get("autenticado"): return {}

        cpf = state.get("cpf_digitado")
        data_nasc = state.get("data_nascimento_digitada")
        tentativas = state.get("tentativas", 0)

        if state["messages"][-1].content.lower().strip() == "encerrar": return {"agente_atual": "encerrar"}

        base = ler_csv(CAMINHO_BASE_CLIENTES, dtype={"cpf": str})
        cliente = base[base["cpf"] == "".join(filter(str.isdigit, cpf or ""))]

        if cliente.empty:
            return self._falha_auth(tentativas, "CPF não encontrado", "cpf")
        
        cliente = cliente.iloc[0]
        dt_user, dt_reg = self._normalizar_data(data_nasc), self._normalizar_data(cliente["data_nascimento"])

        if dt_user != dt_reg:
            return self._falha_auth(tentativas, "Data de nascimento incorreta", "data")

        nome = cliente.get("nome", "Cliente").split()[0]
        return {
            "autenticado": True,
            "dados_cliente": cliente.to_dict(),
            "agente_atual": "menu_principal",
            "messages": [{"role": "assistant", "content": f"{nome}, identifiquei seu cadastro. Como posso ajuda-lo hoje?"}]
        }

    def _falha_auth(self, tent, msg, erro):
        if tent >= TENTATIVAS_AUTENTICACAO - 1:
            return {"agente_atual": "encerrar", "messages": [{"role": "assistant", "content": f"{msg}. Limite de tentativas excedido."}]}
        
        res = {"tentativas": tent + 1, "passo_triagem": "COLETANDO_CPF" if erro == "cpf" else "COLETANDO_DATA_NASCIMENTO", 
                "messages": [{"role": "assistant", "content": f"{msg}. Tente novamente ({tent + 1}/{TENTATIVAS_AUTENTICACAO}):"}]}
        if erro == "cpf": res.update({"cpf_digitado": None, "data_nascimento_digitada": None})
        return res

    def triagem_node(self, state: dict) -> dict:
        msg = state["messages"][-1].content
        analise = self.interpretar_solicitacao(msg)

        if analise["intencao"] == Intencao.OUTRO:
            return {
                "agente_atual": "menu_principal",
                "messages": [{"role": "assistant", "content": "Não identifiquei sua solicitação. Pode repetir?"}]
            }

        return {"agente_atual": analise["intencao"].value, "valor_solicitado": analise.get("valor_extraido"), "intencao_aumento": analise.get("deseja_aumento", False)}

    def interpretar_solicitacao(self, mensagem: str, contexto: str = ""):
        prompt = f"Contexto: {contexto}\n\nMensagem: {mensagem}" if contexto else f"Mensagem: {mensagem}"
        resposta = self._gemini_service.gerar_resposta(prompt, self.INSTRUCOES, AnaliseMensagem)
        return resposta.model_dump() if resposta else {"intencao": Intencao.OUTRO, "detalhes": "Erro na IA", "valor_extraido": None, "deseja_aumento": False}
