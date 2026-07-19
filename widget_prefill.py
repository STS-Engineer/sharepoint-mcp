from __future__ import annotations

import html
import os
from typing import Any, Literal

WIDGET_URI = "ui://widget/sharepoint-upload-prefill.html"


def register_prefill_widget(mcp: Any) -> None:
    base_url = os.getenv(
        "PUBLIC_BASE_URL",
        "https://sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net",
    ).rstrip("/")
    endpoint = html.escape(f"{base_url}/api/browser-upload", quote=True)

    widget_html = f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>body{{font-family:Arial;margin:0;background:#f5f7fa}}main{{padding:18px;background:white}}label{{display:block;margin-top:10px;font-weight:600}}input,select,button{{width:100%;box-sizing:border-box;margin-top:5px;padding:9px}}#status{{margin-top:12px;white-space:pre-wrap}}</style>
</head><body><main><h2>Envoi vers SharePoint</h2><form id='f'>
<label>Fichier<input type='file' name='file' required></label>
<label>Hostname<input id='hostname' name='hostname' value='avocarbongroup.sharepoint.com' required></label>
<label>Site<input id='site_path' name='site_path' value='/sites/pdc' required></label>
<label>Bibliothèque<input id='library_name' name='library_name' value='RFQ_Costing Files'></label>
<label>Dossier<input id='parent_folder_path' name='parent_folder_path' value='RFQ Excel' required></label>
<label>Conflit<select id='conflict_behavior' name='conflict_behavior'><option value='replace'>Remplacer</option><option value='rename'>Renommer</option><option value='fail'>Échouer</option></select></label>
<button id='send' type='submit'>Envoyer vers SharePoint</button></form><div id='status'>Prêt.</div></main>
<script>
const ids=['hostname','site_path','library_name','parent_folder_path','conflict_behavior'];
function apply(data){{const d=data?.structuredContent||data||{{}};ids.forEach(k=>{{if(d[k]!==undefined&&d[k]!==null)document.getElementById(k).value=d[k];}});}}
apply(window.openai?.toolOutput);
window.addEventListener('openai:set_globals',e=>apply(e.detail?.globals?.toolOutput));
document.getElementById('f').addEventListener('submit',async e=>{{e.preventDefault();const b=document.getElementById('send'),s=document.getElementById('status');b.disabled=true;s.textContent='Upload en cours...';try{{const r=await fetch('{endpoint}',{{method:'POST',body:new FormData(e.target)}});const p=await r.json();if(!r.ok)throw new Error(p.error||`HTTP ${{r.status}}`);s.textContent=`Upload réussi\nNom: ${{p.uploaded_item?.name||''}}\nLien: ${{p.uploaded_item?.webUrl||''}}`;}}catch(err){{s.textContent=`Échec: ${{err.message}}`;}}finally{{b.disabled=false;}}}});
</script></body></html>"""

    @mcp.resource(WIDGET_URI, mime_type="text/html+skybridge")
    def sharepoint_upload_prefill_widget() -> str:
        return widget_html

    @mcp.tool(
        name="open_sharepoint_upload",
        meta={
            "openai/outputTemplate": WIDGET_URI,
            "openai/resultCanProduceWidget": True,
            "openai/widgetAccessible": True,
        },
    )
    async def open_sharepoint_upload(
        hostname: str = "avocarbongroup.sharepoint.com",
        site_path: str = "/sites/pdc",
        library_name: str = "RFQ_Costing Files",
        parent_folder_path: str = "RFQ Excel",
        conflict_behavior: Literal["fail", "rename", "replace"] = "replace",
    ) -> dict[str, str]:
        """Open the upload widget. Infer SharePoint destination fields from the user's request and pass them here."""
        return {
            "hostname": hostname,
            "site_path": site_path,
            "library_name": library_name,
            "parent_folder_path": parent_folder_path,
            "conflict_behavior": conflict_behavior,
            "message": "Choisissez le fichier puis confirmez l'envoi vers SharePoint.",
        }
