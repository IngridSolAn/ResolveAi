# Integração com GLPI

Esta pasta será usada para documentação e arquivos específicos da integração.

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
