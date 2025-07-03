"""
Shell alias management for Automagik CLI.
Supports bash, zsh, and fish shells.
"""
import os
import typer
from pathlib import Path
from typing import Optional, Tuple


def detect_shell() -> Optional[str]:
    """Detect the current shell."""
    shell = os.environ.get('SHELL', '')
    if 'bash' in shell:
        return 'bash'
    elif 'zsh' in shell:
        return 'zsh'
    elif 'fish' in shell:
        return 'fish'
    return None


def get_rc_file(shell: str) -> Optional[Path]:
    """Get the RC file path for the given shell."""
    home = Path.home()
    
    if shell == 'bash':
        # Try .bashrc first, then .bash_profile
        bashrc = home / '.bashrc'
        if bashrc.exists():
            return bashrc
        return home / '.bash_profile'
    elif shell == 'zsh':
        return home / '.zshrc'
    elif shell == 'fish':
        config_dir = home / '.config' / 'fish'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.fish'
    
    return None


def get_alias_lines(shell: str) -> Tuple[str, str]:
    """Get the alias lines for the given shell."""
    # Get the project root to find the bash wrapper
    from automagik.cli.agents import get_project_root
    project_root = get_project_root()
    wrapper_path = project_root / "scripts" / "automagik"
    
    if shell == 'fish':
        alias_line = f"alias agent='{wrapper_path} agents'"
        comment_line = "# Automagik Agents alias"
    else:  # bash/zsh
        alias_line = f"alias agent='{wrapper_path} agents'"
        comment_line = "# Automagik Agents alias"
    
    return comment_line, alias_line


def check_alias_exists(rc_file: Path) -> bool:
    """Check if the alias already exists in the RC file."""
    if not rc_file.exists():
        return False
    
    content = rc_file.read_text()
    # Check for both old and new alias formats
    return ("alias agent=" in content and "agents'" in content) or ("alias agent=" in content and 'agents"' in content)


def install_shell_alias():
    """Install shell alias for convenient access."""
    # Detect shell
    shell = detect_shell()
    if not shell:
        typer.echo("❌ Could not detect shell type")
        typer.echo("💡 Supported shells: bash, zsh, fish")
        raise typer.Exit(code=1)
    
    typer.echo(f"🔍 Detected shell: {shell}")
    
    # Get RC file
    rc_file = get_rc_file(shell)
    if not rc_file:
        typer.echo(f"❌ Could not determine RC file for {shell}")
        raise typer.Exit(code=1)
    
    typer.echo(f"📄 RC file: {rc_file}")
    
    # Check if alias already exists
    if check_alias_exists(rc_file):
        typer.echo("✅ Alias 'agent' already exists!")
        typer.echo("💡 You can already use: agent start, agent stop, etc.")
        return
    
    # Get alias lines
    comment_line, alias_line = get_alias_lines(shell)
    
    # Add alias to RC file
    try:
        with open(rc_file, 'a') as f:
            f.write(f"\n{comment_line}\n{alias_line}\n")
        
        typer.echo(f"✅ Added alias 'agent' to {rc_file}")
        typer.echo("💡 Run one of these commands to use it immediately:")
        typer.echo(f"   source {rc_file}")
        typer.echo("   # OR restart your terminal")
        typer.echo()
        typer.echo("🎯 Now you can use:")
        typer.echo("   agent start    # Same as: automagik agents start")
        typer.echo("   agent stop     # Same as: automagik agents stop")
        typer.echo("   agent status   # Same as: automagik agents status")
        
    except Exception as e:
        typer.echo(f"❌ Failed to write to {rc_file}: {e}")
        raise typer.Exit(code=1)


def uninstall_shell_alias():
    """Remove shell alias."""
    # Detect shell
    shell = detect_shell()
    if not shell:
        typer.echo("❌ Could not detect shell type")
        raise typer.Exit(code=1)
    
    # Get RC file
    rc_file = get_rc_file(shell)
    if not rc_file or not rc_file.exists():
        typer.echo("❌ RC file not found")
        raise typer.Exit(code=1)
    
    # Check if alias exists
    if not check_alias_exists(rc_file):
        typer.echo("ℹ️  Alias 'agent' not found - nothing to remove")
        return
    
    # Remove alias lines
    try:
        lines = rc_file.read_text().splitlines()
        new_lines = []
        skip_next = False
        
        for line in lines:
            if skip_next:
                skip_next = False
                continue
                
            if "# Automagik Agents alias" in line:
                skip_next = True  # Skip the next line (the alias)
                continue
            elif ("alias agent=" in line and "agents'" in line) or ("alias agent=" in line and 'agents"' in line):
                continue  # Skip alias line even if comment is missing
            else:
                new_lines.append(line)
        
        # Remove trailing empty lines that we might have created
        while new_lines and new_lines[-1].strip() == '':
            new_lines.pop()
        
        rc_file.write_text('\n'.join(new_lines) + '\n' if new_lines else '')
        
        typer.echo(f"✅ Removed alias 'agent' from {rc_file}")
        typer.echo("💡 Restart your terminal or run:")
        typer.echo(f"   source {rc_file}")
        
    except Exception as e:
        typer.echo(f"❌ Failed to remove alias from {rc_file}: {e}")
        raise typer.Exit(code=1) 