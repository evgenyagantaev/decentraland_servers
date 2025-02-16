import socket

def start_udp_server():
    # Create UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Bind socket to address and port
    server_address = ('0.0.0.0', 13731)
    server_socket.bind(server_address)
    
    # Set socket timeout to allow checking for KeyboardInterrupt
    server_socket.settimeout(1.0)
    
    print(f"UDP Server listening on {server_address[0]}:{server_address[1]}")
    
    try:
        while True:
            try:
                # Receive data (max 4096 bytes)
                data, client_address = server_socket.recvfrom(4096)
                
                # Decode and print received message
                message = data.decode('utf-8')
                print(f"Received from {client_address[0]}:{client_address[1]}: {message}")
            except socket.timeout:
                # Timeout occurred, continue to next iteration to check for KeyboardInterrupt
                continue
            
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    start_udp_server() 