from __future__ import annotations

import contextlib
import os
from typing import Literal

import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from server import GraphError, enc, mcp, out, path_enc, read_bytes, request, upload_bytes

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


def _same_name(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


@mcp.tool()
async def upload_file_by_site_path(
    hostname: str,
    site_path: str,
    library_name: str,
    folder_path: str,
    file_name: str,
    source_path: str | None = None,
    content_base64: str | None = None,
    conflict_behavior: Literal["fail", "replace", "rename"] = "replace",
) -> dict:
    """Upload a file using human-readable SharePoint site, library, and folder names.

    This action resolves the Microsoft Graph site ID, drive ID, and destination
    folder item ID automatically, so callers must not pass technical IDs.
    """
    clean_site_path = site_path.strip().strip("/")
    if not clean_site_path:
        raise GraphError("site_path is required, for example /sites/pdc")

    site = out(await request("GET", f"sites/{enc(hostname)}:/{clean_site_path}"))
    site_id = site.get("id")
    if not site_id:
        raise GraphError("Microsoft Graph did not return a site id.")

    drives_payload = out(await request("GET", f"sites/{enc(site_id)}/drives", params={"$top": "999"}))
    drives = drives_payload.get("value", [])
    drive = next((item for item in drives if _same_name(str(item.get("name", "")), library_name)), None)
    if not drive:
        available = [str(item.get("name", "")) for item in drives]
        raise GraphError(f"Library '{library_name}' not found. Available libraries: {available}")

    drive_id = drive.get("id")
    if not drive_id:
        raise GraphError(f"Library '{library_name}' did not return a drive id.")

    clean_folder_path = folder_path.strip().strip("/")
    if clean_folder_path:
        folder = out(await request("GET", f"drives/{enc(drive_id)}/root:/{path_enc(clean_folder_path)}:"))
    else:
        folder = out(await request("GET", f"drives/{enc(drive_id)}/root"))

    if "folder" not in folder:
        raise GraphError(f"Destination '{folder_path}' is not a folder.")

    folder_id = folder.get("id")
    if not folder_id:
        raise GraphError(f"Folder '{folder_path}' did not return an item id.")

    data = read_bytes(source_path, content_base64)
    uploaded = await upload_bytes(drive_id, folder_id, file_name, data, conflict_behavior)

    return {
        "ok": True,
        "resolved": {
            "hostname": hostname,
            "site_path": site_path,
            "site_id": site_id,
            "library_name": drive.get("name"),
            "drive_id": drive_id,
            "folder_path": folder_path,
            "folder_id": folder_id,
        },
        "uploaded_item": uploaded,
    }


async def health(_: object) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "version": "0.1.2",
            "transport": "streamable-http",
            "upload_by_site_path": True,
        }
    )


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
    allow_origins=[
        "https://chatgpt.com",
        "https://chat.openai.com",
    ],
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
