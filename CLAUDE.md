# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

O projeto, a documentação e as mensagens para o usuário são em português (pt-BR).

## Comandos

Ambiente virtual na raiz: `.venv/` (Windows: `.venv/Scripts/python`).

```bash
# Backend (FastAPI) — rodar de dentro de backend/ (pytest.ini define pythonpath=.)
cd backend
pip install -r requirements-dev.txt
pytest                                              # todos os testes
pytest tests/test_ollama_analyzer.py::test_analyze_explains_missing_model   # um teste
uvicorn app.main:app --reload --env-file ../.env    # API em :8000, docs em /docs
python -m app.index                                 # indexa no Chroma os chamados solucionados do GLPI (incremental)

# Protótipo Streamlit (raiz do projeto)
pip install -r requirements.txt
streamlit run app.py
pytest tests/

# Stack completa: GLPI :1201, backend :8002, ChromaDB :8001, Ollama :11434
docker compose up --build -d
docker compose exec ollama ollama pull qwen2.5:7b   # uma vez, para a IA gratuita
docker compose up --build -d backend-ai             # após mudar código do backend
```

Para indexar dentro do Docker: `docker exec -e GLPI_READONLY_DATABASE_URL="mysql+pymysql://<user>:<senha>@db:3306/glpi?charset=utf8mb4" resolveai-backend python -m app.index`.

Página pública (GitHub Pages): `docs/index.html` + `docs/site.css`, HTML estático.

Não há linter configurado. Os testes não chamam IA real, GLPI, ChromaDB nem Ollama (usam fakes, `httpx.MockTransport` e `app.dependency_overrides`).

## Arquitetura

Há dois códigos independentes:

- **`backend/app/`**: o produto. É o núcleo de inteligência agnóstico de ITSM, exposto por FastAPI.
- **`src/` + `app.py` + `tests/`**: protótipo local em Streamlit (importação de CSV e busca por palavras-chave). Não é usado pelo backend.

### Backend: portas e adaptadores

- `core/models.py`: modelos neutros (`Ticket`, `ResolvedTicket`, `SimilarCase`, `AnalysisResult`). O `AnalysisResult` é o contrato JSON de resposta do `/analyze`, validado também pelo plugin PHP (`glpi/plugins/resolveai/front/insights.php`). Mudar campos exige mudar o PHP e o `RESPONSE_JSON_SCHEMA` em `prompts.py`.
- `core/ports.py`: `TicketSource` (conector de plataforma), `KnowledgeBase` (RAG) e `Analyzer` (LLM), definidos como `Protocol`.
- `core/service.py`: `analyze_ticket` (busca RAG → filtro `max_distance` → analisador) e `index_incremental` (watermark em JSON com janela de sobreposição).
- `connectors/glpi.py`: **único** lugar que conhece tabelas do GLPI (SQL em réplica somente leitura, status 5/6, limpeza de HTML e assinaturas). Novas plataformas (Zammad, Jira...) entram como outro `TicketSource`; o núcleo não muda.
- `knowledge/chroma.py`: IDs `"<source>:<id>"`; metadados `source`, `ticket_id`, `tenant_id`, `updated_at`.
- `llm/`: `ollama.py` (padrão, gratuito), `claude.py` (pago, `client.beta.messages.parse` com saída estruturada Pydantic e `fallbacks="default"`) e `offline.py` (sem IA). Todos levantam `llm/errors.AnalysisError`.
- `main.py`: só faz HTTP ↔ modelos neutros e injeção de dependências (`get_settings`, `get_analyzer`, `get_knowledge_base` com `lru_cache`; os testes as substituem). `build_analyzer` escolhe a IA por `RESOLVEAI_LLM` (`ollama` | `claude` | `offline`).
- `config.py`: toda a configuração vem de variáveis de ambiente (ver `.env.example`).
- Telemetria e painel: `/analyze` grava um `AnalysisEvent` (`core/telemetry.py`, SQLite em `telemetry/sqlite.py`) e devolve `analysis_id`; `/feedback` registra 👍/👎; `/admin/metrics` e `/admin/analyses` alimentam o Painel da IA, que fica **no plugin do GLPI** (Ferramentas → Painel da IA, só Super-Admin = `Session::haveRight('config', UPDATE)`): `front/painel.php` + `public/js/painel.js`/`public/css/painel.css` (CSS todo escopado em `.viz-root`; o tema escuro segue `html[data-glpi-theme-dark="1"]`), com dados via `front/admin.php`, que chama `/admin/*` servidor a servidor com `RESOLVEAI_ADMIN_TOKEN` (separado do token do plugin; sem ele, 403). O menu vem de `inc/dashboard.class.php` e fica em cache na sessão do GLPI: é preciso sair e entrar de novo para vê-lo. A telemetria guarda só IDs e números, nunca texto de chamado. `run_analysis` devolve `AnalysisOutcome` (resultado + casos recuperados/usados/citados), que também é o que o cache guarda.

### Invariantes importantes

- **Isolamento por tenant**: toda busca vetorial filtra por `tenant_id` (no GLPI, `entities_id`, enviado pelo plugin depois de checar `Ticket::can(READ)`). Sem `tenant_id`, a análise roda sem RAG. Nunca aceite um tenant livre do cliente para ampliar o escopo.
- **Prompt** (`prompts.py`): trata o conteúdo do chamado e dos casos como dado não confiável e exige a frase literal `"Não encontrei histórico semelhante no material recuperado do GLPI."` quando não há caso correlacionado (há testes para isso). O Ollama usa `OLLAMA_SYSTEM_PROMPT` (prompt base + orientação extra + schema) e remove essa frase quando o diagnóstico cita um caso, porque modelos pequenos fazem as duas coisas ao mesmo tempo.
- A IA só sugere; não altera nem fecha chamados no GLPI.
- Mudar o formato dos documentos ou dos metadados no Chroma exige reindexar: apagar a coleção e o arquivo de estado (`RAG_STATE_PATH`).

### Plugin GLPI (`glpi/plugins/resolveai/`)

PHP (GLPI 10 a 12). `public/js/resolveai.js` cria um assistente flutuante (robô SVG original) em todas as páginas da interface `central`; em `front/ticket.form.php?id=N` ele se expande e chama `front/insights.php`. Esse endpoint exige a interface `central`, verifica a permissão, lê o chamado e chama o backend servidor a servidor (`RESOLVEAI_API_URL`, `RESOLVEAI_API_TOKEN`, `RESOLVEAI_API_TIMEOUT`); `refresh=1` ignora o cache de análises do backend (`core/cache.py`, `ANALYSIS_CACHE_TTL_SECONDS`). O diretório é montado no container `glpi-app` pelo docker-compose, então mudanças no PHP valem sem reiniciar. O ambiente Docker roda GLPI 12: APIs do GLPI 10 como `Plugin::getWebDir()` não existem mais, então use `method_exists` com fallback; no JS, use `CFG_GLPI.root_doc`. Arquivos estáticos (JS, CSS, imagens) precisam ficar em `public/`; fora dela, o GLPI 11+ responde 404. Em classes do plugin que estendem classes do GLPI, não redeclare propriedades como `$rightname`: no GLPI 12 elas são tipadas (`static string`) e no GLPI 10 não, e qualquer diferença gera erro fatal em todas as páginas. `php -l` não detecta isso; teste com `php -r 'require "vendor/autoload.php"; require "plugins/resolveai/inc/<arquivo>.class.php";'` dentro do container. Ao mudar `PLUGIN_RESOLVEAI_VERSION`, o GLPI desativa o plugin até ele ser atualizado: `docker exec -u www-data glpi-app php /var/www/html/glpi/bin/console plugin:install resolveai --username=glpi --force -n` e depois `plugin:activate resolveai -n`. Erros do plugin aparecem em `files/_log/php-errors.log`, dentro do container.

## Observações de ambiente

- No Git Bash do Windows, enviar JSON com acentos direto na linha de comando do `curl` corrompe a codificação. Grave o corpo num arquivo UTF-8 e use `--data-binary @arquivo`. Use `MSYS_NO_PATHCONV=1` em `docker exec` com caminhos absolutos.
- A busca semântica usa o embedding padrão do Chroma (all-MiniLM, voltado para inglês), cacheado no volume `backend_cache`. O filtro padrão `RAG_MAX_DISTANCE=0.5` foi calibrado com esse embedding.
- Sem GPU, o `qwen2.5:7b` leva cerca de 1 a 2 minutos por análise.
