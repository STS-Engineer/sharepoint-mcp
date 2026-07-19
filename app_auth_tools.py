from __future__ import annotations
from typing import Any
import server as legacy

async def list_drives(site_id: str | None = None, hostname: str = "avocarbongroup.sharepoint.com", site_path: str = "/sites/pdc") -> dict[str, Any]:
    if not site_id:
        site = legacy.out(await legacy.request("GET", f"sites/{legacy.enc(hostname)}:/{site_path.strip().strip('/')}"))
        site_id = site["id"]
    return legacy.out(await legacy.request("GET", f"sites/{legacy.enc(site_id)}/drives"))

async def list_recent_documents(drive_id: str, folder_item_id: str | None = None, folder_path: str | None = None, max_results: int = 50) -> dict[str, Any]:
    endpoint = legacy.item_ep(drive_id, folder_item_id, folder_path) + "/children"
    data = legacy.out(await legacy.request("GET", endpoint, params={"$top": str(min(max_results, 999)), "$orderby": "lastModifiedDateTime desc", "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,file,folder,parentReference"}))
    data["value"] = [item for item in data.get("value", []) if "file" in item]
    return data
