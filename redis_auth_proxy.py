#!/usr/bin/env python3
"""
Redis Authentication Proxy
- Binds to randomized local port
- Requires high-entropy token for access
- Forwards to actual Redis on 127.0.0.1:6379
- Logs all connection attempts
- Zero-config: generates session token on startup
"""

import os
import sys
import socket
import threading
import secrets
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Configuration
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 0  # Random port

# Logging
LOG_DIR = Path(r"C:\Users\hirzi\OneDrive\Documents\Default Project\security_logs")
LOG_DIR.mkdir(exist_ok=True)
PROXY_LOG = LOG_DIR / "redis_proxy.jsonl"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("redis_proxy")


def log_connection(client_addr: str, token: str, allowed: bool, reason: str):
    """Log connection attempt."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client": f"{client_addr[0]}:{client_addr[1]}",
        "token_preview": f"{token[:8]}..." if len(token) > 8 else "****",
        "allowed": allowed,
        "reason": reason
    }
    with open(PROXY_LOG, 'a') as f:
        f.write(json.dumps(entry) + "\n")


class RedisAuthProxy:
    """TCP proxy with token-based authentication."""
    
    def __init__(self, proxy_port: int = 0):
        self.proxy_port = proxy_port
        self.session_token = secrets.token_hex(32)  # 256-bit token
        self.server_socket = None
        self.running = False
        self.connections = []
    
    def start(self):
        """Start the proxy server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((PROXY_HOST, self.proxy_port))
        self.server_socket.listen(5)
        
        actual_port = self.server_socket.getsockname()[1]
        self.running = True
        
        logger.info(f"Redis Auth Proxy started on {PROXY_HOST}:{actual_port}")
        logger.info(f"Session token: {self.session_token}")
        logger.info(f"Connect with: redis-cli -p {actual_port} -a {self.session_token}")
        
        # Write connection info to file
        info_path = LOG_DIR / "redis_proxy_info.json"
        with open(info_path, 'w') as f:
            json.dump({
                "host": PROXY_HOST,
                "port": actual_port,
                "token": self.session_token,
                "created": datetime.now(timezone.utc).isoformat()
            }, f, indent=2)
        
        return actual_port
    
    def handle_client(self, client_socket: socket.socket, client_addr):
        """Handle a client connection."""
        try:
            # Read initial data to check for AUTH command
            client_socket.settimeout(10.0)
            initial_data = client_socket.recv(4096)
            
            if not initial_data:
                client_socket.close()
                return
            
            # Check if it's an AUTH command
            data_str = initial_data.decode('utf-8', errors='ignore').strip()
            
            # Handle Redis RESP protocol (inline or RESP2)
            if data_str.upper().startswith('AUTH'):
                # Extract token from AUTH command
                parts = data_str.split()
                if len(parts) >= 2:
                    provided_token = parts[1].strip('"')
                else:
                    provided_token = ""
                
                if provided_token == self.session_token:
                    log_connection(client_addr, provided_token, True, "Valid token")
                    # Send OK response
                    client_socket.sendall(b"+OK\r\n")
                    
                    # Read remaining data and forward to Redis
                    self.forward_connection(client_socket, client_addr)
                else:
                    log_connection(client_addr, provided_token, False, "Invalid token")
                    client_socket.sendall(b"-ERR invalid password\r\n")
                    client_socket.close()
            else:
                # No AUTH command — reject
                log_connection(client_addr, "none", False, "No AUTH command")
                client_socket.sendall(b"-ERR no AUTH command\r\n")
                client_socket.close()
                
        except socket.timeout:
            log_connection(client_addr, "timeout", False, "Connection timeout")
            client_socket.close()
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
            client_socket.close()
    
    def forward_connection(self, client_socket: socket.socket, client_addr):
        """Forward data between client and Redis."""
        try:
            # Connect to actual Redis
            redis_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            redis_socket.connect((REDIS_HOST, REDIS_PORT))
            
            # Set up bidirectional forwarding
            def forward(src, dst, direction):
                try:
                    while True:
                        data = src.recv(4096)
                        if not data:
                            break
                        dst.sendall(data)
                except:
                    pass
                finally:
                    try:
                        src.close()
                    except:
                        pass
                    try:
                        dst.close()
                    except:
                        pass
            
            # Start forwarding threads
            t1 = threading.Thread(target=forward, args=(client_socket, redis_socket, "client->redis"))
            t2 = threading.Thread(target=forward, args=(redis_socket, client_socket, "redis->client"))
            
            t1.daemon = True
            t2.daemon = True
            
            t1.start()
            t2.start()
            
            # Wait for either thread to finish
            t1.join(timeout=300)  # 5 minute timeout
            t2.join(timeout=1)
            
        except Exception as e:
            logger.error(f"Forwarding error for {client_addr}: {e}")
            try:
                client_socket.close()
            except:
                pass
    
    def run(self):
        """Main server loop."""
        port = self.start()
        
        logger.info("Waiting for connections...")
        
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                logger.info(f"Connection from {client_addr}")
                
                # Handle each client in a new thread
                thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_addr)
                )
                thread.daemon = True
                thread.start()
                
            except KeyboardInterrupt:
                logger.info("Shutting down proxy...")
                self.running = False
            except Exception as e:
                logger.error(f"Accept error: {e}")
        
        self.server_socket.close()


def main():
    print("=" * 60)
    print("REDIS AUTHENTICATION PROXY")
    print("=" * 60)
    
    proxy = RedisAuthProxy()
    
    try:
        proxy.run()
    except KeyboardInterrupt:
        print("\nProxy stopped.")


if __name__ == "__main__":
    main()
