import asyncio
import pathlib
import ssl
import websockets

async def echo_handler(websocket):
    """Handle websocket connection - echo back received messages"""
    try:
        async for message in websocket:
            print(f"{message}")
            await websocket.send(message)
    except websockets.ConnectionClosed:
        pass

async def main():
    # SSL context creation
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Update these paths to your actual certificate files
    ssl_context.load_cert_chain(
        pathlib.Path("cert.pem"),
        keyfile=pathlib.Path("key.pem")
    )

    # Start websocket server (with SSL)
    async with websockets.serve(
        echo_handler, 
        "localhost", 
        1373,
        ssl=ssl_context  # Add SSL
    ):
        print("WS server started on ws://localhost:1373")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
