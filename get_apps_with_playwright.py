"""
QlikSense Playwright Authenticatie en API Demonstratie

Dit script demonstreert hoe Playwright gebruikt kan worden voor QlikSense authenticatie
en hoe de verkregen session_id gebruikt kan worden voor alle API calls via de QlikClient.
Het script toont de volledige workflow van authenticatie tot het ophalen van apps, taken en logs.

Author: QlikSense MCP Server Project
"""

import asyncio
import os
import json
from playwright.async_api import async_playwright
from qlik_client import QlikClient, QlikAuthenticationError, QlikConnectionError
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QlikPlaywrightAuth:
    """
    QlikSense Playwright Authenticatie Manager
    
    Deze klasse beheert de Playwright browser sessie voor QlikSense authenticatie
    en houdt de browser open voor hergebruik van de sessie cookie.
    """
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.session_id = None
        
        # Laad environment variabelen
        load_dotenv()
        self.server_url = os.getenv('QLIK_SERVER')
        self.username = os.getenv('QLIK_USER')
        
        if not self.server_url or not self.username:
            raise ValueError("QLIK_SERVER en QLIK_USER environment variabelen zijn vereist")
    
    async def start_browser(self):
        """Start Playwright browser en maak context aan"""
        logger.info("Starting Playwright browser...")
        
        playwright = await async_playwright().start()
        
        # Browser configuratie
        self.browser = await playwright.chromium.launch(
            headless=True,  # Zet op False voor debugging
            args=['--ignore-certificate-errors', '--ignore-ssl-errors']
        )
        
        # Context met SSL configuratie
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        
        self.page = await self.context.new_page()
        logger.info("Browser gestart en context aangemaakt")
    
    async def authenticate(self) -> str:
        """
        Voer QlikSense authenticatie uit via Playwright
        
        Returns:
            str: Session ID cookie waarde
            
        Raises:
            Exception: Als authenticatie mislukt
        """
        if not self.page:
            await self.start_browser()
        
        logger.info(f"Authenticatie voor gebruiker: {self.username}")
        
        try:
            # Navigeer naar QlikSense hub met X-Qlik-User header
            await self.page.set_extra_http_headers({
                'X-Qlik-User': self.username
            })
            
            hub_url = f"{self.server_url}/hub"
            logger.info(f"Navigeren naar: {hub_url}")
            
            # Navigeer naar hub pagina
            response = await self.page.goto(hub_url, wait_until='networkidle')
            
            if response.status != 200:
                raise Exception(f"Authenticatie mislukt, HTTP status: {response.status}")
            
            # Wacht tot pagina geladen is
            await self.page.wait_for_load_state('networkidle')
            
            # Haal session cookie op
            cookies = await self.context.cookies()
            session_cookie = None
            
            for cookie in cookies:
                if cookie['name'] == 'X-Qlik-Session':
                    session_cookie = cookie['value']
                    break
            
            if not session_cookie:
                raise Exception("Geen X-Qlik-Session cookie gevonden na authenticatie")
            
            self.session_id = session_cookie
            logger.info("Authenticatie succesvol, session_id verkregen")
            return session_cookie
            
        except Exception as e:
            logger.error(f"Authenticatie fout: {str(e)}")
            raise
    
    async def close(self):
        """Sluit browser sessie"""
        if self.browser:
            await self.browser.close()
            logger.info("Browser sessie gesloten")
    
    def get_session_id(self) -> str:
        """Haal huidige session_id op"""
        return self.session_id

async def demonstrate_qlik_functionality():
    """
    Demonstreer volledige QlikSense functionaliteit met Playwright authenticatie
    """
    auth_manager = None
    
    try:
        logger.info("=== QlikSense Playwright Authenticatie Demonstratie ===")
        
        # 1. Start authenticatie
        auth_manager = QlikPlaywrightAuth()
        session_id = await auth_manager.authenticate()
        
        logger.info(f"Session ID verkregen: {session_id[:20]}...")
        
        # 2. Maak QlikClient met session_id
        logger.info("\n=== QlikClient Initialisatie ===")
        qlik_client = QlikClient(session_id=session_id)
        logger.info("QlikClient geïnitialiseerd met session_id")
        
        # 3. Demonstreer apps ophalen
        logger.info("\n=== Apps Ophalen ===")
        try:
            apps = qlik_client.get_apps()
            logger.info(f"Aantal apps gevonden: {len(apps)}")
            
            # Toon eerste paar apps
            for i, app in enumerate(apps[:3]):
                logger.info(f"App {i+1}: {app['name']} (ID: {app['id']})")
                logger.info(f"  Eigenaar: {app['owner']}")
                logger.info(f"  Beschrijving: {app['description'][:100]}..." if app['description'] else "  Geen beschrijving")
                logger.info(f"  Laatst gewijzigd: {app['modified']}")
                
        except Exception as e:
            logger.error(f"Fout bij ophalen apps: {str(e)}")
        
        # 4. Demonstreer taken ophalen
        logger.info("\n=== Taken Ophalen ===")
        try:
            tasks = qlik_client.get_tasks()
            logger.info(f"Aantal taken gevonden: {len(tasks)}")
            
            # Toon eerste paar taken
            for i, task in enumerate(tasks[:3]):
                logger.info(f"Taak {i+1}: {task['name']} (ID: {task['id']})")
                logger.info(f"  Type: {task['type']}")
                logger.info(f"  Status: {task['status']}")
                logger.info(f"  Eigenaar: {task['owner']}")
                if task['app']:
                    logger.info(f"  Gekoppelde app: {task['app']['name']}")
                
                # Haal logs op voor deze taak
                if task['id']:
                    logger.info(f"\n--- Logs voor taak: {task['name']} ---")
                    try:
                        logs = qlik_client.get_logs(task['id'])
                        logger.info(f"Aantal log entries: {len(logs)}")
                        
                        # Toon laatste paar log entries
                        for j, log in enumerate(logs[:2]):
                            logger.info(f"  Log {j+1}: {log['status']} ({log['duration_formatted']})")
                            logger.info(f"    Start: {log['start_time']}")
                            if log['has_errors']:
                                logger.info(f"    Fouten: {len(log['error_messages'])}")
                                for error in log['error_messages'][:2]:
                                    logger.info(f"      - {error[:100]}...")
                    except Exception as e:
                        logger.error(f"Fout bij ophalen logs voor taak {task['id']}: {str(e)}")
                
                if i >= 2:  # Limiteer tot eerste 3 taken voor demo
                    break
                    
        except Exception as e:
            logger.error(f"Fout bij ophalen taken: {str(e)}")
        
        # 5. Test session persistentie
        logger.info("\n=== Session Persistentie Test ===")
        try:
            # Maak nieuwe client met dezelfde session_id
            new_client = QlikClient(session_id=session_id)
            apps_again = new_client.get_apps()
            logger.info(f"Session hergebruik succesvol - {len(apps_again)} apps opgehaald")
        except Exception as e:
            logger.error(f"Session hergebruik mislukt: {str(e)}")
        
        # 6. Demonstreer MCP tool simulatie
        logger.info("\n=== MCP Tool Simulatie ===")
        logger.info("Simulatie van MCP tool calls met session_id parameter:")
        
        # Simuleer list_apps_with_session tool
        logger.info("- list_apps_with_session(session_id)")
        try:
            mcp_apps = qlik_client.get_apps()
            logger.info(f"  Resultaat: {len(mcp_apps)} apps")
        except Exception as e:
            logger.error(f"  Fout: {str(e)}")
        
        # Simuleer list_tasks_with_session tool
        logger.info("- list_tasks_with_session(session_id)")
        try:
            mcp_tasks = qlik_client.get_tasks()
            logger.info(f"  Resultaat: {len(mcp_tasks)} taken")
        except Exception as e:
            logger.error(f"  Fout: {str(e)}")
        
        # Simuleer get_task_logs_with_session tool
        if tasks and len(tasks) > 0:
            first_task_id = tasks[0]['id']
            logger.info(f"- get_task_logs_with_session(session_id, '{first_task_id}')")
            try:
                mcp_logs = qlik_client.get_logs(first_task_id)
                logger.info(f"  Resultaat: {len(mcp_logs)} log entries")
            except Exception as e:
                logger.error(f"  Fout: {str(e)}")
        
        logger.info("\n=== Demonstratie Voltooid ===")
        logger.info("Alle functionaliteit succesvol getest met Playwright authenticatie")
        
    except Exception as e:
        logger.error(f"Demonstratie fout: {str(e)}")
        raise
    finally:
        # Sluit browser sessie
        if auth_manager:
            await auth_manager.close()

def demonstrate_session_usage():
    """
    Demonstreer hoe session_id gebruikt kan worden in synchrone context
    """
    logger.info("\n=== Synchrone Session Gebruik ===")
    
    # In een echte implementatie zou je de session_id opslaan en hergebruiken
    # Hier simuleren we het gebruik van een opgeslagen session_id
    
    # Voorbeeld van hoe MCP tools de session_id zouden gebruiken:
    example_session_id = "example_session_12345"
    
    logger.info("Voorbeeld MCP tool implementatie:")
    logger.info(f"def list_apps_with_session(session_id: str):")
    logger.info(f"    client = QlikClient(session_id=session_id)")
    logger.info(f"    return client.get_apps()")
    logger.info("")
    logger.info("Voordelen van deze aanpak:")
    logger.info("- Consistente authenticatie via Playwright")
    logger.info("- Herbruikbare session_id voor meerdere API calls")
    logger.info("- Geen username/password opslag nodig")
    logger.info("- Browser sessie kan open blijven voor langdurig gebruik")

async def main():
    """Hoofdfunctie voor demonstratie"""
    try:
        await demonstrate_qlik_functionality()
        demonstrate_session_usage()
    except KeyboardInterrupt:
        logger.info("Demonstratie onderbroken door gebruiker")
    except Exception as e:
        logger.error(f"Onverwachte fout: {str(e)}")

if __name__ == "__main__":
    # Voer demonstratie uit
    asyncio.run(main())