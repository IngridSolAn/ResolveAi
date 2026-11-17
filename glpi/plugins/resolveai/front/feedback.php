<?php

/**
 * Recebe a avaliação do analista (👍/👎) e a repassa ao backend.
 *
 * POST JSON: {"analysis_id": "...", "helpful": true|false}
 * No GLPI 11+, a proteção CSRF de POST vem dos cabeçalhos Sec-Fetch-Site/Origin;
 * no GLPI 10, o JavaScript envia o token CSRF no cabeçalho X-Glpi-Csrf-Token.
 */

include('../../../inc/includes.php');
require_once __DIR__ . '/../inc/backend.php';

resolveai_require_technician();

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    resolveai_json_response(405, ['error' => 'Use POST.']);
}

$input = json_decode((string) file_get_contents('php://input'), true);
$analysisId = is_array($input) ? ($input['analysis_id'] ?? null) : null;
$helpful = is_array($input) ? ($input['helpful'] ?? null) : null;

if (!is_string($analysisId) || !preg_match('/^[A-Za-z0-9_-]{1,64}$/', $analysisId) || !is_bool($helpful)) {
    resolveai_json_response(400, ['error' => 'analysis_id and helpful are required.']);
}

[$httpStatus] = resolveai_backend_post('feedback', [
    'analysis_id' => $analysisId,
    'helpful'     => $helpful,
], 10);

if ($httpStatus === 404) {
    resolveai_json_response(404, ['error' => 'Analysis not found.']);
}
if ($httpStatus < 200 || $httpStatus >= 300) {
    error_log('[resolveai] Feedback API returned HTTP ' . $httpStatus . '.');
    resolveai_json_response(502, ['error' => 'Could not save the feedback.']);
}

resolveai_json_response(200, ['ok' => true]);
