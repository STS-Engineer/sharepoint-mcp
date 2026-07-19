from __future__ import annotations
import os
from typing import Literal
from mcp.server.apps import Apps, ResourceCsp

WIDGET_URI = "ui://widget/sharepoint-upload-modern-v2.html"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net").rstrip("/")
apps = Apps()

HTML = f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{{font-family:Arial,sans-serif;margin:0;padding:24px;background:#f4f6f9}}.card{{background:white;padding:24px;border-radius:16px;text-align:center}}a{{display:inline-block;margin-top:12px;padding:12px 18px;background:#ee6b23;color:white;text-decoration:none;border-radius:10px;font-weight:700}}</style></head><body><div class='card'><h2>Upload SharePoint</h2><p>Ouvrez le formulaire sécurisé pour choisir et envoyer votre fichier.</p><a href='{BASE_URL}/upload-modern' target='_blank' rel='noopener'>Ouvrir le formulaire d’upload</a></div></body></html>"""

@apps.tool(resource_uri=WIDGET_URI, name="open_sharepoint_upload", description="Open the SharePoint upload form.")
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
    }

apps.add_html_resource(
    WIDGET_URI,
    HTML,
    title="AVOCarbon SharePoint Upload",
    csp=ResourceCsp(connect_domains=[BASE_URL]),
    domain=BASE_URL,
    prefers_border=True,
)
