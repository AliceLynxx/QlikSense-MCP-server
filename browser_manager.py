"""
Browser Manager Module

Dit module bevat utilities voor browser lifecycle management
en error handling voor de BrowserQlikClient.

Author: QlikSense MCP Server Project
"""

import logging
import time
from typing import Optional, Dict, Any
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


class BrowserManager:
    """
    Manager klasse voor browser lifecycle en error handling
    
    Deze klasse beheert de browser instantie, context en pagina's
    en biedt utilities voor error recovery en resource cleanup.
    """
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        """
        Initialiseer BrowserManager
        
        Args:
            headless: Of browser in headless mode moet draaien
            timeout: Default timeout voor browser operaties in milliseconden
        """
        self.headless = headless
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Browser componenten
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Status tracking
        self.is_started = False
        self.last_error: Optional[Exception] = None
        
    def start(self, context_options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Start browser en maak context aan
        
        Args:
            context_options: Opties voor browser context
            
        Returns:
            bool: True als succesvol gestart, False anders
        """
        try:
            if self.is_started:
                self.logger.info("Browser is al gestart")
                return True
                
            self.logger.info("Browser wordt gestart...")
            
            # Start Playwright
            self.playwright = sync_playwright().start()
            
            # Launch browser
            browser_args = ['--disable-web-security', '--disable-features=VizDisplayCompositor']
            if not self.headless:
                browser_args.extend(['--start-maximized'])
                
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            
            # Maak context
            default_context_options = {
                'ignore_https_errors': True,
                'viewport': {'width': 1920, 'height': 1080} if self.headless else None
            }
            
            if context_options:
                default_context_options.update(context_options)
                
            self.context = self.browser.new_context(**default_context_options)
            
            # Maak pagina
            self.page = self.context.new_page()
            
            # Stel timeouts in
            self.page.set_default_timeout(self.timeout)
            self.page.set_default_navigation_timeout(self.timeout)
            
            self.is_started = True
            self.logger.info("Browser succesvol gestart")
            return True
            
        except Exception as e:
            self.last_error = e
            self.logger.error(f"Fout bij starten browser: {str(e)}")
            self.cleanup()
            return False
    
    def restart(self, context_options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Herstart browser (cleanup en start opnieuw)
        
        Args:
            context_options: Opties voor browser context
            
        Returns:
            bool: True als succesvol herstart, False anders
        """
        self.logger.info("Browser wordt herstart...")
        self.cleanup()
        return self.start(context_options)
    
    def is_healthy(self) -> bool:
        """
        Controleer of browser nog gezond is
        
        Returns:
            bool: True als browser gezond is, False anders
        """
        try:
            if not self.is_started or not self.page:
                return False
                
            # Test browser door simpele operatie uit te voeren
            self.page.evaluate("() => document.title")
            return True
            
        except Exception as e:
            self.last_error = e
            self.logger.warning(f"Browser health check mislukt: {str(e)}")
            return False
    
    def recover_from_error(self, context_options: Optional[Dict[str, Any]] = None) -> bool:
        """
        Probeer te herstellen van browser fouten
        
        Args:
            context_options: Opties voor browser context
            
        Returns:
            bool: True als herstel succesvol, False anders
        """
        self.logger.info("Probeer te herstellen van browser fout...")
        
        # Probeer eerst health check
        if self.is_healthy():
            self.logger.info("Browser is al gezond, geen herstel nodig")
            return True
        
        # Probeer pagina te vervangen
        try:
            if self.context and not self.page:
                self.page = self.context.new_page()
                self.page.set_default_timeout(self.timeout)
                self.page.set_default_navigation_timeout(self.timeout)
                
                if self.is_healthy():
                    self.logger.info("Browser hersteld door nieuwe pagina")
                    return True
        except Exception as e:
            self.logger.warning(f"Kon geen nieuwe pagina maken: {str(e)}")
        
        # Probeer context te vervangen
        try:
            if self.browser and not self.context:
                default_context_options = {
                    'ignore_https_errors': True,
                    'viewport': {'width': 1920, 'height': 1080} if self.headless else None
                }
                
                if context_options:
                    default_context_options.update(context_options)
                    
                self.context = self.browser.new_context(**default_context_options)
                self.page = self.context.new_page()
                self.page.set_default_timeout(self.timeout)
                self.page.set_default_navigation_timeout(self.timeout)
                
                if self.is_healthy():
                    self.logger.info("Browser hersteld door nieuwe context")
                    return True
        except Exception as e:
            self.logger.warning(f"Kon geen nieuwe context maken: {str(e)}")
        
        # Als alles faalt, herstart volledig
        return self.restart(context_options)
    
    def execute_with_retry(self, operation, max_retries: int = 3, 
                          context_options: Optional[Dict[str, Any]] = None):
        """
        Voer operatie uit met retry mechanisme en error recovery
        
        Args:
            operation: Functie om uit te voeren (moet self.page als argument accepteren)
            max_retries: Maximum aantal herhalingen
            context_options: Opties voor browser context bij herstel
            
        Returns:
            Result van operatie
            
        Raises:
            Exception: Als operatie na alle retries nog steeds mislukt
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Zorg dat browser gestart is
                if not self.is_started:
                    if not self.start(context_options):
                        raise Exception("Kon browser niet starten")
                
                # Controleer browser health
                if not self.is_healthy():
                    if not self.recover_from_error(context_options):
                        raise Exception("Kon browser niet herstellen")
                
                # Voer operatie uit
                return operation(self.page)
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Operatie mislukt (poging {attempt + 1}/{max_retries + 1}): {str(e)}")
                
                if attempt < max_retries:
                    # Probeer te herstellen voor volgende poging
                    self.recover_from_error(context_options)
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        # Als alle pogingen mislukken
        raise Exception(f"Operatie mislukt na {max_retries + 1} pogingen: {str(last_exception)}")
    
    def cleanup(self):
        """
        Sluit alle browser resources
        """
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
                
            self.is_started = False
            self.logger.info("Browser resources opgeruimd")
            
        except Exception as e:
            self.logger.warning(f"Fout bij opruimen browser resources: {str(e)}")
    
    def get_cookies(self) -> list:
        """
        Haal alle cookies op van huidige context
        
        Returns:
            list: Lijst van cookies
        """
        if self.context:
            return self.context.cookies()
        return []
    
    def get_session_cookie(self, cookie_name: str = 'X-Qlik-Session') -> Optional[str]:
        """
        Haal specifieke sessie cookie op
        
        Args:
            cookie_name: Naam van de cookie
            
        Returns:
            Optional[str]: Cookie waarde of None als niet gevonden
        """
        cookies = self.get_cookies()
        for cookie in cookies:
            if cookie['name'] == cookie_name:
                return cookie['value']
        return None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# Utility functies
def create_browser_manager(headless: bool = False, timeout: int = 30000, 
                          context_options: Optional[Dict[str, Any]] = None) -> BrowserManager:
    """
    Maak en start BrowserManager
    
    Args:
        headless: Of browser in headless mode moet draaien
        timeout: Default timeout in milliseconden
        context_options: Opties voor browser context
        
    Returns:
        BrowserManager: Gestart browser manager
        
    Raises:
        Exception: Als browser niet gestart kan worden
    """
    manager = BrowserManager(headless=headless, timeout=timeout)
    if not manager.start(context_options):
        raise Exception("Kon browser manager niet starten")
    return manager