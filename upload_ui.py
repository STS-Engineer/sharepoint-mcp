from __future__ import annotations

import html
import os
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from server import GraphError, enc, out, path_enc, request, upload_bytes

MAX_UPLOAD_BYTES = int(os.getenv("MAX_BROWSER_UPLOAD_MB", "50")) * 1024 * 1024


def _same_name(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == " ".join(right.split()).casefold()


async def _resolve_drive(hostname: str, site_path: str, library_name: str | None) -> tuple[str, str]:
    clean_site = site_path.strip().strip("/")
    if not clean_site:
        raise GraphError("site_path is required")

    site = out(await request("GET", f"sites/{enc(hostname)}:/{clean_site}"))
    site_id = site.get("id")
    if not site_id:
        raise GraphError("Microsoft Graph did not return a site id")

    drives = out(
        await request(
            "GET",
            f"sites/{enc(str(site_id))}/drives",
            params={"$top": "999"},
        )
    ).get("value", [])

    if library_name:
        drive = next(
            (item for item in drives if _same_name(str(item.get("name", "")), library_name)),
            None,
        )
    else:
        drive = drives[0] if drives else None

    if not drive or not drive.get("id"):
        available = [str(item.get("name", "")) for item in drives]
        raise GraphError(f"SharePoint library not found. Available libraries: {available}")

    return str(drive["id"]), str(drive.get("name", ""))


async def upload_page(_: Request) -> HTMLResponse:
    page = """<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AVOCarbon SharePoint Upload</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 0; background: #f5f7fa; color: #1f2937; }
    main { max-width: 720px; margin: 28px auto; background: white; padding: 24px; border-radius: 14px; box-shadow: 0 8px 28px rgba(0,0,0,.08); }
    h1 { margin-top: 0; font-size: 24px; }
    label { display: block; margin-top: 14px; font-weight: 600; }
    input, select, button { width: 100%; box-sizing: border-box; margin-top: 6px; padding: 11px; border: 1px solid #cbd5e1; border-radius: 8px; }
    button { margin-top: 20px; border: 0; background: #111827; color: white; cursor: pointer; font-weight: 700; }
    button:disabled { opacity: .55; cursor: wait; }
    #status { margin-top: 16px; white-space: pre-wrap; padding: 12px; border-radius: 8px; background: #f1f5f9; }
  </style>
</head>
<body>
<main>
  <h1>Envoyer un fichier vers SharePoint</h1>
  <form id="uploadForm">
    <label>Fichier<input type="file" name="file" required></label>
    <label>Hostname<input name="hostname" value="avocarbongroup.sharepoint.com" required></label>
    <label>Site path<input name="site_path" value="/sites/pdc" required></label>
    <label>Bibliothèque<input name="library_name" value="RFQ_Costing Files"></label>
    <label>Dossier cible<input name="parent_folder_path" value="RFQ Excel" required></label>
    <label>Comportement en cas de conflit
      <select name="conflict_behavior">
        <option value="replace">Remplacer</option>
        <option value="rename">Renommer</option>
        <option value="fail">Échouer</option>
      </select>
    </label>
    <button id="sendButton" type="submit">Envoyer vers SharePoint</button>
  </form>
  <div id="status">Prêt.</div>
</main>
<script>
const form = document.getElementById('uploadForm');
const statusBox = document.getElementById('status');
const button = document.getElementById('sendButton');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  button.disabled = true;
  statusBox.textContent = 'Upload en cours...';
  try {
    const response = await fetch('/api/browser-upload', { method: 'POST', body: new FormData(form) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    statusBox.textContent = `Upload réussi\nNom: ${payload.uploaded_item?.name || ''}\nLien: ${payload.uploaded_item?.webUrl || ''}`;
  } catch (error) {
    statusBox.textContent = `Échec: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
</script>
</body>
</html>"""
    return HTMLResponse(page)


async def browser_upload(req: Request) -> JSONResponse:
    try:
        form = await req.form()
        uploaded_file = form.get("file")
        if uploaded_file is None or not hasattr(uploaded_file, "read"):
            raise GraphError("A file is required")

        hostname = str(form.get("hostname") or "").strip()
        site_path = str(form.get("site_path") or "").strip()
        library_name = str(form.get("library_name") or "").strip() or None
        parent_folder_path = str(form.get("parent_folder_path") or "").strip()
        conflict_behavior = str(form.get("conflict_behavior") or "replace")
        if conflict_behavior not in {"fail", "rename", "replace"}:
            raise GraphError("Invalid conflict_behavior")

        file_name = os.path.basename(str(getattr(uploaded_file, "filename", "") or "upload.bin"))
        data = await uploaded_file.read()
        if not data:
            raise GraphError("The uploaded file is empty")
        if len(data) > MAX_UPLOAD_BYTES:
            raise GraphError(f"File exceeds the browser upload limit of {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")

        drive_id, resolved_library = await _resolve_drive(hostname, site_path, library_name)
        folder_path = parent_folder_path.strip().strip("/")
        endpoint = (
            f"drives/{enc(drive_id)}/root:/{path_enc(folder_path)}:"
            if folder_path
            else f"drives/{enc(drive_id)}/root"
        )
        folder = out(await request("GET", endpoint))
        if "folder" not in folder or not folder.get("id"):
            raise GraphError(f"Destination '{parent_folder_path}' is not a valid folder")

        uploaded = await upload_bytes(
            drive_id,
            str(folder["id"]),
            file_name,
            data,
            conflict_behavior,
        )
        return JSONResponse(
            {
                "ok": True,
                "library_name": resolved_library,
                "parent_folder_path": parent_folder_path,
                "uploaded_item": uploaded,
            }
        )
    except GraphError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)
    except Exception as exc:
        safe_message = html.escape(str(exc))
        return JSONResponse({"ok": False, "error": safe_message}, status_code=500)


UPLOAD_UI_ROUTES = [
    Route("/upload", upload_page, methods=["GET"]),
    Route("/api/browser-upload", browser_upload, methods=["POST"]),
]
