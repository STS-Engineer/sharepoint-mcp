from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()
GRAPH = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").rstrip("/")
TENANT = os.getenv("AZURE_TENANT_ID", "")
CLIENT = os.getenv("AZURE_CLIENT_ID", "")
SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
STATIC_TOKEN = os.getenv("GRAPH_ACCESS_TOKEN", "")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in {"0", "false", "no"}
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CHUNK = int(os.getenv("UPLOAD_CHUNK_SIZE", str(10 * 1024 * 1024)))
SIMPLE_LIMIT = int(os.getenv("MAX_SIMPLE_UPLOAD_MB", "200")) * 1024 * 1024

mcp = FastMCP("AVOCarbon SharePoint MCP", json_response=True, host=HOST, port=PORT)

class GraphError(RuntimeError):
    pass

class TokenProvider:
    def __init__(self) -> None:
        self.token: str | None = None
        self.expires = 0.0

    async def get(self) -> str:
        if STATIC_TOKEN:
            return STATIC_TOKEN
        if not all([TENANT, CLIENT, SECRET]):
            raise GraphError("Set AZURE_TENANT_ID, AZURE_CLIENT_ID and AZURE_CLIENT_SECRET.")
        if self.token and time.time() < self.expires - 120:
            return self.token
        url = f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token"
        async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY_SSL, trust_env=True) as c:
            r = await c.post(url, data={"client_id": CLIENT, "client_secret": SECRET, "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"})
        if r.is_error:
            raise GraphError(f"OAuth error {r.status_code}: {r.text}")
        data = r.json()
        self.token = data["access_token"]
        self.expires = time.time() + int(data.get("expires_in", 3600))
        return self.token

tokens = TokenProvider()

async def request(method: str, path: str, *, params: dict[str, Any] | None = None, body: Any = None, content: bytes | None = None, headers: dict[str, str] | None = None, auth: bool = True, expected: set[int] | None = None) -> httpx.Response:
    url = path if path.startswith("http") else f"{GRAPH}/{path.lstrip('/')}"
    h = dict(headers or {})
    if auth:
        h["Authorization"] = f"Bearer {await tokens.get()}"
    async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY_SSL, trust_env=True, follow_redirects=True) as c:
        r = await c.request(method, url, params=params, json=body, content=content, headers=h)
    if r.status_code not in (expected or set(range(200, 300))):
        rid = r.headers.get("request-id") or r.headers.get("x-ms-request-id")
        raise GraphError(f"Graph error {r.status_code}: {r.text[:4000]}" + (f" | request-id={rid}" if rid else ""))
    return r

def out(r: httpx.Response) -> dict[str, Any]:
    return r.json() if r.content else {"ok": True, "status_code": r.status_code}

def enc(value: str) -> str:
    return quote(value, safe="")

def path_enc(value: str) -> str:
    return quote(value.strip().strip("/"), safe="/")

def item_ep(drive_id: str, item_id: str | None = None, path: str | None = None) -> str:
    if item_id:
        return f"drives/{enc(drive_id)}/items/{enc(item_id)}"
    if path:
        return f"drives/{enc(drive_id)}/root:/{path_enc(path)}:"
    return f"drives/{enc(drive_id)}/root"

def read_bytes(source_path: str | None, content_base64: str | None) -> bytes:
    if bool(source_path) == bool(content_base64):
        raise GraphError("Provide exactly one of source_path or content_base64.")
    if source_path:
        p = Path(source_path).expanduser().resolve()
        if not p.is_file():
            raise GraphError(f"File not found: {p}")
        return p.read_bytes()
    try:
        return base64.b64decode(content_base64 or "", validate=True)
    except Exception as exc:
        raise GraphError("Invalid Base64 content.") from exc

async def upload_bytes(drive_id: str, parent_id: str, name: str, data: bytes, conflict: str = "replace") -> dict[str, Any]:
    if len(data) <= SIMPLE_LIMIT:
        ep = f"drives/{enc(drive_id)}/items/{enc(parent_id)}:/{enc(name)}:/content"
        return out(await request("PUT", ep, content=data, headers={"Content-Type": "application/octet-stream"}))
    ep = f"drives/{enc(drive_id)}/items/{enc(parent_id)}:/{enc(name)}:/createUploadSession"
    session = out(await request("POST", ep, body={"item": {"@microsoft.graph.conflictBehavior": conflict, "name": name}}))
    url = session["uploadUrl"]
    total = len(data)
    result: dict[str, Any] = {}
    for start in range(0, total, CHUNK):
        end = min(start + CHUNK, total) - 1
        chunk = data[start:end + 1]
        r = await request("PUT", url, content=chunk, auth=False, expected={200, 201, 202}, headers={"Content-Length": str(len(chunk)), "Content-Range": f"bytes {start}-{end}/{total}", "Content-Type": "application/octet-stream"})
        result = out(r)
    return result

@mcp.tool()
async def get_profile() -> dict[str, Any]:
    if STATIC_TOKEN:
        try:
            return out(await request("GET", "me"))
        except GraphError as exc:
            return {"auth_mode": "static_token", "detail": str(exc)}
    return {"auth_mode": "application", "tenant_id": TENANT, "client_id": CLIENT, "organization": out(await request("GET", "organization")).get("value", [])}

@mcp.tool()
async def get_site(hostname: str, site_path: str) -> dict[str, Any]:
    return out(await request("GET", f"sites/{enc(hostname)}:/{site_path.strip().strip('/')}"))

@mcp.tool()
async def list_drives() -> dict[str, Any]:
    return out(await request("GET", "me/drives"))

@mcp.tool()
async def list_site_drives(site_id: str) -> dict[str, Any]:
    return out(await request("GET", f"sites/{enc(site_id)}/drives"))

@mcp.tool()
async def list_folder_items(drive_id: str, folder_item_id: str | None = None, folder_path: str | None = None) -> dict[str, Any]:
    return out(await request("GET", item_ep(drive_id, folder_item_id, folder_path) + "/children", params={"$top": "999"}))

@mcp.tool()
async def list_recent_documents() -> dict[str, Any]:
    return out(await request("GET", "me/drive/recent"))

@mcp.tool(name="search")
async def search_items(drive_id: str, query: str, max_results: int = 100) -> dict[str, Any]:
    q = query.replace("'", "''")
    return out(await request("GET", f"drives/{enc(drive_id)}/root/search(q='{quote(q, safe='')}')", params={"$top": str(min(max_results, 999))}))

@mcp.tool()
async def fetch(drive_id: str, item_id: str | None = None, path: str | None = None, return_base64: bool = False) -> dict[str, Any]:
    if not item_id and not path:
        raise GraphError("Provide item_id or path.")
    meta = out(await request("GET", item_ep(drive_id, item_id, path)))
    data = (await request("GET", item_ep(drive_id, item_id, path) + "/content")).content
    return {"metadata": meta, "content_base64": base64.b64encode(data).decode()} if return_base64 else {"metadata": meta, "size": len(data), "text": data.decode("utf-8", errors="replace")}

@mcp.tool()
async def oai_user_search(drive_id: str, query: str, max_results: int = 100) -> dict[str, Any]:
    return await search_items(drive_id, query, max_results)

@mcp.tool()
async def oai_user_fetch(drive_id: str, item_id: str | None = None, path: str | None = None, return_base64: bool = False) -> dict[str, Any]:
    return await fetch(drive_id, item_id, path, return_base64)

@mcp.tool()
async def create_folder(drive_id: str, parent_item_id: str, folder_name: str, conflict_behavior: Literal["fail", "replace", "rename"] = "rename") -> dict[str, Any]:
    return out(await request("POST", f"drives/{enc(drive_id)}/items/{enc(parent_item_id)}/children", body={"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": conflict_behavior}))

@mcp.tool()
async def create_folders_bulk(drive_id: str, parent_item_id: str, folder_names: list[str], conflict_behavior: str = "rename") -> dict[str, Any]:
    results, errors = [], []
    for name in folder_names:
        try:
            results.append(await create_folder(drive_id, parent_item_id, name, conflict_behavior))
        except Exception as exc:
            errors.append({"name": name, "error": str(exc)})
    return {"results": results, "errors": errors}

@mcp.tool()
async def upload_file(drive_id: str, parent_item_id: str, file_name: str, source_path: str | None = None, content_base64: str | None = None, conflict_behavior: str = "replace") -> dict[str, Any]:
    return await upload_bytes(drive_id, parent_item_id, file_name, read_bytes(source_path, content_base64), conflict_behavior)

@mcp.tool()
async def update_file(drive_id: str, file_path: str, source_path: str | None = None, content_base64: str | None = None) -> dict[str, Any]:
    data = read_bytes(source_path, content_base64)
    if len(data) <= SIMPLE_LIMIT:
        return out(await request("PUT", item_ep(drive_id, path=file_path) + "/content", content=data, headers={"Content-Type": "application/octet-stream"}))
    meta = out(await request("GET", item_ep(drive_id, path=file_path)))
    return await update_file_exact(drive_id, meta["id"], source_path, content_base64)

@mcp.tool()
async def update_file_exact(drive_id: str, item_id: str, source_path: str | None = None, content_base64: str | None = None) -> dict[str, Any]:
    data = read_bytes(source_path, content_base64)
    if len(data) <= SIMPLE_LIMIT:
        return out(await request("PUT", item_ep(drive_id, item_id=item_id) + "/content", content=data, headers={"Content-Type": "application/octet-stream"}))
    session = out(await request("POST", item_ep(drive_id, item_id=item_id) + "/createUploadSession", body={}))
    total, result = len(data), {}
    for start in range(0, total, CHUNK):
        end = min(start + CHUNK, total) - 1
        chunk = data[start:end + 1]
        result = out(await request("PUT", session["uploadUrl"], content=chunk, auth=False, expected={200, 201, 202}, headers={"Content-Length": str(len(chunk)), "Content-Range": f"bytes {start}-{end}/{total}", "Content-Type": "application/octet-stream"}))
    return result

@mcp.tool()
async def copy_item(source_drive_id: str, item_id: str, destination_drive_id: str, destination_parent_item_id: str, new_name: str | None = None, conflict_behavior: str = "rename") -> dict[str, Any]:
    body: dict[str, Any] = {"parentReference": {"driveId": destination_drive_id, "id": destination_parent_item_id}}
    if new_name:
        body["name"] = new_name
    r = await request("POST", f"drives/{enc(source_drive_id)}/items/{enc(item_id)}/copy", params={"@microsoft.graph.conflictBehavior": conflict_behavior}, body=body, expected={202})
    return {"accepted": True, "monitor_url": r.headers.get("Location")}

@mcp.tool()
async def get_copy_status(monitor_url: str) -> dict[str, Any]:
    return out(await request("GET", monitor_url, auth=False, expected={200, 202, 303}))

@mcp.tool()
async def move_or_rename_item(drive_id: str, item_id: str, new_parent_item_id: str | None = None, new_name: str | None = None) -> dict[str, Any]:
    if not new_parent_item_id and not new_name:
        raise GraphError("Provide new_parent_item_id or new_name.")
    body: dict[str, Any] = {}
    if new_parent_item_id:
        body["parentReference"] = {"id": new_parent_item_id}
    if new_name:
        body["name"] = new_name
    return out(await request("PATCH", item_ep(drive_id, item_id=item_id), body=body))

@mcp.tool()
async def move_items_bulk(drive_id: str, operations: list[dict[str, str]]) -> dict[str, Any]:
    results, errors = [], []
    for op in operations:
        try:
            results.append(await move_or_rename_item(drive_id, op["item_id"], op.get("new_parent_item_id"), op.get("new_name")))
        except Exception as exc:
            errors.append({"operation": op, "error": str(exc)})
    return {"results": results, "errors": errors}

@mcp.tool()
async def delete_item(drive_id: str, item_id: str) -> dict[str, Any]:
    r = await request("DELETE", item_ep(drive_id, item_id=item_id), expected={204})
    return {"deleted": True, "status_code": r.status_code}

@mcp.tool()
async def create_sharing_link(drive_id: str, item_id: str, link_type: Literal["view", "edit"] = "view", scope: Literal["anonymous", "organization", "users"] = "organization") -> dict[str, Any]:
    return out(await request("POST", item_ep(drive_id, item_id=item_id) + "/createLink", body={"type": link_type, "scope": scope}))

@mcp.tool()
async def invite_item_recipients(drive_id: str, item_id: str, emails: list[str], roles: list[Literal["read", "write"]] = ["read"], message: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"recipients": [{"email": e} for e in emails], "roles": roles, "requireSignIn": True, "sendInvitation": True}
    if message:
        body["message"] = message
    return out(await request("POST", item_ep(drive_id, item_id=item_id) + "/invite", body=body))

@mcp.tool()
async def list_item_permissions(drive_id: str, item_id: str) -> dict[str, Any]:
    return out(await request("GET", item_ep(drive_id, item_id=item_id) + "/permissions"))

@mcp.tool()
async def list_item_versions(drive_id: str, item_id: str) -> dict[str, Any]:
    return out(await request("GET", item_ep(drive_id, item_id=item_id) + "/versions"))

@mcp.tool()
async def restore_item_version(drive_id: str, item_id: str, version_id: str) -> dict[str, Any]:
    r = await request("POST", item_ep(drive_id, item_id=item_id) + f"/versions/{enc(version_id)}/restoreVersion", body={}, expected={204})
    return {"restored": True, "status_code": r.status_code}

@mcp.tool()
async def get_item_metadata(drive_id: str, item_id: str | None = None, path: str | None = None) -> dict[str, Any]:
    return out(await request("GET", item_ep(drive_id, item_id, path)))

if __name__ == "__main__":
    mcp.run(transport=os.getenv("MCP_TRANSPORT", "streamable-http"))
