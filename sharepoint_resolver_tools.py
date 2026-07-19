from __future__ import annotations

from typing import Any, Literal

from server import GraphError, enc, mcp, out, read_bytes, request, upload_bytes


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


async def _resolve_site(hostname: str, site_path: str) -> dict[str, Any]:
    clean_path = site_path.strip().strip("/")
    if not hostname.strip() or not clean_path:
        raise GraphError("hostname and site_path are required.")
    return out(await request("GET", f"sites/{enc(hostname.strip())}:/{clean_path}"))


async def _resolve_drive(site_id: str, library_name: str) -> dict[str, Any]:
    drives = out(await request("GET", f"sites/{enc(site_id)}/drives")).get("value", [])
    wanted = _normalize(library_name)

    exact = [drive for drive in drives if _normalize(str(drive.get("name", ""))) == wanted]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise GraphError(f"Several libraries have the name '{library_name}'.")

    partial = [drive for drive in drives if wanted in _normalize(str(drive.get("name", "")))]
    if len(partial) == 1:
        return partial[0]

    available = [str(drive.get("name", "")) for drive in drives]
    raise GraphError(
        f"Library '{library_name}' was not found or is ambiguous. Available libraries: {available}"
    )


async def _resolve_folder(drive_id: str, folder_path: str | None) -> dict[str, Any]:
    clean_path = (folder_path or "").strip().strip("/")
    endpoint = f"drives/{enc(drive_id)}/root"
    if clean_path:
        from urllib.parse import quote

        endpoint = f"drives/{enc(drive_id)}/root:/{quote(clean_path, safe='/')}:"

    folder = out(await request("GET", endpoint))
    if "folder" not in folder:
        raise GraphError(f"The path '{folder_path}' does not identify a folder.")
    return folder


@mcp.tool()
async def resolve_sharepoint_destination(
    hostname: str,
    site_path: str,
    library_name: str,
    folder_path: str = "",
) -> dict[str, Any]:
    """Resolve user-friendly SharePoint names to Microsoft Graph IDs."""
    site = await _resolve_site(hostname, site_path)
    drive = await _resolve_drive(site["id"], library_name)
    folder = await _resolve_folder(drive["id"], folder_path)
    return {
        "site": {"id": site.get("id"), "name": site.get("name"), "webUrl": site.get("webUrl")},
        "library": {"drive_id": drive.get("id"), "name": drive.get("name"), "webUrl": drive.get("webUrl")},
        "folder": {"item_id": folder.get("id"), "name": folder.get("name"), "webUrl": folder.get("webUrl")},
    }


@mcp.tool()
async def upload_file_by_site_path(
    hostname: str,
    site_path: str,
    library_name: str,
    folder_path: str,
    file_name: str,
    content_base64: str,
    conflict_behavior: Literal["fail", "replace", "rename"] = "replace",
) -> dict[str, Any]:
    """Upload a Base64 file using SharePoint site, library, and folder names instead of Graph IDs."""
    if not file_name.strip():
        raise GraphError("file_name is required.")

    site = await _resolve_site(hostname, site_path)
    drive = await _resolve_drive(site["id"], library_name)
    folder = await _resolve_folder(drive["id"], folder_path)
    data = read_bytes(None, content_base64)
    uploaded = await upload_bytes(
        drive_id=drive["id"],
        parent_id=folder["id"],
        name=file_name,
        data=data,
        conflict=conflict_behavior,
    )
    return {
        "resolved_destination": {
            "site_id": site.get("id"),
            "site_name": site.get("name"),
            "drive_id": drive.get("id"),
            "library_name": drive.get("name"),
            "folder_item_id": folder.get("id"),
            "folder_path": folder_path,
        },
        "uploaded_file": uploaded,
    }
