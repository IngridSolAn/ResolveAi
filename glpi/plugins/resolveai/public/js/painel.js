/* Painel da IA dentro do GLPI (somente Super-Admin).
 *
 * Usa a sessão do GLPI: os dados vêm de front/admin.php, que confere a
 * permissão e chama o backend servidor a servidor com o token de
 * administrador (que nunca chega ao navegador). Todo texto vindo da API entra
 * via textContent.
 */
(function () {
  'use strict';

  const root = document.querySelector('.viz-root[data-api]');
  if (!root) return;

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const API = root.dataset.api;
  const state = { days: 30 };

  const $ = (selector) => root.querySelector(selector);
  const tooltip = $('#tooltip');

  // ---------- utilidades ----------

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function svg(tag, attrs) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs || {}).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  const pct = (rate) => (rate === null || rate === undefined ? '—' : Math.round(rate * 100) + '%');
  const int = (value) => (value === null || value === undefined ? '—' : value.toLocaleString('pt-BR'));

  function duration(ms) {
    if (ms === null || ms === undefined) return '—';
    if (ms < 1000) return ms + ' ms';
    const seconds = ms / 1000;
    if (Math.round(seconds) < 60) return seconds.toFixed(seconds < 10 ? 1 : 0).replace('.', ',') + ' s';
    const minutes = Math.floor(seconds / 60);
    return minutes + ' min ' + Math.round(seconds % 60) + ' s';
  }

  function shortDate(iso) {
    const [, month, day] = iso.split('-');
    return day + '/' + month;
  }

  function niceMax(value) {
    if (!value || value <= 0) return 1;
    const magnitude = Math.pow(10, Math.floor(Math.log10(value)));
    const step = [1, 2, 2.5, 5, 10].find((m) => m * magnitude >= value) * magnitude;
    return step;
  }

  // ---------- tooltip ----------

  function showTooltip(event, title, rows) {
    tooltip.replaceChildren(el('div', 'tt-title', title));
    rows.forEach((row) => {
      const line = el('div', 'tt-row');
      if (row.color) {
        const key = el('span', 'tt-key');
        key.style.setProperty('--key', row.color);
        line.appendChild(key);
      }
      line.append(el('strong', '', row.value), el('span', 'tt-name', row.name));
      tooltip.appendChild(line);
    });
    tooltip.hidden = false;
    const rect = tooltip.getBoundingClientRect();
    let x = event.clientX + 14;
    let y = event.clientY + 14;
    if (x + rect.width > window.innerWidth - 8) x = event.clientX - rect.width - 14;
    if (y + rect.height > window.innerHeight - 8) y = event.clientY - rect.height - 14;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  }

  function tooltipAtElement(target, title, rows) {
    const box = target.getBoundingClientRect();
    showTooltip({ clientX: box.left + box.width / 2, clientY: box.top }, title, rows);
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  // ---------- gráficos (SVG simples, eixo único) ----------

  const W = 560;
  const H = 220;
  const M = { top: 12, right: 64, bottom: 26, left: 44 };

  function frame(container, yMax, yFormat) {
    const root = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img' });
    const innerH = H - M.top - M.bottom;
    for (let i = 0; i <= 4; i += 1) {
      const value = (yMax / 4) * i;
      const y = M.top + innerH - (innerH * i) / 4;
      root.appendChild(
        svg('line', { class: i === 0 ? 'baseline' : 'grid-line', x1: M.left, x2: W - M.right, y1: y, y2: y })
      );
      const label = svg('text', { class: 'tick', x: M.left - 8, y: y + 4, 'text-anchor': 'end' });
      label.textContent = yFormat(value);
      root.appendChild(label);
    }
    container.replaceChildren(root);
    return { root, innerH, innerW: W - M.left - M.right };
  }

  function xLabels(root, labels, xOf) {
    // Ancora no último rótulo (o dia mais recente) e espaça a partir dele,
    // para os rótulos nunca se sobreporem.
    const every = Math.ceil(labels.length / 8);
    labels.forEach((text, index) => {
      if ((labels.length - 1 - index) % every !== 0) return;
      const label = svg('text', { class: 'tick', x: xOf(index), y: H - 8, 'text-anchor': 'middle' });
      label.textContent = text;
      root.appendChild(label);
    });
  }

  /** Colunas com topo arredondado (4px) ancoradas na linha de base. */
  function columnChart(container, items, options) {
    const total = items.reduce((sum, item) => sum + item.value, 0);
    if (!total) {
      container.replaceChildren(el('p', 'empty', 'Sem dados no período.'));
      return;
    }
    const yMax = niceMax(Math.max(...items.map((item) => item.value)));
    const { root, innerH, innerW } = frame(container, yMax, (v) => (Number.isInteger(v) ? v : ''));
    root.setAttribute('aria-label', options.label);
    const slot = innerW / items.length;
    const barW = Math.max(2, Math.min(slot - 2, 48));
    const xOf = (index) => M.left + slot * index + slot / 2;

    items.forEach((item, index) => {
      const h = (innerH * item.value) / yMax;
      const x = xOf(index) - barW / 2;
      const y = M.top + innerH - h;
      if (h > 0) {
        const r = Math.min(4, barW / 2, h);
        const path = `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + barW - r} Q${x + barW},${y} ${x + barW},${y + r} V${y + h} Z`;
        root.appendChild(svg('path', { class: 'bar', d: path }));
      }
      if (options.valueLabels && item.value > 0) {
        const label = svg('text', { class: 'value-label', x: xOf(index), y: y - 4 });
        label.textContent = item.value;
        root.appendChild(label);
      }
      // Área de hover maior que a barra (toda a coluna).
      const hit = svg('rect', {
        class: 'hit', x: M.left + slot * index, y: M.top, width: slot, height: innerH, tabindex: 0,
        'aria-label': `${item.label}: ${item.value}`,
      });
      const rows = () => options.tooltipRows(item);
      hit.addEventListener('pointermove', (event) => showTooltip(event, item.title || item.label, rows()));
      hit.addEventListener('pointerleave', hideTooltip);
      hit.addEventListener('focus', () => tooltipAtElement(hit, item.title || item.label, rows()));
      hit.addEventListener('blur', hideTooltip);
      root.appendChild(hit);
    });
    xLabels(root, items.map((item) => item.label), xOf);
  }

  /** Linhas de 2px com crosshair; legenda + rótulo direto no fim de cada série. */
  function lineChart(container, labels, series, options) {
    const values = series.flatMap((s) => s.values).filter((v) => v !== null);
    if (!values.length) {
      container.replaceChildren(el('p', 'empty', 'Sem análises geradas no período.'));
      return;
    }
    const yMax = niceMax(Math.max(...values));
    const { root, innerH, innerW } = frame(container, yMax, (v) => options.yFormat(v));
    root.setAttribute('aria-label', options.label);
    const step = labels.length > 1 ? innerW / (labels.length - 1) : 0;
    const xOf = (index) => (labels.length > 1 ? M.left + step * index : M.left + innerW / 2);
    const yOf = (value) => M.top + innerH - (innerH * value) / yMax;

    const endLabels = [];
    series.forEach((s) => {
      let d = '';
      let pen = false;
      s.values.forEach((value, index) => {
        if (value === null) { pen = false; return; }
        d += (pen ? ' L' : ' M') + xOf(index) + ',' + yOf(value);
        pen = true;
      });
      root.appendChild(svg('path', { class: 'line ' + s.cls, d: d.trim() }));
      // Pontos isolados (dias sem vizinhos) ganham marcador de 8px.
      s.values.forEach((value, index) => {
        const prev = s.values[index - 1];
        const next = s.values[index + 1];
        if (value !== null && (prev === null || prev === undefined) && (next === null || next === undefined)) {
          root.appendChild(svg('circle', { class: s.dotCls, cx: xOf(index), cy: yOf(value), r: 4 }));
        }
      });
      const lastIndex = s.values.map((v, i) => (v === null ? -1 : i)).filter((i) => i >= 0).pop();
      if (lastIndex !== undefined) {
        endLabels.push({ name: s.name, x: xOf(lastIndex) + 8, y: yOf(s.values[lastIndex]) + 4 });
      }
    });
    // Rótulos diretos no fim das linhas: afasta os que ficariam encavalados.
    endLabels.sort((a, b) => a.y - b.y);
    for (let i = 1; i < endLabels.length; i += 1) {
      if (endLabels[i].y - endLabels[i - 1].y < 13) endLabels[i].y = endLabels[i - 1].y + 13;
    }
    endLabels.forEach((item) => {
      const label = svg('text', { class: 'direct-label', x: item.x, y: item.y });
      label.textContent = item.name;
      root.appendChild(label);
    });

    const crosshair = svg('line', { class: 'crosshair', y1: M.top, y2: M.top + innerH, visibility: 'hidden' });
    root.appendChild(crosshair);
    const hit = svg('rect', { class: 'hit', x: M.left - 6, y: M.top, width: innerW + 12, height: innerH, tabindex: 0,
      'aria-label': options.label + ': use o mouse para ver os valores por dia' });
    hit.addEventListener('pointermove', (event) => {
      const box = root.getBoundingClientRect();
      const x = ((event.clientX - box.left) / box.width) * W;
      const index = Math.max(0, Math.min(labels.length - 1, Math.round((x - M.left) / (step || 1))));
      crosshair.setAttribute('x1', xOf(index));
      crosshair.setAttribute('x2', xOf(index));
      crosshair.setAttribute('visibility', 'visible');
      showTooltip(event, options.titles[index], series.map((s) => ({
        color: getComputedStyle(container).getPropertyValue(s.colorVar),
        value: options.yFormat(s.values[index], true),
        name: s.name,
      })));
    });
    hit.addEventListener('pointerleave', () => { crosshair.setAttribute('visibility', 'hidden'); hideTooltip(); });
    root.appendChild(hit);
    xLabels(root, labels, xOf);
  }

  // ---------- seções ----------

  function kpi(label, value, sub, status) {
    const card = el('article', 'kpi');
    card.append(el('p', 'kpi-label', label), el('p', 'kpi-value', value));
    if (status) {
      card.appendChild(el('p', 'status ' + status.tone, status.text));
    } else if (sub) {
      card.appendChild(el('p', 'kpi-sub', sub));
    }
    return card;
  }

  function renderKpis(data) {
    const t = data.totals;
    const errorRate = data.rates.error;
    const errorTone = errorRate === null ? null : errorRate === 0 ? 'good' : errorRate < 0.1 ? 'warning' : 'critical';
    const errorText = { good: 'Sem erros', warning: 'Atenção', critical: 'Crítico' }[errorTone];
    $('#kpis').replaceChildren(
      kpi('Análises', int(t.analyses), `${int(t.cache_hits)} do cache`),
      kpi('Tempo mediano', duration(data.latency_ms.p50), `p95: ${duration(data.latency_ms.p95)}`),
      kpi('Confiança média', data.confidence.average === null ? '—' : Math.round(data.confidence.average) + '%', 'informada pela IA'),
      kpi('Avaliações "ajudou"', pct(data.rates.helpful), `${int(t.helpful)} de ${int(t.rated)} avaliações`),
      kpi('Usou o histórico', pct(data.rates.with_history), 'análises com casos parecidos'),
      kpi('Erros', `${int(t.errors)} (${pct(errorRate)})`, null, errorTone ? { tone: errorTone, text: errorText } : null)
    );
  }

  function meter(name, rate, note) {
    const row = el('li', 'meter-row');
    const track = el('div', 'meter-track');
    const fill = el('div', 'meter-fill');
    fill.style.width = rate === null ? '0' : Math.round(rate * 100) + '%';
    track.appendChild(fill);
    track.setAttribute('role', 'meter');
    track.setAttribute('aria-valuemin', '0');
    track.setAttribute('aria-valuemax', '100');
    track.setAttribute('aria-valuenow', rate === null ? '0' : String(Math.round(rate * 100)));
    track.setAttribute('aria-label', name);
    row.append(el('span', 'meter-name', name), el('span', 'meter-value', pct(rate)), track);
    if (note) row.appendChild(el('span', 'meter-note', note));
    return row;
  }

  function renderMeters(data) {
    const r = data.rates;
    $('#meters').replaceChildren(
      meter('Análises com histórico enviado à IA', r.with_history, 'Houve ao menos um caso parecido dentro do limite de distância.'),
      meter('Análises em que a IA citou um caso', r.cited_case, 'O diagnóstico menciona o ID de um chamado do histórico.'),
      meter('Avaliadas como "ajudou"', r.helpful, `${int(data.totals.rated)} avaliações de analistas no período.`),
      meter('Respostas servidas pelo cache', r.cache_hit, 'Chamado reaberto sem alterações: resposta imediata.')
    );
  }

  function renderCharts(data) {
    const daily = data.daily;
    columnChart($('#chart-volume'), daily.map((d) => ({
      label: shortDate(d.date), title: shortDate(d.date), value: d.analyses, errors: d.errors,
    })), {
      label: 'Análises por dia',
      tooltipRows: (item) => [
        { value: int(item.value), name: 'análises' },
        { value: int(item.errors), name: 'com erro' },
      ],
    });

    const style = getComputedStyle($('#chart-latency'));
    const legend = $('#legend-latency');
    legend.replaceChildren(
      ...[['Mediana', '--series-1'], ['p95', '--series-2']].map(([name, colorVar]) => {
        const item = el('span', 'legend-item');
        const key = el('span', 'legend-key');
        key.style.setProperty('--key', style.getPropertyValue(colorVar));
        item.append(key, document.createTextNode(name));
        return item;
      })
    );
    lineChart($('#chart-latency'), daily.map((d) => shortDate(d.date)), [
      { name: 'Mediana', cls: 'line-1', dotCls: 'dot-1', colorVar: '--series-1', values: daily.map((d) => d.p50_ms) },
      { name: 'p95', cls: 'line-2', dotCls: 'dot-2', colorVar: '--series-2', values: daily.map((d) => d.p95_ms) },
    ], {
      label: 'Tempo de resposta por dia',
      titles: daily.map((d) => shortDate(d.date)),
      yFormat: (value, full) => (value === null || value === undefined ? 'sem dados' : full ? duration(value) : Math.round(value / 1000) + ' s'),
    });

    columnChart($('#chart-confidence'), data.confidence.buckets.map((b) => ({
      label: b.range + '%', title: 'Confiança ' + b.range + '%', value: b.count,
    })), {
      label: 'Distribuição da confiança',
      valueLabels: true,
      tooltipRows: (item) => [{ value: int(item.value), name: 'análises' }],
    });
  }

  function renderTable(rows) {
    const body = $('#recent tbody');
    if (!rows.length) {
      const tr = el('tr');
      const td = el('td', 'empty', 'Nenhuma análise registrada ainda.');
      td.colSpan = 9;
      tr.appendChild(td);
      body.replaceChildren(tr);
      return;
    }
    body.replaceChildren(...rows.map((row) => {
      const tr = el('tr');
      const when = new Date(row.created_at).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
      const feedback = row.helpful === null ? '—' : row.helpful ? '👍 Ajudou' : '👎 Não ajudou';
      const status = el('span', 'status ' + (row.status === 'ok' ? 'good' : 'critical'),
        row.status === 'ok' ? 'OK' : 'Erro' + (row.error_type ? ` (${row.error_type})` : ''));
      const cells = [
        el('td', '', when),
        el('td', '', '#' + row.ticket_id),
        el('td', '', row.provider + (row.model ? ' · ' + row.model : '')),
        el('td', 'num', duration(row.duration_ms)),
        el('td', 'num', row.confidence === null ? '—' : row.confidence + '%'),
        el('td', 'num', `${row.cases_used} de ${row.cases_retrieved}`),
        el('td', '', row.cache_hit ? 'Sim' : 'Não'),
        el('td', '', feedback),
      ];
      const statusCell = el('td');
      statusCell.appendChild(status);
      tr.append(...cells, statusCell);
      return tr;
    }));
  }

  function renderConfig(config) {
    const parts = [
      `IA em uso: ${config.provider}${config.model ? ' · ' + config.model : ''}`,
      `RAG: ${config.rag_enabled ? `ligado (até ${config.rag_limit} casos, distância ≤ ${config.rag_max_distance ?? 'sem limite'})` : 'desligado'}`,
      `Cache: ${config.cache_ttl_seconds > 0 ? Math.round(config.cache_ttl_seconds / 3600) + ' h' : 'desligado'}`,
    ];
    $('#config').textContent = parts.join('  ·  ');
  }

  // ---------- dados ----------

  async function api(params) {
    const response = await fetch(API + '?' + new URLSearchParams(params), {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
    let body = null;
    try { body = await response.json(); } catch (error) { /* corpo vazio */ }
    if (!response.ok) throw new Error((body && body.error) || 'Erro ' + response.status);
    return body;
  }

  async function load() {
    const content = $('#content');
    content.classList.add('refreshing');
    $('#load-error').hidden = true;
    try {
      const [metrics, recent] = await Promise.all([
        api({ action: 'metrics', days: state.days }),
        api({ action: 'analyses', limit: 50 }),
      ]);
      renderConfig(metrics.config);
      renderKpis(metrics);
      renderMeters(metrics);
      renderCharts(metrics);
      renderTable(recent);
      $('#updated').textContent = 'Atualizado às ' + new Date().toLocaleTimeString('pt-BR', { timeStyle: 'short' });
    } catch (error) {
      $('#load-error').textContent = 'Não foi possível carregar os dados: ' + error.message;
      $('#load-error').hidden = false;
    } finally {
      content.classList.remove('refreshing');
    }
  }

  $('#reload').addEventListener('click', load);
  root.querySelectorAll('.chip[data-days]').forEach((chip) => {
    chip.addEventListener('click', () => {
      state.days = Number(chip.dataset.days);
      root.querySelectorAll('.chip[data-days]').forEach((c) => c.setAttribute('aria-pressed', String(c === chip)));
      load();
    });
  });

  load();
})();
