<?php

define('PLUGIN_RESOLVEAI_VERSION', '0.1.0');
define('PLUGIN_RESOLVEAI_MIN_GLPI_VERSION', '10.0.0');
define('PLUGIN_RESOLVEAI_MAX_GLPI_VERSION', '11.0.0');

function plugin_init_resolveai(): void
{
    global $PLUGIN_HOOKS;

    $PLUGIN_HOOKS['csrf_compliant']['resolveai'] = true;
    $PLUGIN_HOOKS['add_javascript']['resolveai'] = 'js/resolveai.js';
    $PLUGIN_HOOKS['add_css']['resolveai'] = 'css/resolveai.css';

    Plugin::registerClass(PluginResolveaiTicket::class, [
        'addtabon' => ['Ticket'],
    ]);
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
        echo 'ResolveAI currently supports GLPI 10.x only.';
        return false;
    }

    return true;
}

function plugin_resolveai_check_config($verbose = false): bool
{
    return true;
}
