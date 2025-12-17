import sys
import os
import json
from datetime import datetime
from pathlib import Path

import click
import yaml

from ssh_agent.ssh_client import SSHAgent, SSHBootstrap
from diagnostic import system, network, services, devices



# inventory loading (using yaml directly)
def load_inventory(path: str = "inventory.yaml") -> dict:
    """Load inventory from YAML file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Inventory not found: {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f)



#output header
def print_header(title: str):
    click.echo("")
    click.echo("=" * 65)
    click.echo(f"        {title}")
    click.echo("=" * 65)


def print_step(step: int, total: int, title: str):
    click.echo("")
    click.echo(f"[Step {step}/{total}] {title}")
    click.echo("-" * 45)


def print_ok(message: str):
    click.echo(click.style(f"  ✓ {message}", fg='green'))


def print_fail(message: str):
    click.echo(click.style(f"  ✗ {message}", fg='red'))


def print_warn(message: str):
    click.echo(click.style(f"  ⚠ {message}", fg='yellow'))


def print_info(message: str):
    click.echo(f"    {message}")


def print_hint(message: str):
    click.echo(f"  💡 {message}")


def print_what_to_do(items: list[str]):
    click.echo("")
    click.echo("  WHAT TO DO:")
    for item in items:
        click.echo(f"    {item}")


# support bundle
def save_support_bundle(host_name: str, results: list, logs: dict) -> str:
    """Save diagnostic results and logs for support."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = Path("reports") / host_name / timestamp
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    report_file = bundle_dir / "report.txt"
    with open(report_file, 'w') as f:
        f.write(f"Diagnostic Report: {host_name}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write("=" * 50 + "\n\n")
        for r in results:
            icon = "✓" if r['status'] == 'ok' else ("⚠" if r['status'] == 'warn' else "✗")
            f.write(f"{icon} {r['check']}: {r['message']}\n")
    
    for name, content in logs.items():
        if content:
            log_file = bundle_dir / f"{name}.log"
            with open(log_file, 'w') as f:
                f.write(content)
    
    # Create pasteable support message
    msg_file = bundle_dir / "support_message.txt"
    failures = [r for r in results if r['status'] == 'fail']
    warnings = [r for r in results if r['status'] == 'warn']
    
    with open(msg_file, 'w') as f:
        f.write("--- SUPPORT REQUEST ---\n")
        f.write(f"Host: {host_name}\n")
        f.write(f"Time: {datetime.now().isoformat()}\n\n")
        if failures:
            f.write("FAILURES:\n")
            for r in failures:
                f.write(f"  ✗ {r['check']}: {r['message']}\n")
        if warnings:
            f.write("\nWARNINGS:\n")
            for r in warnings:
                f.write(f"  ⚠ {r['check']}: {r['message']}\n")
        f.write(f"\nBundle: {bundle_dir}\n")
        f.write("--- END ---\n")
    
    return str(bundle_dir)


# ============================================================
# DIAGNOSTIC RUNNER
# ============================================================

def run_diagnostics(host_name: str, host_config: dict, checks: list, verbose: bool) -> tuple[list, bool]:
    """Run diagnostics for a single host. Returns (results, success)."""
    
    results = []
    logs = {}
    conn = host_config.get('connection', {})
    
    print_header(f"DIAGNOSING: {host_name}")
    click.echo(f"  Target: {conn.get('hostname', 'unknown')}")
    click.echo(f"  User: {conn.get('username', 'unknown')}")
    
    total_steps = len(checks) + 1  # +1 for SSH connection
    current_step = 0
    
    
    # STEP: SSH Connection with auto-bootstrap
    current_step += 1
    print_step(current_step, total_steps, "Establishing Connection")
    click.echo("  Connecting to the device...")
    
    bootstrap = SSHBootstrap(
        host=conn.get('hostname', ''),
        username=conn.get('username', ''),
        password=conn.get('password'),
        key_path=conn.get('ssh_key_path'),
        port=conn.get('port', 22)
    )
    
    try:
        ssh, messages = bootstrap.bootstrap_and_connect()
        for msg in messages:
            click.echo(f"  {msg}")
        results.append({'check': 'SSH Connection', 'status': 'ok', 'message': 'Connected successfully'})
    except ConnectionError as e:
        print_fail("Could not connect to device")
        print_what_to_do([
            "1. Check if the device is powered on",
            "2. Verify network/VPN connection",
            "3. Check credentials in inventory.yaml",
            f"4. Try manually: ssh {conn.get('username')}@{conn.get('hostname')}"
        ])
        results.append({'check': 'SSH Connection', 'status': 'fail', 'message': str(e)})
        return results, False
    
    # --------------------------------------------------------
    # STEP: System Checks
    # --------------------------------------------------------
    if 'system' in checks:
        current_step += 1
        print_step(current_step, total_steps, "System Health")
        
        # Hostname
        ok, val, msg = system.check_hostname(ssh)
        print_ok(msg) if ok else print_fail(msg)
        results.append({'check': 'Hostname', 'status': 'ok' if ok else 'fail', 'message': msg})
        
        # Uptime
        ok, val, msg = system.check_uptime(ssh)
        print_ok(msg) if ok else print_warn(msg)
        results.append({'check': 'Uptime', 'status': 'ok' if ok else 'warn', 'message': msg})
        
        # CPU
        status, val, msg = system.check_cpu_load(ssh)
        if status == 'ok': print_ok(msg)
        elif status == 'warn': print_warn(msg)
        else: print_fail(msg)
        results.append({'check': 'CPU Load', 'status': status, 'message': msg})
        
        # Memory
        status, val, msg = system.check_memory(ssh)
        if status == 'ok': print_ok(msg)
        elif status == 'warn': print_warn(msg)
        else: print_fail(msg)
        results.append({'check': 'Memory', 'status': status, 'message': msg})
        if status == 'fail':
            print_hint("Consider restarting the device or stopping unused services")
        
        # Disk
        status, val, msg = system.check_disk(ssh)
        if status == 'ok': print_ok(msg)
        elif status == 'warn': print_warn(msg)
        else: print_fail(msg)
        results.append({'check': 'Disk', 'status': status, 'message': msg})
        if status != 'ok':
            print_hint("Delete old logs or unused files to free space")
    
    # --------------------------------------------------------
    # STEP: Network Checks
    # --------------------------------------------------------
    if 'network' in checks:
        current_step += 1
        print_step(current_step, total_steps, "Network Status")
        
        net_config = host_config.get('network', {})
        vpn_type = net_config.get('vpn_type', 'none')
        
        # VPN check (from local machine)
        if vpn_type == 'tailscale':
            ok, msg = network.check_tailscale_reachable(conn.get('hostname', ''))
            print_ok(msg) if ok else print_warn(msg)
            results.append({'check': 'Tailscale VPN', 'status': 'ok' if ok else 'warn', 'message': msg})
        
        # Network interfaces (on remote)
        ok, count, msg = network.check_network_interfaces(ssh)
        print_ok(msg) if ok else print_fail(msg)
        results.append({'check': 'Network Interfaces', 'status': 'ok' if ok else 'fail', 'message': msg})
    
    # --------------------------------------------------------
    # STEP: Services Checks
    # --------------------------------------------------------
    if 'services' in checks:
        current_step += 1
        print_step(current_step, total_steps, "Services Status")
        
        svc_config = host_config.get('services', {})
        
        # Docker daemon
        ok, msg = services.check_docker_running(ssh)
        print_ok(msg) if ok else print_fail(msg)
        results.append({'check': 'Docker Daemon', 'status': 'ok' if ok else 'fail', 'message': msg})
        
        if not ok:
            print_hint("Run: sudo systemctl start docker")
        else:
            # Check containers
            for container in svc_config.get('docker_containers', []):
                status, msg, container_logs = services.check_container(ssh, container)
                if status == 'ok': print_ok(msg)
                elif status == 'warn': print_warn(msg)
                else: print_fail(msg)
                results.append({'check': f'Container: {container}', 'status': status, 'message': msg})
                if container_logs:
                    logs[f'container_{container}'] = container_logs
                    if verbose:
                        print_info(f"Logs saved for {container}")
        
        # Systemd services
        for service in svc_config.get('systemd_services', []):
            status, msg, svc_logs = services.check_systemd_service(ssh, service)
            if status == 'ok': print_ok(msg)
            elif status == 'warn': print_warn(msg)
            else: print_fail(msg)
            results.append({'check': f'Service: {service}', 'status': status, 'message': msg})
            if svc_logs:
                logs[f'service_{service}'] = svc_logs
    
    # --------------------------------------------------------
    # STEP: Device Checks (USB)
    # --------------------------------------------------------
    if 'devices' in checks:
        current_step += 1
        print_step(current_step, total_steps, "Device Detection")
        
        dev_config = host_config.get('devices', {})
        usb_devices = dev_config.get('usb', [])
        
        # List all USB devices
        click.echo("  Scanning USB devices...")
        all_usb = devices.list_all_usb_devices()
        if all_usb:
            print_ok(f"Found {len(all_usb)} USB device(s)")
            if verbose:
                for d in all_usb[:5]:  # Show first 5
                    print_info(f"{d['vendor_id']}:{d['product_id']} - {d['product']}")
        else:
            print_warn("Could not list USB devices (pyusb may need root)")
        
        # Check required devices
        for usb_dev in usb_devices:
            name = usb_dev.get('name', 'Unknown')
            vid = usb_dev.get('vendor_id', '')
            pid = usb_dev.get('product_id', '')
            required = usb_dev.get('required', True)
            
            found, info = devices.find_usb_device(vid, pid)
            
            if found:
                print_ok(f"{name} detected")
                if verbose and info:
                    print_info(f"Serial: {info.get('serial', 'N/A')}")
                results.append({'check': f'Device: {name}', 'status': 'ok', 'message': f'{name} connected'})
            else:
                if required:
                    print_fail(f"{name} NOT FOUND")
                    print_hint(f"Check if {name} is properly connected")
                    results.append({'check': f'Device: {name}', 'status': 'fail', 'message': f'{name} missing'})
                else:
                    print_warn(f"{name} not found (optional)")
                    results.append({'check': f'Device: {name}', 'status': 'warn', 'message': f'{name} not found'})
    
    # Cleanup
    ssh.disconnect()
    
    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------
    print_header("DIAGNOSTIC SUMMARY")
    
    ok_count = sum(1 for r in results if r['status'] == 'ok')
    warn_count = sum(1 for r in results if r['status'] == 'warn')
    fail_count = sum(1 for r in results if r['status'] == 'fail')
    
    click.echo(f"  ✓ Passed: {ok_count}")
    click.echo(f"  ⚠ Warnings: {warn_count}")
    click.echo(f"  ✗ Failed: {fail_count}")
    click.echo("")
    
    if fail_count > 0:
        click.echo("  WHAT'S BROKEN:")
        for r in results:
            if r['status'] == 'fail':
                click.echo(f"    ✗ {r['check']}: {r['message']}")
        click.echo("")
        
        # Save support bundle
        bundle_path = save_support_bundle(host_name, results, logs)
        print_warn(f"Support bundle saved: {bundle_path}")
        click.echo("")
        click.echo("  Copy the content of support_message.txt to send to support.")
    
    elif warn_count > 0:
        click.echo("  WHAT NEEDS ATTENTION:")
        for r in results:
            if r['status'] == 'warn':
                click.echo(f"    ⚠ {r['check']}: {r['message']}")
    else:
        print_ok("All checks passed! Device is healthy.")
    
    click.echo("")
    click.echo("=" * 65)
    
    return results, fail_count == 0


# ============================================================
# CLI
# ============================================================

@click.command()
@click.option('--host', '-h', multiple=True, help='Host(s) to diagnose')
@click.option('--all-hosts', is_flag=True, help='Diagnose all hosts')
@click.option('--check', '-c', multiple=True, 
              type=click.Choice(['system', 'network', 'services', 'devices']),
              help='Specific checks (default: all)')
@click.option('--verbose', '-v', is_flag=True, help='Show more details')
@click.option('--json-output', is_flag=True, help='Output as JSON')
@click.option('--inventory', default='inventory.yaml', help='Inventory file')


def main(host, all_hosts, check, verbose, json_output, inventory):
    """
    Edge Node Diagnostic Tool
    
    Run diagnostics on devices defined in inventory.yaml.
    """
    # Load inventory
    try:
        inv = load_inventory(inventory)
    except FileNotFoundError:
        print_fail(f"Inventory not found: {inventory}")
        sys.exit(1)
    
    # No host specified - show help
    if not host and not all_hosts:
        print_header("EDGE NODE DIAGNOSTIC TOOL")
        click.echo("")
        click.echo("  Available hosts:")
        for h in inv.keys():
            conn = inv[h].get('connection', {})
            click.echo(f"    • {h} ({conn.get('hostname', '?')})")
        click.echo("")
        click.echo("  Usage:")
        click.echo(f"    python overall_diagnose.py --host {list(inv.keys())[0]}")
        click.echo("    python overall_diagnose.py --all-hosts")
        click.echo("    python overall_diagnose.py --host ocu4 --check system --check services")
        click.echo("")
        click.echo("  Available checks: system, network, services, devices")
        click.echo("")
        sys.exit(0)
    
    # Determine hosts,parse yaml to dict
    if all_hosts:
        targets = list(inv.keys())
    else:
        targets = list(host)
        for h in targets:
            if h not in inv:
                print_fail(f"Host '{h}' not in inventory")
                click.echo(f"  Available: {', '.join(inv.keys())}")
                sys.exit(1)
    
    # Determine arguments
    checks = list(check) if check else ['system', 'network', 'services', 'devices']
    
    # Run diagnostics
    all_results = []
    all_success = True
    
    for target in targets:
        results, success = run_diagnostics(target, inv[target], checks, verbose)
        all_results.append({'host': target, 'results': results, 'success': success})
        if not success:
            all_success = False
    
    # JSON output
    if json_output:
        click.echo(json.dumps(all_results, indent=2))
    
    # Multi-host summary
    if len(targets) > 1:
        print_header("MULTI-HOST SUMMARY")
        for r in all_results:
            icon = "✓" if r['success'] else "✗"
            click.echo(f"  {icon} {r['host']}")
        click.echo("")
    
    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
