from datetime import datetime
import pandas as pd
from src.config import settings
from src.utils.logger import log


class AuthService:
    def __init__(self):
        """Autenticação do cliente
        """
        self.base_clientes = pd.read_csv(settings.CAMINHO_BASE_CLIENTES)

    def _normalizar_data(self, data: str):
        """Normaliza as datas para padronizar o formato

        Args:
            data (str): data a ser normalizada
        """
        formatos = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%Y/%m/%d"
        ]

        for fmt in formatos:
            try:
                return datetime.strptime(data, fmt).date()
            except ValueError:
                continue
        return None

    def autenticar(self, cpf: str, data_nascimento: str):
        """Realiza a busca dos dados do cliente na base

        Args:
            cpf (str): CPF do cliente
            data_nascimento (str): data de nascimento do cliente
        
        Returns:
            dict: {
                "status": bool,
                "mensagem": str,
                "dados_cliente": dict | None
            }
        """
        log("Iniciando autenticação do cliente")
        cpf_digitos = "".join(filter(str.isdigit, cpf))

        cliente = self.base_clientes[self.base_clientes["cpf"].astype(str) == cpf_digitos]

        if cliente.empty:
            mensagem = f"CPF {cpf} não encontrado"
            log(mensagem, "WARN")

            return {
                "status_autenticacao": False, 
                "mensagem": mensagem,
                "dados_cliente": None
            }
        
        cliente = cliente.iloc[0]

        data_nascimento = self._normalizar_data(data_nascimento)
        data_nascimento_registro = self._normalizar_data(cliente["data_nascimento"])

        if data_nascimento != data_nascimento_registro:
            mensagem = f"Data de nascimento incorreta"
            log(mensagem, "WARN")

            return {
                "status_autenticacao": False, 
                "mensagem": mensagem,
                "dados_cliente": None
            }
        
        mensagem = "Autenticação realizada com sucesso"
        log(mensagem)

        return {
            "status_autenticacao": True,
            "mensagem": "Autenticação realizada com sucesso",
            "dados_cliente": cliente.to_dict()
        }
