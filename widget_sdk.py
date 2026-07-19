from __future__ import annotations

import html
import os
from typing import Any

WIDGET_URI = "ui://widget/sharepoint-upload.html"


def register_widget(mcp: Any) -> None:
    base_url = os.getenv(
        "PUBLIC_BASE_URL",
        "https://sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net",
    ).rstrip("/")
    upload_endpoint = f"{base_url}/api/browser-upload"
    safe_endpoint = html.escape(upload_endpoint, quote=True)

    widget_html = f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; color: #1f2937; }}
    main {{ max-width: 680px; margin: 16px auto; padding: 20px; background: white; border-radius: 14px; }}
    label {{ display: block; margin-top: 12px; font-weight: 600; }}
    input, select, button {{ width: 100%; box-sizing: border-box; margin-top: 6px; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; }}
    button {{ margin-top: 18px; border: 0; background: #111827; color: white; font-weight: 700; cursor: pointer; }}
    #status {{ margin-top: 14px; padding: 10px; background: #f1f5f9; border-radius: 8px; white-space: pre-wrap; }}
  </style>
</head>
<body>
<main>
  <h2>Upload SharePoint</h2>
  <form id="uploadForm">
    <label>Fichier<input type="file" name="file" required></label>
    <label>Hostname<input name="hostname" value="avocarbongroup.sharepoint.com" required></label>
    <label>Site<input name="site_path" value="/sites/pdc" required></label>
    <label>Bibliothèque<input name="library_name" value="RFQ_Costing Files"></label>
    <label>Dossier<input name="parent_folder_path" value="RFQ Excel" required></label>
    <label>Conflit<select name="conflict_behavior"><option value="replace">Remplacer</option><option value="rename">Renommer</option><option value="fail">Échouer</option></select></label>
    <button id="sendButton" type="submit">Envoyer vers SharePoint</button>
  </form>
  <div id="status">Prêt.</div>
</main>
<script>
const form = document.getElementById('uploadForm');
const button = document.getElementById('sendButton');
const statusBox = document.getElementById('status');
form.addEventListener('submit', async (event) => {{
  event.preventDefault();
  button.disabled = true;
  statusBox.textContent = 'Upload en cours...';
  try {{
    const response = await fetch('{safe_endpoint}', {{ method: 'POST', body: new FormData(form) }});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${{response.status}}`);
    statusBox.textContent = `Upload réussi\nNom: ${{payload.uploaded_item?.name || ''}}\nLien: ${{payload.uploaded_item?.webUrl || ''}}`;
  }} catch (error) {{
    statusBox.textContent = `Échec: ${{error.message}}`;
  }} finally {{
    button.disabled = false;
  }}
}});
</script>
</body>
</html>"""

    @mcp.resource(WIDGET_URI, mime_type="text/html+skybridge")
    def sharepoint_upload_widget() -> str:
        return widget_html

    @mcp.tool(
        name="open_sharepoint_upload",
        meta={
            "openai/outputTemplate": WIDGET_URI,
            "openai/resultCanProduceWidget": True,
            "openai/widgetAccessible": True,
            "openai/toolInvocation/invoking": "Ouverture de la fenêtre SharePoint...",
            "openai/toolInvocation/invoked": "Fenêtre SharePoint ouverte.",
        },
    )
    async def open_sharepoint_upload() -> dict[str, str]:
        """Open the embedded SharePoint upload interface."""
        return {
            "status": "ready",
            "message": "Choisissez un fichier dans la fenêtre puis envoyez-le vers SharePoint.",
        }
