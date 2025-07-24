"""
Simpele QlikSense client

"""

import requests
import urllib3
import websocket
import ssl
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class QlikClient:
    def __init__(self, server, username, session_id):
        self.server = server
        self.user = username
        self.session_id = session_id
        self.user_ID = username.split(";")[-1] if ";" in username else username
        
        # WebSocket URL voor eventuele toekomstige gebruik
        host = server.replace("https://", "").replace("http://", "")
        self.ws_url = f"wss://{host}/app"
        self.headers = [
            f"Cookie: X-Qlik-Session={session_id}",
            f"X-Qlik-User: {username}"
        ]
    
    def _get_headers(self, xrfkey="0123456789abcdef"):
        """Helper method to get standard headers for QRS API calls."""
        return {
            "X-Qlik-User": self.user,
            "X-Qlik-Xrfkey": xrfkey,
            "Cookie": f"X-Qlik-Session={self.session_id}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def list_apps(self) -> list:
        """Retrieve a list of available apps (IDs and names) from Qlik Sense."""
        xrfkey = "0123456789abcdef"  # Must be 16 characters
        url = f"{self.server}/qrs/app/full?xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

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

        headers = self._get_headers(xrfkey)

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
        url = f"{self.server}/qrs/executionresult/full?filter=task.id eq '{task_id}'&xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

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

    def get_app_script(self, app_id: str) -> str:
        """Retrieve the complete script of a specific QlikSense app."""
        ws = self._connect(app_id)
        # Open document and wait for OpenDoc response
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "OpenDoc",
            "handle": -1,
            "params": {"qDocName": app_id}
        }))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 1 and "result" in resp:
                handle = resp["result"]["qReturn"]["qHandle"]
                break
        # Request script and wait for response
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "GetScript",
            "handle": handle,
            "params": {}
        }))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 2 and "result" in resp:
                script = resp["result"].get("qScript", "")
                break
        ws.close()
        return script

    def get_app_metadata(self, app_id: str) -> dict:
        """Retrieve measures, dimensions and sheets from a specific app."""
        xrfkey = "0123456789abcdef"
        
        # Get measures
        measures_url = f"{self.server}/qrs/app/object/full?filter=app.id eq {app_id} and objectType eq 'measure'&xrfkey={xrfkey}"
        # Get dimensions  
        dimensions_url = f"{self.server}/qrs/app/object/full?filter=app.id eq {app_id} and objectType eq 'dimension'&xrfkey={xrfkey}"
        # Get sheets
        sheets_url = f"{self.server}/qrs/app/object/full?filter=app.id eq {app_id} and objectType eq 'sheet'&xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)
        
        metadata = {
            "measures": [],
            "dimensions": [],
            "sheets": []
        }

        try:
            # Fetch measures
            response = requests.get(measures_url, headers=headers, verify=False)
            if response.status_code == 200:
                measures = response.json()
                metadata["measures"] = [
                    {
                        "id": measure["id"],
                        "name": measure.get("name", ""),
                        "description": measure.get("description", ""),
                        "expression": measure.get("properties", {}).get("qMeasure", {}).get("qDef", "")
                    }
                    for measure in measures
                ]

            # Fetch dimensions
            response = requests.get(dimensions_url, headers=headers, verify=False)
            if response.status_code == 200:
                dimensions = response.json()
                metadata["dimensions"] = [
                    {
                        "id": dimension["id"],
                        "name": dimension.get("name", ""),
                        "description": dimension.get("description", ""),
                        "expression": dimension.get("properties", {}).get("qDim", {}).get("qFieldDefs", [])
                    }
                    for dimension in dimensions
                ]

            # Fetch sheets
            response = requests.get(sheets_url, headers=headers, verify=False)
            if response.status_code == 200:
                sheets = response.json()
                metadata["sheets"] = [
                    {
                        "id": sheet["id"],
                        "name": sheet.get("name", ""),
                        "description": sheet.get("description", ""),
                        "rank": sheet.get("properties", {}).get("rank", 0)
                    }
                    for sheet in sheets
                ]

        except Exception as e:
            raise Exception(f"Failed to fetch app metadata: {str(e)}")

        return metadata

    def update_app_script(self, app_id: str, new_script: str) -> bool:
        """Update the script of a specific QlikSense app and save it."""
        ws = self._connect(app_id)

        # Open the app document
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "OpenDoc",
            "handle": -1,
            "params": {"qDocName": app_id}
        }))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 1 and "result" in resp:
                handle = resp["result"]["qReturn"]["qHandle"]
                break

        # Set new script
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "SetScript",
            "handle": handle,
            "params": {"qScript": new_script}
        }))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 2:
                break

        # Save the app
        ws.send(json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "DoSave",
            "handle": handle,
            "params": {}
        }))
        while True:
            resp = json.loads(ws.recv())
            if resp.get("id") == 3:
                break

        ws.close()
        return True

    def get_app_variables(self, app_id: str) -> list:
        """Retrieve variables from a specific app."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/app/object/full?filter=app.id eq {app_id} and objectType eq 'variable'&xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch app variables: {response.status_code} {response.text}")
        
        variables = response.json()
        return [
            {
                "id": var["id"],
                "name": var.get("name", ""),
                "definition": var.get("properties", {}).get("qDefinition", ""),
                "description": var.get("description", "")
            }
            for var in variables
        ]

    def reload_app(self, app_id: str) -> dict:
        """Start a reload of a specific app."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/app/{app_id}/reload?xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

        response = requests.post(url, headers=headers, verify=False)

        if response.status_code not in [200, 201, 202]:
            raise Exception(f"Failed to reload app: {response.status_code} {response.text}")
        
        return {
            "success": True,
            "message": f"Reload started for app {app_id}",
            "app_id": app_id
        }

    def get_app_connections(self, app_id: str) -> list:
        """Retrieve data connections from a specific app."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/dataconnection/full?filter=app.id eq '{app_id}'&xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch app connections: {response.status_code} {response.text}")
        
        connections = response.json()
        return [
            {
                "id": conn["id"],
                "name": conn.get("name", ""),
                "connectionstring": conn.get("connectionstring", ""),
                "type": conn.get("type", ""),
                "username": conn.get("username", "")
            }
            for conn in connections
        ]

    def export_app(self, app_id: str) -> dict:
        """Export an app as QVF file."""
        xrfkey = "0123456789abcdef"
        url = f"{self.server}/qrs/app/{app_id}/export?xrfkey={xrfkey}"

        headers = self._get_headers(xrfkey)

        response = requests.post(url, headers=headers, verify=False)

        if response.status_code not in [200, 201, 202]:
            raise Exception(f"Failed to export app: {response.status_code} {response.text}")
        
        return {
            "success": True,
            "message": f"Export started for app {app_id}",
            "app_id": app_id,
            "download_url": f"{self.server}/qrs/download/app/{app_id}?xrfkey={xrfkey}"
        }

    def _connect(self, app_id: str):
        return websocket.create_connection(
            f"{self.ws_url}/{app_id}",
            header=self.headers,
            sslopt={"cert_reqs": ssl.CERT_NONE}
        )