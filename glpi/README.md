# Integração com GLPI

Esta pasta será usada para documentação e arquivos específicos da integração.

O esqueleto inicial do plugin GLPI 10 está em
[`plugins/resolveai/`](plugins/resolveai/README.md). Ele exibe uma aba de
insights no chamado e consulta o backend por um proxy PHP autenticado. O
endpoint de análise ainda precisa ser implementado no backend ResolveAI antes
que o plugin possa retornar diagnósticos.

A indexação histórica e incremental de chamados solucionados/fechados está em
[`../src/glpi_rag.py`](../src/glpi_rag.py). Use uma conta MySQL somente leitura
na réplica e mantenha `entities_id` como filtro obrigatório em todas as
consultas vetoriais.

Para habilitar as dependências opcionais, execute
`pip install -r requirements-rag.txt`. Configure
`GLPI_READONLY_DATABASE_URL` com uma URL SQLAlchemy MySQL/MariaDB da réplica e
`CHROMA_PATH` com o diretório persistente do Chroma. Opcionalmente, configure
`RAG_STATE_PATH`, `CHROMA_COLLECTION` e `RAG_SYNC_OVERLAP_SECONDS`. Em seguida,
rode `python -m src.glpi_rag`. O primeiro ciclo usa uma data inicial antiga e
indexa o histórico; os ciclos seguintes reconsultam a partir de `date_mod`
salvo, com uma janela de sobreposição para capturar alterações próximas ao
watermark. `upsert` por ID do chamado torna a reexecução idempotente.

A consulta usa os status GLPI `5` (solucionado) e `6` (fechado), e relaciona
soluções/acompanhamentos por `itemtype = 'Ticket'` e `items_id`. Confirme esses
campos no esquema da instalação antes de produção. A segunda parte da consulta
usa `EXISTS` para não multiplicar soluções quando o chamado tiver vários
acompanhamentos. Chamados sem solução não entram no RAG. O watermark depende de
`glpi_tickets.date_mod` avançar quando uma solução ou acompanhamento for
alterado; confirme esse comportamento na versão instalada. Caso contrário,
inclua os timestamps das tabelas relacionadas na estratégia incremental.

Exemplo de busca autorizada no código:
`search_by_entity(collection, pergunta, entities_id=entidade_autorizada)`. A
entidade deve vir do contexto de autorização do usuário, nunca de um filtro
livre e não verificado do cliente.

## Abordagem definida

A integração futura será feita pela REST API oficial do GLPI, por meio de um
middleware externo ao GLPI. O MVP atual permanece baseado na importação local
de CSV; a integração não deve ser iniciada antes de validar esse fluxo.

O middleware será responsável por autenticar-se no GLPI, limitar as consultas à
entidade autorizada, buscar apenas chamados com status Solucionado ou Fechado e
artigos da Base de Conhecimento da mesma entidade, além de sanitizar os dados
antes de qualquer análise. As credenciais devem ter o menor privilégio
necessário e não podem ser expostas à interface ou ao modelo de IA.

As análises técnicas poderão ser registradas como acompanhamentos privados.
Qualquer sugestão de resposta ao requerente deve ser apresentada separadamente
para revisão do atendente; o middleware não deve publicá-la automaticamente.

Quando não houver evidência histórica semelhante, a análise deve declarar
“Nenhum chamado similar encontrado no histórico do GLPI.” e limitar-se a
orientações genéricas de troubleshooting, sem inventar chamados, soluções ou
artigos.

Antes de implementar, confirmar a versão do GLPI, os endpoints e permissões
disponíveis, a configuração multi-entidade e os requisitos de privacidade e
retenção aplicáveis.

## Segredos

As credenciais do GLPI devem ficar no arquivo `.env`, que não é enviado ao Git.
Use `.env.example` como referência e nunca adicione tokens reais ao projeto.
