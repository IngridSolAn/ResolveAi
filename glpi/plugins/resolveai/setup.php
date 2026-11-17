<?php

define('PLUGIN_RESOLVEAI_VERSION', '0.3.0');
define('PLUGIN_RESOLVEAI_MIN_GLPI_VERSION', '10.0.0');
define('PLUGIN_RESOLVEAI_MAX_GLPI_VERSION', '13.0.0');

function plugin_init_resolveai(): void
{
    global $PLUGIN_HOOKS;

    $PLUGIN_HOOKS['csrf_compliant']['resolveai'] = true;

    // O assistente flutuante é só para analistas (interface "central"); quem
    // abre chamados pela interface simplificada ("helpdesk") não o vê.
    if (Session::getCurrentInterface() === 'central') {
        // Os arquivos ficam em public/. No GLPI 11+, a URL /plugins/resolveai/js/...
        // já aponta para public/js/...; no GLPI 10 é preciso incluir "public/".
        $prefix = version_compare(GLPI_VERSION, '11.0.0', '>=') ? '' : 'public/';
        $PLUGIN_HOOKS['add_javascript']['resolveai'] = $prefix . 'js/resolveai.js';
        $PLUGIN_HOOKS['add_css']['resolveai'] = $prefix . 'css/resolveai.css';

        // Ferramentas > Painel da IA (a classe só mostra o item para Super-Admin).
        $PLUGIN_HOOKS['menu_toadd']['resolveai'] = ['tools' => 'PluginResolveaiDashboard'];
    }
}

function plugin_version_resolveai(): array
{
    return [
        'name'         => 'ResolveAI',
        'version'      => PLUGIN_RESOLVEAI_VERSION,
        'author'       => 'ResolveAI',
        'license'      => 'GPL-3.0-or-later',
        'requirements' => [
            'glpi' => [
                'min' => PLUGIN_RESOLVEAI_MIN_GLPI_VERSION,
                'max' => PLUGIN_RESOLVEAI_MAX_GLPI_VERSION,
            ],
        ],
    ];
}

function plugin_resolveai_check_prerequisites(): bool
{
    if (version_compare(GLPI_VERSION, PLUGIN_RESOLVEAI_MIN_GLPI_VERSION, '<')) {
        echo 'ResolveAI requires GLPI 10.0.0 or later.';
        return false;
    }

    if (version_compare(GLPI_VERSION, PLUGIN_RESOLVEAI_MAX_GLPI_VERSION, '>=')) {
        echo 'ResolveAI supports only GLPI versions below 13.0.0.';
        return false;
    }

    return true;
}

function plugin_resolveai_check_config($verbose = false): bool
{
    return true;
}
