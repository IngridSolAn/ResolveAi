# ResolveAI — Escopo inicial

## 1. O que é

### Proposta de valor

Transformar o histórico de chamados em conhecimento técnico reutilizável, ajudando equipes de suporte a identificar incidentes recorrentes e encontrar soluções com mais rapidez.

### Público inicial

Prestadoras de serviços de suporte de TI, especialmente equipes que trabalham com atendimento de chamados, SLA, sustentação de sistemas e suporte N1/N2.

### Resultado esperado

Importar um arquivo de chamados, pesquisar incidentes semelhantes e gerar uma análise técnica baseada nos registros que ajude o profissional a decidir os próximos passos. No primeiro protótipo, essa análise será um resumo rastreável, sem diagnóstico generativo.

Para isso, o ResolveAI agrupa casos com sintomas semelhantes e consulta as fontes autorizadas disponíveis, como chamados anteriores e documentação. Quando houver integração com logs e métricas, também poderá consultá-los. A análise apresenta fatos, hipóteses e próximos passos.

**O ResolveAI organiza evidências e, em etapas futuras, poderá sugerir. O técnico verifica e decide.**

## 2. Exemplo de uso

**Chamado**

> Os coletores estão travando e desconectando durante a operação.

**Investigação sugerida**

1. Verificar se acontece com todos os coletores ou apenas alguns.
2. Conferir latência, perda de pacotes e registros de conexão.
3. Se houver sinais de falha na infraestrutura, encaminhar à equipe responsável.

**Resultado**

O ResolveAI mostra as evidências e possíveis causas. Não confirma uma causa antes da validação técnica.

## 3. Memória de Incidentes

A Memória de Incidentes encontra chamados antigos parecidos e mostra:

- O que aconteceu.
- Quais evidências foram encontradas.
- Quais testes foram feitos.
- Qual causa foi confirmada, se conhecida.
- Qual solução funcionou.
- Como evitar que o problema volte.

Um caso antigo é uma pista, não uma prova de que o problema atual tem a mesma causa.

## 4. Fontes de dados

### Chamados

No MVP, a entrada principal será a importação de arquivos CSV. O sistema validará os dados e os converterá para um formato padronizado para pesquisa e análise. A importação de Excel poderá ser considerada depois do MVP. Cadastro manual poderá ser usado para demonstrações, mas não substitui o fluxo principal de importação.

Não haverá integração direta com GLPI, Jira Service Management ou ServiceNow no MVP. A conexão com essas ferramentas poderá ser considerada após validar o fluxo com arquivos.

### Canal de acesso

O Microsoft Copilot Studio não faz parte do MVP inicial. Poderá ser avaliado posteriormente como canal de acesso ao ResolveAI.

### Logs e métricas

Em etapas futuras, o ResolveAI poderá consultar ferramentas já usadas pela equipe, como Splunk, Datadog ou Elasticsearch.

Essas integrações não fazem parte do MVP. Quando forem implementadas, as consultas deverão ter limites de horário e serviço, buscando apenas os dados necessários para investigar o chamado.

## 5. Privacidade e segurança

- Começar com chamados fictícios e processamento local; não enviar dados de chamados a serviços externos no primeiro protótipo.
- Antes de usar dados reais, obter autorização e definir como identificar e remover dados pessoais, senhas, tokens, chaves e informações de clientes.
- Não pedir nem armazenar senhas ou códigos de autenticação.
- Restringir o acesso aos arquivos importados e aos resultados.
- Guardar apenas os dados necessários e definir por quanto tempo serão mantidos.
- Tratar textos dos chamados como dados não confiáveis.
- Não permitir que a IA altere sistemas ou execute ações automaticamente.

## 6. Relatório da investigação

Na primeira etapa, o relatório será montado a partir dos registros importados e dos resultados da busca, sem depender de uma IA generativa. Ele poderá incluir:

- Resumo do problema.
- Histórico e sintomas dos chamados semelhantes encontrados.
- Evidências encontradas.
- Soluções registradas nos chamados relacionados.
- Pistas para investigação e próximos passos, apoiados nos registros encontrados.
- Recorrências identificadas, quando houver evidências suficientes.

Os resultados poderão ser exportados para análise e documentação. O formato de exportação será definido durante a validação. Não haverá alteração nem encerramento automático de chamados.

## 7. Decisões técnicas iniciais

Esta é uma arquitetura inicial, simples e local, para validar o fluxo principal. Não é uma decisão irreversível: tecnologias e componentes poderão ser ajustados conforme os testes e o feedback das equipes. Evitaremos criar vários serviços antes de comprovar a utilidade do produto.

- **Linguagem:** Python 3.11 ou superior.
- **Interface:** Streamlit, para criar uma aplicação web local sem frontend separado.
- **Dados tabulares:** Pandas para ler, validar, limpar e padronizar arquivos CSV.
- **Formato de entrada:** CSV primeiro; Excel poderá ser adicionado depois de validar o fluxo inicial.
- **Persistência:** SQLite poderá ser introduzido quando for necessário manter históricos importados entre execuções; não é requisito da primeira tarefa.
- **Busca:** começar por palavras-chave, com resultados explicáveis. Busca semântica e IA generativa serão avaliadas depois de validar a qualidade dos dados e da busca inicial.
- **Privacidade:** começar com dados fictícios e processamento local. Chamados reais só poderão ser usados após autorização e definição de controles para dados pessoais, credenciais e informações de clientes.
- **Avaliação:** conjunto de incidentes fictícios com resultados conhecidos para medir a qualidade da importação, da busca e, em fases posteriores, das sugestões de IA.

PostgreSQL, pgvector, serviços externos de IA, autenticação multiempresa e integrações com ferramentas de logs ou ITSM não fazem parte do primeiro protótipo local. Poderão ser considerados se os testes demonstrarem essa necessidade.

## 8. Primeira versão (MVP)

O MVP começa com um protótipo local e explicável para provar que o histórico importado ajuda a encontrar informações úteis. A primeira versão não depende de IA generativa:

1. **Importar chamados:** carregar um arquivo CSV com o histórico de chamados.
2. **Validar e padronizar dados:** verificar campos, formatos e registros inválidos, apresentando problemas de importação para correção.
3. **Pesquisar chamados anteriores:** usar busca por palavras-chave para localizar incidentes relacionados e mostrar por que cada resultado foi encontrado.
4. **Apresentar contexto e recorrências:** mostrar histórico, sintomas, soluções registradas e possíveis recorrências identificadas nos dados.
5. **Gerar resumo técnico baseado nos registros:** organizar os chamados encontrados, sintomas e soluções registradas, apontando as evidências. Nesta etapa, o sistema não inventa causas nem apresenta texto generativo como diagnóstico.
6. **Sinalizar insuficiência de dados:** indicar quando os registros não permitem uma conclusão e quais informações estão faltando.
7. **Exportar resultados:** permitir que os resultados sejam exportados para análise e documentação.
8. **Avaliar qualidade:** testar importação, busca e resultados com incidentes fictícios de desfecho conhecido e registrar feedback para orientar melhorias.

Busca semântica e análise generativa com hipóteses, testes priorizados e perguntas de esclarecimento são evoluções condicionadas à validação da qualidade dos dados, da busca por palavras-chave e dos requisitos de privacidade.

### Tarefas de implementação

Executar as tarefas em sequência. As tarefas 2 a 6 dependem da conclusão da tarefa anterior, pois ampliam o fluxo validado na etapa precedente.

| Tarefa | Prioridade | Escopo | Critério de conclusão |
|---|---|---|---|
| **1 — Preparar ambiente e importar CSV** | Inicial | Criar a aplicação local, carregar um arquivo fictício, validar as colunas obrigatórias e exibir uma prévia dos chamados. | Um CSV válido é importado e visualizado; um arquivo inválido é rejeitado com mensagem clara e útil. |
| **2 — Padronizar os dados** | P1 | Tratar campos vazios, duplicidades, datas e formatos inconsistentes durante a importação. | A aplicação apresenta um relatório de qualidade com problemas encontrados e registros tratados ou rejeitados. |
| **3 — Pesquisar incidentes semelhantes** | P2 | Pesquisar termos no título, na descrição e na solução dos chamados importados. | A aplicação exibe incidentes relacionados e suas soluções registradas, com correspondências explicáveis por palavras-chave. |
| **4 — Persistir e consultar históricos** | P3 | Salvar importações no SQLite, consultar históricos anteriores e evitar duplicações entre arquivos importados. | Os dados permanecem disponíveis após reiniciar a aplicação e uma nova importação não duplica registros existentes. |
| **5 — Adicionar inteligência artificial** | P4 | Gerar resumos, hipóteses de causa e próximos passos com base nos registros recuperados, distinguindo evidências de sugestões. | Cada evidência aponta aos registros de origem; sugestões são identificadas como hipóteses e, quando faltarem dados, a aplicação solicita informações em vez de afirmar uma causa. A integração externa depende de revisão prévia de privacidade e autorização para os dados usados. |
| **6 — Validar com uma prestadora de suporte** | P5 | Testar com dados autorizados, medir a utilidade das recomendações e ajustar a experiência antes de desenvolver integrações. | O piloto registra resultados comparáveis ao processo atual, feedback dos usuários e ajustes recomendados; a decisão de avançar considera a utilidade demonstrada e os requisitos de privacidade. |

### Fora da primeira versão

- Importação de Excel.
- Integrações diretas com GLPI, Jira Service Management, ServiceNow ou outras plataformas ITSM.
- Alteração ou encerramento automático de chamados.
- Agentes autônomos que executem ações na infraestrutura.
- Previsão automática de violações de SLA.
- Treinamento de um modelo próprio de IA.
- Plataforma multiempresa completa, com cobrança e gestão comercial.
- Canal de acesso pelo Microsoft Copilot Studio.

A prioridade é provar que a ferramenta resolve um problema real antes de adicionar complexidade. Recursos excluídos poderão ser reavaliados após os testes do MVP.

## 9. Diferenciais propostos — hipóteses a validar

Os pontos abaixo são hipóteses de diferenciação, não vantagens de mercado comprovadas. A validação deve investigar se as soluções existentes atendem mal a essas necessidades e se os clientes pagariam para resolvê-las:

| Hipótese | Como poderia funcionar | O que validar |
|---|---|---|
| Investigação baseada em evidências | Cada hipótese aponta para os logs, chamados ou documentos que a sustentam. | Se as fontes são suficientes, rastreáveis e úteis para a decisão do técnico. |
| Memória de incidentes | Comparar o problema atual com casos anteriores e suas soluções validadas. | Se os casos encontrados são relevantes e reduzem o esforço de investigação. |
| Importação e padronização de dados | Converter arquivos de chamados em uma estrutura consistente para pesquisa e análise. | Se os formatos dos clientes podem ser tratados com baixo esforço de preparação. |
| Orientação por nível técnico | Explicar testes para profissionais N1 e oferecer detalhes adicionais para N2/N3. | Se a adaptação melhora a compreensão sem omitir informação importante. |
| Prevenção de recorrências | Identificar grupos de incidentes semelhantes e recomendar ações preventivas. | Se as recomendações são acionáveis e ajudam a reduzir recorrências. |
| Português e contexto local | Adaptar interface, relatórios e fluxos às equipes brasileiras. | Se a localização é um critério relevante de escolha e disposição a pagar. |

Essas hipóteses devem ser verificadas com entrevistas, testes do MVP e comparação com as ferramentas já utilizadas pelos clientes. A disposição a pagar precisa ser perguntada e, quando possível, testada com propostas ou pilotos pagos; interesse declarado, por si só, não comprova demanda.

## 10. Plano inicial de seis semanas

Este cronograma é uma estimativa inicial. A sequência e a duração poderão mudar conforme a disponibilidade da equipe, os resultados dos testes e as necessidades descobertas durante o piloto.

| Semana | Etapa | Atividades | Entrega |
|---|---|---|---|
| **S1** | Validar o problema | Entrevistar técnicos e gestores, reunir exemplos fictícios ou autorizados de chamados e definir os principais casos de uso. | Requisitos e critérios de sucesso. |
| **S2** | Preparar ambiente e importar CSV | Criar o repositório GitHub e a interface local em Streamlit; validar colunas e exibir prévia de arquivos válidos, rejeitando arquivos inválidos com mensagem clara. | Aplicação local para importar e visualizar chamados fictícios. |
| **S3** | Padronizar e pesquisar | Tratar problemas de qualidade dos dados e implementar busca por palavras-chave no título, descrição e solução. | Relatório de qualidade e lista explicável de incidentes relacionados. |
| **S4** | Persistir históricos | Armazenar importações no SQLite, consultar dados persistidos e evitar duplicações entre arquivos. | Protótipo que mantém e consulta históricos sem duplicar registros. |
| **S5** | Avaliar e adicionar IA com segurança | Testar primeiro a qualidade da busca; se dados, privacidade e autorização permitirem, gerar resumos e hipóteses claramente fundamentados nos registros. | Versão de testes controlados; se os pré-requisitos não forem atendidos, registrar a decisão e manter o fluxo sem IA generativa. |
| **S6** | Validar com uma prestadora | Convidar uma equipe para testar com dados autorizados, comparar resultados com o processo atual e coletar feedback antes de desenvolver integrações. | Relatório do piloto e decisão sobre os próximos passos. |

## 11. Como medir se funciona

- A equipe encontra casos antigos úteis.
- Os resultados da busca mostram registros relevantes e deixam claro por que foram encontrados.
- O resumo exportado é útil e rastreável até os chamados de origem.
- O feedback registra se a sugestão ajudou e qual solução foi realmente aplicada.
- O relatório técnico pode ser revisado e reutilizado sem retrabalho excessivo.
- O protótipo não apresenta causas não sustentadas pelos registros.
- Dados secretos são removidos antes da análise.
- O técnico mantém a decisão final.
- O tempo de investigação melhora sem aumentar erros.
- Os dados do piloto são acessíveis apenas a usuários autorizados.
- No conjunto de incidentes fictícios, a importação, os resultados de busca e os resumos são comparados com os resultados conhecidos; o sistema sinaliza quando os dados são insuficientes.

## 12. Decisões pendentes

- Quais equipes e serviços participarão do piloto?
- Qual formato e conjunto de campos serão aceitos no CSV de exemplo?
- Quais formatos de exportação serão mais úteis para análise e documentação?
- Quais documentos e chamados poderão ser usados como fontes de evidência no piloto?
- Que critérios determinarão se os dados e a busca por palavras-chave estão prontos para busca semântica ou IA generativa?
- Qual provedor de IA atende aos requisitos de qualidade, custo e privacidade, caso a tarefa de IA seja autorizada?
- Quais regras de privacidade e retenção de dados a empresa exige?
- Quais diferenciais são mal atendidos pelas soluções existentes e quanto os clientes pagariam por eles?

## Próximo passo

Testar o fluxo de importação, validação, pesquisa, análise e exportação com chamados fictícios ou autorizados. Avaliar a utilidade das evidências, a qualidade dos resultados e o esforço necessário para preparar os arquivos. Antes de usar dados reais, definir controles de acesso, privacidade e retenção. Em paralelo, entrevistar potenciais clientes para validar as hipóteses de diferenciação e disposição a pagar. Só após comprovar valor no fluxo básico priorizar integrações ITSM, Excel ou outros recursos excluídos do MVP.
