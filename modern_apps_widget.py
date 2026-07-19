from __future__ import annotations

import os
from typing import Literal

from mcp.server.apps import Apps, ResourceCsp

WIDGET_URI = "ui://widget/sharepoint-upload-modern.html"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net").rstrip("/")

apps = Apps()

HTML = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>html,body,iframe{{width:100%;height:100%;min-height:700px;margin:0;border:0;background:#f4f6f8}}</style></head><body><iframe id='u' title='AVOCarbon SharePoint Upload'></iframe><script>function p(v){{const d=v?.structuredContent||v||{{}};const q=new URLSearchParams(d);document.getElementById('u').src='{BASE_URL}/upload-modern?'+q.toString()}}p(window.openai?.toolOutput);window.addEventListener('openai:set_globals',e=>p(e.detail?.globals?.toolOutput));</script></body></html>"""

@apps.tool(resource_uri=WIDGET_URI, name="open_sharepoint_upload", description="Open the SharePoint upload window and prefill the destination inferred from the user's request.")
async def open_sharepoint_upload(
    hostname: str = "avocarbongroup.sharepoint.com",
    site_path: str = "/sites/pdc",
    library_name: str = "RFQ_Costing Files",
    parent_folder_path: str = "RFQ Excel",
    conflict_behavior: Literal["fail", "rename", "replace"] = "replace",
) -> dict[str, str]:
    return {
        "hostname": hostname,
        "site_path": site_path,
        "library_name": library_name,
        "parent_folder_path": parent_folder_path,
        "conflict_behavior": conflict_behavior,
        "message": "Destination SharePoint détectée. Choisissez le fichier puis confirmez l'envoi.",
    }

apps.add_html_resource(
    WIDGET_URI,
    HTML,
    title="AVOCarbon SharePoint Upload",
    csp=ResourceCsp(frame_domains=[BASE_URL], connect_domains=[BASE_URL]),
    domain=BASE_URL,
    prefers_border=True,
)
