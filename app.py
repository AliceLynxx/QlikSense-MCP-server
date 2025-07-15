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

@mcp.tool()
def list_apps_with_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense apps op met een bestaande sessie

    Args:
        session_id (str): De X-Qlik-Session cookie waarde

    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare apps met metadata

    Raises:
        Exception: Als het ophalen van apps mislukt
    """
    try:
        server = os.getenv("QLIK_SERVER")
        if not server:
            raise ValueError("QLIK_SERVER environment variabele is vereist")

        client = QlikClient(server_url=server, session_id=session_id)
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
    Haal beschikbare QlikSense taken op
    
    Deze tool haalt alle beschikbare taken op uit de QlikSense omgeving,
    inclusief reload taken, externe programma's en user sync taken.
    Voor elke taak wordt relevante metadata getoond zoals status, 
    gekoppelde app, triggers, en laatste uitvoering informatie.
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare taken met metadata
        
    Raises:
        Exception: Als het ophalen van taken mislukt
    """
    try:
        client = get_qlik_client()
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
    Haal logs op van specifieke QlikSense taak
    
    Deze tool haalt gedetailleerde uitvoeringsresultaten (execution results) op
    van een specifieke QlikSense taak. De logs bevatten informatie over alle
    uitvoeringen van de taak, inclusief status, timestamps, duur, script logs,
    en eventuele foutmeldingen. Dit is essentieel voor troubleshooting en
    monitoring van taakuitvoeringen.
    
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
        client = get_qlik_client()
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

if __name__ == "__main__":
    mcp.run()