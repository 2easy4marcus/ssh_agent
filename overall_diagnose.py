#!/usr/bin/env python3
"""
Edge Node Diagnostic Tool
Simple, friendly diagnostics for any host in inventory.yaml
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

import click
import yaml

from ssh_agent.ssh_client import SSHAgent, SSHBootstrap
from diagnostic import system, network, services, devices


def load_inventory(path: str = "inventory.yaml") -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Inventory not found: {path}")
    with open(path, 'r') as f:
        return yaml.safe_load(f)


# ============================================================
# FRIENDLY OUTPUT HELPERS
# ============================================================

def print_header(title: str):
    click.echo("")
    click.echo("╔" + "═" * 63 + "╗")
    click.echo(f"║{title:^63}║")
    click.echo("╚" + "═" * 63 + "╝")


def print_section(emoji: str, title: str):
    click.echo("")
    click.echo(f"  {emoji} {title}")
    click.echo("  " + "─" * 40)


def print_ok(message: str):
    click.echo(click.style(f"    ✅ {message}", fg='green'))


def print_fail(message: str):
    click.echo(click.style(f"    ❌ {message}", fg='red'))


def print_warn(message: str):
    click.echo(click.style(f"    ⚠️  {message}", fg='yellow'))


def print_info(message: str):
    click.echo(f"       {message}")


def print_hint(message: str):
    click.echo(click.style(f"       💡 {message}", fg='cyan'))



def dump_report(host_name: str, results: list, logs: dict) -> str:
    """Save a mom-friendly diagnostic report. Deletes old reports first."""
    import shutil
    
    # Delete old reports /easier for clients
    host_reports_dir = Path("reports") / host_name
    if host_reports_dir.exists():
        shutil.rmtree(host_reports_dir)
    
    # Create new one
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bundle_dir = host_reports_dir / timestamp
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Count results
    ok_count = sum(1 for r in results if r['status'] == 'ok')
    warn_count = sum(1 for r in results if r['status'] == 'warn')
    fail_count = sum(1 for r in results if r['status'] == 'fail')
    
    # Friendly report
    report_file = bundle_dir / "report.txt"
    with open(report_file, 'w') as f:
        f.write("╔═══════════════════════════════════════════════════════════════╗\n")
        f.write("║              🔍 DEVICE HEALTH CHECK REPORT                    ║\n")
        f.write("╚═══════════════════════════════════════════════════════════════╝\n\n")
        
        f.write(f"📅 Date: {datetime.now().strftime('%B %d, %Y at %H:%M')}\n")
        f.write(f"🖥️  Device: {host_name}\n\n")
        
        # Overall status - big and clear
        f.write("─" * 50 + "\n")
        if fail_count > 0:
            f.write("🔴 OVERALL STATUS: PROBLEMS FOUND\n")
            f.write("   Some things need to be fixed.\n")
        elif warn_count > 0:
            f.write("🟡 OVERALL STATUS: MOSTLY OK\n")
            f.write("   Everything works, but some things need attention.\n")
        else:
            f.write("🟢 OVERALL STATUS: ALL GOOD!\n")
            f.write("   Everything is working perfectly.\n")
        f.write("─" * 50 + "\n\n")
        
        # Summary counts
        f.write("📊 QUICK SUMMARY:\n")
        f.write(f"   ✅ Working fine: {ok_count} checks\n")
        if warn_count > 0:
            f.write(f"   ⚠️  Needs attention: {warn_count} checks\n")
        if fail_count > 0:
            f.write(f"   ❌ Problems: {fail_count} checks\n")
        f.write("\n")
        
        # Problems section (if any)
        if fail_count > 0:
            f.write("─" * 50 + "\n")
            f.write("❌ PROBLEMS THAT NEED FIXING:\n")
            f.write("─" * 50 + "\n\n")
            for r in results:
                if r['status'] == 'fail':
                    f.write(f"   Problem: {_friendly_name(r['check'])}\n")
                    f.write(f"   What's wrong: {_friendly_message(r['check'], r['message'])}\n")
                    f.write(f"   How to fix: {_friendly_fix(r['check'])}\n\n")
        
        # Warnings section (if any)
        if warn_count > 0:
            f.write("─" * 50 + "\n")
            f.write("⚠️  THINGS TO KEEP AN EYE ON:\n")
            f.write("─" * 50 + "\n\n")
            for r in results:
                if r['status'] == 'warn':
                    f.write(f"   Notice: {_friendly_name(r['check'])}\n")
                    f.write(f"   What's happening: {_friendly_message(r['check'], r['message'])}\n")
                    f.write(f"   Suggestion: {_friendly_fix(r['check'])}\n\n")
        
        # What's working (summary only)
        f.write("─" * 50 + "\n")
        f.write("✅ WHAT'S WORKING FINE:\n")
        f.write("─" * 50 + "\n\n")
        
        # Group by category
        categories = {
            'connection': [],
            'system': [],
            'network': [],
            'services': [],
            'devices': []
        }
        for r in results:
            if r['status'] == 'ok':
                cat = _get_category(r['check'])
                categories[cat].append(r['check'])
        
        if categories['connection']:
            f.write("   🔌 Connection: Device is reachable\n")
        if categories['system']:
            f.write(f"   💻 System Health: All {len(categories['system'])} checks passed\n")
        if categories['network']:
            f.write(f"   🌐 Network: All {len(categories['network'])} checks passed\n")
        if categories['services']:
            f.write(f"   ⚙️  Services: All {len(categories['services'])} services running\n")
        if categories['devices']:
            f.write(f"   🔌 Devices: All {len(categories['devices'])} devices connected\n")
        
        f.write("\n")
        f.write("─" * 50 + "\n")
        f.write("📞 Need help? Contact technical support with this report.\n")
        f.write("─" * 50 + "\n")
    
    # Save logs for technical support
    for name, content in logs.items():
        if content:
            log_file = bundle_dir / f"{name}.log"
            with open(log_file, 'w') as f:
                f.write(content)
    
    # Simple support message
    msg_file = bundle_dir / "support_message.txt"
    with open(msg_file, 'w') as f:
        f.write("Hi Support Team,\n\n")
        f.write(f"I ran a health check on device '{host_name}' and found some issues.\n\n")
        
        if fail_count > 0:
            f.write("🔴 Problems found:\n")
            for r in results:
                if r['status'] == 'fail':
                    f.write(f"   • {_friendly_name(r['check'])}: {_friendly_message(r['check'], r['message'])}\n")
            f.write("\n")
        
        if warn_count > 0:
            f.write("🟡 Warnings:\n")
            for r in results:
                if r['status'] == 'warn':
                    f.write(f"   • {_friendly_name(r['check'])}: {_friendly_message(r['check'], r['message'])}\n")
            f.write("\n")
        
        f.write(f"Check date: {datetime.now().strftime('%B %d, %Y at %H:%M')}\n")
        f.write(f"Full report attached in: {bundle_dir}\n\n")
        f.write("Thanks!\n")
    
    return str(bundle_dir)


def _friendly_name(check: str) -> str:
    """Convert technical check name to friendly name."""
    mappings = {
        'SSH Connection': 'Device Connection',
        'Hostname': 'Device Name',
        'Uptime': 'Running Time',
        'CPU Load': 'Processor Usage',
        'Memory': 'Memory Usage',
        'Disk': 'Storage Space',
        'Tailscale VPN': 'VPN Connection',
        'Network Interfaces': 'Network Connection',
        'Docker Daemon': 'Application Engine',
    }
    if check in mappings:
        return mappings[check]
    if check.startswith('Container:'):
        return f"App: {check.replace('Container: ', '')}"
    if check.startswith('Service:'):
        return f"Service: {check.replace('Service: ', '')}"
    if check.startswith('Device:'):
        return check.replace('Device: ', '')
    return check


def _friendly_message(check: str, message: str) -> str:
    """Convert technical message to friendly message."""
    # RESTARTING is the most serious - check first!
    if 'restarting' in message.lower() or 'crash loop' in message.lower():
        return "🚨 CRITICAL: This app keeps crashing and restarting over and over! It cannot work properly."
    if 'Memory' in check and 'low' in message.lower():
        return "The device is running low on memory (like when your phone gets slow)"
    if 'Disk' in check and ('full' in message.lower() or 'low' in message.lower()):
        return "Storage space is running low (like when your phone says 'storage full')"
    if 'CPU' in check and ('high' in message.lower() or 'overload' in message.lower()):
        return "The device is working very hard and might be slow"
    if 'VPN' in check or 'Tailscale' in check:
        return "The secure connection to the device might have issues"
    if 'not found' in message.lower() or 'missing' in message.lower():
        return "This component is not connected or not working"
    if 'stopped' in message.lower() or 'not running' in message.lower():
        return "This service has stopped and needs to be restarted"
    if 'unhealthy' in message.lower():
        return "This app is running but reporting health problems"
    return message


def _friendly_fix(check: str) -> str:
    """Get friendly fix suggestion based on check name and message."""
    fixes = {
        'Memory': "Try restarting the device, or contact support if it keeps happening",
        'Disk': "Old files may need to be cleaned up - contact support for help",
        'CPU Load': "The device might need a restart, or there's too much running",
        'Tailscale VPN': "Check your internet connection, or try restarting the VPN",
        'Network Interfaces': "Check if network cables are connected properly",
        'Docker Daemon': "The application engine needs to be restarted - contact support",
        'SSH Connection': "Make sure the device is powered on and connected to the network",
    }
    if check in fixes:
        return fixes[check]
    if 'Container:' in check or 'Service:' in check:
        return "⚠️ CONTACT SUPPORT IMMEDIATELY - This app needs to be fixed by a technician"
    if 'Device:' in check:
        return "Check if the device is plugged in properly, try a different USB port"
    return "Contact support for assistance"


def _friendly_fix_for_message(check: str, message: str) -> str:
    """Get specific fix based on the actual problem."""
    if 'restarting' in message.lower() or 'crash loop' in message.lower():
        return "🚨 URGENT: Contact support immediately! This app is broken and keeps crashing."
    if 'unhealthy' in message.lower():
        return "The app is working but has issues - monitor it and contact support if it gets worse"
    if 'stopped' in message.lower():
        return "The app needs to be restarted - contact support for help"
    return _friendly_fix(check)


def _get_category(check: str) -> str:
    """Get category for a check."""
    if check == 'SSH Connection':
        return 'connection'
    if check in ['Hostname', 'Uptime', 'CPU Load', 'Memory', 'Disk']:
        return 'system'
    if check in ['Tailscale VPN', 'Network Interfaces']:
        return 'network'
    if 'Container:' in check or 'Service:' in check or check == 'Docker Daemon':
        return 'services'
    if 'Device:' in check:
        return 'devices'
    return 'system'


# ============================================================
# DIAGNOSTIC RUNNER
# ============================================================

def run_diagnostics(host_name: str, host_config: dict, checks: list, verbose: bool) -> tuple[list, bool]:
    """Run diagnostics for a single host."""
    
    results = []
    logs = {}
    conn = host_config.get('connection', {})
    
    print_header(f"🔍 Checking: {host_name}")
    click.echo(f"    Connecting to {conn.get('hostname', 'unknown')}...")
    
    # SSH Connection
    bootstrap = SSHBootstrap(
        host=conn.get('hostname', ''),
        username=conn.get('username', ''),
        password=conn.get('password'),
        key_path=conn.get('ssh_key_path'),
        port=conn.get('port', 22)
    )
    
    try:
        ssh, messages = bootstrap.bootstrap_and_connect()
        print_ok("Connected to device")
        results.append({'check': 'SSH Connection', 'status': 'ok', 'message': 'Connected'})
    except ConnectionError as e:
        print_fail("Could not connect to device")
        print_hint("Check if device is on and connected to network")
        results.append({'check': 'SSH Connection', 'status': 'fail', 'message': str(e)})
        return results, False
    
    # System Checks
    if 'system' in checks:
        print_section("💻", "System Health")
        
        ok, val, msg = system.check_hostname(ssh)
        print_ok(f"Device: {val}") if ok else print_fail("Could not identify device")
        results.append({'check': 'Hostname', 'status': 'ok' if ok else 'fail', 'message': msg})
        
        ok, val, msg = system.check_uptime(ssh)
        print_ok(msg) if ok else print_warn(msg)
        results.append({'check': 'Uptime', 'status': 'ok' if ok else 'warn', 'message': msg})
        
        status, val, msg = system.check_cpu_load(ssh)
        if verbose:
            # Show detailed CPU info
            if status == 'ok': 
                print_ok(f"CPU: {msg}")
            elif status == 'warn': 
                print_warn(f"CPU: {msg}")
            else: 
                print_fail(f"CPU: {msg}")
        else:
            if status == 'ok': 
                print_ok("Processor running smoothly")
            elif status == 'warn': 
                print_warn("Processor working hard")
                print_hint("Device might be slow - consider restarting")
            else: 
                print_fail("Processor overloaded!")
        results.append({'check': 'CPU Load', 'status': status, 'message': msg})
        
        status, val, msg = system.check_memory(ssh)
        if status == 'ok': 
            print_ok(f"Memory OK ({val}% used)")
        elif status == 'warn': 
            print_warn(f"Memory getting low ({val}% used)")
            if not verbose:
                print_hint("Close unused apps or restart device")
        else: 
            print_fail(f"Memory critical ({val}% used)!")
        results.append({'check': 'Memory', 'status': status, 'message': msg})
        
        status, val, msg = system.check_disk(ssh)
        if status == 'ok': 
            print_ok(f"Storage OK ({val}% used)")
        elif status == 'warn': 
            print_warn(f"Storage getting full ({val}% used)")
            if not verbose:
                print_hint("Old files may need cleanup")
        else: 
            print_fail(f"Storage almost full ({val}% used)!")
        results.append({'check': 'Disk', 'status': status, 'message': msg})
    
    # Network Checks
    if 'network' in checks:
        print_section("🌐", "Network")
        
        # Always check Tailscale VPN
        ok, msg = network.check_tailscale_reachable(conn.get('hostname', ''))
        if ok:
            print_ok("Tailscale VPN working")
        else:
            print_warn("Tailscale VPN might have issues")
            print_hint("Run: tailscale status")
        results.append({'check': 'Tailscale VPN', 'status': 'ok' if ok else 'warn', 'message': msg})
        
        ok, count, msg = network.check_network_interfaces(ssh)
        print_ok("Network connected") if ok else print_fail("Network problem!")
        results.append({'check': 'Network Interfaces', 'status': 'ok' if ok else 'fail', 'message': msg})
    
    # Services Checks
    if 'services' in checks:
        print_section("⚙️", "Applications & Services")
        
        svc_config = host_config.get('services', {})
        
        ok, msg = services.check_docker_running(ssh)
        if not ok:
            print_fail("Application engine not running!")
            print_hint("Contact support - services need restart")
            results.append({'check': 'Docker Daemon', 'status': 'fail', 'message': msg})
        else:
            results.append({'check': 'Docker Daemon', 'status': 'ok', 'message': msg})
            
            compose_dir = svc_config.get('compose_dir')
            if compose_dir:
                containers = services.get_containers_from_compose_dir(ssh, compose_dir)
                if containers:
                    if verbose:
                        click.echo(click.style(f"    📋 Found {len(containers)} containers in {compose_dir}", fg='cyan'))
                    
                    # Check all containers
                    container_ok = 0
                    container_problems = []
                    
                    for container in containers:
                        status, msg, container_logs = services.check_container(ssh, container)
                        results.append({'check': f'Container: {container}', 'status': status, 'message': msg})
                        
                        # In verbose mode, show every container
                        if verbose:
                            if status == 'ok':
                                print_ok(f"{container} - running")
                            elif status == 'warn':
                                print_warn(f"{container} - {msg}")
                            else:
                                print_fail(f"{container} - {msg}")
                        
                        if status == 'ok':
                            container_ok += 1
                        else:
                            container_problems.append(container)
                            if container_logs:
                                logs[f'container_{container}'] = container_logs
                    
                    # In non-verbose mode, show summary
                    if not verbose:
                        container_warnings = [c for c in containers if any(
                            r['check'] == f'Container: {c}' and r['status'] == 'warn' for r in results)]
                        container_failures = [c for c in containers if any(
                            r['check'] == f'Container: {c}' and r['status'] == 'fail' for r in results)]
                        
                        if not container_warnings and not container_failures:
                            print_ok(f"All {len(containers)} applications running smoothly")
                        else:
                            if container_ok > 0:
                                print_ok(f"{container_ok} applications running fine")
                            for c in container_warnings:
                                print_warn(f"{c} - running but needs attention")
                                print_hint("App is working but reporting health issues")
                            for c in container_failures:
                                msg = next((r['message'] for r in results if r['check'] == f'Container: {c}'), '')
                                if 'restarting' in msg.lower():
                                    print_fail(f"{c} - keeps crashing and restarting!")
                                    print_hint("This app has a serious problem - contact support")
                                else:
                                    print_fail(f"{c} - has stopped working")
                                    print_hint("This app needs to be restarted")
        
        # Systemd services
        systemd_services = svc_config.get('systemd_services', [])
        service_ok = 0
        service_problems = []
        
        if verbose and systemd_services:
            click.echo(click.style(f"    📋 Checking {len(systemd_services)} system services", fg='cyan'))
        
        for service in systemd_services:
            status, msg, svc_logs = services.check_systemd_service(ssh, service)
            results.append({'check': f'Service: {service}', 'status': status, 'message': msg})
            
            # In verbose mode, show every service
            if verbose:
                if status == 'ok':
                    print_ok(f"{service} - active")
                else:
                    print_fail(f"{service} - {msg}")
            
            if status == 'ok':
                service_ok += 1
            else:
                service_problems.append(service)
                if svc_logs:
                    logs[f'service_{service}'] = svc_logs
        
        # In non-verbose mode, show summary
        if not verbose and systemd_services:
            if not service_problems:
                print_ok(f"All {len(systemd_services)} system services running")
            else:
                for prob in service_problems:
                    print_fail(f"Service problem: {prob}")
    
    # Device Checks
    if 'devices' in checks:
        print_section("🔌", "Connected Devices")
        
        dev_config = host_config.get('devices', {})
        
        all_usb = devices.list_all_usb_devices()
        
        # In verbose mode, list ALL USB devices
        if verbose:
            click.echo(click.style(f"    📋 All USB devices detected on system:", fg='cyan'))
            if all_usb:
                for d in all_usb:
                    click.echo(f"       • {d['vendor_id']}:{d['product_id']} - {d.get('product', 'Unknown')} ({d.get('manufacturer', 'Unknown')})")
            else:
                click.echo("       (No USB devices found or pyusb needs root)")
            click.echo("")
        
        # Check required devices
        devices_ok = 0
        devices_missing = []
        
        for device_name, device_info in dev_config.items():
            vid = device_info.get('vendor_id', '')
            pid = device_info.get('product_id', '')
            
            found, info = devices.find_usb_device(vid, pid)
            
            if found:
                if verbose:
                    serial = info.get('serial', 'N/A') if info else 'N/A'
                    print_ok(f"{device_name} ({vid}:{pid}) - Serial: {serial}")
                else:
                    print_ok(f"{device_name} connected")
                results.append({'check': f'Device: {device_name}', 'status': 'ok', 'message': f'{device_name} connected'})
                devices_ok += 1
            else:
                print_fail(f"{device_name} not found! (expected {vid}:{pid})")
                print_hint("Check if it's plugged in properly")
                results.append({'check': f'Device: {device_name}', 'status': 'fail', 'message': f'{device_name} missing'})
                devices_missing.append(device_name)
    
    ssh.disconnect()
    
    # Summary
    ok_count = sum(1 for r in results if r['status'] == 'ok')
    warn_count = sum(1 for r in results if r['status'] == 'warn')
    fail_count = sum(1 for r in results if r['status'] == 'fail')
    
    print_header("📊 Summary")
    
    if fail_count > 0:
        click.echo(click.style(f"\n    🔴 PROBLEMS FOUND - Action Required!", fg='red', bold=True))
        click.echo(f"       Found {fail_count} problem(s) that need to be fixed:\n")
        for r in results:
            if r['status'] == 'fail':
                click.echo(click.style(f"       ❌ {_friendly_name(r['check'])}", fg='red'))
                click.echo(f"          What's wrong: {_friendly_message(r['check'], r['message'])}")
                click.echo(f"          How to fix: {_friendly_fix_for_message(r['check'], r['message'])}")
                click.echo("")
    
    if warn_count > 0:
        if fail_count > 0:
            click.echo(click.style(f"    🟡 Also found {warn_count} warning(s):\n", fg='yellow'))
        else:
            click.echo(click.style(f"\n    🟡 MOSTLY OK - Some things to watch", fg='yellow', bold=True))
            click.echo(f"       Found {warn_count} thing(s) that might need attention:\n")
        for r in results:
            if r['status'] == 'warn':
                click.echo(click.style(f"       ⚠️  {_friendly_name(r['check'])}", fg='yellow'))
                click.echo(f"          What's happening: {_friendly_message(r['check'], r['message'])}")
                click.echo(f"          Suggestion: {_friendly_fix_for_message(r['check'], r['message'])}")
                click.echo("")
    
    if fail_count == 0 and warn_count == 0:
        click.echo(click.style(f"\n    🟢 ALL GOOD!", fg='green', bold=True))
        click.echo("       Everything is working perfectly.")
        click.echo("       Your device is healthy and all services are running.\n")
    
    # Save report
    bundle_path = dump_report(host_name, results, logs)
    click.echo(f"    📁 Report saved: {bundle_path}")
    
    if fail_count > 0:
        click.echo("")
        click.echo("    ╔════════════════════════════════════════════════════════╗")
        click.echo("    ║  💡 Need help? Send the report folder to support team  ║")
        click.echo("    ╚════════════════════════════════════════════════════════╝")
    
    click.echo("")
    
    return results, fail_count == 0


# ============================================================
# CLI
# ============================================================

@click.command()
@click.option('--host', '-h', multiple=True, required=True, help='Host(s) to diagnose')
@click.option('--check', '-c', multiple=True, 
              type=click.Choice(['system', 'network', 'services', 'devices']),
              help='Specific checks (default: all)')
@click.option('--verbose', '-v', is_flag=True, help='Show more details')
@click.option('--json-output', is_flag=True, help='Output as JSON')
@click.option('--inventory', default='inventory.yaml', help='Inventory file')
def main(host, check, verbose, json_output, inventory):
    """Edge Node Diagnostic Tool - Check if your device is healthy."""
    try:
        inv = load_inventory(inventory)
    except FileNotFoundError:
        click.echo(click.style(f"❌ Could not find {inventory}", fg='red'))
        sys.exit(1)
    
    targets = list(host)
    for h in targets:
        if h not in inv:
            click.echo(click.style(f"❌ Unknown device: {h}", fg='red'))
            click.echo(f"   Available: {', '.join(inv.keys())}")
            sys.exit(1)
    
    checks = list(check) if check else ['system', 'network', 'services', 'devices']
    
    all_results = []
    all_success = True
    
    for target in targets:
        results, success = run_diagnostics(target, inv[target], checks, verbose)
        all_results.append({'host': target, 'results': results, 'success': success})
        if not success:
            all_success = False
    
    if json_output:
        click.echo(json.dumps(all_results, indent=2))
    
    sys.exit(0 if all_success else 1)


if __name__ == '__main__':
    main()
