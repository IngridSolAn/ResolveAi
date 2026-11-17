<?php

/**
 * Painel da IA (somente Super-Admin). Menu: Ferramentas > Painel da IA.
 *
 * A página só tem a estrutura; os dados vêm de front/admin.php, que repete a
 * checagem de permissão e consulta o backend servidor a servidor.
 */

include('../../../inc/includes.php');

Session::checkLoginUser();

if (!PluginResolveaiDashboard::canView()) {
    Html::displayRightError();
}

Html::header(
    PluginResolveaiDashboard::getTypeName(),
    $_SERVER['PHP_SELF'] ?? '',
    'tools',
    PluginResolveaiDashboard::class
);

global $CFG_GLPI;
$pluginWeb = rtrim((string) ($CFG_GLPI['root_doc'] ?? ''), '/') . '/plugins/resolveai';
// No GLPI 10 os arquivos estáticos ficam em /public no caminho da URL.
$assets = $pluginWeb . (version_compare(GLPI_VERSION, '11.0.0', '>=') ? '' : '/public');
$api = $pluginWeb . '/front/admin.php';
$h = static fn (string $value): string => htmlspecialchars($value, ENT_QUOTES, 'UTF-8');

echo '<link rel="stylesheet" href="' . $h($assets . '/css/painel.css?v=' . PLUGIN_RESOLVEAI_VERSION) . '">';
?>
<div class="viz-root" data-api="<?php echo $h($api); ?>">
  <div class="topbar">
    <div>
      <h1>Painel da IA</h1>
      <p class="muted">ResolveAI · acompanhamento do comportamento da IA · visível só para Super-Admin</p>
    </div>
  </div>

  <div class="filters" role="group" aria-label="Período">
    <span class="muted">Período:</span>
    <button type="button" class="chip" data-days="7">7 dias</button>
    <button type="button" class="chip" data-days="30" aria-pressed="true">30 dias</button>
    <button type="button" class="chip" data-days="90">90 dias</button>
    <button type="button" id="reload" class="ghost">Atualizar</button>
    <span id="updated" class="muted small"></span>
  </div>

  <p id="config" class="config muted"></p>
  <p id="load-error" class="error" role="alert" hidden></p>

  <div id="content">
    <section class="kpis" id="kpis" aria-label="Indicadores principais"></section>

    <div class="grid">
      <section class="card">
        <h2>Análises por dia</h2>
        <p class="muted small">Total de análises pedidas pelos analistas (inclui respostas do cache).</p>
        <div class="chart" id="chart-volume"></div>
      </section>
      <section class="card">
        <h2>Tempo de resposta da IA</h2>
        <p class="muted small">Mediana e p95 por dia, só de análises geradas (sem cache).</p>
        <div class="legend" id="legend-latency"></div>
        <div class="chart" id="chart-latency"></div>
      </section>
      <section class="card">
        <h2>Distribuição da confiança</h2>
        <p class="muted small">Quantas análises caíram em cada faixa de confiança (0–100%).</p>
        <div class="chart" id="chart-confidence"></div>
      </section>
      <section class="card">
        <h2>Comportamento do RAG e da IA</h2>
        <p class="muted small">Quanto o histórico de chamados resolvidos está sendo aproveitado.</p>
        <ul class="meters" id="meters"></ul>
      </section>
    </div>

    <section class="card">
      <h2>Últimas análises</h2>
      <p class="muted small">Por privacidade, o painel não guarda o texto dos chamados nem das respostas, só os números.</p>
      <div class="table-wrap">
        <table id="recent">
          <thead>
            <tr>
              <th scope="col">Quando</th>
              <th scope="col">Chamado</th>
              <th scope="col">IA</th>
              <th scope="col" class="num">Tempo</th>
              <th scope="col" class="num">Confiança</th>
              <th scope="col" class="num">Casos usados</th>
              <th scope="col">Cache</th>
              <th scope="col">Avaliação</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </section>
  </div>
  <div id="tooltip" class="tooltip" role="tooltip" hidden></div>
</div>
<?php
echo '<script src="' . $h($assets . '/js/painel.js?v=' . PLUGIN_RESOLVEAI_VERSION) . '"></script>';

Html::footer();
