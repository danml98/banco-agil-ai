import os
from dotenv import load_dotenv

load_dotenv()  

#### Base Clientes
CAMINHO_BASE_CLIENTES = "data/clientes.csv"

#### API Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

#### Autenticação
TENTATIVAS_AUTENTICACAO = 2

#### Logs
LOG_DIR = "logs"