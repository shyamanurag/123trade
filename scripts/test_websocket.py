#!/usr/bin/env python3
"""
Test WebSocket connection to the deployed app
"""
import asyncio
import websockets
import json

async def test_websocket():
    """Test WebSocket connection"""
    uri = "wss://algoauto-9gx56.ondigitalocean.app/ws"
    
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected successfully!")
            
            # Wait for initial message
            message = await websocket.recv()
            print(f"Received: {message}")
            
            # Send a ping
            await websocket.send("ping")
            print("Sent: ping")
            
            # Wait for pong
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Send a test message
            test_msg = json.dumps({"type": "test", "data": "Hello WebSocket!"})
            await websocket.send(test_msg)
            print(f"Sent: {test_msg}")
            
            # Wait for echo
            echo = await websocket.recv()
            print(f"Received: {echo}")
            
            print("\n✅ WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"\n❌ WebSocket connection failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 