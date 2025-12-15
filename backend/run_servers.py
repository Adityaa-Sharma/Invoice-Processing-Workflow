"""
Startup script to run MCP servers and Agent API.

This script starts the MCP servers (COMMON and ATLAS) first,
then starts the main Agent API server.

Usage:
    python run_servers.py
"""
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_port(port: int) -> bool:
    """Check if a port is available."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0


def wait_for_server(port: int, timeout: int = 30) -> bool:
    """Wait for a server to be available on a port."""
    import socket
    start_time = time.time()
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) == 0:
                return True
        time.sleep(0.5)
    return False


def main():
    """Start all servers."""
    print("=" * 60)
    print("Invoice Processing Workflow - Server Startup")
    print("=" * 60)
    
    processes = []
    
    try:
        # Check if ports are available
        ports = {"COMMON MCP": 8001, "ATLAS MCP": 8002, "Agent API": 8000}
        for name, port in ports.items():
            if not check_port(port):
                print(f"ERROR: Port {port} ({name}) is already in use!")
                print("Please free up the port and try again.")
                return 1
        
        # Start COMMON MCP Server
        print("\n[1/3] Starting COMMON MCP Server on port 8001...")
        common_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", 
             "src.mcp.common_server:app", 
             "--host", "0.0.0.0", 
             "--port", "8001"],
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append(("COMMON MCP", common_proc))
        
        if wait_for_server(8001, timeout=10):
            print("  ✓ COMMON MCP Server started successfully")
        else:
            print("  ✗ COMMON MCP Server failed to start")
            raise Exception("COMMON MCP Server startup failed")
        
        # Start ATLAS MCP Server
        print("\n[2/3] Starting ATLAS MCP Server on port 8002...")
        atlas_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", 
             "src.mcp.atlas_server:app", 
             "--host", "0.0.0.0", 
             "--port", "8002"],
            cwd=Path(__file__).parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        processes.append(("ATLAS MCP", atlas_proc))
        
        if wait_for_server(8002, timeout=10):
            print("  ✓ ATLAS MCP Server started successfully")
        else:
            print("  ✗ ATLAS MCP Server failed to start")
            raise Exception("ATLAS MCP Server startup failed")
        
        # Start Agent API
        print("\n[3/3] Starting Agent API on port 8000...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", 
             "src.main:app", 
             "--host", "0.0.0.0", 
             "--port", "8000",
             "--reload"],
            cwd=Path(__file__).parent,
        )
        processes.append(("Agent API", api_proc))
        
        if wait_for_server(8000, timeout=10):
            print("  ✓ Agent API started successfully")
        else:
            print("  ✗ Agent API failed to start")
            raise Exception("Agent API startup failed")
        
        print("\n" + "=" * 60)
        print("All servers started successfully!")
        print("=" * 60)
        print("\nEndpoints:")
        print("  • COMMON MCP Server: http://localhost:8001")
        print("  • ATLAS MCP Server:  http://localhost:8002")
        print("  • Agent API:         http://localhost:8000")
        print("  • API Docs:          http://localhost:8000/docs")
        print("\nPress Ctrl+C to stop all servers...")
        
        # Wait for API process
        api_proc.wait()
        
    except KeyboardInterrupt:
        print("\n\nShutting down servers...")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        # Cleanup all processes
        for name, proc in processes:
            if proc.poll() is None:
                print(f"  Stopping {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print("All servers stopped.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
