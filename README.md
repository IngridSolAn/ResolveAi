# 🤖 ResolveAi

O **ResolveAi** é uma solução inteligente baseada em Inteligência Artificial projetada para automatizar, otimizar e gerenciar processos de suporte e atendimento. O projeto integra técnicas avançadas de RAG (Retrieval-Augmented Generation) com ferramentas de gerenciamento de serviços (como o GLPI) para interagir com usuários de forma autônoma e resolutiva.

---

## 🎯 Objetivo Principal

O maior objetivo desta IA generativa é **reduzir drasticamente o tempo de resposta e o esforço humano no atendimento a chamados técnicos e operacionais**. 

Utilizando a arquitetura RAG, o sistema não apenas gera textos fluidos, mas **garante respostas precisas e fundamentadas** na própria base de conhecimento da empresa (ou nos documentos contidos em `data/samples`). Em vez de um atendente humano buscar manualmente resoluções passadas no GLPI, o ResolveAi analisa o problema, consulta o histórico e os manuais integrados, formula a solução ideal em linguagem natural e pode interagir diretamente com o chamado, escalando para equipes humanas apenas os casos estritamente complexos e atípicos.

---

## 🚀 Funcionalidades Principais

* **Integração com GLPI:** Conexão nativa para leitura, atualização e resolução de chamados baseados na base de conhecimento.
* **Mecanismo RAG (Retrieval-Augmented Generation):** Busca contextual em documentos e dados amostrais para gerar respostas sem alucinações.
* **Ambiente Dockerizado:** Facilidade no deploy e isolamento de dependências com Docker Compose.
* **Arquitetura Modular:** Separação clara entre o `backend`, a lógica do core (`src`) e os ambientes de homologação/testes.

---

## 📁 Estrutura do Repositório

```text
├── .vscode/               # Configurações do ambiente de desenvolvimento no VS Code
├── backend/               # Código fonte da API e backend do ResolveAi
├── data/samples/          # Dados e documentos de exemplo para o motor de RAG
├── glpi/                  # Scripts e integrações específicas com a API do GLPI
├── src/                   # Core do ecossistema e lógicas principais da aplicação
├── tests/                 # Suíte de testes unitários e de integração
├── .env.example           # Modelo de variáveis de ambiente obrigatórias
├── app.py                 # Ponto de entrada (entrypoint) da aplicação
├── docker-compose.yml     # Configuração dos containers Docker
├── requirements.txt       # Dependências gerais do sistema
└── requirements-rag.txt   # Dependências específicas para os modelos de IA/RAG
```

---

## 🛠️ Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
* [Python 3.10+](https://python.org)
* [Docker](https://docker.com) e [Docker Compose](https://docker.com)

---

## ⚙️ Instalação e Configuração

### 1. Clonar o Repositório
```bash
git clone https://github.com
cd ResolveAi
```

### 2. Configurar as Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto copiando as propriedades do `.env.example`:
```bash
cp .env.example .env
```
Abra o arquivo `.env` e preencha com as suas credenciais (APIs de IA, credenciais do GLPI, URLs de banco de dados, etc.).

### 3. Execução

#### Opção A: Executando localmente com Python

1. Crie e ative um ambiente virtual:
   ```bash
   python -m venv venv
   source venv/bin/activate  # No Linux/macOS
   # ou
   .\venv\Scripts\activate  # No Windows
   ```

2. Instale as dependências requeridas:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-rag.txt
   ```

3. Inicie o servidor:
   ```bash
   python app.py
   ```

#### Opção B: Executando via Docker (Recomendado)
Para subir toda a infraestrutura de forma automatizada, execute:
```bash
docker-compose up --build -d
```

---

## 🧪 Testes

Para garantir o funcionamento correto da aplicação e evitar regressões, execute a suíte de testes contida na pasta `/tests`:

```bash
pytest tests/
```

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem Principal:** Python
* **Conteinerização:** Docker / Docker Compose
* **Orquestração de Contexto:** Frameworks RAG (LangChain / LlamaIndex ou bibliotecas similares baseadas no `requirements-rag.txt`)
* **Integrações:** GLPI API

---

## ✒️ Autores

* **Ingrid Sol An** - *Desenvolvimento Inicial* - [IngridSolAn](https://github.com)
