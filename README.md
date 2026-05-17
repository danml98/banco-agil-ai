# Banco Ágil AI

Sistema de atendimento bancário inteligente utilizando agentes de IA para autenticação, análise de crédito, entrevista financeira e consulta de câmbio.

---

# Visão Geral

O projeto simula o fluxo de atendimento de um banco digital fictício chamado Banco Ágil, utilizando múltiplos agentes especializados para atender diferentes demandas dos clientes.

Os agentes trabalham de forma integrada, proporcionando uma experiência contínua para o usuário.

---

# Funcionalidades

## Agente de Triagem
- Autenticação via CPF e data de nascimento
- Controle de tentativas
- Direcionamento automático para agentes especializados

## Agente de Crédito
- Consulta de limite de crédito
- Solicitação de aumento de limite
- Aprovação/reprovação baseada no score

## Agente de Entrevista de Crédito
- Coleta de dados financeiros
- Recalculo de score
- Atualização da base de clientes

## Agente de Câmbio
- Consulta de cotação de moedas em tempo real
- Integração com API externa

---

# Arquitetura do Sistema

```text
UI (Streamlit)
    ↓
Router Central
    ↓
Agentes Especializados
    ↓
Services
    ↓
CSV / APIs Externas
```

## Estrutura de Pastas

```text
src/
├── agents/
├── services/
├── utils/
├── data/
├── prompts/
├── ui/
└── main.py
```

---

# Tecnologias Utilizadas

- Python
- Streamlit
- Gemini API
- Pandas
- CSV
- Requests

---

# Escolhas Técnicas

O sistema foi desenvolvido utilizando uma arquitetura modular baseada em agentes especializados.

A escolha do Streamlit foi realizada visando simplicidade, rapidez de desenvolvimento e facilidade de demonstração.

As regras de negócio críticas foram implementadas diretamente em código, evitando dependência exclusiva do LLM para validações importantes.

---

# Desafios Enfrentados

- Gerenciamento de estado conversacional no Streamlit
- Roteamento implícito entre agentes
- Persistência de dados em CSV
- Tratamento de erros em APIs externas

---

# Como Executar

## Clone o projeto

```bash
git clone <repo>
```

## Instale as dependências

```bash
pip install -r requirements.txt
```

## Configure o arquivo .env

```env
GEMINI_API_KEY=sua_chave
```

## Execute o projeto

```bash
streamlit run src/main.py
```

---

# Possíveis Melhorias Futuras

- Banco de dados relacional
- Memória conversacional avançada
- Autenticação mais robusta
- Histórico de atendimento
- Dockerização

---

# Autor

Danilo Mandaio de Lima