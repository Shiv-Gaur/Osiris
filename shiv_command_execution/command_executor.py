import subprocess  # For running commands
import logging  # For tracking what happens
import shutil  # For checking tool availability
from datetime import datetime  # For timestamps


class CommandExecutor:
    """
    Executes shell commands.
    
    Simple explanation:
    When you type a command, this class runs it and gives you the output.
    """
    
    def __init__(self, config=None):
        """
        Set up the command executor.
        
        Args:
            config: Settings dictionary (optional)
        """
        config = config or {}
        self.logger = logging.getLogger("Osiris.CommandExecutor")
        
        # How long to wait before stopping a command (in seconds)
        self.timeout = config.get('timeout', 300)

        # Whether to prefer running commands via WSL (for Linux-style commands)
        self.use_wsl = config.get('use_wsl', False)

        # Detect if WSL + bash are actually available before honoring the flag
        self._wsl_available = self._detect_wsl()
        if self.use_wsl and not self._wsl_available:
            self.logger.warning("WSL requested but not available; falling back to PowerShell mode.")
            self.use_wsl = False
        
        # Keep track of commands we've run
        self.execution_history = []
        
        self.logger.info("Command Executor ready!")
    
    def execute(self, command, working_dir=None, timeout=None, capture_output=True, use_wsl: bool = None):
        """
        Run a command and return the result.
        
        Args:
            command: The command to run (string)
            working_dir: Where to run the command (folder path, optional)
            timeout: How long to wait before stopping (seconds, optional)
            capture_output: Whether to capture output (default: True)
            
        Returns:
            Dictionary with output, errors, and success status
        """
        start_time = datetime.now()
        timeout = timeout or self.timeout

        # Decide whether to use WSL for this execution
        if use_wsl is None:
            use_wsl = self.use_wsl

        if use_wsl and not self._wsl_available:
            # Auto-disable WSL if the environment disappeared after init
            self.logger.warning("WSL execution unavailable; retrying command via PowerShell.")
            use_wsl = False

        # Step 1: Translate Linux commands to Windows PowerShell (when not using WSL)
        original_command = command
        if not use_wsl and self._is_linux_command(command):
            command = self._translate_to_windows(command)
            self.logger.info(f"Translated '{original_command}' to '{command}'")
        
        self.logger.info(f"Running: {command} (use_wsl={use_wsl})")
        
        try:
            # Step 2: Build the underlying process command
            # When using WSL, run the command through bash so that
            # it is parsed as a normal shell command with arguments.
            if use_wsl:
                popen_cmd = ['wsl', 'bash', '-lc', command]
            else:
                popen_cmd = ['powershell.exe', '-Command', command]

            # Step 3: Run the command
            process = subprocess.Popen(
                popen_cmd,
                stdout=subprocess.PIPE if capture_output else None,  # Capture output
                stderr=subprocess.PIPE if capture_output else None,  # Capture errors
                text=True,  # Get output as string, not bytes
                cwd=working_dir  # Run in specified directory
            )
            
            # Step 4: Wait for command to finish
            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Command took too long - stop it!
                process.kill()
                stdout, stderr = process.communicate()
                stderr = f"Command timeout after {timeout} seconds\n" + (stderr or "")
            
            exit_code = process.returncode

            # Retry automatically on the common "bash not found" style failures
            if use_wsl and exit_code != 0 and self._should_fallback_to_powershell(stderr):
                self.logger.warning("WSL failed to run the command; falling back to PowerShell translation.")
                return self.execute(original_command, working_dir, timeout, capture_output, use_wsl=False)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Step 5: Build the result dictionary
            result = {
                'command': original_command,
                'output': stdout or "",
                'error': stderr or "",
                'exit_code': exit_code,
                'success': exit_code == 0,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time
            }
            
            # Step 6: Log what happened
            if result['success']:
                self.logger.info(f"[OK] Success ({duration:.2f}s)")
            else:
                self.logger.error(f"[FAIL] Failed (exit code: {exit_code})")
            
            # Save to history
            self.execution_history.append(result)
            
            return result
            
        except Exception as e:
            # Step 7: Handle errors
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"Error running command: {e}")
            
            return {
                'command': original_command,
                'output': "",
                'error': str(e),
                'exit_code': -1,
                'success': False,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time
            }
    
    def _is_linux_command(self, command):
        """
        Check if this is a Linux command that needs translation.
        
        Args:
            command: Command string
            
        Returns:
            True if it's a Linux command, False otherwise
        """
        # List of common Linux commands
        linux_commands = [
            'ls', 'cat', 'pwd', 'touch', 'mkdir', 'rm', 'cp', 'mv',
            'echo', 'clear', 'ps', 'kill', 'grep', 'find', 'df',
            'whoami', 'hostname', 'date', 'head', 'tail', 'wc'
        ]
        
        # Get the first word (the command name)
        first_word = command.strip().split()[0] if command.strip() else ''
        
        # Check if it's in our list
        return first_word in linux_commands
    
    def _translate_to_windows(self, command):
        """
        Translate Linux commands to Windows PowerShell.
        
        Args:
            command: Linux command
            
        Returns:
            Windows PowerShell equivalent command
        """
        # Split command into parts
        parts = command.strip().split()
        if not parts:
            return command
        
        cmd = parts[0]  # First word is the command
        args = parts[1:] if len(parts) > 1 else []  # Rest are arguments
        
        # === FILE LISTING COMMANDS ===
        
        if cmd == 'ls':
            # List files and folders
            return 'Get-ChildItem'
        
        elif cmd == 'pwd':
            # Print working directory (show current folder)
            return 'Get-Location'
        
        # === FILE READING COMMANDS ===
        
        elif cmd == 'cat':
            # Show file contents
            if args:
                return f'Get-Content "{args[0]}"'
            return 'Write-Host "cat: missing file name"'
        
        elif cmd == 'head':
            # Show first 10 lines of file
            if args:
                return f'Get-Content "{args[-1]}" | Select-Object -First 10'
            return 'Write-Host "head: missing file name"'
        
        elif cmd == 'tail':
            # Show last 10 lines of file
            if args:
                return f'Get-Content "{args[-1]}" | Select-Object -Last 10'
            return 'Write-Host "tail: missing file name"'
        
        # === FILE CREATION/MODIFICATION COMMANDS ===
        
        elif cmd == 'touch':
            # Create empty file or update timestamp
            if args:
                filename = args[0]
                # If file exists, update time. If not, create it.
                return f'if (Test-Path "{filename}") {{ (Get-Item "{filename}").LastWriteTime = Get-Date }} else {{ New-Item -ItemType File "{filename}" | Out-Null }}'
            return 'Write-Host "touch: missing file name"'
        
        elif cmd == 'mkdir':
            # Make directory
            if args:
                return f'New-Item -ItemType Directory "{args[0]}" -Force'
            return 'Write-Host "mkdir: missing directory name"'
        
        # === FILE DELETION COMMANDS ===
        
        elif cmd == 'rm':
            # Remove file or directory
            if args:
                return f'Remove-Item "{args[0]}" -Force'
            return 'Write-Host "rm: missing file name"'
        
        # === FILE COPY/MOVE COMMANDS ===
        
        elif cmd == 'cp':
            # Copy file
            if len(args) >= 2:
                return f'Copy-Item "{args[0]}" "{args[1]}"'
            return 'Write-Host "cp: need source and destination"'
        
        elif cmd == 'mv':
            # Move/rename file
            if len(args) >= 2:
                return f'Move-Item "{args[0]}" "{args[1]}"'
            return 'Write-Host "mv: need source and destination"'
        
        # === DISPLAY COMMANDS ===
        
        elif cmd == 'echo':
            # Print text to screen
            if args:
                return f'Write-Output {" ".join(args)}'
            return 'Write-Output ""'
        
        elif cmd == 'clear':
            # Clear the screen
            return 'Clear-Host'
        
        # === PROCESS COMMANDS ===
        
        elif cmd == 'ps':
            # Show running programs (processes)
            return 'Get-Process | Select-Object ProcessName,Id,CPU'
        
        elif cmd == 'kill':
            # Stop a running program
            if args:
                return f'Stop-Process -Id {args[0]} -Force'
            return 'Write-Host "kill: missing process ID"'
        
        # === SEARCH COMMANDS ===
        
        elif cmd == 'grep':
            # Search for text in files
            if args:
                return f'Select-String {" ".join(args)}'
            return 'Write-Host "grep: missing search pattern"'
        
        elif cmd == 'find':
            # Find files and folders
            path = args[0] if args else '.'
            return f'Get-ChildItem -Path "{path}" -Recurse'
        
        # === SYSTEM INFO COMMANDS ===
        
        elif cmd == 'df':
            # Show disk space
            return 'Get-PSDrive -PSProvider FileSystem'
        
        elif cmd == 'whoami':
            # Show current username
            return '$env:USERNAME'
        
        elif cmd == 'hostname':
            # Show computer name
            return '$env:COMPUTERNAME'
        
        elif cmd == 'date':
            # Show current date and time
            return 'Get-Date'
        
        elif cmd == 'wc':
            # Count lines, words, characters in file
            if args:
                return f'Get-Content "{args[0]}" | Measure-Object -Line -Word -Character'
            return 'Write-Host "wc: missing file name"'
        
        # === DEFAULT ===
        
        else:
            # If we don't know how to translate, return the original
            return command

    def _detect_wsl(self):
        """Best-effort probe to see whether WSL + bash are runnable."""
        if shutil.which('wsl') is None:
            return False

        try:
            probe = subprocess.run(
                ['wsl', 'bash', '-lc', 'exit'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
        except Exception as exc:
            self.logger.debug(f"WSL probe failed: {exc}")
            return False

        if probe.returncode != 0:
            error_text = (probe.stderr or '').lower()
            patterns = ['bash: not found', 'no installed distributions', 'wsl is not enabled']
            if any(pattern in error_text for pattern in patterns):
                return False
        return True

    def _should_fallback_to_powershell(self, stderr):
        """Detect errors that mean WSL cannot execute the command."""
        if not stderr:
            return False
        message = stderr.lower()
        fallback_tokens = [
            'bash: not found',
            'no installed distributions',
            'wsl.exe was not found',
            'the system cannot find the file specified'
        ]
        return any(token in message for token in fallback_tokens)
    
    def preview_command(self, command):
        """
        Show what a command will do (without running it).
        
        Args:
            command: Command to preview
            
        Returns:
            Dictionary with command info
        """
        parts = command.strip().split()
        if not parts:
            return {
                'command': command,
                'description': 'Empty command',
                'safe': False
            }
        
        cmd = parts[0]
        
        # Describe what each command does
        descriptions = {
            'ls': 'Lists files and folders in current directory',
            'pwd': 'Shows current directory path',
            'cat': 'Displays contents of a file',
            'head': 'Shows first 10 lines of a file',
            'tail': 'Shows last 10 lines of a file',
            'touch': 'Creates a new empty file',
            'mkdir': 'Creates a new directory/folder',
            'rm': 'Deletes a file or directory',
            'cp': 'Copies a file',
            'mv': 'Moves or renames a file',
            'echo': 'Prints text to the screen',
            'clear': 'Clears the screen',
            'ps': 'Shows running processes/programs',
            'kill': 'Stops a running process',
            'grep': 'Searches for text in files',
            'find': 'Finds files and directories',
            'df': 'Shows disk space usage',
            'whoami': 'Shows your username',
            'hostname': 'Shows computer name',
            'date': 'Shows current date and time',
            'wc': 'Counts lines, words, and characters in a file'
        }
        
        return {
            'command': command,
            'description': descriptions.get(cmd, f"Runs the command: {cmd}"),
            'safe': True
        }
    
    def get_recent_executions(self, count=10):
        """
        Get the most recent commands that were run.
        
        Args:
            count: How many recent commands to get (default: 10)
            
        Returns:
            List of recent command results
        """
        return self.execution_history[-count:]


# What this module provides to other files
__all__ = ['CommandExecutor']
