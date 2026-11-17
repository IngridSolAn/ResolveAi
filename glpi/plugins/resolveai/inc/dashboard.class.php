<?php

/**
 * Entrada "Painel da IA" no menu Ferramentas do GLPI.
 *
 * Só aparece (e só abre) para quem pode administrar a configuração do GLPI,
 * isto é, o perfil Super-Admin (direito "config" com permissão de atualização).
 */
class PluginResolveaiDashboard extends CommonGLPI
{
    // Não redeclare $rightname: no GLPI 12 a propriedade é tipada e no GLPI 10
    // não, então redeclará-la quebra uma das versões. canView() faz a checagem.

    public static function getTypeName($nb = 0): string
    {
        return 'Painel da IA (ResolveAI)';
    }

    public static function getMenuName(): string
    {
        return 'Painel da IA';
    }

    public static function getIcon(): string
    {
        return 'ti ti-chart-dots';
    }

    /** Super-Admin: pode alterar a configuração geral do GLPI. */
    public static function canView(): bool
    {
        return Session::getCurrentInterface() === 'central'
            && Session::haveRight('config', UPDATE);
    }

    public static function getMenuContent()
    {
        if (!self::canView()) {
            return false;
        }

        $page = '/plugins/resolveai/front/painel.php';

        return [
            'title' => self::getMenuName(),
            'page'  => $page,
            'icon'  => self::getIcon(),
            'links' => ['search' => $page],
        ];
    }
}
