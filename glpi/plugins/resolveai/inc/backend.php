<?php

/**
 * Funções compartilhadas pelos endpoints do plugin (insights.php e feedback.php).
 *
 * O navegador nunca fala direto com o backend do ResolveAI: estes endpoints
 * validam a sessão do GLPI e fazem a chamada servidor a servidor.
 */

function resolveai_json_response(int $status, array $payload): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    exit;
}

/** Exige usuário logado na interface de analistas ("central"). */
function resolveai_require_technician(): void
{
    Session::checkLoginUser();

    if (Session::getCurrentInterface() !== 'central') {
        resolveai_json_response(403, ['error' => 'ResolveAI is available only to technicians.']);
    }
}

/**
 * URL de um endpoint do backend. RESOLVEAI_API_URL aponta para /analyze; os
 * demais endpoints ficam ao lado dele (ex.: /feedback).
 */
function resolveai_backend_url(string $endpoint): string
{
    $apiUrl = getenv('RESOLVEAI_API_URL');
    if ($apiUrl === false || trim($apiUrl) === '') {
        error_log('[resolveai] RESOLVEAI_API_URL is not configured.');
        resolveai_json_response(503, ['error' => 'ResolveAI API is not configured.']);
    }

    $apiUrl = trim($apiUrl);
    $scheme = strtolower((string) parse_url($apiUrl, PHP_URL_SCHEME));
    if (!filter_var($apiUrl, FILTER_VALIDATE_URL) || !in_array($scheme, ['http', 'https'], true)) {
        error_log('[resolveai] RESOLVEAI_API_URL must be a valid HTTP(S) URL.');
        resolveai_json_response(503, ['error' => 'ResolveAI API configuration is invalid.']);
    }

    if ($endpoint === 'analyze') {
        return $apiUrl;
    }

    return preg_replace('#/analyze/?$#', '', $apiUrl) . '/' . $endpoint;
}

/**
 * POST JSON para o backend. Retorna [status HTTP, corpo decodificado ou null].
 * Em falha de rede ou configuração, responde ao navegador e encerra.
 */
function resolveai_backend_post(string $endpoint, array $payload, int $timeout): array
{
    if (!function_exists('curl_init')) {
        error_log('[resolveai] PHP cURL extension is not available.');
        resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
    }

    $body = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);
    if ($body === false) {
        error_log('[resolveai] Could not encode the API request.');
        resolveai_json_response(500, ['error' => 'Could not prepare the request.']);
    }

    $headers = ['Accept: application/json', 'Content-Type: application/json'];
    $apiToken = getenv('RESOLVEAI_API_TOKEN');
    if ($apiToken !== false && trim($apiToken) !== '') {
        $headers[] = 'Authorization: Bearer ' . trim($apiToken);
    }

    $curl = curl_init(resolveai_backend_url($endpoint));
    if ($curl === false) {
        error_log('[resolveai] Could not initialize the API request.');
        resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
    }

    $configured = curl_setopt_array($curl, [
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $body,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT        => $timeout,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);
    if (!$configured) {
        curl_close($curl);
        error_log('[resolveai] Could not configure the API request.');
        resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
    }

    $response = curl_exec($curl);
    $error = curl_error($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    curl_close($curl);

    if ($response === false) {
        error_log('[resolveai] API request failed: ' . $error);
        resolveai_json_response(502, ['error' => 'Could not reach the ResolveAI API.']);
    }

    $decoded = $response === '' ? null : json_decode($response, true);

    return [$status, is_array($decoded) ? $decoded : null];
}

/**
 * GET autenticado com o token de administrador (RESOLVEAI_ADMIN_TOKEN), usado
 * só pelo Painel da IA. O token fica no ambiente do servidor do GLPI.
 * Retorna [status HTTP, corpo decodificado ou null].
 */
function resolveai_backend_admin_get(string $endpoint, array $query): array
{
    $adminToken = getenv('RESOLVEAI_ADMIN_TOKEN');
    if ($adminToken === false || trim($adminToken) === '') {
        error_log('[resolveai] RESOLVEAI_ADMIN_TOKEN is not configured in the GLPI environment.');
        resolveai_json_response(503, [
            'error' => 'Painel não configurado: defina RESOLVEAI_ADMIN_TOKEN no GLPI e no backend.',
        ]);
    }
    if (!function_exists('curl_init')) {
        resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
    }

    $curl = curl_init(resolveai_backend_url($endpoint) . '?' . http_build_query($query));
    if ($curl === false) {
        resolveai_json_response(503, ['error' => 'ResolveAI integration is unavailable.']);
    }
    curl_setopt_array($curl, [
        CURLOPT_HTTPGET        => true,
        CURLOPT_HTTPHEADER     => ['Accept: application/json', 'Authorization: Bearer ' . trim($adminToken)],
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => true,
        CURLOPT_SSL_VERIFYHOST => 2,
    ]);

    $response = curl_exec($curl);
    $error = curl_error($curl);
    $status = (int) curl_getinfo($curl, CURLINFO_RESPONSE_CODE);
    curl_close($curl);

    if ($response === false) {
        error_log('[resolveai] Admin API request failed: ' . $error);
        resolveai_json_response(502, ['error' => 'Could not reach the ResolveAI API.']);
    }

    $decoded = json_decode($response, true);

    return [$status, is_array($decoded) ? $decoded : null];
}
