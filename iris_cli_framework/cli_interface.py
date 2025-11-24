"""
Iris - CLI Framework (Simplified for Beginners)

This module creates the command-line interface (the shell you see).
It handles user input and displays output in a nice format.

Key concepts for beginners:
- CLI = Command Line Interface (the text-based shell)
- Rich library = Makes output colorful and pretty
- Input loop = Continuously asks for user input
"""

import os  # For file/directory operations
import logging  # For tracking what happens
from rich.console import Console  # For colorful output
from rich.prompt import Prompt  # For user input
from rich.panel import Panel  # For pretty boxes
from rich import box  # For box styles


class CLIFramework:
    """
    Creates the command-line shell interface.
    
    Simple explanation:
    This class shows the welcome message, gets user input,
    and displays results in a nice format.
    """
    
    def __init__(self, config=None):
        """
        Set up the CLI framework.
        
        Args:
            config: Settings dictionary (optional)
        """
        config = config or {}
        
        # Rich console for colorful output
        self.console = Console()
        
        # Shell name and version
        self.shell_name = config.get('shell_name', 'Osiris')
        self.version = config.get('version', '0.1.0')
        self.prompt_symbol = config.get('prompt_symbol', 'osiris>')
        
        # Is the shell running?
        self.running = False
        
        # Current directory
        self.current_directory = os.getcwd()
        
        # Logger
        self.logger = logging.getLogger("Osiris.CLI")
        self.logger.info(f"CLI Framework ready: {self.shell_name} v{self.version}")
    
    def start(self):
        """
        Start the shell interface.
        
        This creates an infinite loop that:
        1. Shows the prompt
        2. Gets user input
        3. Returns the command for processing
        """
        self.running = True
        
        # Show welcome message
        self._display_welcome()
        
        # Main input loop
        while self.running:
            try:
                # Get user input
                user_input = self._get_input()
                
                # Skip empty input
                if not user_input or user_input.strip() == '':
                    continue
                
                # Parse the input
                parsed = self._parse_input(user_input.strip())
                
                # Return parsed command for processing
                yield parsed
                
            except KeyboardInterrupt:
                # User pressed Ctrl+C
                self.console.print("\n[yellow]Use 'exit' or 'quit' to leave Osiris[/yellow]")
                continue
            except EOFError:
                # User pressed Ctrl+D or Ctrl+Z
                self.running = False
    
    def _display_welcome(self):
        """
        Display welcome message when shell starts.
        """
        welcome_text = f"""
[bold cyan]{self.shell_name}[/bold cyan] [dim]v{self.version}[/dim]
Intelligent Command-Line Operating Shell

Type shell commands or use built-in commands.
Type 'help' for assistance, 'exit' to quit.
        """
        
        self.console.print(Panel(welcome_text, box=box.DOUBLE))
    
    def _get_input(self):
        """
        Get input from user with a colorful prompt.
        
        Returns:
            What the user typed (string)
        """
        prompt_text = f"[green]{self.prompt_symbol}[/green] "
        return Prompt.ask(prompt_text)
    
    def _parse_input(self, user_input):
        """
        Parse user input into a structured format.
        
        Args:
            user_input: What the user typed
            
        Returns:
            Dictionary with command info:
                - raw: Original input
                - command: First word (command name)
                - args: Rest of the words (arguments)
                - is_builtin: Is it a built-in command?
        """
        parts = user_input.split()
        
        if not parts:
            return {
                'raw': user_input,
                'command': '',
                'args': [],
                'is_builtin': False
            }
        
        command = parts[0]  # First word
        args = parts[1:]    # Everything else
        
        # Built-in commands
        # 'r' is a special RAG-style helper that converts
        # natural language to shell commands.
        builtins = ['exit', 'quit', 'help', 'team', 'status', 'metrics', 'r']
        
        return {
            'raw': user_input,
            'command': command,
            'args': args,
            'is_builtin': command in builtins
        }
    
    def display_output(self, output, style='info'):
        """
        Display output in a nice format.
        
        Args:
            output: Text to display
            style: Style type ('info', 'success', 'error', 'warning')
        """
        # Choose color based on style
        colors = {
            'info': 'white',
            'success': 'green',
            'error': 'red',
            'warning': 'yellow'
        }
        
        color = colors.get(style, 'white')
        self.console.print(f"[{color}]{output}[/{color}]")
    
    def display_error(self, error_message):
        """
        Display an error message.
        
        Args:
            error_message: Error text to display
        """
        self.console.print(f"[bold red]Error:[/bold red] {error_message}")
    
    def display_success(self, message):
        """
        Display a success message.
        
        Args:
            message: Success text to display
        """
        self.console.print(f"[bold green]✓[/bold green] {message}")
    
    def handle_builtin(self, command, args):
        """
        Handle built-in commands.
        
        Args:
            command: The built-in command name
            args: Command arguments
            
        Returns:
            True if command was handled, False otherwise
        """
        if command == 'exit' or command == 'quit':
            # Exit the shell
            self.console.print("[cyan]Goodbye![/cyan]")
            self.running = False
            return True
        
        elif command == 'help':
            # Show help message
            self._show_help()
            return True
        
        elif command == 'team':
            # This will be handled by the main shell
            return False
        
        elif command == 'status':
            # This will be handled by the main shell
            return False
        
        elif command == 'metrics':
            # This will be handled by the main shell
            return False
        
        return False
    
    def _show_help(self):
        """
        Display help information.
        """
        help_text = """
[bold cyan]Osiris Shell - Help[/bold cyan]

[bold]Built-in Commands:[/bold]
  help        Show this help message
  exit/quit   Exit the shell
  team        Show team member information
  status      Show system status
  metrics     Show performance metrics

[bold]Command R (Natural Language):[/bold]
    r <text>   Ask Command R to understand a request and
                         suggest a safe shell command (e.g.
                         'r make a folder test').

[bold]Linux Commands (Supported):[/bold]
  ls          List files and directories
  pwd         Show current directory
  cat         Display file contents
  touch       Create new file
  mkdir       Create new directory
  cp          Copy file
  mv          Move/rename file
  rm          Remove file
  echo        Print text
  clear       Clear screen
  ps          Show processes
  grep        Search in files
  find        Find files
  
[bold]Tips:[/bold]
  - All Linux commands are translated to Windows PowerShell
  - Dangerous commands are blocked by the safety gate
  - System metrics are monitored in real-time
    - Use 'r' for natural language commands (Command R model)
        """
        
        self.console.print(Panel(help_text, box=box.ROUNDED))


# What this module provides to other files
__all__ = ['CLIFramework']
