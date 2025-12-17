"""
Network diagnostics: VPN, connectivity.
"""
import subprocess


def check_tailscale_reachable(hostname: str, timeout: int = 10) -> tuple[bool, str]:
    """Check if host is reachable via Tailscale."""
    try:
        result = subprocess.run(
            ["tailscale", "ping", "-c", "1", hostname],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if "pong" in result.stdout.lower():
            return True, f"Device reachable via Tailscale"
        return False, "Device not responding on Tailscale"
    except FileNotFoundError:
        return False, "Tailscale not installed on this machine"
    except subprocess.TimeoutExpired:
        return False, "Tailscale ping timed out"


def check_network_interfaces(ssh) -> tuple[bool, int, str]:
    """Check network interfaces are up."""
    code, out, _ = ssh.execute_command(["ip link show | grep -c 'state UP'"])
    if code == 0:
        try:
            count = int(out.strip())
            if count > 0:
                return True, count, f"{count} network interface(s) active"
        except:
            pass
    return False, 0, "No active network interfaces"
