from __future__ import annotations
from typing import Any
import server as legacy

async def _site_id(hostname: str, site_path: str) -> str:
    site = legacy.out(await legacy.request("GET", f"sites/{legacy.enc(hostname)}:/{site_path.strip().strip('/')}"))
    return site["id"]

async def list_drives(site_id: str | None = None, hostname: str = "avocarbongroup.sharepoint.com", site_path: str = "/sites/pdc", library_name: str | None = None) -> dict[str, Any]:
    site_id = site_id or await _site_id(hostname, site_path)
    raw = legacy.out(await legacy.request("GET", f"sites/{legacy.enc(site_id)}/drives"))
    drives = [{"drive_id": d.get("id"), "name": d.get("name"), "web_url": d.get("webUrl"), "drive_type": d.get("driveType")} for d in raw.get("value", [])]
    selected = next((d for d in drives if library_name and d.get("name") == library_name), None)
    return {"site_id": site_id, "drives": drives, "selected_drive": selected, "drive_id": selected.get("drive_id") if selected else None}

async def list_recent_documents(drive_id: str | None = None, folder_item_id: str | None = None, folder_path: str | None = "RFQ Excel", max_results: int = 50, hostname: str = "avocarbongroup.sharepoint.com", site_path: str = "/sites/pdc", library_name: str = "RFQ_Costing Files") -> dict[str, Any]:
    if not drive_id:
        resolved = await list_drives(hostname=hostname, site_path=site_path, library_name=library_name)
        drive_id = resolved.get("drive_id")
    if not drive_id:
        raise legacy.GraphError(f"Library not found: {library_name}")
    endpoint = legacy.item_ep(drive_id, folder_item_id, folder_path) + "/children"
    data = legacy.out(await legacy.request("GET", endpoint, params={"$top": str(min(max_results, 999)), "$orderby": "lastModifiedDateTime desc", "$select": "id,name,size,webUrl,lastModifiedDateTime,createdDateTime,file,folder,parentReference"}))
    files = [item for item in data.get("value", []) if "file" in item]
    return {"drive_id": drive_id, "library_name": library_name, "folder_path": folder_path, "files": files, "latest_file": files[0] if files else None}
