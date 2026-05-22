import requests
from services.gemini_service import GeminiService
from pydantic import BaseModel, Field
from typing import Optional
from tools.logger import log
from tools.utils import formatar_moeda
from agents.triagem_agent import TriagemAgent

class AnaliseCambio(BaseModel):
    moeda_origem: str = Field("BRL", description="Moeda base para conversão (ex: BRL, USD, EUR).")
    moeda_destino: Optional[str] = Field(None, description="Moeda que o cliente deseja saber a cotação (ex: USD, EUR).")
    valor: float = Field(1.0, description="O valor numérico mencionado pelo cliente.")
    valor_referente_a: str = Field("destino", description="Indica se o 'valor' refere-se à 'moeda_origem' (ex: 'tenho 50 reais' -> valor=50, referente='origem') ou 'moeda_destino' (ex: 'quero 50 euros' -> valor=50, referente='destino').")

class CambioAgent:
    def __init__(self):
        self._gemini_service = GeminiService()
        self.triagem = TriagemAgent()
        self._url_api = f"https://economia.awesomeapi.com.br/last/"
        self.instrucao = (
            "Você é um especialista em câmbio do Banco Ágil.",
            "Sua tarefa é extrair os dados para uma cotação de moedas.",
            "Se o cliente não informar a moeda de origem, considere 'BRL' (Real).",
            "Identifique moedas pelo código ISO (USD, EUR, BRL, etc).",
            "Analise cuidadosamente se o valor informado refere-se à moeda que o cliente POSSUI (origem, ex: BRL) ou à que ele DESEJA ADQUIRIR (destino, ex: EUR).",
            "Exemplo: '50 reais para euros' -> valor=50, moeda_origem='BRL', moeda_destino='EUR', valor_referente_a='origem'.",
            "Exemplo: 'comprar 50 euros' -> valor=50, moeda_origem='BRL', moeda_destino='EUR', valor_referente_a='destino'.",
            "Se o cliente disser 'é o contrário' ou corrigir uma conversão, use o histórico para inverter a lógica do campo 'valor_referente_a'.",
            "Atenção: Se a mensagem não for um pedido de cotação ou conversão (ex: perguntas teóricas sobre o que é uma moeda), não identifique a moeda de destino.",
            "Se você não conseguir identificar a moeda de destino, pergunte educadamente ao cliente qual moeda ele gostaria de consultar.",
            "Se o cliente não informar a moeda de destino, deixe o campo vazio no schema."
        )

    def node(self, state: dict) -> dict:
        """Nó que processa solicitações de câmbio."""
        msg = state["messages"][-1]
        ultima_msg = (msg.content if hasattr(msg, 'content') else msg.get('content', '')).strip()
        
        msg_ant = state["messages"][-2] if len(state["messages"]) >= 2 else None
        contexto_anterior = (msg_ant.content if msg_ant and hasattr(msg_ant, 'content') else msg_ant.get('content', '') if msg_ant else "").strip()

        # Valida a intenção antes de processar como câmbio
        analise_triagem = self.triagem.interpretar_solicitacao(ultima_msg, contexto_anterior)
        
        # Só sai do agente se for uma mudança explícita de assunto (ex: crédito)
        # Se for "outro", tentamos processa aqui mesmo no câmbio (pode ser uma correção contextual)
        if analise_triagem["intencao"].value not in ["cambio", "outro"]:
            return {"agente_atual": "menu_principal"}

        historico_lista = []
        for m in state["messages"][-5:]:
            role = "Assistente" if getattr(m, 'type', '') == 'ai' or (isinstance(m, dict) and m.get('role') == 'assistant') else "Usuário"
            content = getattr(m, 'content', '') if not isinstance(m, dict) else m.get('content', '')
            historico_lista.append(f"{role}: {content}")
        historico = "\n".join(historico_lista)

        analise = self._gemini_service.gerar_resposta(
            prompt=f"Histórico:\n{historico}\n\nMensagem atual: {ultima_msg}",
            system_instruction="\n".join(self.instrucao),
            schema=AnaliseCambio
        )

        if not analise or not analise.moeda_destino:
            if analise_triagem["intencao"].value == "outro":
                return {
                    "agente_atual": "menu_principal",
                    "messages": [{"role": "assistant", "content": "Desculpe, não consegui identificar sua solicitação. Poderia repetir o que deseja, por favor?"}]
                }
            return {
                "messages": [{"role": "assistant", "content": "Qual moeda estrangeira você gostaria de consultar hoje? (Ex: Dólar, Euro, Libra)"}],
                "agente_atual": "cambio"
            }

        resultado = self._consultar_api(analise.moeda_origem, analise.moeda_destino, analise.valor, analise.valor_referente_a)
        
        return {
            "messages": [{"role": "assistant", "content": resultado}],
            "agente_atual": "menu_principal"
        }

    def _consultar_api(self, origem: str, destino: str, valor: float, referente: str) -> str:
        """Consulta a cotação de câmbio utilizando a API AwesomeAPI e retorna uma mensagem formatada.

            Args:
                origem (str): Moeda de origem (ex: BRL)
                destino (str): Moeda de destino (ex: USD)
                valor (float): Quantidade da moeda de destino que se deseja converter
                referente (str): Se o valor é da 'origem' ou do 'destino'
            Returns:
                str: Mensagem formatada com a cotação e o valor convertido
        """
        if valor <= 0:
            valor = 1.0
            
        par = f"{destino.upper()}-{origem.upper()}"
        url = f"{self._url_api}{par}"
        
        try:
            log(f"Consultando cotação para {par}")
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return f"Desculpe, não consegui encontrar a cotação para {destino.upper()} em {origem.upper()} no momento."
            
            data = response.json()
            chave = f"{destino.upper()}{origem.upper()}"
            
            if chave not in data:
                return f"Não encontrei informações para a moeda '{destino}'. Tente usar nomes como Dólar ou Euro."

            cotacao = float(data[chave]["bid"])
            
            if referente == "origem":
                # Cliente tem X reais, quer saber quantos Euros dá.
                valor_convertido = valor / cotacao
                msg = f"A cotação atual do {destino.upper()} para {origem.upper()} é {formatar_moeda(cotacao)}.\n\n"
                msg += f"Com {formatar_moeda(valor)}, você consegue adquirir aproximadamente {valor_convertido:.2f} {destino.upper()}."
            else:
                # Cliente quer saber quanto custa X Euros.
                valor_convertido = valor * cotacao
                msg = f"A cotação atual do {destino.upper()} para {origem.upper()} é {formatar_moeda(cotacao)}.\n\n"
                msg += f"Para adquirir {valor:.2f} {destino.upper()}, você precisará de aproximadamente {formatar_moeda(valor_convertido)}."
            
            return msg
        except Exception as e:
            log(f"Erro na consulta de câmbio: {str(e)}", "ERROR")
            return "Tive um problema técnico ao consultar a cotação. Por favor, tente novamente em instantes."