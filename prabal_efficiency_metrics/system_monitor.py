import psutil  # For getting system information
import logging  # For tracking what happens
from datetime import datetime  # For timestamps


class SystemMonitor:
    """
    Monitors your computer's performance.
    
    Simple explanation:
    Checks how much CPU, memory, and disk space you're using.
    """
    
    def __init__(self, config=None):
        """
        Set up the system monitor.
        
        Args:
            config: Settings dictionary (optional)
        """
        config = config or {}
        self.logger = logging.getLogger("Osiris.SystemMonitor")
        
        # Warning thresholds (when to warn about high usage)
        self.cpu_high_threshold = config.get('cpu_high', 80.0)      # 80%
        self.memory_high_threshold = config.get('memory_high', 85.0)  # 85%
        self.disk_high_threshold = config.get('disk_high', 90.0)    # 90%
        
        self.logger.info("System Monitor ready (using psutil)")
    
    def get_current_metrics(self):
        """
        Get current system performance metrics.
        
        Returns:
            Dictionary with:
                - cpu_percent: CPU usage (0-100%)
                - cpu_count: Number of CPU cores
                - memory_percent: Memory usage (0-100%)
                - memory_available_gb: Available memory in GB
                - memory_total_gb: Total memory in GB
                - disk_percent: Disk usage (0-100%)
                - disk_free_gb: Free disk space in GB
                - process_count: Number of running programs
                - timestamp: When this was measured
        """
        try:
            # === CPU INFORMATION ===
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Wait 0.1s for accurate reading
            cpu_count = psutil.cpu_count()  # Number of cores
            
            # === MEMORY INFORMATION ===
            memory = psutil.virtual_memory()  # Get memory info
            memory_percent = memory.percent  # How much is used (%)
            memory_available_gb = memory.available / (1024 ** 3)  # Available in GB
            memory_total_gb = memory.total / (1024 ** 3)  # Total in GB
            
            # === DISK INFORMATION ===
            disk = psutil.disk_usage('/')  # Get disk info for main drive
            disk_percent = disk.percent  # How much is used (%)
            disk_free_gb = disk.free / (1024 ** 3)  # Free space in GB
            
            # === PROCESS INFORMATION ===
            process_count = len(psutil.pids())  # Count running programs
            
            # Build result dictionary
            return {
                'timestamp': datetime.now(),
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_percent': memory_percent,
                'memory_available_gb': memory_available_gb,
                'memory_total_gb': memory_total_gb,
                'disk_percent': disk_percent,
                'disk_free_gb': disk_free_gb,
                'process_count': process_count
            }
        
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return None
    
    def check_resource_pressure(self, metrics=None):
        """
        Check if system resources are running low.
        
        Args:
            metrics: System metrics (optional, will get current if not provided)
            
        Returns:
            Dictionary with:
                - cpu_pressure: Is CPU high? (True/False)
                - memory_pressure: Is memory high? (True/False)
                - disk_pressure: Is disk high? (True/False)
                - warnings: List of warning messages
        """
        # Get current metrics if not provided
        if metrics is None:
            metrics = self.get_current_metrics()
        
        if not metrics:
            return {
                'cpu_pressure': False,
                'memory_pressure': False,
                'disk_pressure': False,
                'warnings': ['Could not get system metrics']
            }
        
        # Check each resource
        cpu_high = metrics['cpu_percent'] > self.cpu_high_threshold
        memory_high = metrics['memory_percent'] > self.memory_high_threshold
        disk_high = metrics['disk_percent'] > self.disk_high_threshold
        
        # Build warning messages
        warnings = []
        if cpu_high:
            warnings.append(f"High CPU usage: {metrics['cpu_percent']:.1f}%")
        if memory_high:
            warnings.append(f"High memory usage: {metrics['memory_percent']:.1f}%")
        if disk_high:
            warnings.append(f"High disk usage: {metrics['disk_percent']:.1f}%")
        
        return {
            'cpu_pressure': cpu_high,
            'memory_pressure': memory_high,
            'disk_pressure': disk_high,
            'warnings': warnings
        }
    
    def format_metrics_display(self, metrics=None):
        """
        Format metrics into a nice display string.
        
        Args:
            metrics: System metrics (optional, will get current if not provided)
            
        Returns:
            Formatted string for display
        """
        # Get current metrics if not provided
        if metrics is None:
            metrics = self.get_current_metrics()
        
        if not metrics:
            return "❌ Could not get system metrics"
        
        # Get pressure info
        pressure = self.check_resource_pressure(metrics)
        
        # Choose emoji/icon based on usage
        cpu_icon = "🔴" if pressure['cpu_pressure'] else "🟢"
        memory_icon = "🔴" if pressure['memory_pressure'] else "🟢"
        disk_icon = "🔴" if pressure['disk_pressure'] else "🟢"
        
        # Build the display string
        display = f"{cpu_icon} CPU: {metrics['cpu_percent']:.1f}% | "
        display += f"{memory_icon} MEM: {metrics['memory_percent']:.1f}% | "
        display += f"{disk_icon} DISK: {metrics['disk_percent']:.1f}% | "
        display += f"Processes: {metrics['process_count']}"
        
        return display
    
    def get_detailed_metrics(self):
        """
        Get detailed system metrics with more information.
        
        Returns:
            Dictionary with detailed metrics
        """
        metrics = self.get_current_metrics()
        if not metrics:
            return None
        
        pressure = self.check_resource_pressure(metrics)
        
        # Add detailed information
        detailed = {
            **metrics,  # Include all basic metrics
            'cpu_pressure': pressure['cpu_pressure'],
            'memory_pressure': pressure['memory_pressure'],
            'disk_pressure': pressure['disk_pressure'],
            'warnings': pressure['warnings'],
            'formatted_display': self.format_metrics_display(metrics)
        }
        
        return detailed
    
    def get_simple_status(self):
        """
        Get a simple status message.
        
        Returns:
            String with overall system status
        """
        metrics = self.get_current_metrics()
        if not metrics:
            return "System status: Unknown"
        
        pressure = self.check_resource_pressure(metrics)
        
        # Determine overall status
        if pressure['cpu_pressure'] or pressure['memory_pressure'] or pressure['disk_pressure']:
            status = "⚠️  High resource usage"
        else:
            status = "✅ All systems normal"
        
        return status


# What this module provides to other files
__all__ = ['SystemMonitor']
