"""
QlikSense Apps Ophalen met Browser-based Client

Dit script demonstreert het gebruik van de nieuwe BrowserQlikClient
voor het ophalen van QlikSense apps via een persistent browser context.
"""

import os
from dotenv import load_dotenv
from browser_qlik_client import BrowserQlikClient, QlikAuthenticationError, QlikConnectionError

def main():
    """
    Hoofdfunctie voor het ophalen van QlikSense apps via browser context
    """
    load_dotenv()
    
    # Valideer environment variabelen
    qlik_server = os.getenv("QLIK_SERVER")
    qlik_username = os.getenv("QLIK_USERNAME")
    qlik_password = os.getenv("QLIK_PASSWORD")
    
    if not qlik_server:
        print("QLIK_SERVER environment variable not set.")
        return
    
    if not qlik_username:
        print("QLIK_USERNAME environment variable not set.")
        return
        
    if not qlik_password:
        print("QLIK_PASSWORD environment variable not set.")
        return

    print(f"Verbinden met QlikSense server: {qlik_server}")
    print(f"Gebruiker: {qlik_username}")
    
    # Maak browser client en haal apps op
    try:
        with BrowserQlikClient() as client:
            print("\\nAuthenticatie wordt uitgevoerd...")
            
            if client.authenticate():
                print("Authenticatie succesvol!")
                
                print("\\nOphalen van beschikbare apps...")
                apps = client.get_apps()
                
                if apps:
                    print(f"\\nSuccesvol {len(apps)} apps opgehaald:")
                    print("-" * 80)
                    
                    for app in apps:
                        print(f"Naam: {app['name']}")
                        print(f"ID: {app['id']}")
                        print(f"Eigenaar: {app['owner']}")
                        print(f"Beschrijving: {app['description'][:100]}..." if len(app['description']) > 100 else f"Beschrijving: {app['description']}")
                        print(f"Laatst gewijzigd: {app['modified']}")
                        print(f"Gepubliceerd: {'Ja' if app['published'] else 'Nee'}")
                        if app['stream']:
                            print(f"Stream: {app['stream']}")
                        if app['tags']:
                            print(f"Tags: {', '.join(app['tags'])}")
                        print("-" * 80)
                else:
                    print("Geen apps gevonden.")
                
                # Test ook taken ophalen
                print("\\nOphalen van beschikbare taken...")
                try:
                    tasks = client.get_tasks()
                    print(f"Succesvol {len(tasks)} taken opgehaald:")
                    
                    for task in tasks[:5]:  # Toon eerste 5 taken
                        print(f"- {task['name']} (ID: {task['id']}, Type: {task['type']}, Status: {task['status']})")
                        if task['app']:
                            print(f"  App: {task['app']['name']}")
                        
                except Exception as e:
                    print(f"Fout bij ophalen taken: {e}")
                
            else:
                print("Authenticatie mislukt!")
                
    except QlikAuthenticationError as e:
        print(f"Authenticatie fout: {e}")
    except QlikConnectionError as e:
        print(f"Verbinding fout: {e}")
    except Exception as e:
        print(f"Onverwachte fout: {e}")

if __name__ == "__main__":
    main()