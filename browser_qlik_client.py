"""
Browser-based QlikSense Client

Deze module implementeert een browser-based client voor QlikSense API communicatie.
Gebruikt sync_playwright voor persistent browser context management en betrouwbare authenticatie.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QlikAuthenticationError(Exception):
    """Raised when QlikSense authentication fails"""
    pass

class QlikConnectionError(Exception):
    """Raised when QlikSense connection fails"""
    pass

class BrowserQlikClient:
    """
    Browser-based QlikSense client voor persistent API communicatie
    
    Deze client gebruikt sync_playwright om een persistent browser context te onderhouden
    voor alle QlikSense API calls. Dit zorgt voor betrouwbare authenticatie en sessie beheer.
    """
    
    def __init__(self):
        """
        Initialiseer BrowserQlikClient
        
        Configureert browser settings en laadt environment variabelen.
        """
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._authenticated = False
        
        # Load configuration from environment
        self.server = os.getenv("QLIK_SERVER")
        self.username = os.getenv("QLIK_USERNAME") 
        self.password = os.getenv("QLIK_PASSWORD")
        
        # Validate configuration
        if not self.server or not self.username or not self.password:
            raise ValueError("QLIK_SERVER, QLIK_USERNAME en QLIK_PASSWORD environment variabelen zijn vereist")
        
        # Ensure server URL format
        if not self.server.startswith(('http://', 'https://')):
            self.server = f"https://{self.server}"
        
        # Browser configuration
        self.browser_config = {
            'headless': os.getenv("QLIK_BROWSER_HEADLESS", "false").lower() == "true",
            'slow_mo': int(os.getenv("QLIK_BROWSER_SLOW_MO", "0")),
            'timeout': int(os.getenv("QLIK_BROWSER_TIMEOUT", "30000"))
        }
        
        logger.info(f"BrowserQlikClient geïnitialiseerd voor server: {self.server}")
    
    def _start_browser(self):
        """Start browser en context indien nog niet gestart"""
        if self.browser is None:
            logger.info("Starting browser...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=self.browser_config['headless'],
                slow_mo=self.browser_config['slow_mo']
            )
            
            # Create persistent context
            self.context = self.browser.new_context(
                ignore_https_errors=True,
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Set default timeout
            self.context.set_default_timeout(self.browser_config['timeout'])
            
            # Create page
            self.page = self.context.new_page()
            
            logger.info("Browser gestart en context aangemaakt")
    
    def authenticate(self) -> bool:
        """
        Authenticeer met QlikSense via browser login
        
        Voert browser-based login uit en houdt sessie persistent voor hergebruik.
        
        Returns:
            bool: True als authenticatie succesvol, False anders
            
        Raises:
            QlikAuthenticationError: Als authenticatie mislukt
            QlikConnectionError: Als verbinding met server mislukt
        """
        try:
            self._start_browser()
            
            logger.info(f"Authenticating with QlikSense server: {self.server}")
            
            # Navigate to QlikSense login page
            login_url = urljoin(self.server, "/hub")
            self.page.goto(login_url)
            
            # Wait for page to load
            self.page.wait_for_load_state("networkidle")
            
            # Check if already authenticated (redirect to hub)
            if "/hub" in self.page.url and "login" not in self.page.url.lower():
                logger.info("Already authenticated - session still valid")
                self._authenticated = True
                return True
            
            # Look for login form elements
            username_selector = 'input[name="username"], input[id="username"], input[type="text"]'
            password_selector = 'input[name="password"], input[id="password"], input[type="password"]'
            
            # Wait for login form
            try:
                self.page.wait_for_selector(username_selector, timeout=10000)
            except:
                # Check if we're already logged in
                if "/hub" in self.page.url:
                    logger.info("Already authenticated - no login form needed")
                    self._authenticated = True
                    return True
                else:
                    raise QlikConnectionError("Login form niet gevonden - controleer server URL")
            
            # Fill in credentials
            logger.info("Filling in login credentials...")
            self.page.fill(username_selector, self.username)
            self.page.fill(password_selector, self.password)
            
            # Submit form
            submit_selector = 'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Sign in")'
            self.page.click(submit_selector)
            
            # Wait for navigation after login
            try:
                self.page.wait_for_url("**/hub**", timeout=15000)
                logger.info("Login successful - redirected to hub")
                self._authenticated = True
                return True
            except:
                # Check for error messages
                error_selectors = [
                    '.error', '.alert-danger', '.login-error', 
                    '[class*="error"]', '[class*="invalid"]'
                ]
                
                error_message = "Unknown authentication error"
                for selector in error_selectors:
                    try:
                        error_element = self.page.query_selector(selector)
                        if error_element:
                            error_message = error_element.text_content().strip()
                            break
                    except:
                        continue
                
                raise QlikAuthenticationError(f"Login failed: {error_message}")
                
        except QlikAuthenticationError:
            raise
        except QlikConnectionError:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise QlikAuthenticationError(f"Unexpected authentication error: {str(e)}")
    
    def is_authenticated(self) -> bool:
        """
        Check of client geauthenticeerd is
        
        Returns:
            bool: True als geauthenticeerd en browser context actief
        """
        return self._authenticated and self.browser is not None and self.page is not None
    
    def _make_api_call(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Voer QRS API call uit via browser context
        
        Args:
            endpoint (str): API endpoint (bijv. "/qrs/app")
            method (str): HTTP method (GET, POST, etc.)
            data (Optional[Dict]): Request data voor POST/PUT calls
            
        Returns:
            Dict[str, Any]: API response data
            
        Raises:
            QlikConnectionError: Als API call mislukt
        """
        if not self.is_authenticated():
            raise QlikConnectionError("Not authenticated - call authenticate() first")
        
        # Construct full API URL
        api_url = urljoin(self.server, endpoint)
        
        # Add xrfkey parameter for QRS API
        xrf_key = "0123456789abcdef"
        separator = "&" if "?" in api_url else "?"
        api_url = f"{api_url}{separator}xrfkey={xrf_key}"
        
        logger.debug(f"Making API call: {method} {api_url}")
        
        try:
            # Prepare fetch options
            fetch_options = {
                'method': method,
                'headers': {
                    'X-Qlik-Xrfkey': xrf_key,
                    'Content-Type': 'application/json'
                }
            }
            
            if data and method in ['POST', 'PUT', 'PATCH']:
                fetch_options['body'] = json.dumps(data)
            
            # Execute API call via browser
            response = self.page.evaluate(f"""
                async (options) => {{
                    const response = await fetch('{api_url}', options);
                    const text = await response.text();
                    return {{
                        status: response.status,
                        statusText: response.statusText,
                        text: text,
                        ok: response.ok
                    }};
                }}
            """, fetch_options)
            
            if not response['ok']:
                raise QlikConnectionError(f"API call failed: {response['status']} {response['statusText']}")
            
            # Parse JSON response
            try:
                return json.loads(response['text']) if response['text'] else {}
            except json.JSONDecodeError:
                logger.warning(f"Non-JSON response from {endpoint}: {response['text'][:200]}")
                return {'raw_response': response['text']}
                
        except Exception as e:
            logger.error(f"API call failed for {endpoint}: {str(e)}")
            raise QlikConnectionError(f"API call failed: {str(e)}")
    
    def get_apps(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense apps op
        
        Returns:
            List[Dict[str, Any]]: Lijst van apps met metadata
            
        Raises:
            QlikConnectionError: Als API call mislukt
        """
        logger.info("Fetching QlikSense apps...")
        
        try:
            # Get apps from QRS API
            apps_data = self._make_api_call("/qrs/app/full")
            
            # Format app data
            formatted_apps = []
            for app in apps_data:
                formatted_app = {
                    'id': app.get('id', ''),
                    'name': app.get('name', 'Unknown'),
                    'description': app.get('description', ''),
                    'published': app.get('published', False),
                    'publishTime': app.get('publishTime', ''),
                    'lastReloadTime': app.get('lastReloadTime', ''),
                    'fileSize': app.get('fileSize', 0),
                    'owner': app.get('owner', {}).get('name', 'Unknown') if app.get('owner') else 'Unknown',
                    'stream': app.get('stream', {}).get('name', 'Personal') if app.get('stream') else 'Personal',
                    'tags': [tag.get('name', '') for tag in app.get('tags', [])],
                    'created': app.get('createdDate', ''),
                    'modified': app.get('modifiedDate', '')
                }
                formatted_apps.append(formatted_app)
            
            logger.info(f"Successfully fetched {len(formatted_apps)} apps")
            return formatted_apps
            
        except Exception as e:
            logger.error(f"Failed to fetch apps: {str(e)}")
            raise QlikConnectionError(f"Failed to fetch apps: {str(e)}")
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense taken op
        
        Returns:
            List[Dict[str, Any]]: Lijst van taken met metadata
            
        Raises:
            QlikConnectionError: Als API call mislukt
        """
        logger.info("Fetching QlikSense tasks...")
        
        try:
            # Get tasks from QRS API
            tasks_data = self._make_api_call("/qrs/task/full")
            
            # Format task data
            formatted_tasks = []
            for task in tasks_data:
                formatted_task = {
                    'id': task.get('id', ''),
                    'name': task.get('name', 'Unknown'),
                    'taskType': task.get('taskType', 'Unknown'),
                    'enabled': task.get('enabled', False),
                    'taskSessionTimeout': task.get('taskSessionTimeout', 0),
                    'maxRetries': task.get('maxRetries', 0),
                    'app': {
                        'id': task.get('app', {}).get('id', '') if task.get('app') else '',
                        'name': task.get('app', {}).get('name', '') if task.get('app') else ''
                    },
                    'isManuallyTriggered': task.get('isManuallyTriggered', False),
                    'isPartialReload': task.get('isPartialReload', False),
                    'created': task.get('createdDate', ''),
                    'modified': task.get('modifiedDate', ''),
                    'lastExecutionResult': task.get('lastExecutionResult', {}),
                    'nextExecution': task.get('nextExecution', ''),
                    'operational': task.get('operational', {})
                }
                formatted_tasks.append(formatted_task)
            
            logger.info(f"Successfully fetched {len(formatted_tasks)} tasks")
            return formatted_tasks
            
        except Exception as e:
            logger.error(f"Failed to fetch tasks: {str(e)}")
            raise QlikConnectionError(f"Failed to fetch tasks: {str(e)}")
    
    def get_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Haal logs op van specifieke taak
        
        Args:
            task_id (str): ID van de taak
            
        Returns:
            List[Dict[str, Any]]: Lijst van log entries
            
        Raises:
            QlikConnectionError: Als API call mislukt
        """
        logger.info(f"Fetching logs for task: {task_id}")
        
        try:
            # Get execution results for the task
            endpoint = f"/qrs/executionresult/full?filter=taskId eq {task_id}"
            logs_data = self._make_api_call(endpoint)
            
            # Format log data
            formatted_logs = []
            for log in logs_data:
                # Calculate duration
                start_time = log.get('startTime', '')
                stop_time = log.get('stopTime', '')
                duration_ms = 0
                duration_formatted = "Unknown"
                
                if start_time and stop_time:
                    try:
                        from datetime import datetime
                        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        stop_dt = datetime.fromisoformat(stop_time.replace('Z', '+00:00'))
                        duration_ms = int((stop_dt - start_dt).total_seconds() * 1000)
                        duration_formatted = f"{duration_ms/1000:.2f}s"
                    except:
                        pass
                
                # Extract script log and errors
                script_log = []
                error_messages = []
                details = log.get('details', [])
                
                for detail in details:
                    if detail.get('detailType') == 'ScriptLogEntry':
                        script_log.append({
                            'timestamp': detail.get('timestamp', ''),
                            'level': detail.get('level', ''),
                            'message': detail.get('message', '')
                        })
                    elif detail.get('detailType') == 'Error':
                        error_messages.append(detail.get('message', ''))
                
                formatted_log = {
                    'id': log.get('id', ''),
                    'task_id': task_id,
                    'task_name': log.get('taskName', 'Unknown'),
                    'status': log.get('status', 'Unknown'),
                    'start_time': start_time,
                    'stop_time': stop_time,
                    'duration_ms': duration_ms,
                    'duration_formatted': duration_formatted,
                    'script_log': script_log,
                    'error_messages': error_messages,
                    'has_errors': len(error_messages) > 0,
                    'created': log.get('createdDate', ''),
                    'modified': log.get('modifiedDate', '')
                }
                formatted_logs.append(formatted_log)
            
            # Sort by start time (newest first)
            formatted_logs.sort(key=lambda x: x.get('start_time', ''), reverse=True)
            
            logger.info(f"Successfully fetched {len(formatted_logs)} log entries for task {task_id}")
            return formatted_logs
            
        except Exception as e:
            logger.error(f"Failed to fetch logs for task {task_id}: {str(e)}")
            raise QlikConnectionError(f"Failed to fetch logs: {str(e)}")
    
    def close(self):
        """
        Sluit browser en cleanup resources
        """
        logger.info("Closing browser client...")
        
        try:
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
            
            self._authenticated = False
            logger.info("Browser client closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing browser client: {str(e)}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()