/**
 * Assistente flutuante do ResolveAI.
 *
 * - Em qualquer página: um robô fica no canto inferior direito.
 * - Ao abrir um chamado (ticket.form.php?id=N), o robô se expande num painel
 *   e já pede a análise do chamado ao endpoint do plugin.
 * - O analista pode minimizar; a escolha vale para aquele chamado na sessão.
 *
 * Todo conteúdo vindo da API é inserido com textContent (nunca innerHTML).
 */
(function () {
    'use strict';

    if (window.ResolveAIAssistantLoaded) {
        return;
    }
    window.ResolveAIAssistantLoaded = true;

    const SVG_NS = 'http://www.w3.org/2000/svg';

    // Mascote original do ResolveAI (SVG estático, sem dados externos).
    const ROBOT_SVG = `
<svg class="resolveai-robot" viewBox="0 0 120 150" role="img" aria-hidden="true" xmlns="${SVG_NS}">
  <defs>
    <linearGradient id="resolveai-shell" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/>
      <stop offset="1" stop-color="#dfe7f3"/>
    </linearGradient>
    <linearGradient id="resolveai-badge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#2dd4bf"/>
      <stop offset="1" stop-color="#2563eb"/>
    </linearGradient>
  </defs>
  <g class="resolveai-robot-float">
    <line x1="60" y1="8" x2="60" y2="22" stroke="#94a3b8" stroke-width="3" stroke-linecap="round"/>
    <circle class="resolveai-robot-antenna" cx="60" cy="8" r="6" fill="#2563eb"/>
    <circle cx="20" cy="46" r="8" fill="#2563eb"/>
    <circle cx="100" cy="46" r="8" fill="#2563eb"/>
    <rect x="22" y="20" width="76" height="56" rx="24" fill="url(#resolveai-shell)" stroke="#cbd5e1" stroke-width="2"/>
    <rect x="31" y="31" width="58" height="34" rx="16" fill="#14213d"/>
    <path class="resolveai-robot-eye" d="M42 49 q6 -8 12 0" fill="none" stroke="#5eead4" stroke-width="4" stroke-linecap="round"/>
    <path class="resolveai-robot-eye" d="M66 49 q6 -8 12 0" fill="none" stroke="#5eead4" stroke-width="4" stroke-linecap="round"/>
    <path d="M52 56 q8 6 16 0" fill="none" stroke="#5eead4" stroke-width="3" stroke-linecap="round"/>
    <g class="resolveai-robot-wave">
      <path d="M30 92 q-16 -10 -18 -30" fill="none" stroke="#cbd5e1" stroke-width="9" stroke-linecap="round"/>
      <circle cx="12" cy="60" r="7" fill="url(#resolveai-shell)" stroke="#cbd5e1" stroke-width="2"/>
    </g>
    <path d="M90 92 q14 8 14 24" fill="none" stroke="#cbd5e1" stroke-width="9" stroke-linecap="round"/>
    <circle cx="104" cy="118" r="7" fill="url(#resolveai-shell)" stroke="#cbd5e1" stroke-width="2"/>
    <rect x="34" y="80" width="52" height="46" rx="18" fill="url(#resolveai-shell)" stroke="#cbd5e1" stroke-width="2"/>
    <circle cx="60" cy="102" r="12" fill="url(#resolveai-badge)"/>
    <path d="M54 102 l4 4 l8 -9" fill="none" stroke="#ffffff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <rect x="44" y="126" width="10" height="14" rx="5" fill="#cbd5e1"/>
    <rect x="66" y="126" width="10" height="14" rx="5" fill="#cbd5e1"/>
  </g>
</svg>`;

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) {
            node.className = className;
        }
        if (text !== undefined) {
            node.textContent = text;
        }
        return node;
    }

    function pluginBaseUrl() {
        const root = (window.CFG_GLPI && window.CFG_GLPI.root_doc) || '';
        return root.replace(/\/$/, '') + '/plugins/resolveai';
    }

    function currentTicketId() {
        if (!/\/front\/ticket\.form\.php$/.test(window.location.pathname)) {
            return null;
        }
        const id = Number.parseInt(new URLSearchParams(window.location.search).get('id'), 10);
        return Number.isInteger(id) && id > 0 ? id : null;
    }

    function storageKey(ticketId) {
        return 'resolveai:minimized:' + ticketId;
    }

    function rememberMinimized(ticketId, minimized) {
        if (!ticketId) {
            return;
        }
        try {
            if (minimized) {
                window.sessionStorage.setItem(storageKey(ticketId), '1');
            } else {
                window.sessionStorage.removeItem(storageKey(ticketId));
            }
        } catch (error) {
            // sessionStorage indisponível (modo privado restrito): ignora.
        }
    }

    function wasMinimized(ticketId) {
        try {
            return window.sessionStorage.getItem(storageKey(ticketId)) === '1';
        } catch (error) {
            return false;
        }
    }

    function isValidPayload(payload) {
        const confidence = payload && payload.nivel_de_confianca;
        return (
            typeof payload.diagnostico_e_evidencias === 'string' &&
            payload.diagnostico_e_evidencias.trim() !== '' &&
            confidence &&
            Number.isInteger(confidence.percentual) &&
            confidence.percentual >= 0 &&
            confidence.percentual <= 100 &&
            typeof confidence.justificativa === 'string' &&
            Array.isArray(payload.passos_sugeridos_de_teste) &&
            payload.passos_sugeridos_de_teste.every(function (step) {
                return typeof step === 'string' && step.trim() !== '';
            })
        );
    }

    function confidenceTone(percent) {
        if (percent >= 70) {
            return 'high';
        }
        if (percent >= 40) {
            return 'medium';
        }
        return 'low';
    }

    function buildAssistant() {
        const ticketId = currentTicketId();

        const root = el('div', 'resolveai-assistant');
        root.dataset.state = 'collapsed';

        // --- Robô (botão) ---
        const launcher = el('button', 'resolveai-launcher');
        launcher.type = 'button';
        launcher.setAttribute('aria-label', 'Abrir o Assistente ResolveAI');
        launcher.setAttribute('aria-expanded', 'false');
        launcher.insertAdjacentHTML('afterbegin', ROBOT_SVG);
        const tooltip = el('span', 'resolveai-tooltip', 'Assistente ResolveAI');
        launcher.appendChild(tooltip);

        // --- Painel ---
        const panel = el('section', 'resolveai-panel');
        panel.id = 'resolveai-panel';
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-labelledby', 'resolveai-panel-title');
        launcher.setAttribute('aria-controls', panel.id);

        const header = el('header', 'resolveai-panel-header');
        const avatar = el('span', 'resolveai-avatar');
        avatar.insertAdjacentHTML('afterbegin', ROBOT_SVG);
        const titles = el('div', 'resolveai-titles');
        const title = el('h2', 'resolveai-title', 'Assistente ResolveAI');
        title.id = 'resolveai-panel-title';
        const subtitle = el(
            'p',
            'resolveai-subtitle',
            ticketId ? 'Chamado #' + ticketId : 'Pronto para ajudar'
        );
        titles.append(title, subtitle);

        const actions = el('div', 'resolveai-actions');
        const refreshButton = el('button', 'resolveai-icon-button', '↻');
        refreshButton.type = 'button';
        refreshButton.title = 'Analisar novamente';
        refreshButton.setAttribute('aria-label', 'Analisar novamente');
        refreshButton.hidden = !ticketId;
        const minimizeButton = el('button', 'resolveai-icon-button', '–');
        minimizeButton.type = 'button';
        minimizeButton.title = 'Minimizar';
        minimizeButton.setAttribute('aria-label', 'Minimizar o assistente');
        actions.append(refreshButton, minimizeButton);

        header.append(avatar, titles, actions);
        const body = el('div', 'resolveai-panel-body');
        body.setAttribute('aria-live', 'polite');
        panel.append(header, body);

        root.append(panel, launcher);

        let loading = false;
        let loaded = false;
        let timer = null;

        function setExpanded(expanded) {
            root.dataset.state = expanded ? 'expanded' : 'collapsed';
            launcher.setAttribute('aria-expanded', expanded ? 'true' : 'false');
            if (expanded && ticketId && !loaded && !loading) {
                analyze(false);
            }
        }

        function renderIdle() {
            body.replaceChildren(
                el('p', 'resolveai-greeting', 'Olá! Eu sou o assistente do ResolveAI.'),
                el(
                    'p',
                    'resolveai-muted',
                    'Abra um chamado e eu busco casos parecidos já resolvidos e sugiro um diagnóstico e passos de teste.'
                )
            );
        }

        function renderLoading() {
            const box = el('div', 'resolveai-loading');
            box.setAttribute('role', 'status');
            const message = el('p', 'resolveai-greeting', 'Analisando o chamado…');
            const hint = el(
                'p',
                'resolveai-muted',
                'Estou buscando chamados parecidos no histórico. Isso pode levar até 2 minutos.'
            );
            const elapsed = el('p', 'resolveai-elapsed', '0 s');
            box.append(message, hint);
            ['resolveai-skeleton-title', '', 'resolveai-skeleton-short'].forEach(function (extra) {
                const line = el('span', ('resolveai-skeleton ' + extra).trim());
                line.setAttribute('aria-hidden', 'true');
                box.appendChild(line);
            });
            box.appendChild(elapsed);
            body.replaceChildren(box);

            const started = Date.now();
            timer = window.setInterval(function () {
                elapsed.textContent = Math.round((Date.now() - started) / 1000) + ' s';
            }, 1000);
        }

        function stopTimer() {
            if (timer) {
                window.clearInterval(timer);
                timer = null;
            }
        }

        function section(titleText, content) {
            const block = el('section', 'resolveai-section');
            block.appendChild(el('h3', 'resolveai-section-title', titleText));
            if (Array.isArray(content)) {
                const list = el('ol', 'resolveai-steps');
                content.forEach(function (step) {
                    list.appendChild(el('li', '', step.replace(/^\s*\d+[.)]\s*/, '')));
                });
                block.appendChild(list);
            } else {
                block.appendChild(content);
            }
            return block;
        }

        function renderResult(payload) {
            const diagnosis = el('p', 'resolveai-text', payload.diagnostico_e_evidencias);

            const confidence = payload.nivel_de_confianca;
            const tone = confidenceTone(confidence.percentual);
            const meter = el('div', 'resolveai-confidence');
            const bar = el('div', 'resolveai-bar');
            const fill = el('span', 'resolveai-bar-fill resolveai-tone-' + tone);
            fill.style.width = confidence.percentual + '%';
            bar.appendChild(fill);
            bar.setAttribute('role', 'meter');
            bar.setAttribute('aria-valuemin', '0');
            bar.setAttribute('aria-valuemax', '100');
            bar.setAttribute('aria-valuenow', String(confidence.percentual));
            bar.setAttribute('aria-label', 'Nível de confiança');
            meter.append(
                el('strong', 'resolveai-percent resolveai-tone-text-' + tone, confidence.percentual + '%'),
                bar,
                el('p', 'resolveai-muted', confidence.justificativa)
            );

            body.replaceChildren(
                section('Diagnóstico e evidências', diagnosis),
                section('Nível de confiança', meter),
                section('Passos sugeridos de teste', payload.passos_sugeridos_de_teste)
            );
            if (typeof payload.analysis_id === 'string' && payload.analysis_id) {
                body.appendChild(buildFeedback(payload.analysis_id));
            }
            body.appendChild(
                el('p', 'resolveai-disclaimer', 'Sugestão gerada por IA. Valide antes de aplicar.')
            );
        }

        /** "Esta sugestão ajudou?" — alimenta o painel de administradores. */
        function buildFeedback(analysisId) {
            const box = el('div', 'resolveai-feedback');
            const question = el('span', 'resolveai-feedback-question', 'Esta sugestão ajudou?');
            const buttons = el('div', 'resolveai-feedback-buttons');
            const status = el('span', 'resolveai-feedback-status');
            status.setAttribute('role', 'status');

            function option(label, helpful) {
                const button = el('button', 'resolveai-feedback-button', label);
                button.type = 'button';
                button.setAttribute('aria-pressed', 'false');
                button.addEventListener('click', function () {
                    sendFeedback(helpful, button);
                });
                return button;
            }
            const yes = option('👍 Ajudou', true);
            const no = option('👎 Não ajudou', false);
            buttons.append(yes, no);
            box.append(question, buttons, status);

            async function sendFeedback(helpful, button) {
                yes.disabled = true;
                no.disabled = true;
                status.textContent = 'Enviando…';
                const headers = { 'Content-Type': 'application/json', Accept: 'application/json' };
                // GLPI 10 valida POST com token CSRF; no GLPI 11+ isso é ignorado.
                if (typeof window.getAjaxCsrfToken === 'function') {
                    headers['X-Glpi-Csrf-Token'] = window.getAjaxCsrfToken();
                }
                try {
                    const response = await fetch(pluginBaseUrl() + '/front/feedback.php', {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: headers,
                        body: JSON.stringify({ analysis_id: analysisId, helpful: helpful }),
                    });
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status);
                    }
                    yes.setAttribute('aria-pressed', String(helpful));
                    no.setAttribute('aria-pressed', String(!helpful));
                    button.classList.add('is-selected');
                    status.textContent = 'Obrigado! Sua avaliação ajuda a melhorar o ResolveAI.';
                } catch (error) {
                    status.textContent = 'Não foi possível enviar a avaliação. Tente de novo.';
                    yes.disabled = false;
                    no.disabled = false;
                }
            }
            return box;
        }

        function renderError(message) {
            const alert = el('div', 'resolveai-error');
            alert.setAttribute('role', 'alert');
            alert.appendChild(el('p', '', message));
            const retry = el('button', 'btn btn-outline-secondary btn-sm', 'Tentar novamente');
            retry.type = 'button';
            retry.addEventListener('click', function () {
                analyze(false);
            });
            alert.appendChild(retry);
            body.replaceChildren(alert);
        }

        async function analyze(refresh) {
            if (loading) {
                return;
            }
            loading = true;
            refreshButton.disabled = true;
            renderLoading();

            const url =
                pluginBaseUrl() +
                '/front/insights.php?ticket_id=' +
                encodeURIComponent(ticketId) +
                (refresh ? '&refresh=1' : '');

            try {
                const response = await fetch(url, {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' },
                });

                if (response.status === 403) {
                    // Usuário sem perfil de analista: o assistente some.
                    root.remove();
                    return;
                }

                let payload;
                try {
                    payload = await response.json();
                } catch (parseError) {
                    throw new Error(
                        'O GLPI retornou uma resposta inesperada (HTTP ' + response.status +
                        '). Verifique o log files/_log/php-errors.log.'
                    );
                }

                if (!response.ok) {
                    throw new Error(payload.error || 'Não foi possível analisar o chamado.');
                }
                if (!isValidPayload(payload)) {
                    throw new Error('A API do ResolveAI retornou uma resposta inválida.');
                }

                renderResult(payload);
                loaded = true;
            } catch (error) {
                renderError(error.message || 'Não foi possível analisar o chamado.');
            } finally {
                stopTimer();
                loading = false;
                refreshButton.disabled = false;
            }
        }

        launcher.addEventListener('click', function () {
            const expand = root.dataset.state !== 'expanded';
            setExpanded(expand);
            rememberMinimized(ticketId, !expand);
        });
        minimizeButton.addEventListener('click', function () {
            setExpanded(false);
            rememberMinimized(ticketId, true);
            launcher.focus();
        });
        refreshButton.addEventListener('click', function () {
            analyze(true);
        });
        root.addEventListener('keydown', function (event) {
            if (event.key === 'Escape' && root.dataset.state === 'expanded') {
                setExpanded(false);
                rememberMinimized(ticketId, true);
                launcher.focus();
            }
        });

        renderIdle();
        document.body.appendChild(root);

        // Ao abrir um chamado, o assistente cresce sozinho (a menos que o
        // analista o tenha minimizado neste chamado durante a sessão).
        if (ticketId && !wasMinimized(ticketId)) {
            window.setTimeout(function () {
                setExpanded(true);
            }, 400);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', buildAssistant);
    } else {
        buildAssistant();
    }
})();
