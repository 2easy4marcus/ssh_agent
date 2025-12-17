""" check the container status(running,healthy,restarting) 
"""
def check_docker_running(ssh) -> tuple[bool, str]:
    """Check if Docker daemon is running."""
    code, out, _ = ssh.execute_command(["systemctl is-active docker"])
    if code == 0 and "active" in out:
        return True, "Docker is running"
    return False, "Docker is not running"


def check_container(ssh, name: str) -> tuple[str, str, str | None]:
    """
    Check container status.
    Returns (status, message, logs_if_failed).
    """
    code, out, _ = ssh.execute_command([f"docker ps -a --filter 'name=^{name}$' --format '{{{{.Status}}}}'"])
    
    if code != 0 or not out.strip():
        return "fail", f"Container '{name}' not found", None
    
    status = out.strip().lower()
    
    if "up" in status:
        if "unhealthy" in status:
            logs = _get_container_logs(ssh, name)
            return "warn", f"Container '{name}' running but unhealthy", logs
        return "ok", f"Container '{name}' is running", None
    
    if "exited" in status or "dead" in status:
        logs = _get_container_logs(ssh, name)
        return "fail", f"Container '{name}' has stopped", logs
    
    if "restarting" in status:
        logs = _get_container_logs(ssh, name)
        return "fail", f"Container '{name}' keeps restarting (crash loop)", logs
    
    return "warn", f"Container '{name}' status unclear: {status}", None


def check_systemd_service(ssh, name: str) -> tuple[str, str, str | None]:
    """
    Check systemd service status.
    Returns (status, message, logs_if_failed).
    """
    code, out, _ = ssh.execute_command([f"systemctl is-active {name}"])
    status = out.strip()
    
    if status == "active":
        return "ok", f"Service '{name}' is running", None
    
    if status in ["inactive", "dead", "failed"]:
        logs = _get_service_logs(ssh, name)
        return "fail", f"Service '{name}' is {status}", logs
    
    return "warn", f"Service '{name}' status: {status}", None


def _get_container_logs(ssh, name: str, lines: int = 50) -> str:
    """Get recent container logs."""
    code, out, _ = ssh.execute_command([f"docker logs --tail {lines} {name} 2>&1"])
    return out if code == 0 else ""


def _get_service_logs(ssh, name: str, lines: int = 50) -> str:
    """Get recent service logs."""
    code, out, _ = ssh.execute_command([f"journalctl -u {name} --no-pager -n {lines} 2>&1"])
    return out if code == 0 else ""
