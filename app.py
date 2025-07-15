"""
QlikSense MCP Server Application

Minimale implementatie van een MCP server voor QlikSense functionaliteit.
"""

from mcp.server.fastmcp import FastMCP
from qlik_client import QlikClient, QlikAuthenticationError, QlikConnectionError
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("QlikSense MCP Server")

def get_qlik_client() -> QlikClient:
    """
    Maak en authenticeer een QlikClient instantie
    
    Returns:
        QlikClient: Geauthenticeerde QlikClient instantie
        
    Raises:
        ValueError: Als configuratie ontbreekt
        Exception: Als authenticatie mislukt
    """
    # Valideer configuratie
    server = os.getenv("QLIK_SERVER")
    user = os.getenv("QLIK_USER")
    
    if not server or not user:
        raise ValueError("QLIK_SERVER en QLIK_USER environment variabelen zijn vereist")
    
    # Maak en authenticeer client
    client = QlikClient()
    if not client.authenticate():
        raise Exception("QlikSense authenticatie mislukt")
    
    return client

@mcp.tool()
def list_apps() -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense apps op
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare apps met metadata
        
    Raises:
        Exception: Als het ophalen van apps mislukt
    """
    try:
        client = get_qlik_client()
        return client.get_apps()
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen apps: {str(e)}")

if __name__ == "__main__":
    mcp.run()