"""
Osiris Team Project - Main Shell (Simplified for Beginners)

This is the main file that combines all team member modules:
- Iris: CLI Framework (the interface you see)
- Shiv: Command Execution (runs your commands)
- Kshitij: Safety Gate (blocks dangerous commands)
- Prabal: System Monitor (tracks CPU, memory, disk)

How it works:
1. User types a command
2. Safety gate checks if it's safe
3. System monitor checks if resources are available
4. Command executor runs the command
5. CLI displays the result

This version is simplified for beginners to understand!
"""

import os
import sys
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

# Add project folder to Python's path
sys.path.insert(0, str(Path(__file__).parent))

# Import our team modules
from shared.utils import OsirisConfig, setup_logging, CommandHistory
from shared.command_r import CommandRModel
from iris_cli_framework import CLIFramework
from shiv_command_execution import CommandExecutor
from kshitij_safety_gate import SafetyGate, RiskLevel
from prabal_efficiency_metrics import SystemMonitor


class OsirisTeamShell:
    """
    The main Osiris shell that combines all team member work.
    
    Simple explanation:
    This class brings together all 4 team member modules
    into one working shell.
    """
    
    def __init__(self, config_path=None):
        """
        Set up the Osiris shell.
        
        Args:
            config_path: Path to config file (optional)
        """
        # Load configuration file
        self.config = OsirisConfig(config_path)
        
        # Setup logging
        log_level = self.config.get('logging.level', 'INFO')
        self.logger = setup_logging(log_level)
        
        # Rich console for colorful output
        self.console = Console()
        
        # Command history
        history_file = self.config.get('shell.history_file', '.osiris_history')
        max_history = self.config.get('shell.max_history', 1000)
        self.history = CommandHistory(history_file, max_history)
        
        # Command R - RAG-style natural language command model
        command_r_config = self.config.get('command_r', {})
        self.command_r = CommandRModel(command_r_config)
        
        # Initialize all team member modules
        self._initialize_modules()
        
        self.logger.info("Osiris Team Shell initialized successfully!")
    
    def _initialize_modules(self):
        """
        Start up all 4 team member modules.
        """
        try:
            # === IRIS: CLI Framework ===
            cli_config = {
                'shell_name': self.config.get('shell.name', 'Osiris'),
                'version': self.config.get('shell.version', '0.1.0-team'),
                'prompt_symbol': self.config.get('shell.prompt_symbol', 'osiris>')
            }
            self.cli = CLIFramework(cli_config)
            self.logger.info("[OK] Iris: CLI Framework initialized")
            
            # === SHIV: Command Executor ===
            executor_config = self.config.get('command_execution', {})
            self.executor = CommandExecutor(executor_config)
            self.logger.info("[OK] Shiv: Command Executor initialized")
            
            # === KSHITIJ: Safety Gate ===
            safety_config = self.config.get('safety', {})
            self.safety_gate = SafetyGate(safety_config)
            self.logger.info("[OK] Kshitij: Safety Gate initialized")
            
            # === PRABAL: System Monitor ===
            monitor_config = self.config.get('system_monitoring.thresholds', {})
            self.system_monitor = SystemMonitor(monitor_config)
            self.logger.info("[OK] Prabal: System Monitor initialized")
            
        except Exception as e:
            self.logger.error(f"Error initializing modules: {e}")
            raise
    
    def run(self):
        """
        Run the Osiris shell.
        
        This is the main loop that:
        1. Gets user input
        2. Processes commands
        3. Shows results
        """
        # Show welcome message and system status
        self._display_welcome()
        
        # Start the CLI framework (this gives us commands)
        for parsed_command in self.cli.start():
            
            # Save command to history
            self.history.add(parsed_command['raw'])
            
            # === STEP 1: Check if it's a built-in command ===
            if parsed_command['is_builtin']:
                if parsed_command['command'] in ['exit', 'quit', 'help']:
                    # CLI framework handles these
                    self.cli.handle_builtin(parsed_command['command'], parsed_command['args'])
                else:
                    # We handle these
                    self._handle_special_command(parsed_command)
                continue
            
            # === STEP 2: Safety Gate - Check if command is safe ===
            safety_result = self.safety_gate.evaluate_command(parsed_command['raw'])
            
            if not safety_result['allowed']:
                # Command is BLOCKED!
                self.cli.display_error(f"BLOCKED: {safety_result['reason']}")
                self.logger.warning(f"Blocked command: {parsed_command['raw']} (Risk: {safety_result['risk_level']})")
                continue
            
            # Show warnings if any
            for warning in safety_result['warnings']:
                self.console.print(f"[yellow]⚠️  {warning}[/yellow]")
            
            # === STEP 3: System Monitor - Check if resources are available ===
            metrics = self.system_monitor.get_current_metrics()
            pressure = self.system_monitor.check_resource_pressure(metrics)
            
            if pressure['cpu_pressure'] or pressure['memory_pressure']:
                self.console.print("[yellow]⚠️  High system load detected[/yellow]")
            
            # === STEP 4: Execute the command ===
            self.logger.info(f"Executing: {parsed_command['raw']}")
            result = self.executor.execute(parsed_command['raw'])
            
            # === STEP 5: Show the result ===
            if result['success']:
                # Command succeeded
                if result['output'].strip():
                    self.console.print(result['output'])
            else:
                # Command failed
                self.cli.display_error(f"Command failed (exit code: {result['exit_code']})")
                if result['error'].strip():
                    self.console.print(f"[red]{result['error']}[/red]")
    
    def _display_welcome(self):
        """
        Show welcome message with system information.
        """
        # Get system status
        metrics = self.system_monitor.get_current_metrics()
        status_line = self.system_monitor.format_metrics_display(metrics)
        
        # Show system status
        self.console.print(f"\n[dim]{status_line}[/dim]\n")
    
    def _handle_special_command(self, parsed_command):
        """
        Handle special built-in commands (team, status, metrics, r).
        
        Args:
            parsed_command: The parsed command dictionary
        """
        cmd = parsed_command['command']
        
        if cmd == 'team':
            # Show team member information
            self._show_team_info()
        
        elif cmd == 'status':
            # Show system status
            self._show_status()
        
        elif cmd == 'metrics':
            # Show detailed metrics
            self._show_metrics()

        elif cmd == 'r':
            # Command R model: natural language to shell command or help
            self._handle_rag_command(parsed_command['args'])

    def _handle_rag_command(self, args):
        """Use Command R to understand natural language and act.

        Usage:
            r make a folder test
            r list files
            r show current directory
            r delete folder demo

        Command R returns a suggested shell command and explanation,
        which we confirm with the user, pass through the safety gate,
        then execute via the CommandExecutor.
        """
        if not args:
            self.cli.display_error("Usage: r <natural language instruction>")
            return

        instruction = " ".join(args).lower().strip()
        
        # Ask Command R model for a suggestion
        suggestion = self.command_r.suggest(instruction)
        if suggestion is None:
            self.cli.display_error("Command R could not understand that request yet.")
            return

        command = suggestion.command
        self.console.print(
            f"[cyan]Command R suggests:[/cyan] [yellow]{command}[/yellow]\n"
            f"[dim]{suggestion.explanation} (confidence: {suggestion.confidence:.2f})[/dim]"
        )

        # Simple confirmation prompt
        self.console.print("Run this command? [y/N] ", end="")
        try:
            choice = input().strip().lower()
        except EOFError:
            choice = "n"

        if choice not in ("y", "yes"):
            self.console.print("[yellow]Cancelled.[/yellow]")
            return

        # Run through safety gate + executor like normal commands
        safety_result = self.safety_gate.evaluate_command(command)

        if not safety_result['allowed']:
            self.cli.display_error(f"BLOCKED: {safety_result['reason']}")
            self.logger.warning(f"Blocked translated command: {command} (Risk: {safety_result['risk_level']})")
            return

        for warning in safety_result['warnings']:
            self.console.print(f"[yellow]⚠️  {warning}[/yellow]")

        self.logger.info(f"Executing Command R suggestion: {command}")
        # For Command R suggestions, run via the Windows shell
        # (use_wsl=False) so that simple filesystem commands like
        # mkdir/rm work reliably even if WSL's default shell is
        # limited or missing bash.
        result = self.executor.execute(command, use_wsl=False)

        if result['success']:
            if result['output'].strip():
                self.console.print(result['output'])
        else:
            self.cli.display_error(f"Command failed (exit code: {result['exit_code']})")
            if result['error'].strip():
                self.console.print(f"[red]{result['error']}[/red]")
    
    def _show_team_info(self):
        """
        Display team member information.
        """
        table = Table(title="Osiris Team Members", box=box.ROUNDED)
        
        table.add_column("Member", style="cyan", no_wrap=True)
        table.add_column("Module", style="magenta")
        table.add_column("Description", style="white")
        
        table.add_row(
            "Iris",
            "CLI Framework",
            "Command-line interface and user interaction"
        )
        table.add_row(
            "Shiv",
            "Command Execution",
            "Runs commands and translates Linux to Windows"
        )
        table.add_row(
            "Kshitij",
            "Safety Gate",
            "Blocks dangerous commands for system protection"
        )
        table.add_row(
            "Prabal",
            "System Monitor",
            "Tracks CPU, memory, and disk usage"
        )
        
        self.console.print(table)
    
    def _show_status(self):
        """
        Display current system status.
        """
        metrics = self.system_monitor.get_current_metrics()
        if not metrics:
            self.cli.display_error("Could not get system metrics")
            return
        
        pressure = self.system_monitor.check_resource_pressure(metrics)
        
        # Create status table
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Resource", style="cyan")
        table.add_column("Usage", style="yellow")
        table.add_column("Status", style="white")
        
        # CPU row
        cpu_status = "🔴 HIGH" if pressure['cpu_pressure'] else "🟢 OK"
        table.add_row("CPU", f"{metrics['cpu_percent']:.1f}%", cpu_status)
        
        # Memory row
        mem_status = "🔴 HIGH" if pressure['memory_pressure'] else "🟢 OK"
        table.add_row("Memory", f"{metrics['memory_percent']:.1f}%", mem_status)
        
        # Disk row
        disk_status = "🔴 HIGH" if pressure['disk_pressure'] else "🟢 OK"
        table.add_row("Disk", f"{metrics['disk_percent']:.1f}%", disk_status)
        
        # Processes row
        table.add_row("Processes", str(metrics['process_count']), "🟢 OK")
        
        self.console.print(table)
        
        # Show warnings if any
        if pressure['warnings']:
            self.console.print("\n[yellow]Warnings:[/yellow]")
            for warning in pressure['warnings']:
                self.console.print(f"  ⚠️  {warning}")
    
    def _show_metrics(self):
        """
        Display detailed performance metrics.
        """
        metrics = self.system_monitor.get_current_metrics()
        if not metrics:
            self.cli.display_error("Could not get system metrics")
            return
        
        # Create detailed metrics table
        table = Table(title="Detailed Performance Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        # CPU
        table.add_row("CPU Usage", f"{metrics['cpu_percent']:.1f}%")
        table.add_row("CPU Cores", str(metrics['cpu_count']))
        
        # Memory
        table.add_row("Memory Usage", f"{metrics['memory_percent']:.1f}%")
        table.add_row("Memory Available", f"{metrics['memory_available_gb']:.2f} GB")
        table.add_row("Memory Total", f"{metrics['memory_total_gb']:.2f} GB")
        
        # Disk
        table.add_row("Disk Usage", f"{metrics['disk_percent']:.1f}%")
        table.add_row("Disk Free", f"{metrics['disk_free_gb']:.2f} GB")
        
        # Processes
        table.add_row("Running Processes", str(metrics['process_count']))
        
        self.console.print(table)


def main():
    """
    Main entry point for the Osiris shell.
    
    This function:
    1. Creates the shell
    2. Runs it
    3. Handles any errors
    """
    try:
        # Create and run the shell
        shell = OsirisTeamShell()
        shell.run()
    
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        print("\n\nShell interrupted by user")
    
    except Exception as e:
        # Something went wrong
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# Run the shell when this file is executed
if __name__ == "__main__":
    main()
