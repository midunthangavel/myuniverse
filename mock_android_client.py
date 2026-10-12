import os
import asyncio
import json
import hashlib
import time
import websockets

async def mock_client():
    token = os.getenv("DEVICE_TOKEN", "dev_token_nexus_01")
    uri = f"ws://localhost:8000/ws/agent?token={token}"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Mock Android device is ready.")
            
            while True:
                try:
                    message = await websocket.recv()
                    payload = json.loads(message)
                    
                    if payload.get("type") == "COMMAND":
                        command_id = payload.get("command_id")
                        task_id = payload.get("task_id")
                        sequence = payload.get("sequence", 0)
                        action = payload.get("action", {})
                        
                        print(f"\n[RECEIVED COMMAND] {action}")
                        
                        # Simulate physical gesture and UI transition delay
                        await asyncio.sleep(0.3)
                        
                        # Generate a mock screen observation based on the action
                        action_name = action.get("action_type", "OBSERVE")
                        target = action.get("target") or action.get("resource_id") or action.get("name")
                        
                        mock_nodes = [
                            {"id": "com.mock.app:id/title", "text": "Mock Calculator", "desc": "", "bounds": [0,0,1080,200]}
                        ]
                        
                        if action_name == "TYPE":
                            mock_nodes.append({"id": target or "com.mock.app:id/input", "text": action.get("value", ""), "desc": "", "bounds": [100,100,500,200]})
                        elif action_name == "TAP":
                            mock_nodes.append({"id": target or "com.mock.app:id/btn", "text": "Tapped Button", "desc": "", "bounds": [100,100,500,200]})
                            
                        # Compute SHA-256 fingerprint matching the Kotlin implementation
                        sb = "com.mock.app|"
                        for n in mock_nodes:
                            sb += f"{n.get('id', '')}:{n.get('text', '')}:{n.get('desc', '')}::true:[0,0][0,0];"
                        fingerprint = hashlib.sha256(sb.encode()).hexdigest()
                        
                        result = {
                            "type": "COMMAND_RESULT",
                            "command_id": command_id,
                            "task_id": task_id,
                            "sequence": sequence,
                            "status": "DISPATCHED",
                            "execution_status": "DISPATCHED",
                            "screen_fingerprint": fingerprint,
                            "observation": {
                                "foreground_package": "com.mock.app",
                                "visible_nodes": mock_nodes
                            }
                        }
                        
                        print(f"[SENDING RESULT] DISPATCHED (Fingerprint: {fingerprint[:8]})")
                        await websocket.send(json.dumps(result))

                    elif payload.get("type") in ("HIGH_RISK_PROMPT", "FINANCIAL_AUTH_REQUIRED"):
                        task_id = payload.get("task_id") or payload.get("plan", {}).get("task_id")
                        token = payload.get("token") or payload.get("plan", {}).get("token")
                        amount = payload.get("amount") or payload.get("plan", {}).get("amount", "$0.00")
                        print(f"\n[RECEIVED HIGH_RISK_PROMPT] Task: {task_id}, Token: {token}")
                        # Simulate physical biometric fingerprint authorization
                        await asyncio.sleep(0.1)
                        auth_result = {
                            "type": "BIOMETRIC_AUTH_RESULT",
                            "task_id": task_id,
                            "token": token,
                            "status": "APPROVED",
                            "amount": amount,
                            "action": "Authorized Transaction",
                            "signature": "mock_biometric_signature_approved"
                        }
                        await websocket.send(json.dumps(auth_result))
                        print(f"[SENT BIOMETRIC_AUTH_RESULT] APPROVED for Task {task_id}")
                
                except websockets.exceptions.ConnectionClosed:
                    print("Server closed connection.")
                    break
                except Exception as e:
                    print(f"Error handling message: {e}")
                    break
                    
    except ConnectionRefusedError:
        print("ERROR: Connection Refused. Is the backend running on port 8000?")
    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(mock_client())
