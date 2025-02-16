import socket
import time

def start_udp_client():
    # Create UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # Server address and port
    server_address = ('localhost', 13731)
    counter = 1
    
    try:
        while True:
            # Create message with counter
            message = f"test connection {counter}"
            
            # Send message
            client_socket.sendto(message.encode('utf-8'), server_address)
            print(f"Sent: {message}")
            
            # Increment counter and wait
            counter += 1
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    finally:
        client_socket.close()

if __name__ == "__main__":
    start_udp_client() 