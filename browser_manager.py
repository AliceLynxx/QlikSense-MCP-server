"""
Browser Manager voor QlikSense MCP Server

Deze module beheert de browser lifecycle voor de QlikSense MCP server.
Zorgt voor proper startup, shutdown en resource management van browser instances.
"""

import os
import logging
import threading
import time
from typing import Optional
from browser_qlik_client import BrowserQlikClient, QlikAuthenticationError, QlikConnectionError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserManager:
    """
    Browser lifecycle manager voor QlikSense client
    
    Deze klasse beheert de browser instanties en zorgt voor proper resource management,
    error handling en recovery van browser crashes.
    """
    
    def __init__(self):
        """
        Initialiseer BrowserManager
        """
        self._client: Optional[BrowserQlikClient] = None
        self._lock = threading.Lock()
        self._startup_time: Optional[float] = None
        self._health_check_interval = int(os.getenv("QLIK_HEALTH_CHECK_INTERVAL", "300"))  # 5 minutes
        self._max_retries = int(os.getenv("QLIK_MAX_RETRIES", "3"))
        self._retry_delay = int(os.getenv("QLIK_RETRY_DELAY", "5"))  # seconds
        
        logger.info("BrowserManager geïnitialiseerd")
    
    def start_browser(self) -> bool:
        """
        Start browser en authenticeer
        
        Returns:
            bool: True als browser succesvol gestart en geauthenticeerd
            
        Raises:
            Exception: Als browser start mislukt na alle retry pogingen
        """
        with self._lock:
            if self._client and self._client.is_authenticated():
                logger.info("Browser is al gestart en geauthenticeerd")
                return True
            
            logger.info("Starting browser...")
            
            for attempt in range(self._max_retries):
                try:
                    # Sluit bestaande client indien aanwezig
                    if self._client:
                        self._client.close()
                        self._client = None
                    
                    # Maak nieuwe client
                    self._client = BrowserQlikClient()
                    
                    # Authenticeer
                    if self._client.authenticate():
                        self._startup_time = time.time()
                        logger.info(f"Browser succesvol gestart en geauthenticeerd (poging {attempt + 1})")
                        return True
                    else:
                        logger.warning(f"Authenticatie mislukt (poging {attempt + 1})")
                        
                except QlikAuthenticationError as e:
                    logger.error(f"Authenticatie fout (poging {attempt + 1}): {str(e)}")
                    if attempt == self._max_retries - 1:
                        raise Exception(f"Authenticatie mislukt na {self._max_retries} pogingen: {str(e)}")
                        
                except QlikConnectionError as e:
                    logger.error(f"Verbinding fout (poging {attempt + 1}): {str(e)}")
                    if attempt == self._max_retries - 1:
                        raise Exception(f"Verbinding mislukt na {self._max_retries} pogingen: {str(e)}")
                        
                except Exception as e:
                    logger.error(f"Onverwachte fout bij browser start (poging {attempt + 1}): {str(e)}")
                    if attempt == self._max_retries - 1:
                        raise Exception(f"Browser start mislukt na {self._max_retries} pogingen: {str(e)}")
                
                # Cleanup bij mislukte poging
                if self._client:
                    try:
                        self._client.close()
                    except:
                        pass
                    self._client = None
                
                # Wacht voor retry
                if attempt < self._max_retries - 1:
                    logger.info(f"Wacht {self._retry_delay} seconden voor retry...")
                    time.sleep(self._retry_delay)
            
            return False
    
    def stop_browser(self):
        """
        Stop browser en cleanup resources
        """
        with self._lock:
            logger.info("Stopping browser...")
            
            if self._client:
                try:
                    self._client.close()
                    logger.info("Browser succesvol gestopt")
                except Exception as e:
                    logger.error(f"Fout bij stoppen browser: {str(e)}")
                finally:
                    self._client = None
                    self._startup_time = None
            else:
                logger.info("Browser was niet gestart")
    
    def get_client(self) -> BrowserQlikClient:
        """
        Krijg BrowserQlikClient instance
        
        Start browser automatisch indien nog niet gestart.
        
        Returns:
            BrowserQlikClient: Geauthenticeerde client instance
            
        Raises:
            Exception: Als client niet beschikbaar is of authenticatie mislukt
        """
        with self._lock:
            # Check of client beschikbaar en geauthenticeerd is
            if not self._client or not self._client.is_authenticated():
                logger.info("Client niet beschikbaar, start browser...")
                if not self.start_browser():
                    raise Exception("Kan browser niet starten of authenticeren")
            
            return self._client
    
    def is_browser_running(self) -> bool:
        """
        Check of browser actief is
        
        Returns:
            bool: True als browser actief en geauthenticeerd
        """
        with self._lock:
            return self._client is not None and self._client.is_authenticated()
    
    def get_browser_status(self) -> dict:
        """
        Krijg browser status informatie
        
        Returns:
            dict: Status informatie over browser
        """
        with self._lock:
            status = {
                'running': self.is_browser_running(),
                'startup_time': self._startup_time,
                'uptime_seconds': time.time() - self._startup_time if self._startup_time else 0,
                'client_available': self._client is not None,
                'authenticated': self._client.is_authenticated() if self._client else False
            }
            
            return status
    
    def health_check(self) -> bool:
        """
        Voer health check uit op browser
        
        Test of browser nog correct functioneert door een eenvoudige API call te doen.
        
        Returns:
            bool: True als browser gezond is, False anders
        """
        try:
            if not self.is_browser_running():
                logger.warning("Health check: Browser niet actief")
                return False
            
            # Test met eenvoudige API call
            client = self.get_client()
            
            # Probeer apps op te halen als health check
            apps = client.get_apps()
            
            logger.debug(f"Health check succesvol: {len(apps)} apps gevonden")
            return True
            
        except Exception as e:
            logger.error(f"Health check mislukt: {str(e)}")
            return False
    
    def restart_browser(self) -> bool:
        """
        Herstart browser
        
        Stop huidige browser en start nieuwe instance.
        
        Returns:
            bool: True als herstart succesvol
        """
        logger.info("Restarting browser...")
        
        try:
            self.stop_browser()
            time.sleep(2)  # Korte pauze voor cleanup
            return self.start_browser()
            
        except Exception as e:
            logger.error(f"Browser restart mislukt: {str(e)}")
            return False
    
    def auto_recovery(self) -> bool:
        """
        Automatische recovery bij browser problemen
        
        Probeert browser te herstellen bij crashes of authenticatie problemen.
        
        Returns:
            bool: True als recovery succesvol
        """
        logger.info("Starting auto recovery...")
        
        try:
            # Probeer eerst health check
            if self.health_check():
                logger.info("Auto recovery: Browser is gezond, geen actie nodig")
                return True
            
            # Health check mislukt, probeer restart
            logger.info("Auto recovery: Health check mislukt, probeer restart...")
            if self.restart_browser():
                logger.info("Auto recovery: Browser restart succesvol")
                return True
            
            logger.error("Auto recovery: Browser restart mislukt")
            return False
            
        except Exception as e:
            logger.error(f"Auto recovery mislukt: {str(e)}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_browser()

# Global browser manager instance
_browser_manager: Optional[BrowserManager] = None

def get_browser_manager() -> BrowserManager:
    """
    Krijg global BrowserManager instance
    
    Returns:
        BrowserManager: Singleton browser manager instance
    """
    global _browser_manager
    
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    
    return _browser_manager

def cleanup_browser_manager():
    """
    Cleanup global browser manager
    
    Wordt aangeroepen bij shutdown om resources op te ruimen.
    """
    global _browser_manager
    
    if _browser_manager:
        try:
            _browser_manager.stop_browser()
        except Exception as e:
            logger.error(f"Error during browser manager cleanup: {str(e)}")
        finally:
            _browser_manager = None

# Register cleanup functie voor graceful shutdown
import atexit
atexit.register(cleanup_browser_manager)