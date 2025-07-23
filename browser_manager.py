"""
Simpele browser manager voor QlikSense authenticatie
"""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

class BrowserManager:
    def __init__(self):
        self.server = os.getenv("QLIK_SERVER")
        self.username = os.getenv("QLIK_USERNAME") 
        self.password = os.getenv("QLIK_PASSWORD")
        
        if not all([self.server, self.username, self.password]):
            raise ValueError("QLIK_SERVER, QLIK_USERNAME en QLIK_PASSWORD environment variabelen zijn vereist")
    
    def get_session_id(self):
        """Start browser, authenticeer en haal session_id op"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # Context met http_credentials
            context = browser.new_context(
                http_credentials={
                    "username": self.username,
                    "password": self.password
                },
                ignore_https_errors=True
            )
            
            page = context.new_page()
            
            # Ga naar QlikSense
            page.goto(f"https://{self.server}/hub")
            
            # Wacht tot pagina geladen is
            page.wait_for_load_state("networkidle")
            
            # Haal session_id uit cookies
            cookies = context.cookies()
            session_id = None
            
            for cookie in cookies:
                if cookie["name"] == "X-Qlik-Session":
                    session_id = cookie["value"]
                    break
            
            browser.close()
            
            if not session_id:
                raise Exception("Kon geen session_id verkrijgen")
                
            return session_id