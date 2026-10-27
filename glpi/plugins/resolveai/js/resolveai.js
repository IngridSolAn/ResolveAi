(function () {
    'use strict';

    const rootSelector = '[data-resolveai-insights]';

    function renderError(container, message) {
        const body = container.querySelector('.card-body');
        const result = document.createElement('p');
        result.className = 'alert alert-danger';
        result.textContent = message;
        body.replaceChildren(result);
        body.setAttribute('aria-busy', 'false');
    }

    function appendSection(body, title, content) {
        const section = document.createElement('section');
        section.className = 'resolveai-section';

        const heading = document.createElement('h4');
        heading.className = 'h5';
        heading.textContent = title;
        section.appendChild(heading);

        if (Array.isArray(content)) {
            const list = document.createElement('ol');
            content.forEach(function (step) {
                const item = document.createElement('li');
                item.textContent = step;
                list.appendChild(item);
            });
            section.appendChild(list);
        } else {
            const text = document.createElement('p');
            text.className = 'resolveai-insight';
            text.textContent = content;
            section.appendChild(text);
        }

        body.appendChild(section);
    }

    function renderInsights(container, payload) {
        const body = container.querySelector('.card-body');
        body.replaceChildren();

        appendSection(
            body,
            'Diagnóstico e Evidências',
            payload.diagnostico_e_evidencias
        );

        const confidence = payload.nivel_de_confianca;
        appendSection(
            body,
            'Nível de Confiança (0-100%)',
            confidence.percentual + '% — ' + confidence.justificativa
        );

        appendSection(
            body,
            'Passos Sugeridos de Teste',
            payload.passos_sugeridos_de_teste
        );
        body.setAttribute('aria-busy', 'false');
    }

    async function loadInsights(container) {
        if (container.dataset.loading === 'true' || container.dataset.loaded === 'true') {
            return;
        }

        container.dataset.loading = 'true';
        const body = container.querySelector('.card-body');
        const ticketId = container.dataset.ticketId;
        const endpoint = container.dataset.endpoint;

        try {
            const response = await fetch(
                endpoint + '?ticket_id=' + encodeURIComponent(ticketId),
                {
                    method: 'GET',
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' },
                }
            );
            const payload = await response.json();

            if (!response.ok) {
                throw new Error(payload.error || 'Não foi possível carregar os insights.');
            }

            const confidence = payload.nivel_de_confianca;
            if (
                typeof payload.diagnostico_e_evidencias !== 'string' ||
                payload.diagnostico_e_evidencias.trim() === '' ||
                !confidence ||
                !Number.isInteger(confidence.percentual) ||
                confidence.percentual < 0 ||
                confidence.percentual > 100 ||
                typeof confidence.justificativa !== 'string' ||
                confidence.justificativa.trim() === '' ||
                !Array.isArray(payload.passos_sugeridos_de_teste) ||
                !payload.passos_sugeridos_de_teste.every(
                    function (step) {
                        return typeof step === 'string' && step.trim() !== '';
                    }
                )
            ) {
                throw new Error('A API do ResolveAI retornou um JSON inválido.');
            }

            renderInsights(container, payload);
            container.dataset.loaded = 'true';
        } catch (error) {
            renderError(container, error.message || 'Não foi possível carregar os insights.');

            const retry = document.createElement('button');
            retry.type = 'button';
            retry.className = 'btn btn-outline-secondary btn-sm mt-2';
            retry.textContent = 'Tentar novamente';
            retry.addEventListener('click', function () {
                body.replaceChildren(createLoadingPlaceholder());
                body.setAttribute('aria-busy', 'true');
                container.dataset.loading = 'false';
                loadInsights(container);
            });
            body.appendChild(retry);
        } finally {
            container.dataset.loading = 'false';
        }
    }

    function createLoadingPlaceholder() {
        const loading = document.createElement('div');
        loading.className = 'resolveai-loading';
        loading.setAttribute('role', 'status');

        const title = document.createElement('span');
        title.className = 'resolveai-skeleton resolveai-skeleton-title';
        title.setAttribute('aria-hidden', 'true');

        const line = document.createElement('span');
        line.className = 'resolveai-skeleton';
        line.setAttribute('aria-hidden', 'true');

        const shortLine = document.createElement('span');
        shortLine.className = 'resolveai-skeleton resolveai-skeleton-short';
        shortLine.setAttribute('aria-hidden', 'true');

        loading.append(title, line, shortLine);
        return loading;
    }

    function initialize(root) {
        if (root instanceof Element && root.matches(rootSelector)) {
            loadInsights(root);
        }

        root.querySelectorAll(rootSelector).forEach(loadInsights);
    }

    initialize(document);

    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node instanceof Element) {
                    initialize(node);
                }
            });
        });
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
