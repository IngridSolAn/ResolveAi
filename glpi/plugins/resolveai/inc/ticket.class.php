<?php

class PluginResolveaiTicket extends CommonGLPI
{
    public static function getTypeName($nb = 0): string
    {
        return __('ResolveAI Insights', 'resolveai');
    }

    public function getTabNameForItem(CommonGLPI $item, $withtemplate = 0): string
    {
        if ($item instanceof Ticket && $item->getID() > 0) {
            return self::getTypeName();
        }

        return '';
    }

    public static function displayTabContentForItem(
        CommonGLPI $item,
        $tabnum = 1,
        $withtemplate = 0
    ): bool {
        if (!$item instanceof Ticket || $item->getID() <= 0) {
            return false;
        }

        $endpoint = Plugin::getWebDir('resolveai', true) . '/front/insights.php';
        $endpoint = htmlspecialchars($endpoint, ENT_QUOTES, 'UTF-8');

        echo '<section class="resolveai-card card"'
            . ' data-resolveai-insights'
            . ' data-ticket-id="' . (int) $item->getID() . '"'
            . ' data-endpoint="' . $endpoint . '"'
            . ' aria-labelledby="resolveai-insights-title">';
        echo '<div class="card-header">';
        echo '<h3 class="card-title" id="resolveai-insights-title">'
            . htmlspecialchars(self::getTypeName(), ENT_QUOTES, 'UTF-8')
            . '</h3>';
        echo '</div>';
        echo '<div class="card-body" aria-live="polite" aria-busy="true">';
        echo '<div class="resolveai-loading" role="status">';
        echo '<span class="visually-hidden">' . __('Loading insights…', 'resolveai') . '</span>';
        echo '<span class="resolveai-skeleton resolveai-skeleton-title" aria-hidden="true"></span>';
        echo '<span class="resolveai-skeleton" aria-hidden="true"></span>';
        echo '<span class="resolveai-skeleton resolveai-skeleton-short" aria-hidden="true"></span>';
        echo '</div>';
        echo '</div>';
        echo '</section>';

        return true;
    }
}
