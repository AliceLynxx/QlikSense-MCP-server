"""
Simpele QlikSense MCP Server

MCP server implementatie voor QlikSense functionaliteit met Playwright-based authenticatie.
Alle tools vereisen een session_id parameter die verkregen moet worden via Playwright authenticatie.

"""

from mcp.server.fastmcp import FastMCP
from browser_manager import BrowserManager
from qlik_client import QlikClient
import os
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("QlikSense MCP Server")

def _get_qlik_client():
    """Helper function to create QlikClient with session management."""
    browser_manager = BrowserManager()
    session_id = browser_manager.get_session_id()
    
    return QlikClient(
        server=os.getenv("QLIK_SERVER"),
        username=os.getenv("QLIK_USERNAME"), 
        session_id=session_id
    )

@mcp.tool()
def list_apps():
    """Haal beschikbare QlikSense apps op"""
    client = _get_qlik_client()
    return client.list_apps()

@mcp.tool()
def list_tasks():
    """Haal beschikbare QlikSense taken op"""
    client = _get_qlik_client()
    return client.list_tasks()

@mcp.tool()
def get_task_logs(task_id: str):
    """Haal logs op van specifieke QlikSense taak"""
    client = _get_qlik_client()
    return client.get_task_logs(task_id)

@mcp.tool()
def get_app_script(app_id: str):
    """Haal het script van een specifieke QlikSense app op"""
    client = _get_qlik_client()
    return client.get_app_script(app_id)

@mcp.tool() 
def get_app_metadata(app_id: str):
    """Haal measures, dimensions en sheets van een specifieke app op"""
    client = _get_qlik_client()
    return client.get_app_metadata(app_id)

@mcp.tool()
def update_app_script(app_id: str, script: str):
    """Overschrijf het script van een app met een nieuwe versie"""
    client = _get_qlik_client()
    return client.update_app_script(app_id, script)

@mcp.tool()
def get_app_variables(app_id: str):
    """Haal variabelen uit een app op"""
    client = _get_qlik_client()
    return client.get_app_variables(app_id)

@mcp.tool()
def reload_app(app_id: str):
    """Start een reload van een specifieke app"""
    client = _get_qlik_client()
    return client.reload_app(app_id)

@mcp.tool()
def get_app_connections(app_id: str):
    """Haal data connecties van een app op"""
    client = _get_qlik_client()
    return client.get_app_connections(app_id)

@mcp.tool()
def export_app(app_id: str):
    """Exporteer een app als QVF bestand"""
    client = _get_qlik_client()
    return client.export_app(app_id)

if __name__ == "__main__":
    mcp.run()