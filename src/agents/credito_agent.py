from config.variables import CAMINHO_SOLICITACOES, CAMINHO_SCORE, CAMINHO_BASE_CLIENTES
from datetime import datetime
import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field
from tools.utils import extrair_valor_monetario, formatar_moeda, criar_csv, ler_csv, salvar_csv
from tools.logger import log
from agents.triagem_agent import TriagemAgent


class DecisaoCredito(BaseModel):
    decisao_entrevista: Optional[str] = Field(None, description="Interpretação da resposta sobre fazer entrevista: sim ou não.")
    decisao_pos_aprovacao: Optional[str] = Field(None, description="Interpretação da opção pós-aprovação: aceitar_contraproposta, outro_assunto ou encerrar.")


class CreditoAgent:
    MENU = "MENU_CREDITO"
    AGUARDANDO_VALOR = "AGUARDANDO_VALOR"
    AGUARDANDO_DECISAO_ENTREVISTA = "AGUARDANDO_DECISAO_ENTREVISTA"
    ESCOLHA_POS_APROVACAO = "ESCOLHA_POS_APROVACAO"

    def __init__(self):
        self.caminho_base_clientes = CAMINHO_BASE_CLIENTES
        self.caminho_score = CAMINHO_SCORE
        self.caminho_solicitacoes = CAMINHO_SOLICITACOES
        self.triagem = TriagemAgent()
        self.gemini = self.triagem._gemini_service

        criar_csv(self.caminho_solicitacoes, ["cpf_cliente", "data_hora_solicitacao", "limite_atual", "novo_limite_solicitado", "status_pedido"])

    def node(self, state: dict) -> dict:
        msg = state["messages"][-1]
        ultima_msg = (msg.content if hasattr(msg, 'content') else msg.get('content', '')).strip()
        contexto_anterior = state["messages"][-2].content if len(state["messages"]) >= 2 else ""
        analise_ia = self.triagem.interpretar_solicitacao(ultima_msg, contexto_anterior)
        return self.executar_fluxo(state, analise_ia)

    def executar_fluxo(self, state: dict, analise_ia: dict) -> dict:
        cpf = state["cpf_digitado"]
        nome = state.get("dados_cliente", {}).get("nome", "Cliente")
        passo = state.get("passo_credito") or self.MENU
        entrevista_realizada = state.get("entrevista_realizada", False)
        intencao = analise_ia["intencao"].value

        if intencao == "encerrar":
            return {"agente_atual": "encerrar", "passo_credito": None}
        
        # Handoff Imediato: Se o usuário mudar de assunto (ex: câmbio)
        if intencao not in ["credito", "outro"]:
            return {"agente_atual": intencao, "passo_credito": None, "valor_solicitado": None}

        if intencao == "outro" and passo == self.MENU:
            return {
                "agente_atual": "menu_principal", 
                "passo_credito": None, 
                "valor_solicitado": None, 
                "messages": [{"role": "assistant", "content": "Desculpe, não consegui identificar sua solicitação. Poderia repetir o que deseja?"}]
            }

        # Fluxos de captura de valor
        if passo in [self.MENU, self.AGUARDANDO_VALOR]:
            valor = analise_ia.get("valor_extraido") or state.get("valor_solicitado")
            if not valor and passo == self.AGUARDANDO_VALOR:
                msg = state["messages"][-1]
                texto_valor = msg.content if hasattr(msg, 'content') else msg.get('content', '')
                valor = extrair_valor_monetario(texto_valor)
            
            if valor:
                return self._processar_pedido(cpf, valor, entrevista_realizada)
            
            if analise_ia.get("deseja_aumento") or passo == self.AGUARDANDO_VALOR:
                return {
                    "messages": [{"role": "assistant", "content": "Por favor, digite o valor do novo limite desejado (ex: 5000,00):"}],
                    "passo_credito": self.AGUARDANDO_VALOR,
                }
            
            return {"messages": [{"role": "assistant", "content": self.formatar_consulta_limite(cpf, nome)}], "passo_credito": self.MENU}

        # Fluxos de decisão via IA
        historico = self._montar_historico(state["messages"])
        if passo == self.AGUARDANDO_DECISAO_ENTREVISTA:
            decisao = self._interpretar_decisao(historico, "O cliente responde se deseja a entrevista.")
            if decisao and decisao.decisao_entrevista == "sim":
                return {"agente_atual": "agente_entrevista", "passo_credito": None}
            if decisao and decisao.decisao_entrevista == "não":
                return {
                    "messages": [{"role": "assistant", "content": "Entendido. No que mais posso ajudar?\n\n1- Outro assunto\n\n2- Encerrar"}], 
                    "passo_credito": self.ESCOLHA_POS_APROVACAO
                }
            return {"messages": [{"role": "assistant", "content": "Por favor responda apenas com sim ou não."}], "passo_credito": self.AGUARDANDO_DECISAO_ENTREVISTA}

        if passo == self.ESCOLHA_POS_APROVACAO:
            decisao = self._interpretar_decisao(historico, "O cliente escolhe a próxima ação pós-crédito.")
            if decisao and decisao.decisao_pos_aprovacao == "aceitar_contraproposta":
                return self._processar_pedido(cpf, self._obter_limite_maximo_permitido(cpf), False, posteridade=True)
            if decisao and decisao.decisao_pos_aprovacao == "outro_assunto":
                return {"agente_atual": "menu_principal", "passo_credito": None, "valor_solicitado": None}
            if decisao and decisao.decisao_pos_aprovacao == "encerrar":
                return {"agente_atual": "encerrar", "passo_credito": None}
            return {"messages": [{"role": "assistant", "content": "Não entendi. Por favor escolha uma das opções acima."}], "passo_credito": self.ESCOLHA_POS_APROVACAO}

        return {"agente_atual": "menu_principal", "passo_credito": None, "messages": [{"role": "assistant", "content": "Entendido. Como posso te ajudar em algo mais?"}]}

    def _montar_historico(self, messages: list) -> str:
        historico = []
        for m in messages[-10:]:
            role = getattr(m, 'type', 'ai') if not isinstance(m, dict) else m.get('role', 'user')
            content = getattr(m, 'content', '') if not isinstance(m, dict) else m.get('content', '')
            historico.append(f"{role}: {content}")
        return "\n".join(historico)

    def _interpretar_decisao(self, texto: str, contexto: str) -> Optional[DecisaoCredito]:
        sistema = (
            "Você é um assistente do Banco Ágil que interpreta respostas de clientes em um fluxo de crédito.\n"
            "Identifique se o cliente aceitou ou recusou a entrevista financeira e se ele escolheu uma opção pós-aprovação.\n"
            "Responda usando apenas os campos do schema: decisao_entrevista e decisao_pos_aprovacao.\n"
            "Os valores válidos para decisao_entrevista são 'sim' ou 'não'.\n"
            "Os valores válidos para decisao_pos_aprovacao são 'aceitar_contraproposta', 'outro_assunto' ou 'encerrar'.\n"
            "Se não for possível interpretar, deixe os campos vazios."
        )
        prompt = f"Contexto: {contexto}\n\nMensagem do cliente: {texto}"
        try:
            return self.gemini.gerar_resposta(
                prompt=prompt,
                system_instruction=sistema,
                schema=DecisaoCredito,
            )
        except Exception:
            return None

    def _processar_pedido(self, cpf: str, valor: float, entrevista_realizada: bool, posteridade: bool = False) -> dict:
        limite_atual = self._consultar_limite_disponivel(cpf)
        limite_maximo = self._obter_limite_maximo_permitido(cpf)
        status = "aprovado" if valor <= limite_maximo else "rejeitado"

        if status == "aprovado":
            self._atualizar_cliente(cpf, {"limite": valor})

        self._registrar_solicitacao(cpf, limite_atual, valor, status)

        if status == "aprovado":
            return {
                "messages": [{"role": "assistant", "content": f"Ótima notícia! Seu novo limite de {formatar_moeda(valor)} foi aprovado e já está disponível para uso!\n\nPosso ajuda-lo em algo mais?"}] ,
                "agente_atual": "credito",
                "passo_credito": self.ESCOLHA_POS_APROVACAO,
                "valor_solicitado": None,
            }

        if entrevista_realizada:
            if limite_maximo > 0:
                mensagem = f"Mesmo após a entrevista, não conseguimos liberar {formatar_moeda(valor)}. Seu limite máximo pré-aprovado agora é {formatar_moeda(limite_maximo)}.\n\n1- Solicitar esse limite\n2- Outro assunto\n3- Encerrar"
            else:
                mensagem = "Mesmo após a entrevista, seu perfil ainda não apresenta limite pré-aprovado.\n\nPosso ajuda-lo em algo mais?"
            return {"messages": [{"role": "assistant", "content": mensagem}], "agente_atual": "credito", "passo_credito": self.ESCOLHA_POS_APROVACAO}

        if posteridade and limite_maximo == 0:
            return {"messages": [{"role": "assistant", "content": "Não há limite pré-aprovado disponível para essa opção."}], "passo_credito": self.ESCOLHA_POS_APROVACAO}

        if limite_maximo > 0:
            mensagem = (
                f"No momento não conseguimos liberar {formatar_moeda(valor)}. Seu limite máximo pré-aprovado é {formatar_moeda(limite_maximo)}. " 
                "Mas podemos realizar uma entrevista financeira para tentarmos melhorar o seu score e oferecer um limite mais alto.\n\n"
                "Voce gostaria de realizar a entrevista financeira?\n\n1- Sim\n\n2- Não"
            )
        else:
            mensagem = (
                f"No momento não conseguimos liberar {formatar_moeda(valor)} e não há limite pré-aprovado disponível. "
                "Mas podemos realizar uma entrevista financeira para tentarmos melhorar o seu score e oferecer um limite mais alto.\n\n"
                "Voce gostaria de realizar a entrevista financeira?\n\n1- Sim\n\n2- Não"
            )

        return {"messages": [{"role": "assistant", "content": mensagem}], "passo_credito": self.AGUARDANDO_DECISAO_ENTREVISTA, "valor_solicitado": valor}

    def _consultar_limite_disponivel(self, cpf: str) -> float:
        cliente = self._buscar_cliente(cpf)
        return float(cliente.iloc[0]["limite"]) if not cliente.empty else 0.0

    def _obter_limite_maximo_permitido(self, cpf: str) -> float:
        cliente = self._buscar_cliente(cpf)
        score = int(cliente.iloc[0]["score"]) if not cliente.empty else 0
        tabela_limites = ler_csv(self.caminho_score, skipinitialspace=True)
        faixa = tabela_limites[(tabela_limites["score_minimo"] <= score) & (tabela_limites["score_maximo"] >= score)]
        return float(faixa.iloc[0]["limite_maximo"]) if not faixa.empty else 0.0

    def _buscar_cliente(self, cpf: str) -> pd.DataFrame:
        base_clientes = ler_csv(self.caminho_base_clientes, dtype={"cpf": str})
        return base_clientes[base_clientes["cpf"] == cpf]

    def _atualizar_cliente(self, cpf: str, campos: dict) -> None:
        base_clientes = ler_csv(self.caminho_base_clientes, dtype={"cpf": str})
        seleciona = base_clientes["cpf"] == cpf
        for chave, valor in campos.items():
            base_clientes.loc[seleciona, chave] = valor
        salvar_csv(self.caminho_base_clientes, base_clientes)

    def _registrar_solicitacao(self, cpf: str, limite_atual: float, novo_limite: float, status: str) -> None:
        nova_solicitacao = {
            "cpf_cliente": cpf,
            "data_hora_solicitacao": datetime.now().isoformat(),
            "limite_atual": limite_atual,
            "novo_limite_solicitado": novo_limite,
            "status_pedido": status,
        }
        df_solicitacoes = ler_csv(self.caminho_solicitacoes)
        df_solicitacoes = pd.concat([df_solicitacoes, pd.DataFrame([nova_solicitacao])], ignore_index=True)
        salvar_csv(self.caminho_solicitacoes, df_solicitacoes)
        log(f"Solicitação de crédito para CPF {cpf}: {status} (Solicitado: {novo_limite}, Máximo: {self._obter_limite_maximo_permitido(cpf)})")

    def formatar_consulta_limite(self, cpf: str, nome: str) -> str:
        limite = self._consultar_limite_disponivel(cpf)
        primeiro_nome = nome.split()[0] if nome else "Cliente"
        return (
            f"{primeiro_nome}, seu limite atual disponível é de {formatar_moeda(limite)}.\n\n"
            "Selecione uma opção:\n\n1- Solicitar mais limite\n\n2- Escolher outro assunto\n\n3- Encerrar"
        )

    def calcular_score(self, cpf: str, dados_financeiros: dict) -> int:
        renda = float(dados_financeiros.get("renda_mensal", 0))
        despesas = float(dados_financeiros.get("despesas_mensais", 0))
        tipo_emprego = dados_financeiros.get("tipo_emprego", "desempregado").lower()
        num_dep = int(dados_financeiros.get("num_dependentes", 0))
        tem_dividas = dados_financeiros.get("tem_dividas", "sim").lower()

        pesos_emprego = {"formal": 300, "autônomo": 200, "desempregado": 0}
        pesos_dependentes = {0: 100, 1: 80, 2: 60, 3: 30}
        pesos_dividas = {"sim": -100, "não": 100}

        peso_dependentes = pesos_dependentes.get(num_dep, min(pesos_dependentes.values()))
        peso_emprego = pesos_emprego.get(tipo_emprego, min(pesos_emprego.values()))
        peso_dividas = pesos_dividas.get(tem_dividas, min(pesos_dividas.values()))

        score_base = (renda / (despesas + 1)) * 30
        score_total = score_base + peso_emprego + peso_dependentes + peso_dividas
        novo_score = max(0, min(1000, int(score_total)))

        self._atualizar_cliente(cpf, {"score": novo_score})
        log(f"Novo score calculado para CPF {cpf}: {novo_score}")
        return novo_score
