"""
Browser-based QlikSense Client Module

Dit module bevat de BrowserQlikClient klasse die sync_playwright gebruikt
voor alle QlikSense API communicatie. Dit zorgt voor een persistent browser
context waarbij authenticatie en sessie staat behouden blijft.

Author: QlikSense MCP Server Project
"""

import os
import json
import logging
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright


class QlikAuthenticationError(Exception):
    """Uitzondering voor authenticatie fouten"""
    pass


class QlikConnectionError(Exception):
    """Uitzondering voor verbindingsfouten"""
    pass


class BrowserQlikClient:
    """
    Browser-based QlikSense API Client met persistent browser context
    
    Deze klasse gebruikt sync_playwright voor alle QlikSense API communicatie.
    De browser context blijft persistent waardoor authenticatie en sessie staat
    behouden blijft voor alle API calls.
    
    Attributes:
        server_url (str): QlikSense server URL
        username (str): Gebruikersnaam voor authenticatie
        password (str): Wachtwoord voor authenticatie
        timeout (int): Request timeout in seconden
        max_retries (int): Maximum aantal herhalingen bij fouten
        playwright (Playwright): Playwright instance
        browser (Browser): Browser instance
        context (BrowserContext): Browser context
        page (Page): Browser page
        authenticated (bool): Authenticatie status
    """
    
    def __init__(self, server_url: Optional[str] = None, username: Optional[str] = None,
                 password: Optional[str] = None, timeout: int = 30, max_retries: int = 3):
        """
        Initialiseer BrowserQlikClient
        
        Args:
            server_url: QlikSense server URL (optioneel, gebruikt QLIK_SERVER env var)
            username: Gebruikersnaam (optioneel, gebruikt QLIK_USERNAME env var)
            password: Wachtwoord (optioneel, gebruikt QLIK_PASSWORD env var)
            timeout: Request timeout in seconden
            max_retries: Maximum aantal herhalingen bij fouten
            
        Raises:
            QlikConnectionError: Als vereiste configuratie ontbreekt
        """
        # Laad environment variabelen
        load_dotenv()
        
        # Configuratie laden
        self.server_url = server_url or os.getenv('QLIK_SERVER')
        self.username = username or os.getenv('QLIK_USERNAME')
        self.password = password or os.getenv('QLIK_PASSWORD')
        self.timeout = timeout * 1000  # Playwright gebruikt milliseconden
        self.max_retries = max_retries
        
        # Valideer vereiste configuratie
        if not self.server_url:
            raise QlikConnectionError("Server URL is vereist (QLIK_SERVER environment variabele)")
        if not self.username:
            raise QlikConnectionError("Gebruikersnaam is vereist (QLIK_USERNAME environment variabele)")
        if not self.password:
            raise QlikConnectionError("Wachtwoord is vereist (QLIK_PASSWORD environment variabele)")

        # Normaliseer server URL
        self.server_url = self.server_url.rstrip('/')
        
        # Initialiseer browser componenten
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.authenticated = False
        
        # SSL verificatie configuratie
        self.ssl_verify = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
        
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"BrowserQlikClient geïnitialiseerd voor server: {self.server_url}")

    def _start_browser(self):
        """Start browser en maak context aan"""
        if self.playwright is None:
            self.playwright = sync_playwright().start()
            
        if self.browser is None:
            # Launch browser met debugging mogelijkheden
            self.browser = self.playwright.chromium.launch(
                headless=False,  # Zichtbaar voor debugging
                args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
            )
            
        if self.context is None:
            # Maak browser context met HTTP credentials
            context_options = {
                'ignore_https_errors': not self.ssl_verify,
                'http_credentials': {
                    'username': self.username,
                    'password': self.password
                }
            }
            
            self.context = self.browser.new_context(**context_options)
            
        if self.page is None:
            self.page = self.context.new_page()
            
        self.logger.info("Browser context gestart")

    def authenticate(self) -> bool:
        """
        Voer browser-based authenticatie uit
        
        Navigeert naar QlikSense hub en voert authenticatie uit via browser.
        De browser context behoudt alle cookies en authenticatie staat.
        
        Returns:
            bool: True als authenticatie succesvol, False anders
            
        Raises:
            QlikAuthenticationError: Als authenticatie mislukt
            QlikConnectionError: Als verbinding mislukt
        """
        if self.authenticated:
            self.logger.info("Al geauthenticeerd, authenticatie overgeslagen")
            return True

        try:
            # Start browser indien nodig
            self._start_browser()
            
            # Navigeer naar hub voor authenticatie
            hub_url = f"{self.server_url}/hub"
            self.logger.info(f"Navigeren naar hub voor authenticatie: {hub_url}")
            
            # Ga naar hub pagina
            response = self.page.goto(hub_url, wait_until='domcontentloaded', timeout=self.timeout)
            
            if response and response.status >= 400:
                raise QlikConnectionError(f"HTTP fout bij laden hub: {response.status}")
            
            # Wacht even voor volledige pagina load
            time.sleep(2)
            
            # Controleer of we succesvol zijn ingelogd door te kijken naar de pagina titel of URL
            current_url = self.page.url
            page_title = self.page.title()
            
            self.logger.info(f"Huidige URL na navigatie: {current_url}")
            self.logger.info(f"Pagina titel: {page_title}")
            
            # Controleer voor sessie cookie
            cookies = self.context.cookies()
            session_cookie = None
            for cookie in cookies:
                if cookie['name'] == 'X-Qlik-Session':
                    session_cookie = cookie['value']
                    break
            
            if session_cookie:
                self.authenticated = True
                self.logger.info("Authenticatie succesvol, sessie cookie gevonden")
                return True
            else:
                # Mogelijk is er een login form, probeer automatisch in te loggen
                self.logger.info("Geen sessie cookie gevonden, probeer automatisch inloggen")
                
                # Zoek naar username/password velden en probeer in te loggen
                try:
                    # Verschillende mogelijke selectors voor login velden
                    username_selectors = [
                        'input[name="username"]',
                        'input[name="user"]', 
                        'input[type="text"]',
                        '#username',
                        '#user'
                    ]
                    
                    password_selectors = [
                        'input[name="password"]',
                        'input[type="password"]',
                        '#password'
                    ]
                    
                    username_field = None
                    password_field = None
                    
                    # Zoek username veld
                    for selector in username_selectors:
                        try:
                            if self.page.is_visible(selector, timeout=1000):
                                username_field = selector
                                break
                        except:
                            continue
                    
                    # Zoek password veld
                    for selector in password_selectors:
                        try:
                            if self.page.is_visible(selector, timeout=1000):
                                password_field = selector
                                break
                        except:
                            continue
                    
                    if username_field and password_field:
                        self.logger.info("Login velden gevonden, voer automatisch login uit")
                        
                        # Vul login gegevens in
                        self.page.fill(username_field, self.username)
                        self.page.fill(password_field, self.password)
                        
                        # Zoek en klik submit button
                        submit_selectors = [
                            'input[type="submit"]',
                            'button[type="submit"]',
                            'button:has-text("Login")',
                            'button:has-text("Sign in")',
                            'button:has-text("Log in")',
                            '.login-button',
                            '#login-button'
                        ]
                        
                        for selector in submit_selectors:
                            try:
                                if self.page.is_visible(selector, timeout=1000):
                                    self.page.click(selector)
                                    break
                            except:
                                continue
                        
                        # Wacht op navigatie na login
                        try:
                            self.page.wait_for_load_state('domcontentloaded', timeout=10000)
                        except:
                            pass
                        
                        # Controleer opnieuw voor sessie cookie
                        cookies = self.context.cookies()
                        for cookie in cookies:
                            if cookie['name'] == 'X-Qlik-Session':
                                session_cookie = cookie['value']
                                break
                        
                        if session_cookie:
                            self.authenticated = True
                            self.logger.info("Automatische login succesvol")
                            return True
                
                except Exception as e:
                    self.logger.warning(f"Automatische login mislukt: {str(e)}")
                
                # Als automatische login niet werkt, wacht op handmatige login
                self.logger.info("Wacht op handmatige login in browser...")
                print("Log in handmatig in de browser en druk op Enter om door te gaan...")
                input()
                
                # Controleer opnieuw voor sessie cookie na handmatige login
                cookies = self.context.cookies()
                for cookie in cookies:
                    if cookie['name'] == 'X-Qlik-Session':
                        session_cookie = cookie['value']
                        break
                
                if session_cookie:
                    self.authenticated = True
                    self.logger.info("Handmatige login succesvol")
                    return True
                else:
                    raise QlikAuthenticationError("Geen sessie cookie gevonden na login poging")
                    
        except Exception as e:
            if isinstance(e, (QlikAuthenticationError, QlikConnectionError)):
                raise
            else:
                raise QlikConnectionError(f"Onverwachte fout tijdens authenticatie: {str(e)}")

    def _make_api_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Voer API request uit via browser context
        
        Args:
            endpoint: API endpoint (zonder server URL)
            method: HTTP methode (GET, POST, etc.)
            data: Request data voor POST requests
            
        Returns:
            Dict[str, Any]: Response data
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        if not self.authenticated:
            raise QlikAuthenticationError("Niet geauthenticeerd, authenticatie vereist")
        
        if not self.page:
            raise QlikConnectionError("Browser pagina niet beschikbaar")
        
        url = f"{self.server_url}{endpoint}"
        
        # Retry mechanisme
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(f"API request poging {attempt + 1}/{self.max_retries} voor {endpoint}")
                
                # Gebruik browser's fetch API via page.evaluate
                fetch_script = f"""
                async () => {{
                    const response = await fetch('{url}', {{
                        method: '{method}',
                        headers: {{
                            'Content-Type': 'application/json',
                            'X-Qlik-User': '{self.username}'
                        }},
                        {f"body: JSON.stringify({json.dumps(data)})," if data and method != 'GET' else ""}
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}
                    
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {{
                        return await response.json();
                    }} else {{
                        return await response.text();
                    }}
                }}
                """
                
                result = self.page.evaluate(fetch_script)
                
                # Als result een string is, probeer JSON te parsen
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        # Als het geen JSON is, wrap in een dict
                        result = {'data': result}
                
                return result
                
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(f"API request mislukt, wacht {wait_time}s voor retry: {str(e)}")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"API request definitief mislukt na {self.max_retries} pogingen")
        
        # Bepaal exception type op basis van foutmelding
        error_msg = str(last_exception)
        if 'HTTP 401' in error_msg or 'HTTP 403' in error_msg:
            raise QlikAuthenticationError(f"Authenticatie fout voor {endpoint}: {error_msg}")
        else:
            raise QlikConnectionError(f"API request fout voor {endpoint} na {self.max_retries} pogingen: {error_msg}")

    def get_apps(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense apps op via browser context
        
        Returns:
            List[Dict[str, Any]]: Lijst van app informatie met relevante metadata
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info("Ophalen van beschikbare apps via browser")
        
        try:
            # QRS API endpoint voor apps
            apps_data = self._make_api_request('/qrs/app/full')
            
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
            
            self.logger.info(f"Succesvol {len(formatted_apps)} apps opgehaald via browser")
            return formatted_apps
            
        except Exception as e:
            if isinstance(e, (QlikAuthenticationError, QlikConnectionError)):
                raise
            else:
                self.logger.error(f"Fout bij ophalen apps via browser: {str(e)}")
                raise QlikConnectionError(f"Onverwachte fout bij ophalen apps: {str(e)}")

    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense taken op via browser context
        
        Returns:
            List[Dict[str, Any]]: Lijst van taak informatie met relevante metadata
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info("Ophalen van beschikbare taken via browser")
        
        try:
            # QRS API endpoint voor taken
            tasks_data = self._make_api_request('/qrs/task/full')
            
            # Format task data voor MCP tool (zelfde logica als originele client)
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
            
            self.logger.info(f"Succesvol {len(formatted_tasks)} taken opgehaald via browser")
            return formatted_tasks
            
        except Exception as e:
            if isinstance(e, (QlikAuthenticationError, QlikConnectionError)):
                raise
            else:
                self.logger.error(f"Fout bij ophalen taken via browser: {str(e)}")
                raise QlikConnectionError(f"Onverwachte fout bij ophalen taken: {str(e)}")

    def get_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Haal logs op van specifieke taak via browser context
        
        Args:
            task_id: ID van de taak waarvoor logs opgehaald moeten worden
            
        Returns:
            List[Dict[str, Any]]: Lijst van log entries met relevante metadata
            
        Raises:
            ValueError: Als task_id leeg of None is
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
        """
        self.logger.info(f"Ophalen van logs voor taak via browser: {task_id}")
        
        # Valideer input
        if not task_id or not task_id.strip():
            raise ValueError("Task ID is vereist en mag niet leeg zijn")
        
        task_id = task_id.strip()
        
        try:
            # QRS API endpoint voor execution results gefilterd op TaskId
            filter_param = f"TaskId eq '{task_id}'"
            endpoint = f"/qrs/executionresult?filter={filter_param}"
            
            self.logger.debug(f"Ophalen execution results via browser met endpoint: {endpoint}")
            
            execution_results = self._make_api_request(endpoint)
            
            self.logger.debug(f"Ontvangen {len(execution_results)} execution results voor taak {task_id}")
            
            # Format execution results voor MCP tool (zelfde logica als originele client)
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
            
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            if isinstance(e, (QlikAuthenticationError, QlikConnectionError)):
                raise
            else:
                self.logger.error(f"Fout bij ophalen logs voor taak {task_id}: {str(e)}")
                raise QlikConnectionError(f"Onverwachte fout bij ophalen logs voor taak {task_id}: {str(e)}")

    def is_authenticated(self) -> bool:
        """
        Controleer of client geauthenticeerd is
        
        Returns:
            bool: True als geauthenticeerd, False anders
        """
        return self.authenticated

    def close(self):
        """
        Sluit browser en alle gerelateerde resources
        """
        if self.page:
            self.page.close()
            self.page = None
            
        if self.context:
            self.context.close()
            self.context = None
            
        if self.browser:
            self.browser.close()
            self.browser = None
            
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
            
        self.authenticated = False
        self.logger.info("BrowserQlikClient gesloten")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Convenience functie voor eenvoudige client initialisatie
def create_browser_qlik_client(**kwargs) -> BrowserQlikClient:
    """
    Maak en authenticeer BrowserQlikClient
    
    Args:
        **kwargs: Argumenten voor BrowserQlikClient constructor
        
    Returns:
        BrowserQlikClient: Geauthenticeerde client instance
        
    Raises:
        QlikAuthenticationError: Als authenticatie mislukt
        QlikConnectionError: Als verbinding mislukt
    """
    client = BrowserQlikClient(**kwargs)
    client.authenticate()
    return client