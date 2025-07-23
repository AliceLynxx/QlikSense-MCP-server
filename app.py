"""
Async QlikSense MCP Server

MCP server implementatie voor QlikSense functionaliteit met async Playwright-based authenticatie.
Alle tools zijn nu async voor betere performance en concurrency.

"""

from mcp.server.fastmcp import FastMCP
from browser_manager import AsyncBrowserManager
from qlik_client import QlikClient
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("QlikSense MCP Server")

async def _get_qlik_client():
    """Helper function to create QlikClient with async session management."""
    browser_manager = AsyncBrowserManager()
    session_id = await browser_manager.get_session_id()
    
    return QlikClient(
        server=os.getenv("QLIK_SERVER"),
        username=os.getenv("QLIK_USERNAME"), 
        session_id=session_id
    )

@mcp.tool()
async def list_apps():
    """Haal beschikbare QlikSense apps op"""
    try:
        client = await _get_qlik_client()
        return client.list_apps()
    except Exception as e:
        return {"error": f"Fout bij ophalen apps: {str(e)}"}

@mcp.tool()
async def list_tasks():
    """Haal beschikbare QlikSense taken op"""
    try:
        client = await _get_qlik_client()
        return client.list_tasks()
    except Exception as e:
        return {"error": f"Fout bij ophalen taken: {str(e)}"}

@mcp.tool()
async def get_task_logs(task_id: str):
    """Haal logs op van specifieke QlikSense taak"""
    try:
        client = await _get_qlik_client()
        return client.get_task_logs(task_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen logs voor taak {task_id}: {str(e)}"}

@mcp.tool()
async def get_app_script(app_id: str):
    """Haal het script van een specifieke QlikSense app op"""
    try:
        client = await _get_qlik_client()
        return client.get_app_script(app_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen script voor app {app_id}: {str(e)}"}

@mcp.tool() 
async def get_app_metadata(app_id: str):
    """Haal measures, dimensions en sheets van een specifieke app op"""
    try:
        client = await _get_qlik_client()
        return client.get_app_metadata(app_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen metadata voor app {app_id}: {str(e)}"}

@mcp.tool()
async def update_app_script(app_id: str, script: str):
    """Overschrijf het script van een app met een nieuwe versie"""
    try:
        client = await _get_qlik_client()
        return client.update_app_script(app_id, script)
    except Exception as e:
        return {"error": f"Fout bij updaten script voor app {app_id}: {str(e)}"}

@mcp.tool()
async def get_app_variables(app_id: str):
    """Haal variabelen uit een app op"""
    try:
        client = await _get_qlik_client()
        return client.get_app_variables(app_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen variabelen voor app {app_id}: {str(e)}"}

@mcp.tool()
async def reload_app(app_id: str):
    """Start een reload van een specifieke app"""
    try:
        client = await _get_qlik_client()
        return client.reload_app(app_id)
    except Exception as e:
        return {"error": f"Fout bij reloaden app {app_id}: {str(e)}"}

@mcp.tool()
async def get_app_connections(app_id: str):
    """Haal data connecties van een app op"""
    try:
        client = await _get_qlik_client()
        return client.get_app_connections(app_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen connecties voor app {app_id}: {str(e)}"}

@mcp.tool()
async def export_app(app_id: str):
    """Exporteer een app als QVF bestand"""
    try:
        client = await _get_qlik_client()
        return client.export_app(app_id)
    except Exception as e:
        return {"error": f"Fout bij exporteren app {app_id}: {str(e)}"}

if __name__ == "__main__":
    mcp.run()
