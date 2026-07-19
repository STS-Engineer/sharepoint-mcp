from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import unquote, urlparse

import httpx
import uvicorn
from pydantic import Field
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from server import GraphError, enc, mcp, out, path_enc, request, upload_bytes

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in {"0", "false", "no"}

FileUri = Annotated[
    str,
    Field(
        description="Uploaded file reference supplied by ChatGPT",
        json_schema_extra={"format": "uri"},
    ),
]


def _same_name(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


async def _resolve_drive(hostname: str, site_path: str, library_name: str | None) -> tuple[str, str]:
    clean_site = site_path.strip().strip("/")
    if not clean_site:
        raise GraphError("site_path is required, for example /sites/pdc")
    site = out(await request("GET", f"sites/{enc(hostname)}:/{clean_site}"))
    site_id = site.get("id")
    if not site_id:
        raise GraphError("Microsoft Graph did not return a site id.")
    drives = out(await request("GET", f"sites/{enc(str(site_id))}/drives", params={"$top": "999"})).get("value", [])
    drive = next((d for d in drives if _same_name(str(d.get("name", "")), library_name)), None) if library_name else (drives[0] if drives else None)
    if not drive or not drive.get("id"):
        available = [str(d.get("name", "")) for d in drives]
        raise GraphError(f"SharePoint library not found. Available libraries: {available}")
    return str(drive["id"]), str(drive.get("name", ""))


def _local_path_from_uri(file_uri: str) -> Path:
    value = file_uri.strip()
    if value.startswith("sandbox:"):
        value = value.removeprefix("sandbox:")
    if value.startswith("file://"):
        parsed = urlparse(value)
        return Path(unquote(parsed.path))
    return Path(value)


async def _read_file_uri(file_uri: str) -> tuple[bytes, str]:
    value = file_uri.strip()
    if value.startswith(("https://", "http://")):
        async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY_SSL, follow_redirects=True, trust_env=True) as client:
            response = await client.get(value)
        if response.is_error:
            raise GraphError(f"Unable to download file_uri: HTTP {response.status_code}.")
        return response.content, "url"
    path = _local_path_from_uri(value).expanduser()
    if not path.is_file():
        raise GraphError(
            f"Transferred file not found: {path}. The ChatGPT runtime must rewrite the attachment to an accessible path or URL before this MCP action runs."
        )
    return path.read_bytes(), "local_path"


try:
    mcp._tool_manager._tools.pop("upload_file", None)
except AttributeError:
    pass


@mcp.tool(name="upload_file")
async def upload_file_openai_style(
    hostname: str,
    site_path: str,
    parent_folder_path: str,
    file_name: str,
    file_uri: FileUri,
    mime_type: str = "text/plain",
    conflict_behavior: Literal["fail", "rename", "replace"] = "replace",
    library_name: str | None = None,
) -> dict[str, Any]:
    """Upload a ChatGPT-provided file reference into SharePoint."""
    drive_id, resolved_library = await _resolve_drive(hostname, site_path, library_name)
    folder_path = parent_folder_path.strip().strip("/")
    endpoint = f"drives/{enc(drive_id)}/root:/{path_enc(folder_path)}:" if folder_path else f"drives/{enc(drive_id)}/root"
    folder = out(await request("GET", endpoint))
    if "folder" not in folder or not folder.get("id"):
        raise GraphError(f"Destination '{parent_folder_path}' is not a valid folder.")
    data, input_mode = await _read_file_uri(file_uri)
    uploaded = await upload_bytes(drive_id, str(folder["id"]), file_name, data, conflict_behavior)
    return {
        "ok": True,
        "input_mode": input_mode,
        "mime_type": mime_type,
        "resolved": {
            "drive_id": drive_id,
            "library_name": resolved_library,
            "folder_id": folder["id"],
            "parent_folder_path": parent_folder_path,
        },
        "uploaded_item": uploaded,
    }


async def health(_: object) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": "0.1.6",
        "transport": "streamable-http",
        "upload_schema": "file-uri-string",
    })


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


starlette_app = Starlette(
    routes=[Route("/health", health, methods=["GET"]), Mount("/", app=mcp.streamable_http_app())],
    lifespan=lifespan,
)

app = CORSMiddleware(
    app=starlette_app,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
    allow_credentials=False,
)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, proxy_headers=True, forwarded_allow_ips="*")
