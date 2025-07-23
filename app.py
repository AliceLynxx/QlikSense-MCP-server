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

@mcp.tool()
def list_apps():
    """Haal beschikbare QlikSense apps op"""
    # Start browser en haal session_id op
    browser_manager = BrowserManager()
    session_id = browser_manager.get_session_id()
    
    # Maak QlikClient en haal apps op
    client = QlikClient(
        server=os.getenv("QLIK_SERVER"),
        username=os.getenv("QLIK_USERNAME"), 
        session_id=session_id
    )
    
    return client.list_apps()

@mcp.tool()
def list_tasks():
    """Haal beschikbare QlikSense taken op"""
    # Start browser en haal session_id op
    browser_manager = BrowserManager()
    session_id = browser_manager.get_session_id()
    
    # Maak QlikClient en haal taken op
    client = QlikClient(
        server=os.getenv("QLIK_SERVER"),
        username=os.getenv("QLIK_USERNAME"),
        session_id=session_id
    )
    
    return client.list_tasks()

@mcp.tool()
def get_task_logs(task_id: str):
    """Haal logs op van specifieke QlikSense taak"""
    # Start browser en haal session_id op
    browser_manager = BrowserManager()
    session_id = browser_manager.get_session_id()
    
    # Maak QlikClient en haal logs op
    client = QlikClient(
        server=os.getenv("QLIK_SERVER"),
        username=os.getenv("QLIK_USERNAME"),
        session_id=session_id
    )
    
    return client.get_task_logs(task_id)

if __name__ == "__main__":
    mcp.run()