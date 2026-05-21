# Banco Ágil AI

Sistema de atendimento bancário inteligente orquestrado via **LangGraph**, utilizando agentes de IA (Gemini) para autenticação, análise de crédito, entrevista financeira e consulta de câmbio.

---

# Visão Geral

O projeto simula o fluxo de atendimento de um banco digital fictício chamado Banco Ágil. A inteligência do sistema é baseada em um grafo de estados onde cada agente atua como um **Nó (Node)**, e as transições são decididas por um **Roteador (Router)** central.

A solução utiliza o modelo **Gemini** para interpretação de intenções e extração de dados estruturados via Pydantic.

---

# Funcionalidades

## Agente de Triagem
- Autenticação via CPF e data de nascimento
- Controle de tentativas
- Direcionamento automático para agentes especializados

## Agente de Crédito
- Consulta de limite de crédito
- Solicitação de aumento de limite via processamento de linguagem natural
- Aprovação/reprovação baseada no score

## Agente de Entrevista de Crédito
- Coleta dinâmica de dados financeiros (Slot Filling)
- Recalculo de score
- Atualização da base de clientes

## Agente de Câmbio
- Consulta de cotação de moedas em tempo real
- Integração com API externa

---

# Arquitetura do Sistema

```text
UI (Streamlit) ↔ StateGraph (LangGraph)
                    ↓
            [Flow Router (Logic)]
            ↙       ↓       ↘
    [Triagem]   [Crédito]   [Câmbio]
        ↓           ↓           ↓
    [Gemini]    [Gemini]    [API Externa]
```

## Estrutura de Pastas

```text
src/
├── agents/
├── services/
├── utils/
├── data/
├── ui/
└── app.py
```

---

# Tecnologias Utilizadas

- Python
- Streamlit
- LangGraph
- Pydantic
- Gemini API
- Pandas
- Requests

---

# Escolhas Técnicas

O sistema foi desenvolvido utilizando uma arquitetura modular baseada em agentes especializados.

A escolha do Streamlit foi realizada visando simplicidade, rapidez de desenvolvimento e facilidade de demonstração.

As regras de negócio críticas foram implementadas diretamente em código, evitando dependência exclusiva do LLM para validações importantes.

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
streamlit run app.py
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