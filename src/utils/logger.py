import os
from datetime import datetime


LOG_DIR = "src/logs"
os.makedirs(LOG_DIR, exist_ok=True)

def _obter_caminho_log():
    """Cria arquivo por dia"""
    date = datetime.now().strftime("%d%m%Y")
    return os.path.join(LOG_DIR, f"log_{date}.log")


def log(message: str, level: str = "LOG"):
    """Adiciona uma linha na log

        Args:
            message (str): Mensagem a adicionar no arquivo
            level (str): LOG, WARN ou ERROR
    """
    level = level.upper()

    if level not in ["LOG", "WARN", "ERROR"]:
        raise ValueError("Level inválido, utilize LOG, WARN ou ERROR") 

    timestamp = datetime.now().strftime("%d%m%YT%H:%M:%S:%f")[:-3]

    entrada = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }

    linha = f"{timestamp} [{level}] {message}\n"

    file_path = _obter_caminho_log()

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(linha)

    return entrada