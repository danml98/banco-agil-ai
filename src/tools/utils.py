import os
import pandas as pd
import re
import requests

# Monetarios
def extrair_valor_monetario(texto: str):
    """Extrai o valor monetário brasileiro de um textol

    Args:
        texto (str): Texto do qual extrair o valor
    Returns:
        float: Valor monetário extraído, ou None se não for possível extrair
    """
    texto = texto.upper().replace("R$", "").strip()
    padrao = r"^(\d{1,3}(\.\d{3})*(,\d{2})?|\d+(,\d{2})?|\d+(\.\d{3})*|\d+)$"
    valor_extraido = re.search(padrao, texto)

    if valor_extraido:
        valor_str = valor_extraido.group(1)
        valor_str = valor_str.replace(".", "").replace(",", ".")
        try:
            return float(valor_str)
        except ValueError:
            return None
    return None

def formatar_moeda(valor: float) -> str:
    """Formata valores monetários no padrão brasileiro.

    Args:
        valor (float): Valor a ser formatado
    Returns:
        str: Valor formatado como string no formato brasileiro (ex: R$ 1.234,56)
    """
    return f"R\$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# CSV
def criar_csv(caminho: str, colunas: list):
    """Cria um arquivo CSV vazio com as colunas especificadas, se ele não existir.
    Args:
        caminho (str): Caminho do arquivo CSV a ser criado
        colunas (list): Lista de nomes de colunas
    """
    if not os.path.exists(caminho):
        df = pd.DataFrame(columns=colunas)
        df.to_csv(caminho, index=False)

def ler_csv(caminho: str, dtype: dict = None, skipinitialspace: bool = False) -> pd.DataFrame:
    """Le um CSV
    Args:
        caminho (str): Caminho do arquivo CSV a ser lido
        dtype (dict, optional): Dicionário de tipos de dados para as colunas
        skipinitialspace (bool, optional): Se deve pular espaços iniciais
    Returns:
        pd.DataFrame: DataFrame com os dados do CSV
    """
    return pd.read_csv(caminho, dtype=dtype, skipinitialspace=skipinitialspace)

def salvar_csv(caminho: str, dados: pd.DataFrame):
    """Salva um csv
    Args:
        caminho (str): Caminho do arquivo CSV a ser salvo
        dados (pd.DataFrame): DataFrame com os dados a serem salvos
    """
    dados.to_csv(caminho, index=False)


