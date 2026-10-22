# ResolveAi

# ResolveAI 🤖

### Copiloto inteligente para investigação e resolução de incidentes de TI integrado ao GLPI

O **ResolveAI** é um projeto em desenvolvimento que tem como objetivo utilizar inteligência artificial para auxiliar equipes de suporte e sustentação de sistemas na investigação de incidentes, identificação de possíveis causas e documentação de soluções técnicas.

Integrado ao **GLPI 10.x**, o projeto pretende apoiar os profissionais de TI na análise de chamados, consulta ao histórico de incidentes e sugestão de possíveis soluções, contribuindo para a redução do tempo de atendimento e a melhoria contínua dos processos de suporte.

> **Status:** Em desenvolvimento — fase inicial de configuração e integração.

## 🎯 Objetivos

- Apoiar a análise e a resolução de incidentes de TI.
- Utilizar IA generativa para sugerir possíveis causas e soluções.
- Consultar informações de chamados do GLPI por meio de integração controlada.
- Facilitar o acesso ao histórico de incidentes e às soluções documentadas.
- Contribuir para a padronização do atendimento e a melhoria dos indicadores de suporte.

## ✨ Funcionalidades planejadas

- Integração com a API REST do GLPI.
- Consulta de chamados por identificador.
- Análise contextual de incidentes com auxílio de IA.
- Sugestões de procedimentos de diagnóstico e resolução.
- Geração de resumos técnicos para documentação.
- Evolução futura para uma base de conhecimento inteligente.

*As funcionalidades serão implementadas gradualmente, conforme a evolução do projeto.*

## 🧰 Tecnologias previstas

- **GLPI 10.x:** gerenciamento de serviços e chamados de TI.
- **Python:** linguagem principal do backend.
- **FastAPI:** criação dos endpoints de integração.
- **Docker e Docker Compose:** execução de serviços em ambiente local.
- **API REST:** comunicação entre o ResolveAI e o GLPI.
- **IA generativa:** análise e sugestão de soluções, em uma etapa posterior.

## 🏗️ Arquitetura proposta

```text
┌──────────────────────────┐
│       Profissional       │
│          de TI           │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│        ResolveAI         │
│       Python / API       │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      Integração GLPI     │
│         API REST         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│      GLPI 10.x           │
│ Chamados e conhecimento  │
└──────────────────────────┘
```

A arquitetura será evoluída para incorporar o processamento de contexto e a integração com um modelo de IA, mantendo controles de acesso e proteção dos dados.

## 💻 Instalação e configuração inicial

Esta seção descreve a preparação sugerida para executar o ambiente de desenvolvimento local. Os comandos pressupõem que o backend inicial do ResolveAI será criado conforme a estrutura indicada abaixo.

### 1. Pré-requisitos

Instale os seguintes componentes:

- **Git:** para clonar e versionar o projeto.
- **Python 3.11 ou superior:** para executar o backend.
- **Docker Desktop:** para Windows, ou Docker Engine em Linux.
- **Docker Compose:** para gerenciar os serviços em contêineres.
- **GLPI 10.x:** uma instância local ou de desenvolvimento acessível.
- **Visual Studio Code (opcional):** para editar e executar o código.

Verifique as instalações pelo terminal:

```bash
git --version
python --version
docker --version
docker compose version
```

No Windows, se o comando `python` não funcionar, experimente `py --version`.

### 2. Clonar o repositório

No terminal, execute:

```bash
git clone https://github.com/SEU-USUARIO/ResolveAI.git
cd ResolveAI
```

Substitua `SEU-USUARIO` pelo nome de usuário ou organização do GitHub e confirme o nome exato do repositório.

Se o repositório ainda não existir no GitHub, crie-o primeiro e envie os arquivos iniciais.

### 3. Criar o ambiente virtual Python

Na pasta do projeto, crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente no Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Prompt de Comando do Windows:

```bat
.venv\Scripts\activate.bat
```

No Linux ou macOS:

```bash
source .venv/bin/activate
```

Atualize o instalador de pacotes:

```bash
python -m pip install --upgrade pip
```

### 4. Preparar a estrutura inicial do backend

Organize o projeto com uma estrutura semelhante a esta:

```text
ResolveAI/
├── backend/
│   └── app/
│       ├── __init__.py
│       └── main.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Essa é uma estrutura inicial sugerida; os arquivos precisam ser criados no repositório caso ainda não existam.

No arquivo `requirements.txt`, adicione as dependências iniciais:

```text
fastapi
uvicorn[standard]
httpx
python-dotenv
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

### 5. Configurar as variáveis de ambiente

Crie o arquivo `.env.example` na raiz do projeto:

```dotenv
GLPI_BASE_URL=http://localhost/glpi
GLPI_APP_TOKEN=
GLPI_USER_TOKEN=
```

Ajuste `GLPI_BASE_URL` para o endereço real da sua instância. Por exemplo, se o GLPI estiver disponível na raiz do servidor, a URL poderá ser `http://localhost`.

Crie uma cópia chamada `.env` e preencha as credenciais necessárias para a integração.

**Importante:** não publique tokens, senhas ou outros segredos no GitHub. O arquivo `.env` deve permanecer fora do controle de versão.

Adicione ao `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.env
.pytest_cache/
```

O `.env.example` pode ser versionado, desde que contenha apenas valores ilustrativos e nenhum segredo real.

### 6. Preparar o GLPI

Você pode utilizar uma instância de desenvolvimento já existente ou preparar uma instalação local do GLPI 10.x.

Antes de integrar:

1. Confirme que o GLPI está acessível pelo navegador.
2. Verifique a versão instalada.
3. Habilite e configure a API REST conforme a documentação da sua versão.
4. Crie um usuário ou perfil de integração com as permissões mínimas necessárias.
5. Gere e configure os tokens exigidos pela API.
6. Teste a autenticação e a consulta de chamados antes de conectar a IA.

Consulte a documentação oficial do projeto: [GLPI — documentação](https://glpi-project.org/documentation/).

**Segurança:** comece com consultas somente de leitura. Não conceda permissões para excluir, alterar ou fechar chamados sem uma necessidade clara e controles específicos.

> A configuração dos tokens e os endpoints exatos dependem da versão do GLPI e das opções habilitadas na instância.

### 7. Executar o backend

Depois de criar o módulo inicial `backend/app/main.py`, instale as dependências e execute:

```bash
uvicorn backend.app.main:app --reload
```

Caso a estrutura de pacotes seja diferente, ajuste o caminho do módulo conforme os arquivos existentes.

Se a inicialização ocorrer corretamente, a API ficará disponível normalmente em:

- API local: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Documentação interativa: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Esses endereços pressupõem que o servidor esteja em execução com a configuração padrão do Uvicorn.

### 8. Validar a instalação

Faça os seguintes testes iniciais:

1. Confirme que o servidor inicia sem erros.
2. Acesse a documentação interativa em `/docs`.
3. Verifique o endpoint de saúde, caso ele já tenha sido implementado.
4. Teste a autenticação na API do GLPI.
5. Consulte um chamado de teste usando uma conta com permissão de leitura.
6. Confira os logs para identificar erros de conexão, autenticação ou permissão.

A existência e o funcionamento dos endpoints dependem da implementação atual do backend; os testes devem ser adaptados ao código disponível no repositório.

## 🔌 Integração com o GLPI

A comunicação será realizada pela API REST do GLPI, permitindo que o backend consulte informações autorizadas sobre chamados.

O fluxo planejado é:

1. O usuário solicita a análise de um incidente.
2. O ResolveAI recebe o identificador ou a descrição do chamado.
3. O backend consulta as informações autorizadas no GLPI.
4. O contexto do incidente é preparado para análise.
5. Em uma etapa posterior, um modelo de IA poderá sugerir hipóteses e procedimentos de diagnóstico.
6. O profissional de TI revisa as recomendações antes de aplicá-las.

As sugestões da IA deverão ser tratadas como apoio à decisão, e não como garantia de diagnóstico correto.

## 🔐 Segurança e boas práticas

- Não versionar tokens, senhas ou arquivos `.env`.
- Utilizar credenciais exclusivas para a integração.
- Aplicar o princípio do menor privilégio.
- Evitar expor dados pessoais ou informações confidenciais dos chamados a modelos externos sem autorização.
- Registrar erros sem incluir credenciais ou dados sensíveis nos logs.
- Validar os dados recebidos pela API.
- Utilizar HTTPS em ambientes de produção.
- Exigir revisão humana para ações que alterem chamados ou afetem sistemas.

## 🗺️ Roadmap

- [ ] Preparar o ambiente local de desenvolvimento.
- [ ] Configurar uma instância GLPI 10.x.
- [ ] Implementar o backend inicial em FastAPI.
- [ ] Criar um endpoint de verificação de saúde.
- [ ] Implementar autenticação e consulta de chamados no GLPI.
- [ ] Tratar erros de conexão, autenticação e permissões.
- [ ] Implementar análise de incidentes com IA.
- [ ] Criar uma interface para interação com o ResolveAI.
- [ ] Desenvolver testes automatizados.
- [ ] Documentar a implantação em ambiente de produção.

## 🤝 Contribuição

Sugestões, melhorias e contribuições são bem-vindas.

1. Faça um fork do repositório.
2. Crie uma branch para sua alteração.
3. Implemente e teste a mudança.
4. Envie um pull request com a descrição do que foi realizado.

## 📄 Licença

A licença do projeto ainda será definida. Até sua inclusão no repositório, não presuma que o código esteja liberado para reutilização ou distribuição.

---

**ResolveAI — inteligência artificial aplicada à sustentação de sistemas e à resolução de incidentes de TI.**
