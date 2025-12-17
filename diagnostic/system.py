
def check_hostname(ssh) -> tuple[bool, str, str]:
    """Get hostname. Returns (ok, value, message)."""
    code, out, _ = ssh.execute_command(["hostname"])
    if code == 0:
        return True, out.strip(), f"Device name: {out.strip()}"
    return False, "", "Could not get hostname"


def check_uptime(ssh) -> tuple[bool, str, str]:
    """Get uptime. Returns (ok, value, message)."""
    code, out, _ = ssh.execute_command(["uptime -p"])
    if code == 0:
        return True, out.strip(), f"System {out.strip()}"
    return False, "", "Could not get uptime"


def check_cpu_load(ssh) -> tuple[str, float, str]:
    """Check CPU load. Returns (status, value, message)."""
    code, out, _ = ssh.execute_command(["cat /proc/loadavg | awk '{print $1}'"])
    if code != 0:
        return "warn", 0, "Could not check CPU"
    
    try:
        load = float(out.strip())
        code2, cores, _ = ssh.execute_command(["nproc"])
        cpu_count = int(cores.strip()) if code2 == 0 else 1
        ratio = load / cpu_count
        
        if ratio < 0.7:
            return "ok", load, f"CPU load normal ({load:.1f} on {cpu_count} cores)"
        elif ratio < 1.0:
            return "warn", load, f"CPU load elevated ({load:.1f} on {cpu_count} cores)"
        else:
            return "fail", load, f"CPU overloaded ({load:.1f} on {cpu_count} cores)"
    except:
        return "warn", 0, "Could not parse CPU load"


def check_memory(ssh) -> tuple[str, int, str]:
    """Check memory usage. Returns (status, percent, message)."""
    code, out, _ = ssh.execute_command(["free -m | awk 'NR==2{printf \"%.0f\", $3*100/$2}'"])
    if code != 0:
        return "warn", 0, "Could not check memory"
    
    try:
        usage = int(out.strip())
        if usage < 70:
            return "ok", usage, f"Memory OK ({usage}% used)"
        elif usage < 85:
            return "warn", usage, f"Memory getting low ({usage}% used)"
        else:
            return "fail", usage, f"Memory critical ({usage}% used)"
    except:
        return "warn", 0, "Could not parse memory"


def check_disk(ssh) -> tuple[str, int, str]:
    """Check disk usage. Returns (status, percent, message)."""
    code, out, _ = ssh.execute_command(["df -h / | tail -1 | awk '{print $5}' | tr -d '%'"])
    if code != 0:
        return "warn", 0, "Could not check disk"
    
    try:
        usage = int(out.strip())
        if usage < 70:
            return "ok", usage, f"Disk space OK ({usage}% used)"
        elif usage < 85:
            return "warn", usage, f"Disk getting full ({usage}% used)"
        else:
            return "fail", usage, f"Disk critical ({usage}% used)"
    except:
        return "warn", 0, "Could not parse disk usage"
