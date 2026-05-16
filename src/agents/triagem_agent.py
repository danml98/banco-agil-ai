from config.prompts import PromptsTriagem
import enum
from pydantic import BaseModel, Field
from config.settings import TENTATIVAS_AUTENTICACAO
from services.auth_service import AuthService
from services.gemini_service import GeminiService
from utils.logger import log


class Intencao(str, enum.Enum):
    CREDITO = "credito"
    CAMBIO = "cambio"
    ENCERRAR = "encerrar"
    OUTRO = "outro"

class AnaliseMensagem(BaseModel):
    intencao: Intencao = Field(description="A intenção principal do cliente baseada na mensagem.")
    detalhes: str = Field(description="Breve explicação de por que você tomou essa decisão.")

class TriagemAgent:
    def __init__(self):
        self._authcliente = AuthService()
        self.max_tentativas_autenticacao = TENTATIVAS_AUTENTICACAO
        self._gemini_service = GeminiService()
        self.instrucao_sistema = PromptsTriagem.INSTRUCAO_SISTEMA

    def saudacao(self):
        """ Retorna a mensagem de saudação

        Returns:
            list: Linhas da mensagem de saudação
        """
        return [
            "Olá, seja muito bem vindo ao atendimento do banco Agil!",
            "Sou Agilia, assistente virtual do Banco Ágil. Para começarmos o atendimento com segurança, **por favor, digite o seu CPF (apenas números):**"
        ]

    def validar_cpf(self, cpf: str):
        """Valida se o CPF é válido

        Args:
            cpf (str): CPF do cliente
        Returns:
            dict: {
                "status": bool,
                "mensagem": str,
                "dados_cliente": dict | None
            }
        """

        if len(cpf) != 11:
            return False
        return True
    
    def autenticacao(self, cpf: str, data_nascimento: str, tentativa: int):
        dados_autenticacao = self._authcliente.autenticar(cpf, data_nascimento)

        if not dados_autenticacao["status_autenticacao"]:
            if tentativa >= self.max_tentativas_autenticacao:
                dados_autenticacao["mensagem"] += f". Por favor, tente novamente. Tentatativa {tentativa + 1}/{self.max_tentativas_autenticacao}"
                return dados_autenticacao
            else:
                dados_autenticacao["mensagem"] = f"Não foi possível concluir sua autenticação após {self.max_tentativas_autenticacao} tentativas. Por segurança, encerraremos esse atendimento, mas você pode tentar novamente mais tarde."
                log(f"Cliente com CPF {cpf} atingiu o número máximo de tentativas de autenticação", "WARN")
                return dados_autenticacao
            
        log(f"Cliente com CPF {cpf} autenticado com sucesso")
        return dados_autenticacao
    
    def interpretar_solicitacao(self, mensagem: str):
        """Interpreta a mensagem do cliente para identificar a intenção

        Args:
            mensagem (str): Mensagem do cliente
        
        Returns:
            dict: {
                "intencao": Intencao,
                "detalhes": str
            }
        """
        

        try:
            log(f"Interpretando a mensagem do cliente: {mensagem}")

            resposta = self._gemini_service.gerar_resposta(
                prompt=f"Mensagem do cliente: {mensagem}",
                system_instruction=self.instrucao_sistema,
                schema=AnaliseMensagem
            )

            if resposta is None:
                log("Não foi possível interpretar a solicitação do cliente", "ERROR")
                return {
                    "intencao": Intencao.OUTRO,
                    "detalhes": "Não foi possível interpretar a solicitação do cliente"
                }

            log(f"Intenção identificada: {resposta['intencao']}")
            return resposta
        except Exception as e:
            log(f"Erro ao interpretar a mensagem do cliente: {str(e)}", "ERROR")
            return {
                "intencao": Intencao.OUTRO,
                "detalhes": "Não foi possível interpretar a solicitação do cliente"
            }