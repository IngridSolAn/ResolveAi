<?php

include('../../../inc/includes.php');
require_once __DIR__ . '/../inc/backend.php';

resolveai_require_technician();

$ticketId = filter_input(INPUT_GET, 'ticket_id', FILTER_VALIDATE_INT);
if (!$ticketId || $ticketId < 1) {
    resolveai_json_response(400, ['error' => 'A valid ticket_id is required.']);
}

$ticket = new Ticket();
if (!$ticket->getFromDB($ticketId) || !$ticket->can($ticketId, READ)) {
    resolveai_json_response(404, ['error' => 'Ticket not found or access denied.']);
}

$ticketTitle = html_entity_decode(
    strip_tags((string) $ticket->fields['name']),
    ENT_QUOTES | ENT_HTML5,
    'UTF-8'
);
$ticketDescriptionHtml = preg_replace(
    '/<(br|\/p|\/div|\/li)\b[^>]*>/i',
    "\n",
    (string) $ticket->fields['content']
);
$ticketDescription = html_entity_decode(
    trim(strip_tags((string) $ticketDescriptionHtml)),
    ENT_QUOTES | ENT_HTML5,
    'UTF-8'
);

// A IA local (Ollama) pode levar alguns minutos em máquinas sem GPU.
$apiTimeout = (int) getenv('RESOLVEAI_API_TIMEOUT');
if ($apiTimeout < 10) {
    $apiTimeout = 300;
}

[$httpStatus, $result] = resolveai_backend_post('analyze', [
    'ticket_id'   => (int) $ticketId,
    'title'       => $ticketTitle,
    'description' => $ticketDescription,
    // Isola o RAG: só busca casos parecidos na mesma entidade do chamado.
    'tenant_id'   => (int) $ticket->fields['entities_id'],
    // "Analisar novamente" no assistente ignora o cache do backend.
    'refresh'     => filter_input(INPUT_GET, 'refresh', FILTER_VALIDATE_BOOLEAN) === true,
], $apiTimeout);

if ($httpStatus < 200 || $httpStatus >= 300) {
    error_log('[resolveai] API returned HTTP ' . $httpStatus . '.');
    resolveai_json_response(502, ['error' => 'ResolveAI API returned an unsuccessful response.']);
}

if (
    !is_array($result)
    || !isset($result['diagnostico_e_evidencias'])
    || !is_string($result['diagnostico_e_evidencias'])
    || trim($result['diagnostico_e_evidencias']) === ''
    || !isset($result['nivel_de_confianca'])
    || !is_array($result['nivel_de_confianca'])
    || !isset($result['nivel_de_confianca']['percentual'])
    || !is_int($result['nivel_de_confianca']['percentual'])
    || $result['nivel_de_confianca']['percentual'] < 0
    || $result['nivel_de_confianca']['percentual'] > 100
    || !isset($result['nivel_de_confianca']['justificativa'])
    || !is_string($result['nivel_de_confianca']['justificativa'])
    || trim($result['nivel_de_confianca']['justificativa']) === ''
    || !isset($result['passos_sugeridos_de_teste'])
    || !is_array($result['passos_sugeridos_de_teste'])
) {
    error_log('[resolveai] API response did not match the insights JSON contract.');
    resolveai_json_response(502, ['error' => 'ResolveAI API returned an invalid response.']);
}

foreach ($result['passos_sugeridos_de_teste'] as $step) {
    if (!is_string($step) || trim($step) === '') {
        error_log('[resolveai] API returned an invalid test step.');
        resolveai_json_response(502, ['error' => 'ResolveAI API returned an invalid response.']);
    }
}

$analysisId = $result['analysis_id'] ?? null;
if (!is_string($analysisId) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/', $analysisId)) {
    $analysisId = null; // backend antigo: o assistente só não mostra a avaliação
}

resolveai_json_response(200, [
    'analysis_id'               => $analysisId,
    'diagnostico_e_evidencias'  => $result['diagnostico_e_evidencias'],
    'nivel_de_confianca'        => $result['nivel_de_confianca'],
    'passos_sugeridos_de_teste' => $result['passos_sugeridos_de_teste'],
]);
