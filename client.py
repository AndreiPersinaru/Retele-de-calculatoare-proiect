import socket
import sys

class DebuggerClient:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        self.connected = False
        self.attached_program = None 

    def connect(self):
        if self.connected:
            print("[Client] Already connected.")
            return True
        print(f"[Client] Attempting connection to {self.host}:{self.port}...")
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10.0)
            self.sock.connect((self.host, self.port))
            self.connected = True
            print("[Client] Connection successful.")
            return True
        except socket.timeout:
            print(f"[Client] Error: Connection to {self.host}:{self.port} timed out.")
        except socket.error as e:
            print(f"[Client] Error: Connection failed - {e}")
        except Exception as e:
            print(f"[Client] Error: Unexpected connection error: {e}")
        self.sock = None
        self.connected = False
        return False

    def disconnect(self):
        if not self.connected:
            print("[Client] Not connected.")
            return
        print("[Client] Disconnecting...")
        try:
            if self.sock:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
            print("[Client] Disconnected successfully.")
        except socket.error as e:
            print(f"[Client] Error: Disconnection error: {e}")
        except Exception as e:
            print(f"[Client] Error: Unexpected disconnection error: {e}")
        finally:
            self.sock = None
            self.connected = False
            self.attached_program = None

    def send_command(self, cmd):
        if not self.connected or not self.sock:
            print("[Client] Error: Not connected. Use 'connect' first.")
            return
        
        cmd_parts = cmd.strip().split(maxsplit=1)
        cmd_name = cmd_parts[0].lower() if cmd_parts else ""
        
        try:
            if not cmd.endswith('\n'):
                cmd += '\n'
            self.sock.sendall(cmd.encode())

            response = []
            while True:
                try:
                    chunk = self.sock.recv(4096)
                    if not chunk:
                        print("[Client] Server closed connection.")
                        self.disconnect()
                        return
                    response.append(chunk)
                    if chunk.endswith(b'\n'):
                        break
                except socket.timeout:
                    print("[Client] Warning: Timeout waiting for response.")
                    return
                except socket.error as e:
                    print(f"[Client] Error: Receive error: {e}")
                    self.disconnect()
                    return

            response_text = b''.join(response).decode().strip()
            print(response_text)
            
            if cmd_name == "attach" and response_text.startswith("Attached to"):
                program_name = response_text.split("'")[1] if "'" in response_text else None
                self.attached_program = program_name
            elif cmd_name == "detach" and response_text.startswith("Detached from"):
                self.attached_program = None

        except (socket.error, BrokenPipeError, ConnectionResetError) as e:
            print(f"[Client] Error: Send error: {e}")
            self.disconnect()
        except Exception as e:
            print(f"[Client] Error: Unexpected send error: {e}")

    def interactive_mode(self):
        print("--- Debugger Client ---")
        print(f"Target: {self.host}:{self.port}")
        print("Type 'connect', 'help', 'exit'.")

        while True:
            try:
                if not self.connected:
                    prompt = "[Client] disconnected > "
                elif self.attached_program:
                    prompt = f"[Client] attached to '{self.attached_program}' > "
                else:
                    prompt = "[Client] connected > "
                
                cmd = input(prompt).strip()
                if not cmd:
                    continue
                low = cmd.lower()
                if low == 'connect':
                    self.connect()
                elif low == 'disconnect':
                    self.disconnect()
                elif low == 'exit':
                    print("[Client] Exiting...")
                    self.disconnect()
                    break
                elif low == 'help':
                    print("--- Client Help ---")
                    print("connect | help | exit") if not self.connected else self.send_command(cmd)
                else:
                    self.send_command(cmd)
            except EOFError:
                print("\n[Client] EOF. Exiting...")
                self.disconnect()
                break
            except KeyboardInterrupt:
                print("\n[Client] Interrupted. Exiting...")
                self.disconnect()
                break
            except Exception as e:
                print(f"\n[Client] Loop error: {e}")

if __name__ == '__main__':
    host = '127.0.0.1'
    port = 5000
    if len(sys.argv) == 3:
        host = sys.argv[1]
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"[Client Setup] Invalid port: {sys.argv[2]}. Using default port {port}.")
    elif len(sys.argv) != 1:
        print(f"Usage: python {sys.argv[0]} [host] [port]")
        sys.exit(1)

    DebuggerClient(host, port).interactive_mode()