-- Chamados de teste do ResolveAI (entidade raiz = 0).
SET NAMES utf8mb4;
SET @now = NOW();

INSERT INTO glpi_tickets (entities_id, name, content, status, date, date_mod, date_creation, solvedate, closedate, users_id_recipient, type, urgency, impact, priority)
VALUES
(0, 'Coletor desconecta do Wi-Fi durante o turno', '<p>Os coletores de dados do galpão perdem a conexão Wi-Fi várias vezes ao dia, principalmente perto das docas.</p>', 6, @now - INTERVAL 40 DAY, @now - INTERVAL 38 DAY, @now - INTERVAL 40 DAY, @now - INTERVAL 38 DAY, @now - INTERVAL 38 DAY, 2, 1, 3, 3, 3),
(0, 'Impressora de etiquetas Zebra não imprime', '<p>A impressora recebe o trabalho, mas nenhuma etiqueta sai. O LED fica piscando em vermelho.</p>', 6, @now - INTERVAL 35 DAY, @now - INTERVAL 34 DAY, @now - INTERVAL 35 DAY, @now - INTERVAL 34 DAY, @now - INTERVAL 34 DAY, 2, 1, 3, 3, 3),
(0, 'Sistema ERP lento na filial', '<p>Usuários da filial relatam que o ERP demora mais de 1 minuto para abrir telas.</p>', 6, @now - INTERVAL 30 DAY, @now - INTERVAL 28 DAY, @now - INTERVAL 30 DAY, @now - INTERVAL 28 DAY, @now - INTERVAL 28 DAY, 2, 1, 4, 3, 4),
(0, 'Usuário não consegue acessar a VPN', '<p>Ao conectar na VPN aparece "falha na autenticação", mesmo com a senha correta.</p>', 6, @now - INTERVAL 25 DAY, @now - INTERVAL 24 DAY, @now - INTERVAL 25 DAY, @now - INTERVAL 24 DAY, @now - INTERVAL 24 DAY, 2, 1, 3, 2, 3),
(0, 'Outlook não sincroniza e-mails', '<p>O Outlook fica com status "Desconectado" e não recebe novos e-mails desde ontem.</p>', 6, @now - INTERVAL 20 DAY, @now - INTERVAL 19 DAY, @now - INTERVAL 20 DAY, @now - INTERVAL 19 DAY, @now - INTERVAL 19 DAY, 2, 1, 3, 2, 3),
(0, 'Coletor perde sinal na área de expedição', '<p>Na expedição o coletor mostra sinal fraco e trava ao enviar as leituras.</p>', 6, @now - INTERVAL 10 DAY, @now - INTERVAL 9 DAY, @now - INTERVAL 10 DAY, @now - INTERVAL 9 DAY, @now - INTERVAL 9 DAY, 2, 1, 3, 3, 3);

SET @first = LAST_INSERT_ID();

INSERT INTO glpi_itilsolutions (itemtype, items_id, content, status, date_creation, date_mod, users_id)
VALUES
('Ticket', @first,     '<p>Interferência entre access points no mesmo canal. Canal do AP das docas alterado de 6 para 11 e potência ajustada. Coletores estáveis após a mudança.</p>', 3, @now - INTERVAL 38 DAY, @now - INTERVAL 38 DAY, 4),
('Ticket', @first + 1, '<p>Ribbon instalado ao contrário e sensor de etiqueta descalibrado. Ribbon reposicionado e calibração feita pelo menu da impressora (segurar FEED por 2 piscadas).</p>', 3, @now - INTERVAL 34 DAY, @now - INTERVAL 34 DAY, 4),
('Ticket', @first + 2, '<p>Link MPLS da filial com perda de pacotes. Operadora acionada, link normalizado. Latência voltou para 20 ms.</p>', 3, @now - INTERVAL 28 DAY, @now - INTERVAL 28 DAY, 4),
('Ticket', @first + 3, '<p>Senha do usuário havia expirado no AD; a VPN usa autenticação RADIUS no AD. Senha redefinida e usuário orientado sobre a política de expiração.</p>', 3, @now - INTERVAL 24 DAY, @now - INTERVAL 24 DAY, 4),
('Ticket', @first + 4, '<p>Arquivo OST corrompido. Perfil do Outlook recriado e caixa resincronizada.</p>', 3, @now - INTERVAL 19 DAY, @now - INTERVAL 19 DAY, 4),
('Ticket', @first + 5, '<p>Access point da expedição estava sem PoE suficiente e reiniciando. Porta do switch trocada para uma com PoE+. Sinal normalizado.</p>', 3, @now - INTERVAL 9 DAY, @now - INTERVAL 9 DAY, 4);

INSERT INTO glpi_itilfollowups (itemtype, items_id, content, date, date_creation, date_mod, users_id, is_private)
VALUES
('Ticket', @first, '<p>Problema ocorre só perto das docas 3 e 4. Atenciosamente,<br>Equipe</p>', @now - INTERVAL 39 DAY, @now - INTERVAL 39 DAY, @now - INTERVAL 39 DAY, 4, 0);

-- Chamado ABERTO para testar a análise no plugin.
INSERT INTO glpi_tickets (entities_id, name, content, status, date, date_mod, date_creation, users_id_recipient, type, urgency, impact, priority)
VALUES
(0, 'Coletores caindo da rede no galpão novo', '<p>Desde segunda-feira os coletores do galpão novo desconectam do Wi-Fi a cada poucos minutos. No galpão antigo funcionam normalmente.</p>', 1, @now, @now, @now, 2, 1, 4, 3, 4);

SELECT LAST_INSERT_ID() AS chamado_aberto;
