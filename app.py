"""
QlikSense MCP Server Application

Browser-based implementatie van een MCP server voor QlikSense functionaliteit.
Gebruikt BrowserQlikClient voor persistent browser context authenticatie.
"""

from mcp.server.fastmcp import FastMCP
from browser_qlik_client import BrowserQlikClient, QlikAuthenticationError, QlikConnectionError
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("QlikSense MCP Server")

# Global browser client instance voor hergebruik
_browser_client: BrowserQlikClient = None

def get_browser_qlik_client() -> BrowserQlikClient:
    """
    Maak en authenticeer een BrowserQlikClient instantie
    
    Hergebruikt bestaande client instance voor efficiency en persistent browser context.
    
    Returns:
        BrowserQlikClient: Geauthenticeerde BrowserQlikClient instantie
        
    Raises:
        ValueError: Als configuratie ontbreekt
        Exception: Als authenticatie mislukt
    """
    global _browser_client
    
    # Valideer configuratie
    server = os.getenv("QLIK_SERVER")
    username = os.getenv("QLIK_USERNAME")
    password = os.getenv("QLIK_PASSWORD")
    
    if not server or not username or not password:
        raise ValueError("QLIK_SERVER, QLIK_USERNAME en QLIK_PASSWORD environment variabelen zijn vereist")
    
    # Hergebruik bestaande client indien beschikbaar en geauthenticeerd
    if _browser_client and _browser_client.is_authenticated():
        return _browser_client
    
    # Maak nieuwe client en authenticeer
    try:
        if _browser_client:
            _browser_client.close()  # Sluit oude client
            
        _browser_client = BrowserQlikClient()
        if not _browser_client.authenticate():
            raise Exception("QlikSense browser authenticatie mislukt")
        
        return _browser_client
        
    except Exception as e:
        if _browser_client:
            _browser_client.close()
            _browser_client = None
        raise

@mcp.tool()
def list_apps() -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense apps op via browser context
    
    Deze tool gebruikt een persistent browser context voor authenticatie,
    waardoor alle QlikSense API calls gebruik maken van dezelfde geauthenticeerde
    sessie. Dit zorgt voor betrouwbare communicatie met QlikSense.
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare apps met metadata
        
    Raises:
        Exception: Als het ophalen van apps mislukt
    """
    try:
        client = get_browser_qlik_client()
        return client.get_apps()
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen apps: {str(e)}")

@mcp.tool()
def list_apps_with_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense apps op met browser context
    
    Deze functie is behouden voor backward compatibility, maar gebruikt nu
    de browser-based client voor alle API calls. De session_id parameter
    wordt genegeerd omdat de browser context de volledige sessie staat beheert.
    
    Args:
        session_id (str): Genegeerd - browser context beheert sessie automatisch
        
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare apps met metadata
        
    Raises:
        Exception: Als het ophalen van apps mislukt
    """
    try:
        # Gebruik browser client in plaats van session-based approach
        client = get_browser_qlik_client()
        return client.get_apps()
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen apps: {str(e)}")

@mcp.tool()
def list_tasks() -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense taken op via browser context
    
    Deze tool haalt alle beschikbare taken op uit de QlikSense omgeving,
    inclusief reload taken, externe programma's en user sync taken.
    Voor elke taak wordt relevante metadata getoond zoals status, 
    gekoppelde app, triggers, en laatste uitvoering informatie.
    
    Gebruikt browser context voor betrouwbare authenticatie en API communicatie.
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare taken met metadata
        
    Raises:
        Exception: Als het ophalen van taken mislukt
    """
    try:
        client = get_browser_qlik_client()
        return client.get_tasks()
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen taken: {str(e)}")

@mcp.tool()
def get_task_logs(task_id: str) -> List[Dict[str, Any]]:
    """
    Haal logs op van specifieke QlikSense taak via browser context
    
    Deze tool haalt gedetailleerde uitvoeringsresultaten (execution results) op
    van een specifieke QlikSense taak via browser context. De logs bevatten 
    informatie over alle uitvoeringen van de taak, inclusief status, timestamps, 
    duur, script logs, en eventuele foutmeldingen. 
    
    De browser context zorgt voor betrouwbare authenticatie en sessie beheer,
    waardoor alle API calls gebruik maken van dezelfde geauthenticeerde sessie.
    
    De tool is nuttig voor:
    - Ontwikkelaars die QlikSense taken willen debuggen
    - Data analisten die taakuitvoering willen monitoren  
    - Systeembeheerders die operationeel beheer uitvoeren
    
    Args:
        task_id (str): ID van de taak waarvoor logs opgehaald moeten worden.
                      Dit moet een geldige QlikSense taak ID zijn.
    
    Returns:
        List[Dict[str, Any]]: Lijst van log entries gesorteerd op uitvoeringstijd
                             (nieuwste eerst). Elke entry bevat:
                             - id: Unieke ID van de log entry
                             - task_id: ID van de bijbehorende taak
                             - task_name: Naam van de bijbehorende taak
                             - status: Status van de uitvoering (FinishedSuccess, FinishedFail, etc.)
                             - start_time: Start timestamp van de uitvoering
                             - stop_time: Stop timestamp van de uitvoering
                             - duration_ms: Duur van de uitvoering in milliseconden
                             - duration_formatted: Geformatteerde duur (bijv. "2.34s")
                             - script_log: Lijst van script log entries
                             - error_messages: Lijst van foutmeldingen
                             - has_errors: Boolean die aangeeft of er fouten zijn
                             - created: Aanmaakdatum van de log entry
                             - modified: Laatste wijzigingsdatum
        
    Raises:
        Exception: Als het ophalen van logs mislukt, inclusief:
                  - Authenticatie fouten
                  - Verbindingsfouten  
                  - Ongeldige task_id
                  - Onvoldoende rechten
    
    Example:
        logs = get_task_logs("12345678-1234-1234-1234-123456789abc")
        for log in logs:
            print(f"Uitvoering {log['id']}: {log['status']} ({log['duration_formatted']})")
            if log['has_errors']:
                for error in log['error_messages']:
                    print(f"  Fout: {error}")
    """
    try:
        # Valideer input parameter
        if not task_id:
            raise ValueError("Task ID parameter is vereist")
        
        if not isinstance(task_id, str):
            raise ValueError("Task ID moet een string zijn")
        
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("Task ID mag niet leeg zijn")
        
        # Maak client en haal logs op
        client = get_browser_qlik_client()
        logs = client.get_logs(task_id)
        
        return logs
        
    except ValueError as e:
        raise Exception(f"Parameter validatie fout: {str(e)}")
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen logs voor taak {task_id}: {str(e)}")

# Cleanup functie voor graceful shutdown
def cleanup_browser_client():
    """Sluit browser client bij shutdown"""
    global _browser_client
    if _browser_client:
        _browser_client.close()
        _browser_client = None

# Register cleanup functie
import atexit
atexit.register(cleanup_browser_client)

if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        cleanup_browser_client()