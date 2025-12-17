# Edge Node Diagnostic Tool

A simple, inventory-driven diagnostic framework for edge devices. One tool, many hosts.

## Overview

This tool runs health checks on remote edge devices (OCUs, sensors, etc.) via SSH. All host-specific configuration lives in `inventory.yaml` - the code stays generic.

**Key Features:**
- 🔧 Inventory-driven - add hosts without changing code
- 🔐 Auto SSH key bootstrap - handles authentication automatically
- 📊 Human-friendly output - clear status with actionable hints
- 📦 Support bundles - auto-generated on failures for easy troubleshooting

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your hosts in inventory.yaml (see below)

# 3. Run diagnostics
python overall_diagnose.py --host ocu4
```

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd edge-diagnostic

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `click` | CLI interface |
| `paramiko` | SSH connections |
| `PyYAML` | Inventory parsing |
| `pyusb` | Local USB detection (optional) |

## Usage

### Show Available Hosts

```bash
python overall_diagnose.py
```

Output:
```
=================================================================
        EDGE NODE DIAGNOSTIC TOOL
=================================================================

  Available hosts:
    • ocu4 (100.64.0.14)
    • edge1 (192.168.1.100)

  Usage:
    python overall_diagnose.py --host ocu4
    python overall_diagnose.py --all-hosts
```

### Diagnose a Single Host

```bash
python overall_diagnose.py --host ocu4
```

### Diagnose All Hosts

```bash
python overall_diagnose.py --all-hosts
```

### Run Specific Checks Only

```bash
# Only system checks
python overall_diagnose.py --host ocu4 --check system

# Multiple specific checks
python overall_diagnose.py --host ocu4 --check system --check services
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--host` | `-h` | Host(s) to diagnose (from inventory) |
| `--all-hosts` | | Run on all hosts in inventory |
| `--check` | `-c` | Specific check(s): `system`, `network`, `services`, `devices` |
| `--verbose` | `-v` | Show more technical details |
| `--json-output` | | Output results as JSON |
| `--inventory` | | Custom inventory file path |

## Configuration

### inventory.yaml

All host configuration lives here. Add new hosts by copying an existing block:

```yaml
ocu4:
  connection:
    hostname: "100.64.0.14"      # IP or hostname
    username: admin              # SSH user
    port: 22                     # SSH port (default: 22)
    password: "123456"           # For initial connection / key bootstrap
    ssh_key_path: "~/.ssh/ansible"  # SSH key to use

  network:
    vpn_type: tailscale          # tailscale | none

  services:
    docker_containers:           # Required containers to check
      - ocu-app
      - mqtt-broker
    systemd_services:            # Required services to check
      - docker
      - tailscaled

  devices:
    usb:                         # Required USB devices
      - name: "Oxxius Laser"
        vendor_id: "0x0403"
        product_id: "0x90D9"
        required: true
      - name: "USB Hub"
        vendor_id: "0x0bda"
        product_id: "0x5411"
        required: false          # Optional device
```

### Adding a New Host

1. Copy an existing host block in `inventory.yaml`
2. Change the host name and connection details
3. Adjust services/devices as needed
4. Run: `python overall_diagnose.py --host <new-host>`

No code changes required!

## Available Checks

### System (`--check system`)

| Check | What it does |
|-------|--------------|
| Hostname | Verifies device identity |
| Uptime | Shows how long system has been running |
| CPU Load | Checks processor usage (warns if overloaded) |
| Memory | Checks RAM usage (warns >70%, fails >85%) |
| Disk | Checks disk space (warns >70%, fails >85%) |

### Network (`--check network`)

| Check | What it does |
|-------|--------------|
| Tailscale VPN | Pings device via Tailscale (if configured) |
| Network Interfaces | Verifies network interfaces are up |

### Services (`--check services`)

| Check | What it does |
|-------|--------------|
| Docker Daemon | Verifies Docker is running |
| Containers | Checks each container is running (not crashed/restarting) |
| Systemd Services | Verifies each service is active |

On failure, logs are automatically collected for the support bundle.

### Devices (`--check devices`)

| Check | What it does |
|-------|--------------|
| USB Scan | Lists all connected USB devices |
| Required Devices | Verifies each required device is present |

**Note:** USB detection runs on the **local machine** using `pyusb`. For remote USB detection, the tool uses `lsusb` over SSH.

## Output Format

The tool provides human-friendly output:

```
[Step 1/4] Establishing Connection
---------------------------------------------
  ✓ Connected using SSH key: ~/.ssh/ansible

[Step 2/4] System Health
---------------------------------------------
  ✓ Device name: ocu4
  ✓ System up 5 days, 3 hours
  ✓ CPU load normal (0.5 on 4 cores)
  ✓ Memory OK (45% used)
  ⚠ Disk getting full (78% used)
  💡 Delete old logs or unused files to free space

=================================================================
        DIAGNOSTIC SUMMARY
=================================================================
  ✓ Passed: 5
  ⚠ Warnings: 1
  ✗ Failed: 0

  WHAT NEEDS ATTENTION:
    ⚠ Disk: Disk getting full (78% used)
```

### Status Icons

| Icon | Meaning |
|------|---------|
| ✓ | OK - Everything working |
| ⚠ | Warning - Needs attention soon |
| ✗ | Failed - Action required |
| 💡 | Hint - Suggested action |

## Support Bundles

When failures occur, a support bundle is automatically created:

```
reports/
└── ocu4/
    └── 20241217_143052/
        ├── report.txt           # Human-readable report
        ├── support_message.txt  # Copy-paste for support ticket
        ├── container_ocu-app.log
        └── service_docker.log
```

The `support_message.txt` contains a pre-formatted message you can paste directly into a support ticket.

## SSH Key Bootstrap

The tool handles SSH authentication automatically:

1. **First run:** Connects with password, generates SSH key, copies to remote
2. **Subsequent runs:** Uses SSH key (no password needed)

This is idempotent - running multiple times won't duplicate keys.

If connection fails, you'll see clear instructions:

```
  ✗ Could not connect to device

  WHAT TO DO:
    1. Check if the device is powered on
    2. Verify network/VPN connection
    3. Check credentials in inventory.yaml
    4. Try manually: ssh admin@100.64.0.14
```

## Project Structure

```
├── overall_diagnose.py     # Main CLI entrypoint
├── inventory.yaml          # Host configurations
├── requirements.txt        # Python dependencies
├── diagnostic/
│   ├── system.py          # CPU, memory, disk, uptime checks
│   ├── network.py         # VPN, interface checks
│   ├── services.py        # Docker, systemd checks
│   └── devices.py         # USB device detection
├── ssh_agent/
│   └── ssh_client.py      # SSH connection & key bootstrap
└── reports/               # Generated support bundles
```

## Extending

### Adding a New Check Module

1. Create `diagnostic/mycheck.py`:

```python
def check_something(ssh) -> tuple[str, str]:
    """Returns (status, message). Status: ok/warn/fail"""
    code, out, _ = ssh.execute_command(["my-command"])
    if code == 0:
        return "ok", "Everything is fine"
    return "fail", "Something went wrong"
```

2. Import and use in `overall_diagnose.py`

### Adding New Host Types

Just add to `inventory.yaml` - no code changes needed. The same checks run on all hosts; only the expected values differ.

## Troubleshooting

### "Could not connect to device"

- Check VPN connection (Tailscale status)
- Verify host is powered on
- Test manually: `ssh user@host`
- Check credentials in `inventory.yaml`

### "pyusb not available"

USB detection requires `pyusb` and may need root permissions:

```bash
pip install pyusb
# For Linux, you may need udev rules or run as root
```

### "Container keeps restarting"

Check the support bundle logs in `reports/<host>/<timestamp>/`

## License

Internal use only.
