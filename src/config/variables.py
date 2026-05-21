import os
from dotenv import load_dotenv

load_dotenv()  

#### Caminho base do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#### Pasta base de dados
BASE_DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(BASE_DATA_DIR, exist_ok=True)

#### Base Clientes
CAMINHO_BASE_CLIENTES = os.path.join(BASE_DATA_DIR, "clientes.csv")

#### Bases Crédito
CAMINHO_SOLICITACOES = os.path.join(BASE_DATA_DIR, "solicitacoes_aumento_limite.csv")
CAMINHO_SCORE = os.path.join(BASE_DATA_DIR, "score_limite.csv")

#### API Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

#### Autenticação
TENTATIVAS_AUTENTICACAO = 2

#### Logs
LOG_DIR = os.path.join(BASE_DIR, "logs")