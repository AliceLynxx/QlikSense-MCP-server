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
        Voer geauthenticeerde request uit
        
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
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            raise QlikConnectionError(f"Request fout voor {endpoint}: {str(e)}")
    
    def get_apps(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare QlikSense apps op
        
        Returns:
            List[Dict[str, Any]]: Lijst van app informatie
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
            
        Note:
            Deze methode is voorbereidend geïmplementeerd.
            Volledige implementatie volgt in volgende development stappen.
        """
        self.logger.info("Ophalen van beschikbare apps")
        
        # Placeholder implementatie - volledige implementatie volgt
        # In volgende stappen wordt dit uitgebreid met daadwerkelijke API calls
        try:
            # Voorbeeld endpoint - dit wordt aangepast op basis van daadwerkelijke QlikSense API
            response = self._make_authenticated_request('GET', '/qrs/app')
            return response.json()
        except Exception as e:
            self.logger.error(f"Fout bij ophalen apps: {str(e)}")
            # Voorlopig lege lijst teruggeven
            return []
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """
        Haal beschikbare taken op
        
        Returns:
            List[Dict[str, Any]]: Lijst van taak informatie
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
            
        Note:
            Deze methode is voorbereidend geïmplementeerd.
            Volledige implementatie volgt in volgende development stappen.
        """
        self.logger.info("Ophalen van beschikbare taken")
        
        # Placeholder implementatie - volledige implementatie volgt
        try:
            # Voorbeeld endpoint - dit wordt aangepast op basis van daadwerkelijke QlikSense API
            response = self._make_authenticated_request('GET', '/qrs/task')
            return response.json()
        except Exception as e:
            self.logger.error(f"Fout bij ophalen taken: {str(e)}")
            # Voorlopig lege lijst teruggeven
            return []
    
    def get_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        Haal logs op van specifieke taak
        
        Args:
            task_id: ID van de taak
            
        Returns:
            List[Dict[str, Any]]: Lijst van log entries
            
        Raises:
            QlikAuthenticationError: Als authenticatie vereist is
            QlikConnectionError: Als request mislukt
            
        Note:
            Deze methode is voorbereidend geïmplementeerd.
            Volledige implementatie volgt in volgende development stappen.
        """
        self.logger.info(f"Ophalen van logs voor taak: {task_id}")
        
        if not task_id:
            raise ValueError("Task ID is vereist")
        
        # Placeholder implementatie - volledige implementatie volgt
        try:
            # Voorbeeld endpoint - dit wordt aangepast op basis van daadwerkelijke QlikSense API
            response = self._make_authenticated_request('GET', f'/qrs/executionresult?filter=TaskId eq {task_id}')
            return response.json()
        except Exception as e:
            self.logger.error(f"Fout bij ophalen logs voor taak {task_id}: {str(e)}")
            # Voorlopig lege lijst teruggeven
            return []
    
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