import os
from typing import Type
from google import genai
from pydantic import BaseModel
from config.settings import GEMINI_API_KEY
from utils.logger import log


class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não encontrada. Por favor, defina a variável no arquivo .env.")
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "gemini-2.5-flash"  

    def gerar_resposta(self, prompt: str, system_instruction:str, schema: Type[BaseModel]):
        """Gera uma resposta utilizando o modelo Gemini

        Args:
            prompt (str): Pergunta ou mensagem do cliente
            system_instruction (str): Instrução para o modelo sobre o comportamento esperado
            schema (Type[BaseModel]): Esquema de validação da resposta esperada
        
        Returns:
            dict: Resposta gerada pelo modelo, validada e convertida para dicionário
        """

        try:
            log(f"Gerando resposta para o prompt: {prompt}")
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "schema": schema,
                    "system_instruction": system_instruction
                }
            )
            return response.parsed
        except Exception as e:
            log(f"Erro ao gerar resposta com Gemini: {str(e)}", "ERROR")
            return None