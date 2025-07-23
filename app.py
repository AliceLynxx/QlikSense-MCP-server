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

@mcp.tool()
async def list_apps():
    """Haal beschikbare QlikSense apps op"""
    try:
        # Start browser en haal session_id op (async)
        browser_manager = AsyncBrowserManager()
        session_id = await browser_manager.get_session_id()
        
        # Maak QlikClient en haal apps op
        client = QlikClient(
            server=os.getenv("QLIK_SERVER"),
            username=os.getenv("QLIK_USERNAME"), 
            session_id=session_id
        )
        
        return client.list_apps()
    except Exception as e:
        return {"error": f"Fout bij ophalen apps: {str(e)}"}

@mcp.tool()
async def list_tasks():
    """Haal beschikbare QlikSense taken op"""
    try:
        # Start browser en haal session_id op (async)
        browser_manager = AsyncBrowserManager()
        session_id = await browser_manager.get_session_id()
        
        # Maak QlikClient en haal taken op
        client = QlikClient(
            server=os.getenv("QLIK_SERVER"),
            username=os.getenv("QLIK_USERNAME"),
            session_id=session_id
        )
        
        return client.list_tasks()
    except Exception as e:
        return {"error": f"Fout bij ophalen taken: {str(e)}"}

@mcp.tool()
async def get_task_logs(task_id: str):
    """Haal logs op van specifieke QlikSense taak"""
    try:
        # Start browser en haal session_id op (async)
        browser_manager = AsyncBrowserManager()
        session_id = await browser_manager.get_session_id()
        
        # Maak QlikClient en haal logs op
        client = QlikClient(
            server=os.getenv("QLIK_SERVER"),
            username=os.getenv("QLIK_USERNAME"),
            session_id=session_id
        )
        
        return client.get_task_logs(task_id)
    except Exception as e:
        return {"error": f"Fout bij ophalen logs voor taak {task_id}: {str(e)}"}

if __name__ == "__main__":
    mcp.run()