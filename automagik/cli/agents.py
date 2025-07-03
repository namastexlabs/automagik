"""
Automagik Agents CLI commands.
This module contains all commands related to the Automagik Agents component.
"""
import typer
import os
import subprocess
import signal
import time
import requests
from typing import Optional
from pathlib import Path

# Import existing command modules
from automagik.cli.db import db_app
from automagik.cli.agent import agent_app
from automagik.cli.mcp import mcp_app

# Create the agents command group
agents_app = typer.Typer(
    help="Automagik Agents - AI agent framework with memory, tools, and API",
    no_args_is_help=True
)

# Add existing subcommands
agents_app.add_typer(db_app, name="db", help="Database management commands")
agents_app.add_typer(agent_app, name="agent", help="Agent management and interaction commands")
agents_app.add_typer(mcp_app, name="mcp", help="MCP server management commands")

# === DEPLOYMENT MODE DETECTION ===

def detect_deployment_mode() -> tuple[str, str]:
    """
    Detect how automagik-agents is currently deployed.
    Returns: tuple of (mode, environment) where:
    - mode: 'service', 'docker', or 'process' 
    - environment: 'production', 'development', or None
    """
    
    # Check for systemd service first
    try:
        result = subprocess.run(
            ["systemctl", "list-unit-files", "automagik-agents.service"],
            capture_output=True, text=True, check=False
        )
        if "automagik-agents.service" in result.stdout:
            return "service", None
    except FileNotFoundError:
        pass
    
    # Check for Docker containers
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=automagik"],
            capture_output=True, text=True, check=False
        )
        if "automagik" in result.stdout:
            # Determine if it's production or development based on container names and .env
            env_mode = get_env_mode()
            return "docker", env_mode
    except FileNotFoundError:
        pass
    
    return "process", None  # Default to process mode

def get_env_mode() -> str:
    """Get the environment mode from .env file."""
    try:
        project_root = get_project_root()
        env_file = project_root / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.strip().startswith('ENVIRONMENT='):
                        value = line.split('=', 1)[1].strip().strip('"').strip("'")
                        return value
    except Exception:
        pass
    return "development"  # Default

def get_docker_config(env_mode: str) -> tuple[str, str]:
    """Get Docker compose file and container name based on environment."""
    if env_mode == "production":
        return "docker-compose-prod.yml", "automagik-agents-prod"
    else:
        return "docker-compose.yml", "automagik_agents"

def get_docker_compose_cmd() -> str:
    """Get the appropriate docker compose command (v1 or v2)."""
    try:
        if subprocess.run(["docker", "compose", "version"], 
                         capture_output=True, check=False).returncode == 0:
            return "docker compose"
    except FileNotFoundError:
        pass
    
    try:
        if subprocess.run(["docker-compose", "version"], 
                         capture_output=True, check=False).returncode == 0:
            return "docker-compose"
    except FileNotFoundError:
        pass
    
    return "docker compose"  # Default

def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from current file and go up to find project root
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "pyproject.toml").exists() or (current / ".env").exists():
            return current
        current = current.parent
    return Path.cwd()

def get_effective_port() -> int:
    """Get the effective port from settings or environment."""
    try:
        from automagik.config import settings
        return settings.AUTOMAGIK_API_PORT
    except Exception:
        # Fallback: try to read from .env file
        env_file = get_project_root() / ".env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('AUTOMAGIK_API_PORT='):
                        try:
                            return int(line.split('=')[1].strip().strip('"\''))
                        except ValueError:
                            pass
        return 8881  # Default port

# === PROCESS MANAGEMENT UTILITIES ===

def kill_process_on_port(port: int) -> bool:
    """Kill any process running on the specified port."""
    try:
        # Find process using the port (works on Linux/macOS)
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"], 
            capture_output=True, 
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            killed_any = False
            
            for pid in pids:
                try:
                    pid_int = int(pid)
                    typer.echo(f"🔪 Terminating process {pid_int} on port {port}")
                    os.kill(pid_int, signal.SIGTERM)
                    killed_any = True
                    
                    # Wait a bit, then force kill if still running
                    time.sleep(2)
                    try:
                        os.kill(pid_int, 0)  # Check if still running
                        typer.echo(f"🔪 Force killing process {pid_int}")
                        os.kill(pid_int, signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Process already terminated
                        
                except (ValueError, ProcessLookupError):
                    continue
                    
            return killed_any
        else:
            typer.echo(f"ℹ️  No process found on port {port}")
            return False
            
    except FileNotFoundError:
        # lsof not available, try alternative methods
        typer.echo(f"⚠️  lsof not available, cannot clean port {port}")
        return False
    except Exception as e:
        typer.echo(f"⚠️  Could not clean port {port}: {e}")
        return False

def write_pid_file(pid: int):
    """Write PID to file for process tracking."""
    pid_file = Path.home() / ".automagik" / "agents.pid"
    pid_file.parent.mkdir(exist_ok=True)
    pid_file.write_text(str(pid))

def read_pid_file() -> Optional[int]:
    """Read PID from file."""
    pid_file = Path.home() / ".automagik" / "agents.pid"
    if pid_file.exists():
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, FileNotFoundError):
            return None
    return None

def check_process_status():
    """Check process status in process mode."""
    port = get_effective_port()
    
    # First try to check via PID file
    pid = read_pid_file()
    if pid:
        try:
            os.kill(pid, 0)  # Check if process exists
            typer.echo(f"✅ Process running (PID: {pid})")
        except ProcessLookupError:
            typer.echo("❌ Process not running (stale PID file)")
            return False
    
    # Also check via port
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=3)
        if response.status_code == 200:
            typer.echo(f"✅ API responding on port {port}")
            return True
        else:
            typer.echo(f"⚠️  API responded with status: {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        typer.echo(f"❌ No API response on port {port}")
        return False

def show_process_logs(follow: bool = False):
    """Show process logs in process mode."""
    log_dir = get_project_root() / "logs"
    
    if not log_dir.exists():
        typer.echo("📋 No log directory found. Logs may be written to stdout/stderr.")
        return
    
    # Look for recent log files
    log_files = list(log_dir.glob("*.log"))
    if not log_files:
        typer.echo("📋 No log files found in logs directory.")
        return
    
    # Get the most recent log file
    latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
    typer.echo(f"📋 Showing logs from: {latest_log}")
    
    try:
        if follow:
            subprocess.run(["tail", "-f", str(latest_log)])
        else:
            subprocess.run(["tail", "-50", str(latest_log)])
    except FileNotFoundError:
        typer.echo("⚠️  'tail' command not available. Showing file content:")
        typer.echo(latest_log.read_text())

# Add direct commands from agent subcommand for convenience
@agents_app.command("create")
def create_agent_command(
    name: str = typer.Option(..., "--name", "-n", help="Name of the new agent to create"),
    template: str = typer.Option("simple", "--template", "-t", help="Template folder to use as base"),
    category: str = typer.Option("simple", "--category", "-c", help="Category folder to use")
):
    """Create a new agent by cloning an existing agent template."""
    from automagik.cli.agent.create import create_agent
    create_agent(name=name, category=category, template=template)

@agents_app.command("run")
def run_agent_command(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to use"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use/create"),
    user: int = typer.Option(1, "--user", "-u", help="User ID to use"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Message to send"),
    model: Optional[str] = typer.Option(None, "--model", help="Model to use (overrides agent's default)"),
):
    """Run a single message through an agent."""
    from automagik.cli.agent.run import message
    message(agent=agent, session=session, user=user, message=message, model=model)

@agents_app.command("chat")
def chat_agent_command(
    agent: str = typer.Option(..., "--agent", "-a", help="Agent to chat with"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Session name to use/create"),
    user: Optional[str] = typer.Option(None, "--user", "-u", help="User ID (UUID) to use"),
):
    """Start an interactive chat session with an agent."""
    from automagik.cli.agent.chat import start
    start(agent=agent, session=session, user=user)

# New server management commands
@agents_app.command("start")
def start_server(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True)
):
    """Start the Automagik Agents server."""
    mode, env_mode = detect_deployment_mode()
    typer.echo(f"🚀 Starting automagik agents (mode: {mode})...")
    
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
    
    if mode == "service":
        # Service mode: use systemctl start
        try:
            subprocess.run(["sudo", "systemctl", "start", "automagik-agents"], 
                                 capture_output=True, text=True, check=True)
            typer.echo("✅ Service started successfully")
            
            # Give it a moment to start up
            time.sleep(3)
            
            # Check if it started properly
            status_result = subprocess.run(["systemctl", "is-active", "automagik-agents"], 
                                        capture_output=True, text=True, check=False)
            if status_result.returncode == 0:
                typer.echo("✅ Service is running and healthy")
            else:
                typer.echo("⚠️  Service started but may not be fully ready yet")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start service: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    elif mode == "docker":
        # Docker mode: start the container
        try:
            docker_compose = get_docker_compose_cmd()
            project_root = get_project_root()
            compose_file, container_name = get_docker_config(env_mode)
            
            subprocess.run([
                *docker_compose.split(), 
                "-f", compose_file,
                "--env-file", str(project_root / ".env"),
                "up", "-d", container_name
            ], cwd=project_root / "docker", capture_output=True, text=True, check=True)
            
            typer.echo("✅ Docker container started successfully")
            
            # Give it a moment to start up
            time.sleep(5)
            
            # Check if it's healthy
            health_result = subprocess.run([
                "docker", "inspect", container_name, 
                "--format={{.State.Health.Status}}"
            ], capture_output=True, text=True, check=False)
            
            if "healthy" in health_result.stdout:
                typer.echo("✅ Container is healthy")
            else:
                typer.echo("⚠️  Container started but health check pending")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start Docker container: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    else:  # process mode
        # Process mode: direct python execution
        typer.echo("🖥️  Starting in process mode...")
        try:
            subprocess.run(["python", "-m", "src"], check=True)
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to start server: {e}", err=True)
            raise typer.Exit(code=1)
        except KeyboardInterrupt:
            typer.echo("\n🛑 Server stopped by user")
            raise typer.Exit(code=0)

@agents_app.command("stop")
def stop_server():
    """Stop the Automagik Agents server."""
    mode, env_mode = detect_deployment_mode()
    typer.echo(f"🛑 Stopping automagik agents (mode: {mode})...")
    
    if mode == "service":
        # Exactly what service mode does: sudo systemctl stop automagik-agents
        try:
            subprocess.run(["sudo", "systemctl", "stop", "automagik-agents"], 
                                 capture_output=True, text=True, check=True)
            typer.echo("✅ Service stopped successfully")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to stop service: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    elif mode == "docker":
        # Exactly what Docker mode does: docker compose stop automagik-agents
        try:
            docker_compose = get_docker_compose_cmd()
            project_root = get_project_root()
            compose_file, container_name = get_docker_config(env_mode)
            
            subprocess.run([
                *docker_compose.split(), 
                "-f", compose_file,
                "--env-file", str(project_root / ".env"),
                "stop", container_name
            ], cwd=project_root / "docker", capture_output=True, text=True, check=True)
            
            typer.echo("✅ Docker container stopped successfully")
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to stop Docker container: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    else:  # process mode
        # Enhanced version of existing kill_process_on_port
        port = get_effective_port()
        killed = kill_process_on_port(port)
        if killed:
            typer.echo("✅ Process stopped successfully")
        else:
            typer.echo("ℹ️  No running process found to stop")

@agents_app.command("restart")
def restart_server():
    """Restart the Automagik Agents server."""
    mode, env_mode = detect_deployment_mode()
    typer.echo(f"🔄 Restarting automagik agents (mode: {mode})...")
    
    if mode == "service":
        # Exactly what service mode does: sudo systemctl restart automagik-agents
        try:
            subprocess.run(["sudo", "systemctl", "restart", "automagik-agents"], 
                                 capture_output=True, text=True, check=True)
            typer.echo("✅ Service restarted successfully")
            
            # Give it a moment to start up
            time.sleep(3)
            
            # Check if it started properly
            status_result = subprocess.run(["systemctl", "is-active", "automagik-agents"], 
                                        capture_output=True, text=True, check=False)
            if status_result.returncode == 0:
                typer.echo("✅ Service is running and healthy")
            else:
                typer.echo("⚠️  Service restarted but may not be fully ready yet")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to restart service: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    elif mode == "docker":
        # Docker mode: docker restart container_name
        try:
            compose_file, container_name = get_docker_config(env_mode)
            subprocess.run(["docker", "restart", container_name], 
                                 capture_output=True, text=True, check=True)
            typer.echo("✅ Docker container restarted successfully")
            
            # Give it a moment to start up
            time.sleep(5)
            
            # Check if it's healthy
            health_result = subprocess.run([
                "docker", "inspect", container_name, 
                "--format={{.State.Health.Status}}"
            ], capture_output=True, text=True, check=False)
            
            if "healthy" in health_result.stdout:
                typer.echo("✅ Container is healthy")
            else:
                typer.echo("⚠️  Container restarted but health check pending")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to restart Docker container: {e.stderr.strip()}")
            raise typer.Exit(code=1)
    
    else:  # process mode
        # Stop then start
        typer.echo("🛑 Stopping current process...")
        stop_server()
        time.sleep(2)
        typer.echo("🚀 Starting new process...")
        start_server()

@agents_app.command("status")
def status_server():
    """Show Automagik Agents server status."""
    mode, env_mode = detect_deployment_mode()
    typer.echo(f"📊 Automagik Agents Status (mode: {mode})")
    typer.echo("=" * 50)
    
    if mode == "service":
        # Exactly what service mode does: systemctl status automagik-agents --no-pager
        try:
            subprocess.run(["systemctl", "status", "automagik-agents", "--no-pager"], 
                                 check=False)
            # systemctl status returns different exit codes but we want to show the output regardless
        except Exception as e:
            typer.echo(f"❌ Failed to get service status: {e}")
    
    elif mode == "docker":
        # Exactly what Docker mode does: docker ps | grep automagik
        try:
            typer.echo("🐳 Docker Container Status:")
            subprocess.run(["docker", "ps", "-a", "--filter", "name=automagik"], 
                                 check=True)
            
            # Also show health if container exists
            typer.echo("\n🏥 Container Health:")
            compose_file, container_name = get_docker_config(env_mode)
            health_result = subprocess.run([
                "docker", "inspect", container_name, 
                "--format={{.State.Health.Status}} ({{.State.Status}})"
            ], capture_output=True, text=True, check=False)
            
            if health_result.returncode == 0:
                typer.echo(f"   Health: {health_result.stdout.strip()}")
            else:
                typer.echo("   Health: Container not found or no health check configured")
                
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to get Docker status: {e}")
    
    else:  # process mode
        # Check process status with comprehensive info
        typer.echo("🖥️  Process Mode Status:")
        port = get_effective_port()
        
        # Check via PID file
        pid = read_pid_file()
        if pid:
            try:
                os.kill(pid, 0)  # Check if process exists
                typer.echo(f"   Process: ✅ Running (PID: {pid})")
            except ProcessLookupError:
                typer.echo("   Process: ❌ Not running (stale PID file)")
        else:
            typer.echo("   Process: ❌ No PID file found")
        
        # Check port/health
        typer.echo(f"   Port: {port}")
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=3)
            if response.status_code == 200:
                typer.echo("   Health: ✅ API responding")
                typer.echo(f"   URL: http://localhost:{port}")
            else:
                typer.echo(f"   Health: ⚠️  API responded with status {response.status_code}")
        except requests.exceptions.RequestException:
            typer.echo("   Health: ❌ API not responding")

@agents_app.command("logs")
def logs_server(
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output")
):
    """Show Automagik Agents logs."""
    mode, env_mode = detect_deployment_mode()
    typer.echo(f"📋 Automagik Agents Logs (mode: {mode})")
    
    if mode == "service":
        # Exactly what service mode does: journalctl -u automagik-agents -f (or without -f)
        cmd = ["journalctl", "-u", "automagik-agents", "--no-pager"]
        if follow:
            cmd.append("-f")
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to get service logs: {e}")
        except KeyboardInterrupt:
            typer.echo("\n📋 Log following stopped")
    
    elif mode == "docker":
        # Exactly what Docker mode does: docker logs container_name -f (or without -f)
        compose_file, container_name = get_docker_config(env_mode)
        cmd = ["docker", "logs", container_name]
        if follow:
            cmd.append("-f")
        
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            typer.echo(f"❌ Failed to get Docker logs: {e}")
        except KeyboardInterrupt:
            typer.echo("\n📋 Log following stopped")
    
    else:  # process mode
        # Show process logs from log files
        show_process_logs(follow)

@agents_app.command("health")
def health_check():
    """Check Automagik Agents health."""
    mode, env_mode = detect_deployment_mode()
    port = get_effective_port()
    
    typer.echo(f"🔍 Checking automagik agents health (mode: {mode})...")
    
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=5)
        if response.status_code == 200:
            typer.echo("✅ API is healthy and responding")
            typer.echo("📡 Available endpoints:")
            typer.echo(f"  • API: http://localhost:{port}")
            typer.echo(f"  • Docs: http://localhost:{port}/docs")
            typer.echo(f"  • Health: http://localhost:{port}/health")
            
            # Mode-specific additional health info
            if mode == "service":
                # Check if service is active
                result = subprocess.run(["systemctl", "is-active", "automagik-agents"], 
                                     capture_output=True, text=True, check=False)
                if result.returncode == 0:
                    typer.echo("🔧 Service: ✅ Active")
                else:
                    typer.echo("🔧 Service: ⚠️  Not active")
            
            elif mode == "docker":
                # Check container health
                compose_file, container_name = get_docker_config(env_mode)
                health_result = subprocess.run([
                    "docker", "inspect", container_name, 
                    "--format={{.State.Health.Status}}"
                ], capture_output=True, text=True, check=False)
                
                if health_result.returncode == 0:
                    health_status = health_result.stdout.strip()
                    if health_status == "healthy":
                        typer.echo("🐳 Container: ✅ Healthy")
                    else:
                        typer.echo(f"🐳 Container: ⚠️  {health_status}")
                else:
                    typer.echo("🐳 Container: ❌ Not found")
                    
        else:
            typer.echo(f"⚠️  API responded with status: {response.status_code}")
            typer.echo("💡 Try: automagik agents restart")
            
    except requests.exceptions.RequestException:
        typer.echo("❌ API is not responding")
        typer.echo("💡 Try: automagik agents start")
        
        # Show deployment-specific troubleshooting
        if mode == "service":
            typer.echo("🔧 Check service status with: systemctl status automagik-agents")
        elif mode == "docker":
            typer.echo("🐳 Check container status with: docker ps -a | grep automagik")
        else:
            typer.echo(f"🖥️  Check if process is running on port {port}")

@agents_app.command("dev")
def dev_server(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True)
):
    """Start server in development mode with auto-reload (python -m src --reload)."""
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG"
        
    # Get port from settings
    port = get_effective_port()
    
    typer.echo(f"🔍 Checking for existing server on port {port}...")
    
    # Check if something is running on the port
    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=2)
        if response.status_code == 200:
            typer.echo(f"🛑 Found existing server on port {port}, stopping it...")
            killed = kill_process_on_port(port)
            if killed:
                typer.echo("✅ Existing server stopped")
                time.sleep(1)  # Give it a moment to fully stop
            else:
                typer.echo("⚠️  Could not stop existing server, proceeding anyway...")
    except requests.exceptions.RequestException:
        typer.echo(f"✅ Port {port} is available")
    
    typer.echo("🚀 Starting development server with auto-reload...")
    
    try:
        subprocess.run(["python", "-m", "src", "--reload"], check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"❌ Failed to start development server: {e}", err=True)
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        typer.echo("\n🛑 Development server stopped by user")
        raise typer.Exit(code=0)

@agents_app.callback()
def agents_callback(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode", is_flag=True, hidden=True)
):
    """
    Automagik Agents - AI agent framework with memory, tools, and API.
    
    Available commands:
    - start: Start the server (python -m src)
    - stop: Stop the server (auto-detects service/docker/process mode)
    - restart: Restart the server (auto-detects mode)
    - status: Show server status (comprehensive for each mode)
    - logs: Show server logs (-f to follow)
    - health: Check API health and connectivity
    - dev: Start in development mode with auto-reload
    - create: Create a new agent from template
    - run: Run a single message through an agent
    - chat: Start interactive chat with an agent
    - db: Database management commands
    - agent: Advanced agent management commands
    
    The CLI automatically detects your deployment mode:
    • Service Mode: Uses systemctl commands for systemd service
    • Docker Mode: Uses docker/compose commands for containers  
    • Process Mode: Direct process management via PID/port
    
    Examples:
      automagik agents start                    # Start the server
      automagik agents status                   # Show comprehensive status
      automagik agents logs -f                  # Follow live logs
      automagik agents health                   # Quick health check
      automagik agents restart                  # Restart in current mode
      automagik agents dev                      # Start in development mode
      automagik agents create --name my_agent   # Create a new agent
      automagik agents run --agent simple --message "Hello"  # Run agent
      automagik agents chat --agent simple     # Start chat session
    """
    if debug:
        os.environ["AUTOMAGIK_LOG_LEVEL"] = "DEBUG" 