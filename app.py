"""
QlikSense MCP Server Application

MCP server implementatie voor QlikSense functionaliteit met Playwright-based authenticatie.
Alle tools vereisen een session_id parameter die verkregen moet worden via Playwright authenticatie.
"""

from mcp.server.fastmcp import FastMCP
from qlik_client import QlikClient, QlikAuthenticationError, QlikConnectionError
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("QlikSense MCP Server")

@mcp.tool()
def list_apps_with_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense apps op met session_id
    
    Deze tool haalt alle beschikbare QlikSense apps op uit de omgeving
    met behulp van een door Playwright verkregen session_id. De tool
    toont relevante metadata zoals eigenaar, beschrijving, tags en
    aangepaste eigenschappen voor elke app.
    
    Args:
        session_id (str): Sessie ID verkregen via Playwright authenticatie.
                         Dit moet een geldige QlikSense sessie ID zijn.
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare apps met metadata:
                             - id: Unieke app ID
                             - name: App naam
                             - description: App beschrijving
                             - owner: Eigenaar van de app
                             - created: Aanmaakdatum
                             - modified: Laatste wijzigingsdatum
                             - published: Boolean of app gepubliceerd is
                             - stream: Stream naam indien gepubliceerd
                             - file_size: Bestandsgrootte in bytes
                             - last_reload_time: Laatste reload timestamp
                             - tags: Lijst van toegewezen tags
                             - custom_properties: Aangepaste eigenschappen
        
    Raises:
        Exception: Als het ophalen van apps mislukt, inclusief:
                  - Authenticatie fouten (ongeldige session_id)
                  - Verbindingsfouten
                  - Onvoldoende rechten
    """
    try:
        # Valideer input parameter
        if not session_id:
            raise ValueError("Session ID parameter is vereist")
        
        if not isinstance(session_id, str):
            raise ValueError("Session ID moet een string zijn")
        
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("Session ID mag niet leeg zijn")
        
        # Maak client met session_id
        client = QlikClient(session_id=session_id)
        return client.get_apps()
        
    except ValueError as e:
        raise Exception(f"Parameter validatie fout: {str(e)}")
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen apps: {str(e)}")

@mcp.tool()
def list_tasks_with_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Haal beschikbare QlikSense taken op met session_id
    
    Deze tool haalt alle beschikbare taken op uit de QlikSense omgeving
    met behulp van een door Playwright verkregen session_id. De tool toont
    reload taken, externe programma's en user sync taken inclusief relevante
    metadata zoals status, gekoppelde app, triggers, en laatste uitvoering informatie.
    
    Args:
        session_id (str): Sessie ID verkregen via Playwright authenticatie.
                         Dit moet een geldige QlikSense sessie ID zijn.
    
    Returns:
        List[Dict[str, Any]]: Lijst van beschikbare taken met metadata:
                             - id: Unieke taak ID
                             - name: Taak naam
                             - type: Type taak (Reload, External Program, User Sync)
                             - status: Status (Enabled/Disabled)
                             - enabled: Boolean of taak actief is
                             - app: Gekoppelde app informatie (indien van toepassing)
                             - created: Aanmaakdatum
                             - modified: Laatste wijzigingsdatum
                             - owner: Eigenaar van de taak
                             - triggers: Lijst van triggers
                             - last_execution: Informatie over laatste uitvoering
                             - max_retries: Maximum aantal herhalingen
                             - timeout: Timeout waarde
                             - tags: Lijst van toegewezen tags
                             - custom_properties: Aangepaste eigenschappen
        
    Raises:
        Exception: Als het ophalen van taken mislukt, inclusief:
                  - Authenticatie fouten (ongeldige session_id)
                  - Verbindingsfouten
                  - Onvoldoende rechten
    """
    try:
        # Valideer input parameter
        if not session_id:
            raise ValueError("Session ID parameter is vereist")
        
        if not isinstance(session_id, str):
            raise ValueError("Session ID moet een string zijn")
        
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("Session ID mag niet leeg zijn")
        
        # Maak client met session_id
        client = QlikClient(session_id=session_id)
        return client.get_tasks()
        
    except ValueError as e:
        raise Exception(f"Parameter validatie fout: {str(e)}")
    except QlikAuthenticationError as e:
        raise Exception(f"Authenticatie fout: {str(e)}")
    except QlikConnectionError as e:
        raise Exception(f"Verbinding fout: {str(e)}")
    except Exception as e:
        raise Exception(f"Fout bij ophalen taken: {str(e)}")

@mcp.tool()
def get_task_logs_with_session(session_id: str, task_id: str) -> List[Dict[str, Any]]:
    """
    Haal logs op van specifieke QlikSense taak met session_id
    
    Deze tool haalt gedetailleerde uitvoeringsresultaten (execution results) op
    van een specifieke QlikSense taak met behulp van een door Playwright verkregen
    session_id. De logs bevatten informatie over alle uitvoeringen van de taak,
    inclusief status, timestamps, duur, script logs, en eventuele foutmeldingen.
    Dit is essentieel voor troubleshooting en monitoring van taakuitvoeringen.
    
    De tool is nuttig voor:
    - Ontwikkelaars die QlikSense taken willen debuggen
    - Data analisten die taakuitvoering willen monitoren  
    - Systeembeheerders die operationeel beheer uitvoeren
    
    Args:
        session_id (str): Sessie ID verkregen via Playwright authenticatie.
                         Dit moet een geldige QlikSense sessie ID zijn.
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
                  - Authenticatie fouten (ongeldige session_id)
                  - Verbindingsfouten  
                  - Ongeldige task_id
                  - Onvoldoende rechten
    
    Example:
        logs = get_task_logs_with_session("abc123", "12345678-1234-1234-1234-123456789abc")
        for log in logs:
            print(f"Uitvoering {log['id']}: {log['status']} ({log['duration_formatted']})")
            if log['has_errors']:
                for error in log['error_messages']:
                    print(f"  Fout: {error}")
    """
    try:
        # Valideer input parameters
        if not session_id:
            raise ValueError("Session ID parameter is vereist")
        
        if not isinstance(session_id, str):
            raise ValueError("Session ID moet een string zijn")
        
        session_id = session_id.strip()
        if not session_id:
            raise ValueError("Session ID mag niet leeg zijn")
        
        if not task_id:
            raise ValueError("Task ID parameter is vereist")
        
        if not isinstance(task_id, str):
            raise ValueError("Task ID moet een string zijn")
        
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("Task ID mag niet leeg zijn")
        
        # Maak client met session_id en haal logs op
        client = QlikClient(session_id=session_id)
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