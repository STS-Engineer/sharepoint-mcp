from __future__ import annotations

import base64
import contextlib
import os
from pathlib import Path
from typing import Any, Literal

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from server import GraphError, enc, mcp, out, path_enc, request, upload_bytes

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in {"0", "false", "no"}


def _same_name(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


async def _resolve_drive(hostname: str, site_path: str, library_name: str | None) -> tuple[str, str]:
    clean_site = site_path.strip().strip("/")
    if not clean_site:
        raise GraphError("site_path is required, for example /sites/pdc")

    site = out(await request("GET", f"sites/{enc(hostname)}:/{clean_site}"))
    site_id = site.get("id")
    if not site_id:
        raise GraphError("Microsoft Graph did not return a site id.")

    drives = out(await request("GET", f"sites/{enc(str(site_id))}/drives", params={"$top": "999"})).get("value", [])
    if library_name:
        drive = next((d for d in drives if _same_name(str(d.get("name", "")), library_name)), None)
    else:
        drive = drives[0] if drives else None

    if not drive or not drive.get("id"):
        available = [str(d.get("name", "")) for d in drives]
        raise GraphError(f"SharePoint library not found. Available libraries: {available}")

    return str(drive["id"]), str(drive.get("name", ""))


async def _read_file_uri(file_uri: Any) -> tuple[bytes, str]:
    if file_uri is None:
        raise GraphError("file_uri is required.")

    if isinstance(file_uri, str):
        value = file_uri
        if value.startswith("sandbox:"):
            value = value.removeprefix("sandbox:")
        path = Path(value).expanduser()
        if path.is_file():
            return path.read_bytes(), "local_path"
        if value.startswith(("https://", "http://")):
            async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY_SSL, follow_redirects=True, trust_env=True) as client:
                response = await client.get(value)
            if response.is_error:
                raise GraphError(f"Unable to download file_uri: HTTP {response.status_code}.")
            return response.content, "url"
        raise GraphError(
            "file_uri was received as a path that is not mounted on the Azure MCP host. "
            "The ChatGPT runtime must rewrite the attached file into a transferable file reference."
        )

    if isinstance(file_uri, dict):
        content = file_uri.get("content_base64") or file_uri.get("base64")
        if content:
            try:
                return base64.b64decode(content, validate=True), "structured_base64"
            except Exception as exc:
                raise GraphError("Invalid Base64 content in file_uri.") from exc

        local_path = file_uri.get("path") or file_uri.get("file_path")
        if local_path:
            path = Path(str(local_path)).expanduser()
            if path.is_file():
                return path.read_bytes(), "structured_path"

        url = file_uri.get("download_url") or file_uri.get("url")
        if url:
            headers = file_uri.get("headers") or {}
            async with httpx.AsyncClient(timeout=TIMEOUT, verify=VERIFY_SSL, follow_redirects=True, trust_env=True) as client:
                response = await client.get(str(url), headers=headers)
            if response.is_error:
                raise GraphError(f"Unable to download structured file_uri: HTTP {response.status_code}.")
            return response.content, "structured_url"

    raise GraphError("Unsupported file_uri reference received from the connector runtime.")


# Remove the legacy upload_file tool imported from server.py before registering
# the OpenAI-compatible replacement under the same public tool name.
try:
    mcp._tool_manager._tools.pop("upload_file", None)
except AttributeError:
    pass


@mcp.tool(name="upload_file")
async def upload_file_openai_style(
    hostname: str,
    site_path: str,
    file_name: str,
    file_uri: Any,
    parent_folder_path: str | None = None,
    mime_type: str = "text/plain",
    conflict_behavior: Literal["fail", "rename", "replace"] = "replace",
    library_name: str | None = None,
) -> dict[str, Any]:
    """Upload a file reference into SharePoint using the OpenAI SharePoint action shape.

    In ChatGPT, pass the exact sandbox path of an uploaded/generated file as file_uri.
    The runtime is expected to rewrite it into a transferable file reference before
    this MCP action runs. Large files use a Microsoft Graph upload session automatically.
    """
    drive_id, resolved_library = await _resolve_drive(hostname, site_path, library_name)
    folder_path = (parent_folder_path or "").strip().strip("/")
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
        "version": "0.1.5",
        "transport": "streamable-http",
        "upload_schema": "openai-sharepoint-file-uri",
    })


@contextlib.asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield


starlette_app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Mount("/", app=mcp.streamable_http_app()),
    ],
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
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
