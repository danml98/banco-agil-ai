import os
import time
from typing import Type
from google import genai
from pydantic import BaseModel
from config.variables import GEMINI_API_KEY
from tools.logger import log


class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não encontrada. Por favor, defina a variável no arquivo .env.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"  

    def gerar_resposta(self, prompt: str, system_instruction: str, schema: Type[BaseModel], max_retries: int = 3):
        """Gera uma resposta utilizando o modelo Gemini

        Args:
            prompt (str): Pergunta ou mensagem do cliente
            system_instruction (str): Instrução para o modelo sobre o comportamento esperado
            schema (Type[BaseModel]): Esquema de validação da resposta esperada
            max_retries (int): Número máximo de tentativas em caso de erro temporário (503)
        
        Returns:
            dict: Resposta gerada pelo modelo, validada e convertida para dicionário
        """

        for tentativa in range(max_retries):
            try:
                log(f"Gerando resposta para o prompt (Tentativa {tentativa + 1}): {prompt}")
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": schema,
                        "system_instruction": system_instruction
                    }
                )
                return response.parsed
            except Exception as e:
                if "503" in str(e) and tentativa < max_retries - 1:
                    wait_time = (tentativa + 1) * 2 
                    log(f"Gemini ocupado (503). Tentando novamente em {wait_time}s...", "WARN")
                    time.sleep(wait_time)
                    continue
                
                log(f"Erro ao gerar resposta com Gemini: {str(e)}", "ERROR")
                return None