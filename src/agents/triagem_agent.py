from src.services.auth_service import AuthService
from src.utils.logger import log


class TriagemAgent:
    def __init__(self):
        self._authcliente = AuthService()
        self.max_tentativas_autenticacao = 3

    def saudacao(self):
        """ Retorna a mensagem de saudação

        Returns:
            list: Linhas da mensagem de saudação
        """
        return [
            "Olá, seja muito bem vindo ao atendimento do banco Agil!",
            "Sou Agilia, assistente virtual do Banco Ágil."
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
            if tentativa + 1 < self.max_tentativas_autenticacao:
                dados_autenticacao["mensagem"] += f". Por favor, tente novamente. Tentatativa {tentativa + 1}/{self.max_tentativas_autenticacao}"
                return dados_autenticacao
            else:
                dados_autenticacao["mensagem"] = "Não foi possível concluir sua autenticação após 3 tentativas. Por segurança, encerraremos esse atendimento, mas você pode tentar novamente mais tarde."
                log(f"Cliente com CPF {cpf} atingiu o número máximo de tentativas de autenticação", "WARN")
                return dados_autenticacao
            
        log(f"Cliente com CPF {cpf} autenticado com sucesso")
        return dados_autenticacao