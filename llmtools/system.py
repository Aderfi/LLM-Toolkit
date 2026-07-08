import shutil
import subprocess

from llmtools.core import tool


@tool
def system_info() -> str:
    """Report CPU, RAM, and disk usage."""
    try:
        import psutil
    except ImportError:
        return "Error: install 'psutil'."
    vm = psutil.virtual_memory()
    du = shutil.disk_usage("/")
    return (
        f"CPU: {psutil.cpu_percent(interval=0.3)}%\n"
        f"RAM: {vm.percent}% ({vm.used // 2**20}/{vm.total // 2**20} MB)\n"
        f"Disk /: {du.used // 2**30}/{du.total // 2**30} GB used"
    )


@tool
def list_processes(top: int = 10, sort_by: str = "memory") -> str:
    """List the top processes by memory or CPU.

    Args:
        top: Number of processes to show.
        sort_by: 'memory' or 'cpu'.
    """
    try:
        import psutil
    except ImportError:
        return "Error: install 'psutil'."
    key = "memory_percent" if sort_by == "memory" else "cpu_percent"
    procs = [p.info for p in psutil.process_iter(["pid", "name", key])]
    procs.sort(key=lambda x: x.get(key) or 0, reverse=True)
    return "\n".join(f"{p['pid']:>7} {p.get(key) or 0:5.1f}% {p['name']}" for p in procs[:top])


@tool
def desktop_notify(title: str, message: str = "") -> str:
    """Show a desktop notification (uses notify-send).

    Args:
        title: Notification title.
        message: Notification body.
    """
    if shutil.which("notify-send") is None:
        return "Error: 'notify-send' not found."
    subprocess.run(["notify-send", title, message])
    return "Notification sent."
