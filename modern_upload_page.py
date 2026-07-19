from __future__ import annotations

from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.routing import Route

async def modern_upload_page(req: Request) -> HTMLResponse:
    q = req.query_params
    values = {
        "hostname": q.get("hostname", "avocarbongroup.sharepoint.com"),
        "site_path": q.get("site_path", "/sites/pdc"),
        "library_name": q.get("library_name", "RFQ_Costing Files"),
        "parent_folder_path": q.get("parent_folder_path", "RFQ Excel"),
        "conflict_behavior": q.get("conflict_behavior", "replace"),
    }
    page = """<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>
:root{--orange:#ee6b23;--dark:#28313d;--line:#d9dee6;--bg:#f4f6f9}*{box-sizing:border-box}body{margin:0;font-family:Arial,sans-serif;background:var(--bg);color:var(--dark)}.wrap{max-width:760px;margin:0 auto;padding:18px}.card{background:white;border-radius:18px;overflow:hidden;box-shadow:0 14px 38px rgba(31,41,55,.12)}.hero{padding:22px;background:linear-gradient(120deg,#242c36,#3e4957);color:white}.brand{display:flex;gap:12px;align-items:center}.logo{width:42px;height:42px;border-radius:11px;background:var(--orange);display:grid;place-items:center;font-weight:800}.hero h1{margin:0;font-size:21px}.hero p{margin:5px 0 0;color:#d8dde5;font-size:13px}.body{padding:22px}.hint{padding:12px 14px;border:1px solid #ffd9c1;background:#fff8f3;border-radius:11px;margin-bottom:16px;font-size:13px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.wide{grid-column:1/-1}label{display:block;font-size:12px;font-weight:700;margin-bottom:6px;color:#586273}input,select{width:100%;padding:11px 12px;border:1px solid var(--line);border-radius:10px;background:white;font-size:14px}input:focus,select:focus{outline:none;border-color:var(--orange);box-shadow:0 0 0 3px rgba(238,107,35,.14)}.drop{padding:18px;border:2px dashed #cbd3de;border-radius:13px;background:#fafbfd}.drop input{border:0;padding:0;background:transparent}.btn{width:100%;margin-top:18px;border:0;border-radius:11px;padding:13px;background:var(--orange);color:white;font-weight:800;font-size:14px;cursor:pointer}.btn:disabled{opacity:.55}.status{margin-top:14px;padding:12px;border-radius:10px;background:#f1f4f7;white-space:pre-wrap;font-size:13px}.ok{background:#ecfdf3;color:#16703a}.err{background:#fff1f0;color:#a6231b}@media(max-width:620px){.grid{grid-template-columns:1fr}.wide{grid-column:auto}.wrap{padding:8px}.body,.hero{padding:17px}}
</style></head><body><div class='wrap'><div class='card'><div class='hero'><div class='brand'><div class='logo'>AVO</div><div><h1>Envoi vers SharePoint</h1><p>Destination préremplie depuis la conversation ChatGPT</p></div></div></div><div class='body'><div class='hint'>Vérifiez la destination, choisissez le fichier, puis confirmez l’envoi.</div><form id='f'><div class='grid'><div class='wide drop'><label>Fichier</label><input type='file' name='file' required></div><input type='hidden' name='hostname' value='__HOST__'><div><label>Site</label><input name='site_path' value='__SITE__' required></div><div><label>Bibliothèque</label><input name='library_name' value='__LIB__'></div><div class='wide'><label>Dossier cible</label><input name='parent_folder_path' value='__FOLDER__' required></div><div class='wide'><label>Si le fichier existe déjà</label><select name='conflict_behavior'><option value='replace'>Remplacer</option><option value='rename'>Créer une copie renommée</option><option value='fail'>Annuler</option></select></div></div><button id='send' class='btn' type='submit'>Envoyer vers SharePoint</button></form><div id='status' class='status'>Prêt.</div></div></div></div><script>
const form=document.getElementById('f'),btn=document.getElementById('send'),box=document.getElementById('status');form.conflict_behavior.value='__CONFLICT__';form.addEventListener('submit',async e=>{e.preventDefault();btn.disabled=true;box.className='status';box.textContent='Upload en cours...';try{const r=await fetch('/api/browser-upload',{method:'POST',body:new FormData(form)});const p=await r.json();if(!r.ok)throw new Error(p.error||`HTTP ${r.status}`);box.className='status ok';box.textContent=`Upload réussi\n${p.uploaded_item?.name||''}\n${p.uploaded_item?.webUrl||''}`}catch(err){box.className='status err';box.textContent=`Échec : ${err.message}`}finally{btn.disabled=false}})
</script></body></html>"""
    for token, key in [("__HOST__","hostname"),("__SITE__","site_path"),("__LIB__","library_name"),("__FOLDER__","parent_folder_path"),("__CONFLICT__","conflict_behavior")]:
        page = page.replace(token, values[key].replace("'", "&#39;").replace('"', '&quot;'))
    return HTMLResponse(page)

MODERN_UPLOAD_ROUTES = [Route('/upload-modern', modern_upload_page, methods=['GET'])]
