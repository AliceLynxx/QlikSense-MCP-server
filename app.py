"""
QlikSense MCP Server Application

Dit is de hoofdmodule van de QlikSense MCP Server die een FastMCP server
opzet voor het aanbieden van QlikSense functionaliteit via het Model Context Protocol.

De server biedt een gestandaardiseerde interface voor MCP-compatibele tools
om QlikSense functionaliteit te benutten zoals het ophalen van apps, taken en logs.

Author: QlikSense MCP Server Project
"""

import os
import sys
import asyncio
import logging
from typing import Optional
from dotenv import load_dotenv

# MCP server imports
from mcp.server.fastmcp import FastMCP

# Local imports
from qlik_client import QlikClient, QlikAuthenticationError, QlikConnectionError


class QlikMCPServer:
    """
    QlikSense MCP Server klasse
    
    Deze klasse beheert de FastMCP server instantie en integreert
    QlikSense functionaliteit via de QlikClient.
    
    Attributes:
        app (FastMCP): FastMCP server instantie
        qlik_client (Optional[QlikClient]): QlikSense client instantie
        logger (logging.Logger): Logger instantie
    """
    
    def __init__(self):
        """Initialiseer QlikMCP Server"""
        # Laad environment variabelen
        load_dotenv()
        
        # Logging configuratie
        self._setup_logging()
        
        # FastMCP server initialisatie
        self.app = FastMCP("QlikSense MCP Server")
        
        # QlikClient instantie (wordt later geïnitialiseerd)
        self.qlik_client: Optional[QlikClient] = None
        
        self.logger.info("QlikMCP Server geïnitialiseerd")
    
    def _setup_logging(self):
        """Configureer logging voor de server"""
        # Log level uit environment variabele
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        # Logging configuratie
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                # Optioneel: file handler toevoegen
                # logging.FileHandler('qlik_mcp_server.log')
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Logging geconfigureerd op niveau: {log_level}")
    
    def _validate_configuration(self) -> bool:
        """
        Valideer vereiste configuratie
        
        Returns:
            bool: True als configuratie geldig is, False anders
        """
        required_vars = ['QLIK_SERVER', 'QLIK_USER']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.error(f"Ontbrekende environment variabelen: {', '.join(missing_vars)}")
            self.logger.error("Zorg ervoor dat .env bestand correct is geconfigureerd")
            return False
        
        self.logger.info("Configuratie validatie succesvol")
        return True
    
    async def _initialize_qlik_client(self) -> bool:
        """
        Initialiseer en authenticeer QlikClient
        
        Returns:
            bool: True als initialisatie succesvol, False anders
        """
        try:
            self.logger.info("Initialiseren van QlikClient...")
            
            # QlikClient instantie maken
            self.qlik_client = QlikClient()
            
            # Authenticatie uitvoeren
            if self.qlik_client.authenticate():
                self.logger.info("QlikClient succesvol geauthenticeerd")
                return True
            else:
                self.logger.error("QlikClient authenticatie mislukt")
                return False
                
        except QlikAuthenticationError as e:
            self.logger.error(f"QlikSense authenticatie fout: {str(e)}")
            return False
        except QlikConnectionError as e:
            self.logger.error(f"QlikSense verbinding fout: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Onverwachte fout bij QlikClient initialisatie: {str(e)}")
            return False
    
    async def startup(self):
        """
        Server startup routine
        
        Voert alle benodigde initialisatie stappen uit voordat
        de server beschikbaar wordt voor requests.
        """
        self.logger.info("Server startup gestart...")
        
        # Configuratie valideren
        if not self._validate_configuration():
            raise RuntimeError("Configuratie validatie mislukt")
        
        # QlikClient initialiseren
        if not await self._initialize_qlik_client():
            raise RuntimeError("QlikClient initialisatie mislukt")
        
        self.logger.info("Server startup voltooid")
    
    async def shutdown(self):
        """
        Server shutdown routine
        
        Voert cleanup uit bij het afsluiten van de server.
        """
        self.logger.info("Server shutdown gestart...")
        
        # QlikClient afsluiten
        if self.qlik_client:
            self.qlik_client.close()
            self.qlik_client = None
        
        self.logger.info("Server shutdown voltooid")
    
    def get_app(self) -> FastMCP:
        """
        Geef FastMCP app instantie terug
        
        Returns:
            FastMCP: Geconfigureerde FastMCP server instantie
        """
        return self.app


# Globale server instantie
server = QlikMCPServer()

# FastMCP app instantie voor externe toegang
app = server.get_app()


# Event handlers voor server lifecycle
@app.on_event("startup")
async def startup_event():
    """FastMCP startup event handler"""
    try:
        await server.startup()
    except Exception as e:
        logging.getLogger(__name__).error(f"Server startup fout: {str(e)}")
        # Re-raise om server startup te stoppen
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """FastMCP shutdown event handler"""
    try:
        await server.shutdown()
    except Exception as e:
        logging.getLogger(__name__).error(f"Server shutdown fout: {str(e)}")


async def main():
    """
    Hoofdfunctie voor het starten van de MCP server
    
    Deze functie is het entry point van de applicatie en start
    de FastMCP server met proper error handling.
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("QlikSense MCP Server wordt gestart...")
        
        # Server configuratie
        host = os.getenv('MCP_HOST', '127.0.0.1')
        port = int(os.getenv('MCP_PORT', '8000'))
        
        logger.info(f"Server wordt gestart op {host}:{port}")
        
        # FastMCP server starten
        # Note: In een echte implementatie zou hier uvicorn of een andere ASGI server gebruikt worden
        # Voor nu is dit een placeholder die de basis server structuur toont
        
        # Placeholder voor server start - dit wordt aangepast wanneer tools worden toegevoegd
        logger.info("Server gestart en klaar voor requests")
        logger.info("Druk Ctrl+C om de server te stoppen")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Server shutdown geïnitieerd door gebruiker")
            
    except Exception as e:
        logger.error(f"Fatale fout bij server start: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Entry point voor directe uitvoering
    
    Voert de main functie uit met proper asyncio event loop handling.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer gestopt door gebruiker")
    except Exception as e:
        print(f"Fatale fout: {str(e)}")
        sys.exit(1)