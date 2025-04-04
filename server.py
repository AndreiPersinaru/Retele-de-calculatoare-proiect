import json
import socket
import threading
import traceback
import os

class DebuggerServer:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.programs = {}
        self.breakpoints = {}
        self.clients = {}
        self.contexts = {}
        self.debugging = {}
        self.executing = set()
        self.paused = set()
        self.states = {}
        self.load_programs()

    def load_programs(self, folder="programs"):
        base_path = os.path.dirname(os.path.abspath(__file__))
        folder_path = os.path.join(base_path, folder)
        if not os.path.isdir(folder_path):
            print(f"[Server] Warning: Folder '{folder_path}' not found.")
            return
        for file in os.listdir(folder_path):
            if file.endswith(".txt"):
                name = os.path.splitext(file)[0]
                with open(os.path.join(folder_path, file)) as f:
                    self.programs[name] = f.read()
                print(f"[Server] Loaded '{name}'")

    def handle_client(self, conn, addr):
        print(f"[Server] Connected: {addr}")
        self.clients[addr] = conn
        try:
            while True:
                data = conn.recv(4096).decode().strip()
                if not data:
                    break
                print(f"[Server] From {addr}: {data}")
                resp = self.process_command(data, addr)
                print(f"[Server] To {addr}: {resp[:100]}{'...' if len(resp) > 100 else ''}")
                conn.sendall((resp + '\n').encode())
        except Exception:
            traceback.print_exc()
        finally:
            if addr in self.clients:
                del self.clients[addr]
            for program, user in list(self.debugging.items()):
                if user == addr:
                    del self.debugging[program]
                    if program in self.executing:
                        self.executing.discard(program)
                    if program in self.paused:
                        self.paused.discard(program)
            conn.close()

    def help_text(self):
        return "\n".join([
            "Available Commands:",
            "  help                               - Shows this help message.",
            "  list_programs                      - Lists all loaded program names.",
            "  list_breakpoints <program>         - Lists breakpoints for a program.",
            "  add_breakpoint <program> <line>    - Sets a breakpoint (not available during execution).",
            "  rmv_breakpoint <program> <line>    - Removes a breakpoint (not available during execution).",
            "  attach <program>                   - Attaches the debugger to a program.",
            "  detach                             - Detaches the debugger from the current program.",
            "  start                              - Starts or restarts execution from the beginning (requires attachment).",
            "  continue                           - Continues execution from a breakpoint (requires program to be paused).",
            "  get_var <var_name>                 - Gets the value of a variable in the current context (requires attachment).",
            "  set_var <var_name> <value>         - Sets the value of a variable in the current context (requires attachment).",
            "Client-side commands:",   
            "  disconnect                         - Disconnects from the server.",
            "  exit                               - Disconnects and exits the client."
        ])

    def process_command(self, cmd, addr):
        parts = cmd.split(maxsplit=1)
        if not parts:
            return 'Error: Invalid command.'
        name, args = parts[0].lower(), parts[1] if len(parts) > 1 else ""

        if name == 'help':
            return self.help_text()
        if name == 'list_programs':
            return f"Programs: {json.dumps(list(self.programs.keys()))}"
        if name == 'list_breakpoints':
            program = args
            if program not in self.breakpoints:
                return f"Error: Program '{program}' not found."
            breakpoints = sorted(self.breakpoints[program])
            return f"Breakpoints in '{program}': {json.dumps(breakpoints)}"

        if name == 'add_breakpoint':
            args = args.split()
            if len(args) != 2:
                return 'Error: Format add_breakpoint <program> <line>'
            program, line = args
            if program not in self.programs:
                return f"Error: Program '{program}' not found."
            if program in self.executing or program in self.paused:
                return f"Error: '{program}' is currently executing."
            try:
                self.breakpoints.setdefault(program, set()).add(int(line))
                return f"Breakpoint set at line {line} in '{program}'."
            except:
                return "Error: Line must be integer."

        if name == 'rmv_breakpoint':
            args = args.split()
            if len(args) != 2:
                return 'Error: Format rmv_breakpoint <program> <line>'
            program, line = args
            if program not in self.programs:
                return f"Error: Program '{program}' not found."
            if program in self.executing or program in self.paused:
                return f"Error: '{program}' is currently executing."
            try:
                self.breakpoints.setdefault(program, set()).discard(int(line))
                return f"Breakpoint removed from line {line} in '{program}'."
            except:
                return "Error: Line must be integer."

        if name == 'attach':
            program = args
            if not program or program not in self.programs:
                return f"Error: Program '{program}' not found."
            if program in self.debugging:
                return f"Error: '{program}' is already debugged."
            for p, a in self.debugging.items():
                if a == addr:
                    return f"Error: You are already debugging '{p}'."
            self.debugging[program] = addr
            if program not in self.states:
                self.contexts[program] = {}
                self.states[program] = (0, self.contexts[program])
            return f"Attached to '{program}'"

        if name == 'detach':
            for p, a in list(self.debugging.items()):
                if a == addr:
                    del self.debugging[p]
                    if p in self.executing:
                        self.executing.discard(p)
                    if p in self.paused:
                        self.paused.discard(p)
                    return f"Detached from '{p}'"
            return "Not attached."

        program = None
        for p, a in self.debugging.items():
            if a == addr:
                program = p
                break

        if not program:
            return f"Error: '{name}' needs attachment."

        if name == 'start':
            return self.run(program)
            
        if name == 'continue':
            if program not in self.paused:
                return f"Error: '{program}' is not paused at a breakpoint. Use 'start' first."
            return self.cont(program)

        if name == 'get_var':
            var = args
            ctx = self.contexts.get(program, {})
            if var in ctx:
                return f"{var} = {repr(ctx[var])}"
            return f"{var} not found."

        if name == 'set_var':
            parts = args.split(maxsplit=1)
            if len(parts) != 2:
                return "Error: Format set_var <name> <value>"
            var, val = parts
            try:
                val = eval(val, globals(), self.contexts[program])
                self.contexts[program][var] = val
                return f"{var} set to {repr(val)}"
            except Exception as e:
                return f"Error: {e}"

        return f"Error: Unknown command '{name}'"

    def run(self, program):
        self.executing.add(program)
        self.paused.discard(program)
        self.contexts[program] = {}
        self.states[program] = (0, self.contexts[program])
        return self.cont(program)

    def cont(self, program):
        if program not in self.states:
            return "Error: Start first."
        
        self.executing.add(program)
        self.paused.discard(program)
        
        lines = self.programs[program].splitlines()
        idx, ctx = self.states[program]
        try:
            while idx < len(lines):
                line = lines[idx].strip()
                idx += 1
                if not line or line.startswith('#'):
                    continue
                exec(line, globals(), ctx)
                if program in self.breakpoints and (idx + 1) in self.breakpoints[program]:
                    self.states[program] = (idx, ctx)
                    self.executing.discard(program)
                    self.paused.add(program)
                    return f"Breakpoint at line {idx + 1}: {lines[idx].strip() if idx < len(lines) else 'end of program'}"
            
            self.executing.discard(program)
            self.paused.discard(program)
            
            self.states[program] = (idx, ctx)
            vars = {k: repr(v) for k, v in ctx.items() if not k.startswith('__')}
            return f"Finished '{program}'. Vars: {vars}"
        except Exception as e:
            self.executing.discard(program)
            self.paused.discard(program)
            return f"Error on line {idx}: {e}"

    def start(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"[Server] Running on {self.host}:{self.port}")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[Server] Fatal: {e}")
        finally:
            s.close()

if __name__ == '__main__':
    DebuggerServer().start()