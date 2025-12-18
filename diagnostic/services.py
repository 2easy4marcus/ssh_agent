
import yaml


def get_containers_from_compose_dir(ssh, compose_dir: str) -> list[str]:
    code, out, _ = ssh.execute_command([
        f"find {compose_dir} -maxdepth 1 \\( -name '*.yml' -o -name '*.yaml' \\) 2>/dev/null"
    ])
    
    if code != 0 or not out.strip():
        return []
    
    yaml_files = [f.strip() for f in out.strip().split('\n') if f.strip()]
    all_services = []
    
    for yaml_file in yaml_files:
        services = _parse_if_compose(ssh, yaml_file)
        all_services.extend(services)
    
    seen = set()
    unique_services = []
    for s in all_services:
        if s not in seen:
            seen.add(s)
            unique_services.append(s)
    
    return unique_services

#this one is good for prekit as it has more than one compose 
def _parse_if_compose(ssh, yaml_path: str) -> list[str]:
    """
    Parse yaml file and return services only if it's a docker-compose file.
    A docker-compose file has a 'services' key at the root level.
    """
    code, out, _ = ssh.execute_command([f"cat {yaml_path} 2>/dev/null"])
    
    if code != 0 or not out.strip():
        return []
    
    try:
        data = yaml.safe_load(out)
        if not isinstance(data, dict):
            return []
        
        if 'services' not in data:
            return []  #could be pipeline, config, etc.
        
        services = data.get('services', {})
        if isinstance(services, dict):
            return list(services.keys())
        return []
    except:
        return []


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
    
    Priority:
    1. Restarting = FAIL (crash loop - serious problem!)
    2. Exited/Dead = FAIL (stopped)
    3. Unhealthy = WARN (running but sick)
    4. Up/Running = OK
    """
    # Get container state more reliably
    code, out, _ = ssh.execute_command([
        f"docker ps -a --filter 'name={name}' --format '{{{{.State}}}} {{{{.Status}}}}'"
    ])
    
    if code != 0 or not out.strip():
        return "fail", f"Container '{name}' not found", None
    
    state_status = out.strip().lower()
    
    # PRIORITY 1: Check for restarting FIRST - this is a serious problem!
    if "restarting" in state_status:
        logs = _get_container_logs(ssh, name)
        return "fail", f"Container '{name}' is RESTARTING (crash loop!)", logs
    
    # PRIORITY 2: Check for stopped/dead containers
    if "exited" in state_status or "dead" in state_status:
        logs = _get_container_logs(ssh, name)
        return "fail", f"Container '{name}' has stopped", logs
    
    # PRIORITY 3: Check for running but unhealthy
    if "running" in state_status or "up" in state_status:
        if "unhealthy" in state_status:
            logs = _get_container_logs(ssh, name)
            return "warn", f"Container '{name}' running but unhealthy", logs
        return "ok", f"Container '{name}' is running", None
    
    # Unknown state
    return "warn", f"Container '{name}' status unclear: {state_status}", None


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
