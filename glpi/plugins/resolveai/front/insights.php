<?php

include('../../../inc/includes.php');

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function resolveai_json_response(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

Session::checkLoginUser();

$ticketId = filter_input(INPUT_GET, 'ticket_id', FILTER_VALIDATE_INT);
if (!$ticketId || $ticketId < 1) {
    resolveai_json_response(400, ['error' => 'A valid ticket_id is required.']);
}

$ticket = new Ticket();
if (!$ticket->getFromDB($ticketId) || !$ticket->can($ticketId, READ)) {
    resolveai_json_response(404, ['error' => 'Ticket not found or access denied.']);
}

$apiUrl = getenv('RESOLVEAI_API_URL');
if ($apiUrl === false || trim($apiUrl) === '') {
    error_log('[resolveai] RESOLVEAI_API_URL is not configured.');
    resolveai_json_response(503, ['error' => 'ResolveAI API is not configured.']);
}

$parsedUrl = filter_var($apiUrl, FILTER_VALIDATE_URL);
$scheme = strtolower((string) parse_url($apiUrl, PHP_URL_SCHEME));
if (!$parsedUrl || !in_array($scheme, ['http', 'https'], true)) {
    error_log('[resolveai] RESOLVEAI_API_URL must be a valid HTTP(S) URL.');
    resolveai_json_response(503, ['error' => 'ResolveAI API configuration is invalid.']);
}

if (!function_exists('curl_init')) {
    error_log('[resolveai] PHP cURL extension is not available.');
    resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
}

$ticketTitle = html_entity_decode(
    strip_tags((string) $ticket->fields['name']),
    ENT_QUOTES | ENT_HTML5,
    'UTF-8'
);
$ticketDescriptionHtml = (string) $ticket->fields['content'];
$ticketDescriptionHtml = preg_replace(
    '/<(br|\/p|\/div|\/li)\b[^>]*>/i',
    "\n",
    $ticketDescriptionHtml
);
$ticketDescription = html_entity_decode(
    trim(strip_tags((string) $ticketDescriptionHtml)),
    ENT_QUOTES | ENT_HTML5,
    'UTF-8'
);

$requestBody = json_encode([
    'ticket_id'   => (int) $ticketId,
    'title'       => $ticketTitle,
    'description' => $ticketDescription,
], JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);

if ($requestBody === false) {
    error_log('[resolveai] Could not encode ticket data for the API request.');
    resolveai_json_response(500, ['error' => 'Could not prepare the ticket for analysis.']);
}

$headers = [
    'Accept: application/json',
    'Content-Type: application/json',
];
$apiToken = getenv('RESOLVEAI_API_TOKEN');
if ($apiToken !== false && trim($apiToken) !== '') {
    $headers[] = 'Authorization: Bearer ' . trim($apiToken);
}

$curl = curl_init($apiUrl);
if ($curl === false) {
    error_log('[resolveai] Could not initialize the API request.');
    resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
}

$curlConfigured = curl_setopt_array($curl, [
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => $requestBody,
    CURLOPT_HTTPHEADER     => $headers,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_TIMEOUT        => 20,
    CURLOPT_FOLLOWLOCATION => false,
    CURLOPT_SSL_VERIFYPEER => true,
    CURLOPT_SSL_VERIFYHOST => 2,
]);

if (!$curlConfigured) {
    curl_close($curl);
    error_log('[resolveai] Could not configure the API request.');
    resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
}

$apiResponse = curl_exec($curl);
$curlError = curl_error($curl);
$httpStatus = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
curl_close($curl);

if ($apiResponse === false) {
    error_log('[resolveai] API request failed: ' . $curlError);
    resolveai_json_response(502, ['error' => 'Could not reach the ResolveAI API.']);
}

if ($httpStatus < 200 || $httpStatus >= 300) {
    error_log('[resolveai] API returned HTTP ' . $httpStatus . '.');
    resolveai_json_response(502, ['error' => 'ResolveAI API returned an unsuccessful response.']);
}

$result = json_decode($apiResponse, true);
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

resolveai_json_response(200, [
    'diagnostico_e_evidencias' => $result['diagnostico_e_evidencias'],
    'nivel_de_confianca'      => $result['nivel_de_confianca'],
    'passos_sugeridos_de_teste' => $result['passos_sugeridos_de_teste'],
]);
