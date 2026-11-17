<?php

/**
 * Dados do Painel da IA (somente Super-Admin).
 *
 * GET ?action=metrics&days=30 | ?action=analyses&limit=50
 * Repassa ao backend (/admin/*) usando RESOLVEAI_ADMIN_TOKEN, que fica só no
 * servidor do GLPI e nunca chega ao navegador.
 */

include('../../../inc/includes.php');
require_once __DIR__ . '/../inc/backend.php';

Session::checkLoginUser();

if (!PluginResolveaiDashboard::canView()) {
    resolveai_json_response(403, ['error' => 'Acesso restrito a administradores (Super-Admin).']);
}

$action = filter_input(INPUT_GET, 'action');
if ($action === 'metrics') {
    $days = filter_input(INPUT_GET, 'days', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 365]]);
    [$status, $body] = resolveai_backend_admin_get('admin/metrics', ['days' => $days ?: 30]);
} elseif ($action === 'analyses') {
    $limit = filter_input(INPUT_GET, 'limit', FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 500]]);
    [$status, $body] = resolveai_backend_admin_get('admin/analyses', ['limit' => $limit ?: 50]);
} else {
    resolveai_json_response(400, ['error' => 'Ação inválida.']);
}

if ($status === 401 || $status === 403) {
    error_log('[resolveai] Backend rejected the admin token (HTTP ' . $status . ').');
    resolveai_json_response(503, [
        'error' => 'O backend recusou o acesso: confira se RESOLVEAI_ADMIN_TOKEN é o mesmo no GLPI e no backend.',
    ]);
}
if ($status < 200 || $status >= 300 || !is_array($body)) {
    error_log('[resolveai] Admin API returned HTTP ' . $status . '.');
    resolveai_json_response(502, ['error' => 'Não foi possível obter os dados do backend.']);
}

resolveai_json_response(200, $body);
