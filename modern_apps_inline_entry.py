from __future__ import annotations
import sys,types
from contextlib import asynccontextmanager
_CAPTURED=[]
class LegacyFastMCP:
    def __init__(self,*a,**k): pass
    def tool(self,*a,**k):
        name=k.get('name')
        def deco(fn): _CAPTURED.append((name or fn.__name__,fn)); return fn
        return deco
    def run(self,*a,**k): return None
compat=types.ModuleType('mcp.server.fastmcp'); compat.FastMCP=LegacyFastMCP; sys.modules['mcp.server.fastmcp']=compat
import server as legacy
from app_auth_tools_v2 import list_drives,list_recent_documents
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount,Route
from modern_apps_widget_inline import apps
from modern_upload_page import MODERN_UPLOAD_ROUTES
from upload_ui import UPLOAD_UI_ROUTES
AZURE_HOST='sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net'
mcp=MCPServer('AVOCarbon SharePoint MCP',extensions=[apps])
for n,f in _CAPTURED:
    if n not in {'list_drives','list_recent_documents'}: mcp.add_tool(f,name=n)
mcp.add_tool(list_drives,name='list_drives'); mcp.add_tool(list_recent_documents,name='list_recent_documents')
security=TransportSecuritySettings(allowed_hosts=[AZURE_HOST,f'{AZURE_HOST}:*','localhost','localhost:*'],allowed_origins=['https://chatgpt.com','https://chat.openai.com'])
async def health(_): return JSONResponse({'status':'ok','version':'1.4.0-inline-upload','mcp_apps':True,'inline_upload':True,'endpoint':'/mcp','total_tools':len(_CAPTURED)+1})
@asynccontextmanager
async def lifespan(_):
    async with mcp.session_manager.run(): yield
mcp_app=mcp.streamable_http_app(transport_security=security,stateless_http=True,json_response=True)
starlette_app=Starlette(routes=[Route('/health',health,methods=['GET']),*MODERN_UPLOAD_ROUTES,*UPLOAD_UI_ROUTES,Mount('/',app=mcp_app)],lifespan=lifespan)
app=CORSMiddleware(app=starlette_app,allow_origin_regex='https://.*',allow_methods=['GET','POST','DELETE','OPTIONS'],allow_headers=['*'],expose_headers=['Mcp-Session-Id'],allow_credentials=False)
