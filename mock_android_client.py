import asyncio
import json
import hashlib
import time
import websockets

async def mock_client():
    uri = "ws://localhost:8000/ws/agent?token=prod_token_xyz_2026"
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
                        await asyncio.sleep(1.5)
                        
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
                            "status": "VERIFIED",
                            "screen_fingerprint": fingerprint,
                            "observation": {
                                "foreground_package": "com.mock.app",
                                "visible_nodes": mock_nodes
                            }
                        }
                        
                        print(f"[SENDING RESULT] VERIFIED (Fingerprint: {fingerprint[:8]})")
                        await websocket.send(json.dumps(result))
                
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
