"""
Simpele QlikSense client

"""

import requests
import urllib3
import websocket
import ssl

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class QlikClient:
    def __init__(self, server, username, session_id):
        self.server = server
        self.user = username
        self.session_id = session_id
        self.user_ID = username.split(";")[-1] if ";" in username else username
        
        # WebSocket URL voor eventuele toekomstige gebruik
        self.ws_url = f"wss://{server}/app"
        self.headers = [
            f"Cookie: X-Qlik-Session={session_id}",
            f"X-Qlik-User: {username}"
        ]
    
    def list_apps(self) -> list:
        """Retrieve a list of available apps (IDs and names) from Qlik Sense."""
        xrfkey = "0123456789abcdef"  # Must be 16 characters
        url = f"{self.server}/qrs/app/full?xrfkey={xrfkey}"

        headers = {
            "X-Qlik-User": self.user,
            "X-Qlik-Xrfkey": xrfkey,
            "Cookie": f"X-Qlik-Session={self.session_id}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch apps: {response.status_code} {response.text}")
        
        # Filter for apps owned by the current user and not published
        apps = response.json()
        user_identifier = self.user.split(";")[-1]  # e.g. UserId=sa_repository -> 'sa_repository'
        
        personal_apps = [
            {"id": app["id"], "name": app["name"]}
            for app in apps
            if app.get("published") is False and app.get("owner", {}).get("userId", "")==self.user_ID.lower()
        ]
        
        return personal_apps
    
    def list_tasks(self) -> list:
        """Retrieve a list of available tasks from Qlik Sense."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/task/full?xrfkey={xrfkey}"

        headers = {
            "X-Qlik-User": self.user,
            "X-Qlik-Xrfkey": xrfkey,
            "Cookie": f"X-Qlik-Session={self.session_id}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch tasks: {response.status_code} {response.text}")
        
        tasks = response.json()
        return [
            {
                "id": task["id"], 
                "name": task["name"],
                "taskType": task.get("taskType", "Unknown"),
                "enabled": task.get("enabled", False)
            } 
            for task in tasks
        ]
    
    def get_task_logs(self, task_id: str) -> list:
        """Retrieve logs for a specific task."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/executionresult/full?filter=executionId eq '{task_id}'&xrfkey={xrfkey}"

        headers = {
            "X-Qlik-User": self.user,
            "X-Qlik-Xrfkey": xrfkey,
            "Cookie": f"X-Qlik-Session={self.session_id}",
            "Accept": "application/json"
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch task logs: {response.status_code} {response.text}")
        
        logs = response.json()
        return [
            {
                "id": log["id"],
                "status": log.get("status", "Unknown"),
                "startTime": log.get("startTime", ""),
                "stopTime": log.get("stopTime", ""),
                "details": log.get("details", [])
            }
            for log in logs
        ]

    def _connect(self):
        return websocket.create_connection(
            self.ws_url,
            header=self.headers,
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )
