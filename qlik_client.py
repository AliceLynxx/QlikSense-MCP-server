"""
QlikSense Client Module

Dit module bevat de QlikClient klasse voor communicatie met QlikSense server
via session-based authenticatie. De client biedt een betrouwbare interface
voor het uitvoeren van QlikSense API operaties.

Author: QlikSense MCP Server Project
"""

import os
import requests
import logging
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


class QlikAuthenticationError(Exception):
    """Uitzondering voor authenticatie fouten"""
    pass


class QlikConnectionError(Exception):
    """Uitzondering voor verbindingsfouten"""
    pass


class QlikClient:
    """
    QlikSense API Client met session-based authenticatie
    
    Deze klasse biedt een interface voor communicatie met QlikSense server
    via session-based authenticatie. De client beheert automatisch sessies
    en biedt methoden voor het ophalen van apps, taken en logs.
    
    Attributes:
        server_url (str): QlikSense server URL
        username (str): Gebruikersnaam voor authenticatie
        app_id (Optional[str]): Standaard app ID
        session (requests.Session): HTTP sessie object
        session_id (Optional[str]): Actieve sessie ID
        timeout (int): Request timeout in seconden
        max_retries (int): Maximum aantal herhalingen bij fouten
    """
    
    def __init__(self, server_url: Optional[str] = None, username: Optional[str] = None, 
                 app_id: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        """
        Initialiseer QlikClient
        
        Args:
            server_url: QlikSense server URL (optioneel, gebruikt QLIK_SERVER env var)
            username: Gebruikersnaam (optioneel, gebruikt QLIK_USER env var)
            app_id: Standaard app ID (optioneel, gebruikt APP_ID env var)
            timeout: Request timeout in seconden
            max_retries: Maximum aantal herhalingen bij fouten
            
        Raises:
            QlikConnectionError: Als vereiste configuratie ontbreekt
        """
        # Laad environment variabelen
        load_dotenv()
        
        # Configuratie laden
        self.server_url = server_url or os.getenv('QLIK_SERVER')
        self.username = username or os.getenv('QLIK_USER')
        self.app_id = app_id or os.getenv('APP_ID')
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Valideer vereiste configuratie
        if not self.server_url:
            raise QlikConnectionError("Server URL is vereist (QLIK_SERVER environment variabele)")
        if not self.username:
            raise QlikConnectionError("Gebruikersnaam is vereist (QLIK_USER environment variabele)")
            
        # Normaliseer server URL
        self.server_url = self.server_url.rstrip('/')
        
        # Initialiseer sessie
        self.session = requests.Session()
        self.session_id: Optional[str] = None
        
        # SSL verificatie configuratie
        ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
        self.session.verify = ssl_verify
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"QlikClient geïnitialiseerd voor server: {self.server_url}")
    
    def authenticate(self) -> bool:
        """
        Voer session-based authenticatie uit
        
        Maakt verbinding met QlikSense server via X-Qlik-User header
        en slaat de sessie cookie op voor hergebruik.
        
        Returns:
            bool: True als authenticatie succesvol, False anders
            
        Raises:
            QlikAuthenticationError: Als authenticatie mislukt
            QlikConnectionError: Als verbinding mislukt
        """
        try:
            # Stel authenticatie headers in
            headers = {
                'X-Qlik-User': self.username,
                'Content-Type': 'application/json'
            }
            
            # Maak verbinding met /hub endpoint
            hub_url = f"{self.server_url}/hub"
            
            self.logger.info(f"Authenticatie poging voor gebruiker: {self.username}")
            
            response = self.session.get(
                hub_url,
                headers=headers,
                timeout=self.timeout
            )
            
            # Controleer response status
            if response.status_code == 200:
                # Zoek naar sessie cookie
                session_cookie = None
                for cookie in self.session.cookies:
                    if cookie.name == 'X-Qlik-Session':
                        session_cookie = cookie.value
                        break
                
                if session_cookie:
                    self.session_id = session_cookie
                    self.logger.info("Authenticatie succesvol, sessie opgeslagen")
                    return True
                else:
                    self.logger.warning("Geen sessie cookie ontvangen")
                    return False
                    
            elif response.status_code == 401:
                raise QlikAuthenticationError(f"Authenticatie mislukt voor gebruiker: {self.username}")
            elif response.status_code == 403:
                raise QlikAuthenticationError(f"Toegang geweigerd voor gebruiker: {self.username}")
            else:
                raise QlikConnectionError(f"Onverwachte response status: {response.status_code}")
                
        except requests.exceptions.Timeout:
            raise QlikConnectionError(f"Timeout bij verbinding met server: {self.server_url}")
        except requests.exceptions.ConnectionError:
            raise QlikConnectionError(f"Kan geen verbinding maken met server: {self.server_url}")
        except requests.exceptions.RequestException as e:
            raise QlikConnectionError(f"Request fout: {str(e)}")
    
    def _make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Voer geauthenticeerde request uit met retry mechanisme
        
        Args:
            method: HTTP methode (GET, POST, etc.)
            endpoint: API endpoint (zonder server URL)
            **kwargs: Aanvullende argumenten voor requests
            
        Returns:
            requests.Response: Response object
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        if not self.session_id:
            raise QlikAuthenticationError("Geen actieve sessie, authenticatie vereist")
        
        url = f"{self.server_url}{endpoint}"
        
        # Standaard headers
        headers = kwargs.get('headers', {})
        headers.update({
            'X-Qlik-User': self.username,
            'Content-Type': 'application/json'
        })
        kwargs['headers'] = headers
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        
        # Retry mechanisme
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"Request poging {attempt + 1}/{self.max_retries} voor {endpoint}")
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"Request mislukt, wacht {wait_time}s voor retry: {str(e)}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"Request definitief mislukt na {self.max_retries} pogingen")
        
        raise QlikConnectionError(f"Request fout voor {endpoint} na {self.max_retries} pogingen: {str(last_exception)}")
    
    def get_apps(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense apps op
        
        Returns:
            List[Dict[str, Any]]: Lijst van app informatie met relevante metadata
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info("Ophalen van beschikbare apps")
        
        try:
            # QRS API endpoint voor apps
            response = self._make_authenticated_request('GET', '/qrs/app/full')
            
            # Parse response
            apps_data = response.json()
            
            # Format app data voor MCP tool
            formatted_apps = []
            for app in apps_data:
                formatted_app = {
                    'id': app.get('id', ''),
                    'name': app.get('name', 'Onbekend'),
                    'description': app.get('description', ''),
                    'owner': app.get('owner', {}).get('name', 'Onbekend'),
                    'created': app.get('createdDate', ''),
                    'modified': app.get('modifiedDate', ''),
                    'published': app.get('published', False),
                    'stream': app.get('stream', {}).get('name', '') if app.get('stream') else '',
                    'file_size': app.get('fileSize', 0),
                    'last_reload_time': app.get('lastReloadTime', ''),
                    'thumbnail': app.get('thumbnail', ''),
                    'tags': [tag.get('name', '') for tag in app.get('tags', [])],
                    'custom_properties': [
                        {
                            'name': prop.get('definition', {}).get('name', ''),
                            'value': prop.get('value', '')
                        } for prop in app.get('customProperties', [])
                    ]
                }
                formatted_apps.append(formatted_app)
            
            self.logger.info(f"Succesvol {len(formatted_apps)} apps opgehaald")
            return formatted_apps
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise QlikAuthenticationError("Authenticatie verlopen, hernieuw sessie")
            elif e.response.status_code == 403:
                raise QlikAuthenticationError("Onvoldoende rechten voor apps endpoint")
            else:
                raise QlikConnectionError(f"HTTP fout bij ophalen apps: {e.response.status_code}")
        except Exception as e:
            self.logger.error(f"Fout bij ophalen apps: {str(e)}")
            raise QlikConnectionError(f"Onverwachte fout bij ophalen apps: {str(e)}")
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense taken op
        
        Returns:
            List[Dict[str, Any]]: Lijst van taak informatie met relevante metadata
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info("Ophalen van beschikbare taken")
        
        try:
            # QRS API endpoint voor taken
            response = self._make_authenticated_request('GET', '/qrs/task/full')
            
            # Parse response
            tasks_data = response.json()
            
            # Format task data voor MCP tool
            formatted_tasks = []
            for task in tasks_data:
                # Bepaal taak type
                task_type = 'Unknown'
                if task.get('taskType') == 0:
                    task_type = 'Reload'
                elif task.get('taskType') == 1:
                    task_type = 'External Program'
                elif task.get('taskType') == 2:
                    task_type = 'User Sync'
                
                # Bepaal taak status
                task_status = 'Unknown'
                if task.get('enabled'):
                    task_status = 'Enabled'
                else:
                    task_status = 'Disabled'
                
                # Haal app informatie op indien beschikbaar
                app_info = {}
                if task.get('app'):
                    app_info = {
                        'id': task.get('app', {}).get('id', ''),
                        'name': task.get('app', {}).get('name', 'Onbekend')
                    }
                
                # Haal trigger informatie op
                triggers = []
                for trigger in task.get('operational', {}).get('triggers', []):
                    trigger_info = {
                        'id': trigger.get('id', ''),
                        'name': trigger.get('name', ''),
                        'enabled': trigger.get('enabled', False),
                        'type': trigger.get('type', 'Unknown')
                    }
                    triggers.append(trigger_info)
                
                # Haal laatste uitvoering informatie op
                last_execution = {}
                if task.get('operational', {}).get('lastExecutionResult'):
                    exec_result = task.get('operational', {}).get('lastExecutionResult', {})
                    last_execution = {
                        'status': exec_result.get('status', 'Unknown'),
                        'start_time': exec_result.get('startTime', ''),
                        'stop_time': exec_result.get('stopTime', ''),
                        'duration': exec_result.get('duration', 0),
                        'details': exec_result.get('details', [])
                    }
                
                formatted_task = {
                    'id': task.get('id', ''),
                    'name': task.get('name', 'Onbekend'),
                    'type': task_type,
                    'status': task_status,
                    'enabled': task.get('enabled', False),
                    'app': app_info,
                    'created': task.get('createdDate', ''),
                    'modified': task.get('modifiedDate', ''),
                    'owner': task.get('owner', {}).get('name', 'Onbekend'),
                    'triggers': triggers,
                    'last_execution': last_execution,
                    'max_retries': task.get('maxRetries', 0),
                    'timeout': task.get('timeout', 0),
                    'tags': [tag.get('name', '') for tag in task.get('tags', [])],
                    'custom_properties': [
                        {
                            'name': prop.get('definition', {}).get('name', ''),
                            'value': prop.get('value', '')
                        } for prop in task.get('customProperties', [])
                    ]
                }
                formatted_tasks.append(formatted_task)
            
            self.logger.info(f"Succesvol {len(formatted_tasks)} taken opgehaald")
            return formatted_tasks
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise QlikAuthenticationError("Authenticatie verlopen, hernieuw sessie")
            elif e.response.status_code == 403:
                raise QlikAuthenticationError("Onvoldoende rechten voor tasks endpoint")
            else:
                raise QlikConnectionError(f"HTTP fout bij ophalen taken: {e.response.status_code}")
        except Exception as e:
            self.logger.error(f"Fout bij ophalen taken: {str(e)}")
            raise QlikConnectionError(f"Onverwachte fout bij ophalen taken: {str(e)}")
    
    def get_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Haal logs op van specifieke taak
        
        Deze methode haalt uitvoeringsresultaten (execution results) op van een specifieke
        taak via de QRS API. De logs bevatten informatie over taakuitvoeringen inclusief
        status, timestamps, duur, details en eventuele foutmeldingen.
        
        Args:
            task_id: ID van de taak waarvoor logs opgehaald moeten worden
            
        Returns:
            List[Dict[str, Any]]: Lijst van log entries met relevante metadata:
                - id: Unieke ID van de log entry
                - task_id: ID van de bijbehorende taak
                - task_name: Naam van de bijbehorende taak
                - status: Status van de uitvoering (Success, Failed, etc.)
                - start_time: Start timestamp van de uitvoering
                - stop_time: Stop timestamp van de uitvoering
                - duration: Duur van de uitvoering in milliseconden
                - details: Gedetailleerde informatie over de uitvoering
                - script_log: Script log entries indien beschikbaar
                - error_message: Foutmelding indien van toepassing
                - created: Aanmaakdatum van de log entry
                - modified: Laatste wijzigingsdatum van de log entry
                
        Raises:
            ValueError: Als task_id leeg of None is
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info(f"Ophalen van logs voor taak: {task_id}")
        
        # Valideer input
        if not task_id or not task_id.strip():
            raise ValueError("Task ID is vereist en mag niet leeg zijn")
        
        task_id = task_id.strip()
        
        try:
            # QRS API endpoint voor execution results gefilterd op TaskId
            # Gebruik URL encoding voor de filter parameter
            filter_param = f"TaskId eq '{task_id}'"
            endpoint = f"/qrs/executionresult?filter={filter_param}"
            
            self.logger.debug(f"Ophalen execution results met endpoint: {endpoint}")
            
            response = self._make_authenticated_request('GET', endpoint)
            
            # Parse response
            execution_results = response.json()
            
            self.logger.debug(f"Ontvangen {len(execution_results)} execution results voor taak {task_id}")
            
            # Format execution results voor MCP tool
            formatted_logs = []
            for result in execution_results:
                # Bepaal status string
                status_mapping = {
                    0: 'NeverStarted',
                    1: 'Triggered',
                    2: 'Started',
                    3: 'Queued',
                    4: 'AbortInitiated',
                    5: 'Aborting',
                    6: 'Aborted',
                    7: 'FinishedSuccess',
                    8: 'FinishedFail',
                    9: 'Skipped',
                    10: 'Retry',
                    11: 'Error',
                    12: 'Reset'
                }
                
                status_code = result.get('status', -1)
                status_text = status_mapping.get(status_code, f'Unknown({status_code})')
                
                # Haal taak informatie op indien beschikbaar
                task_info = result.get('task', {})
                task_name = task_info.get('name', 'Onbekend') if task_info else 'Onbekend'
                
                # Parse details array voor meer informatie
                details = result.get('details', [])
                script_log_entries = []
                error_messages = []
                
                for detail in details:
                    detail_message = detail.get('message', '')
                    detail_type = detail.get('detailType', 0)
                    
                    # DetailType mapping (gebaseerd op QlikSense documentatie):
                    # 0 = Information, 1 = Warning, 2 = Error
                    if detail_type == 2:  # Error
                        error_messages.append(detail_message)
                    else:
                        script_log_entries.append({
                            'timestamp': detail.get('timestamp', ''),
                            'type': 'Warning' if detail_type == 1 else 'Information',
                            'message': detail_message
                        })
                
                # Bereken duur indien start en stop tijd beschikbaar zijn
                duration_ms = 0
                start_time = result.get('startTime', '')
                stop_time = result.get('stopTime', '')
                
                if start_time and stop_time:
                    try:
                        from datetime import datetime
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        stop_dt = datetime.fromisoformat(stop_time.replace('Z', '+00:00'))
                        duration_ms = int((stop_dt - start_dt).total_seconds() * 1000)
                    except Exception as e:
                        self.logger.warning(f"Kon duur niet berekenen: {str(e)}")
                        duration_ms = result.get('duration', 0)
                else:
                    duration_ms = result.get('duration', 0)
                
                formatted_log = {
                    'id': result.get('id', ''),
                    'task_id': task_id,
                    'task_name': task_name,
                    'status': status_text,
                    'status_code': status_code,
                    'start_time': start_time,
                    'stop_time': stop_time,
                    'duration_ms': duration_ms,
                    'duration_formatted': f"{duration_ms / 1000:.2f}s" if duration_ms > 0 else "0s",
                    'details_count': len(details),
                    'script_log': script_log_entries,
                    'error_messages': error_messages,
                    'has_errors': len(error_messages) > 0,
                    'created': result.get('createdDate', ''),
                    'modified': result.get('modifiedDate', ''),
                    'execution_id': result.get('executionId', ''),
                    'session_id': result.get('sessionId', ''),
                    'raw_details': details  # Voor debugging doeleinden
                }
                formatted_logs.append(formatted_log)
            
            # Sorteer logs op start tijd (nieuwste eerst)
            formatted_logs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            
            self.logger.info(f"Succesvol {len(formatted_logs)} log entries opgehaald voor taak {task_id}")
            return formatted_logs
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise QlikAuthenticationError("Authenticatie verlopen, hernieuw sessie")
            elif e.response.status_code == 403:
                raise QlikAuthenticationError("Onvoldoende rechten voor execution results endpoint")
            elif e.response.status_code == 404:
                self.logger.warning(f"Geen execution results gevonden voor taak {task_id}")
                return []  # Geen logs gevonden is geen fout
            else:
                raise QlikConnectionError(f"HTTP fout bij ophalen logs voor taak {task_id}: {e.response.status_code}")
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            self.logger.error(f"Fout bij ophalen logs voor taak {task_id}: {str(e)}")
            raise QlikConnectionError(f"Onverwachte fout bij ophalen logs voor taak {task_id}: {str(e)}")
    
    def is_authenticated(self) -> bool:
        """
        Controleer of client geauthenticeerd is
        
        Returns:
            bool: True als geauthenticeerd, False anders
        """
        return self.session_id is not None
    
    def close(self):
        """
        Sluit de client sessie
        """
        if self.session:
            self.session.close()
            self.session_id = None
            self.logger.info("QlikClient sessie gesloten")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience functie voor eenvoudige client initialisatie
def create_qlik_client(**kwargs) -> QlikClient:
    """
    Maak en authenticeer QlikClient
    
    Args:
        **kwargs: Argumenten voor QlikClient constructor
        
    Returns:
        QlikClient: Geauthenticeerde client instance
        
    Raises:
        QlikAuthenticationError: Als authenticatie mislukt
        QlikConnectionError: Als verbinding mislukt
    """
    client = QlikClient(**kwargs)
    client.authenticate()
    return client