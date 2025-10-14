import logging  # For tracking what happens


# Risk levels (how dangerous a command is)
class RiskLevel:
    """
    Different levels of danger for commands.
    
    SAFE = No risk
    LOW = Minor risk
    MEDIUM = Could cause problems
    HIGH = Very dangerous
    CRITICAL = Extremely dangerous (always blocked)
    """
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SafetyGate:
    """
    Checks if commands are safe to run.
    
    Simple explanation:
    Before running a command, we check if it's dangerous.
    If it's too risky, we block it!
    """
    
    def __init__(self, config=None):
        """
        Set up the safety gate.
        
        Args:
            config: Settings dictionary (optional)
        """
        config = config or {}
        self.logger = logging.getLogger("Osiris.SafetyGate")
        
        # Is the safety gate turned on?
        self.enabled = config.get('enabled', True)
        
        # Sandbox mode (test mode - doesn't actually block)
        self.sandbox_mode = config.get('sandbox_mode', False)
        
        # Get dangerous patterns from config
        self.dangerous_commands = config.get('dangerous_commands', [])
        self.sensitive_paths = config.get('sensitive_paths', [])
        
        self.logger.info(f"Safety Gate ready (enabled: {self.enabled}, sandbox: {self.sandbox_mode})")
    
    def evaluate_command(self, command, context=None):
        """
        Check if a command is safe to run.
        
        Args:
            command: The command to check
            context: Extra information (optional)
            
        Returns:
            Dictionary with:
                - allowed: Can we run it? (True/False)
                - risk_level: How dangerous it is
                - reason: Why it's blocked (if blocked)
                - warnings: Any warnings about the command
        """
        if not self.enabled:
            # Safety gate is off - allow everything
            return {
                'allowed': True,
                'risk_level': RiskLevel.SAFE,
                'reason': 'Safety gate disabled',
                'warnings': []
            }
        
        # Check for critical (extremely dangerous) commands
        is_critical, critical_reason = self._is_critical_command(command)
        if is_critical:
            return {
                'allowed': False,  # BLOCKED!
                'risk_level': RiskLevel.CRITICAL,
                'reason': critical_reason,
                'warnings': ['This command could destroy your system!']
            }
        
        # Check for high-risk commands
        is_high_risk, high_risk_reason = self._is_high_risk_command(command)
        if is_high_risk:
            return {
                'allowed': False,  # BLOCKED!
                'risk_level': RiskLevel.HIGH,
                'reason': high_risk_reason,
                'warnings': ['This command is very dangerous!']
            }
        
        # Check for medium-risk commands
        is_medium_risk, medium_risk_reason = self._is_medium_risk_command(command)
        if is_medium_risk:
            return {
                'allowed': True,  # Allowed but warned
                'risk_level': RiskLevel.MEDIUM,
                'reason': '',
                'warnings': [medium_risk_reason]
            }
        
        # Check for commands that need confirmation
        needs_confirm, confirm_reason = self._needs_confirmation(command)
        if needs_confirm:
            return {
                'allowed': True,  # Allowed but needs confirmation
                'risk_level': RiskLevel.LOW,
                'reason': '',
                'warnings': [confirm_reason]
            }
        
        # Command is safe!
        return {
            'allowed': True,
            'risk_level': RiskLevel.SAFE,
            'reason': '',
            'warnings': []
        }
    
    def _is_critical_command(self, command):
        """
        Check if command is CRITICALLY dangerous.
        
        These commands could destroy your entire system!
        Examples: rm -rf /, format C:, fork bombs
        
        Args:
            command: Command to check
            
        Returns:
            (is_critical, reason)
        """
        command_lower = command.lower()
        
        # Fork bomb - creates infinite processes
        if ':(){' in command or ':|:&' in command:
            return True, "Fork bomb detected - would crash system"
        
        # Delete everything in root directory
        if 'rm -rf /' in command or 'rm -fr /' in command:
            return True, "Attempting to delete root directory"
        
        # Format hard drive
        if 'mkfs' in command_lower or 'format' in command_lower:
            return True, "Attempting to format hard drive"
        
        # Overwrite hard drive
        if 'dd if=/dev/zero' in command_lower or 'dd if=/dev/random' in command_lower:
            return True, "Attempting to overwrite hard drive"
        
        # Destroy boot partition
        if any(path in command_lower for path in ['/boot', '/dev/sda', '/dev/nvme']):
            if 'rm' in command_lower or 'dd' in command_lower or '>' in command:
                return True, "Attempting to destroy boot partition"
        
        # Check configured dangerous commands
        for dangerous in self.dangerous_commands:
            if dangerous.lower() in command_lower:
                return True, f"Matches dangerous pattern: {dangerous}"
        
        return False, ""
    
    def _is_high_risk_command(self, command):
        """
        Check if command is HIGH risk.
        
        These commands are very dangerous but not instant-death.
        Examples: rm -rf (on a folder), recursive chmod, kill -9 1
        
        Args:
            command: Command to check
            
        Returns:
            (is_high_risk, reason)
        """
        command_lower = command.lower()
        
        # Recursive delete
        if ('rm -rf' in command or 'rm -fr' in command) and '/' not in command:
            return True, "Recursive delete detected"
        
        # Recursive permission change
        if 'chmod -r' in command_lower or 'chown -r' in command_lower:
            return True, "Recursive permission change detected"
        
        # Kill init process (PID 1)
        if 'kill' in command_lower and (' 1' in command or '-9 1' in command):
            return True, "Attempting to kill init process"
        
        # Delete Windows system folders
        if any(path in command_lower for path in ['c:\\windows', 'c:\\program files']):
            if 'rm' in command_lower or 'del' in command_lower:
                return True, "Attempting to delete Windows system folder"
        
        return False, ""
    
    def _is_medium_risk_command(self, command):
        """
        Check if command is MEDIUM risk.
        
        These commands could cause problems but won't destroy everything.
        Examples: rm with wildcards, changing permissions
        
        Args:
            command: Command to check
            
        Returns:
            (is_medium_risk, reason)
        """
        command_lower = command.lower()
        
        # Delete with wildcards
        if ('rm' in command_lower or 'del' in command_lower) and '*' in command:
            return True, "Deleting multiple files with wildcard"
        
        # Changing file permissions
        if 'chmod' in command_lower or 'icacls' in command_lower:
            return True, "Changing file permissions"
        
        # Check sensitive paths
        for sensitive_path in self.sensitive_paths:
            if sensitive_path.lower() in command_lower:
                return True, f"Accessing sensitive path: {sensitive_path}"
        
        return False, ""
    
    def _needs_confirmation(self, command):
        """
        Check if command needs user confirmation.
        
        These are potentially risky commands that should be confirmed.
        Examples: rm, kill, chmod, chown
        
        Args:
            command: Command to check
            
        Returns:
            (needs_confirmation, reason)
        """
        command_lower = command.lower()
        
        # Get first word (the command)
        parts = command_lower.split()
        if not parts:
            return False, ""
        
        cmd = parts[0]
        
        # Commands that need confirmation
        confirm_commands = ['rm', 'del', 'kill', 'chmod', 'chown', 'rmdir']
        
        if cmd in confirm_commands:
            return True, f"'{cmd}' command requires confirmation"
        
        return False, ""
    
    def simulate_command(self, command):
        """
        Show what a command would do (without actually running it).
        
        Args:
            command: Command to simulate
            
        Returns:
            Dictionary with simulation results
        """
        # Evaluate the command
        evaluation = self.evaluate_command(command)
        
        # Build simulation result
        parts = command.split()
        cmd = parts[0] if parts else ''
        
        simulation = {
            'command': command,
            'would_execute': evaluation['allowed'],
            'risk_level': evaluation['risk_level'],
            'blocked_reason': evaluation['reason'] if not evaluation['allowed'] else None,
            'warnings': evaluation['warnings'],
            'description': self._describe_command(cmd)
        }
        
        return simulation
    
    def _describe_command(self, cmd):
        """
        Describe what a command does.
        
        Args:
            cmd: Command name
            
        Returns:
            Description string
        """
        descriptions = {
            'rm': 'Removes/deletes files or directories',
            'del': 'Deletes files',
            'kill': 'Terminates a running process',
            'chmod': 'Changes file permissions',
            'chown': 'Changes file owner',
            'mkfs': 'Creates a new filesystem (formats a drive)',
            'dd': 'Copies data at a low level',
            'format': 'Formats a hard drive',
            'mkdir': 'Creates a new directory',
            'cp': 'Copies files or directories',
            'mv': 'Moves or renames files',
            'cat': 'Displays file contents',
            'ls': 'Lists files and directories'
        }
        
        return descriptions.get(cmd.lower(), f"Executes the '{cmd}' command")


# What this module provides to other files
__all__ = ['SafetyGate', 'RiskLevel']
