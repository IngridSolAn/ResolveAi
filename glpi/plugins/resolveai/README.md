# ResolveAI GLPI plugin

Initial GLPI 10 plugin scaffold. Copy this directory to the GLPI installation's
`plugins/resolveai` directory, then install and activate **ResolveAI** from
**Setup > Plugins**.

The plugin adds an **Insights do ResolveAI** tab to ticket pages. Opening the
tab loads a skeleton placeholder and makes an authenticated same-origin request
to `front/insights.php`. The PHP endpoint verifies that the logged-in user can
read the ticket, reads its title and description from GLPI, and forwards them
server-to-server to the configured ResolveAI API. Ticket contents and API
credentials are never sent directly by browser JavaScript.

## API contract

Configure these environment variables for the PHP process serving GLPI:

- `RESOLVEAI_API_URL`: full HTTP(S) URL of the ResolveAI analysis endpoint.
- `RESOLVEAI_API_TOKEN`: optional bearer token for that endpoint.

The endpoint is called with `POST` and a JSON body containing `ticket_id`,
`title`, and `description`. It must return this structured JSON contract:

```json
{
  "diagnostico_e_evidencias": "Texto do diagnóstico e das evidências.",
  "nivel_de_confianca": {
    "percentual": 35,
    "justificativa": "Há poucos dados para confirmar a hipótese."
  },
  "passos_sugeridos_de_teste": [
    "Compare um dispositivo afetado com outro não afetado."
  ]
}
```

The GLPI plugin validates this response and renders each block separately using
text nodes, not model-generated HTML. Configure HTTPS in production; the plugin
verifies TLS certificates and does not follow redirects.

The current ResolveAI FastAPI backend only exposes `/health`. The insights
endpoint described above must be implemented in the backend before the plugin
can return analysis.

## Layout

- `setup.php`: plugin metadata, GLPI version compatibility, and tab/assets
  registration.
- `hook.php`: install and uninstall hooks; no database tables are needed yet.
- `inc/ticket.class.php`: ticket tab and loading UI.
- `front/insights.php`: authenticated proxy that checks ticket read access.
- `js/resolveai.js` and `css/resolveai.css`: asynchronous loading and styling.

## Security notes

Use an API URL controlled by the GLPI administrator, not one supplied by the
browser. Give the API token only to the PHP process environment. Keep the
ResolveAI API protected against unauthorized callers and restrict access to
ticket data according to the GLPI instance's entity and privacy policies.
