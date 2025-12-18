# 🔍 Edge Node Diagnostic Tool

A simple, friendly diagnostic tool for edge devices. Check if your devices are healthy with one command.

## What It Does

- ✅ Checks if your device is reachable
- 💻 Monitors system health (CPU, memory, storage)
- 🌐 Verifies network and VPN connections
- ⚙️ Checks if all applications are running properly
- 🔌 Detects connected USB devices

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run diagnostics on a device
python overall_diagnose.py --host ocu4
```

## Output Example

```
╔═══════════════════════════════════════════════════════════════╗
║                      🔍 Checking: ocu4                        ║
╚═══════════════════════════════════════════════════════════════╝

  💻 System Health
  ──────────────────────────────────────
    ✅ Device: ocu4
    ✅ System up 5 days, 3 hours
    ✅ Processor running smoothly
    ✅ Memory OK (45% used)
    ✅ Storage OK (32% used)

  ⚙️ Applications & Services
  ──────────────────────────────────────
    ✅ All 12 applications running smoothly

╔═══════════════════════════════════════════════════════════════╗
║                        📊 Summary                             ║
╚═══════════════════════════════════════════════════════════════╝

    🟢 ALL GOOD!
       Everything is working perfectly.
```

## When Problems Are Found

The tool clearly explains what's wrong and how to fix it:

```
    🔴 PROBLEMS FOUND - Action Required!
       Found 1 problem(s) that need to be fixed:

       ❌ App: aggregator
          What's wrong: 🚨 CRITICAL: This app keeps crashing and restarting!
          How to fix: 🚨 URGENT: Contact support immediately!
```

## Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd edge-diagnostic

# 2. Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Commands

```bash
# Check a single device
python overall_diagnose.py --host ocu4

# Check multiple devices
python overall_diagnose.py --host ocu4 --host edge1

# Run only specific checks
python overall_diagnose.py --host ocu4 --check system
python overall_diagnose.py --host ocu4 --check services --check devices
```

### Available Options

| Option | Short | Description |
|--------|-------|-------------|
| `--host` | `-h` | Device to check (required) |
| `--check` | `-c` | Specific checks: `system`, `network`, `services`, `devices` |
| `--verbose` | `-v` | Show more technical details |
| `--json-output` | | Output results as JSON |
| `--inventory` | | Custom inventory file path |

### Available Checks

| Check | What It Does |
|-------|--------------|
| `system` | CPU, memory, storage, uptime |
| `network` | VPN connection, network interfaces |
| `services` | Docker containers, system services |
| `devices` | USB devices (laser, sensors, etc.) |

## Configuration

### inventory.yaml

Add your devices to `inventory.yaml`:

```yaml
ocu4:
  connection:
    hostname: "100.64.0.14"    # IP address or hostname
    username: admin            # SSH username
    port: 22                   # SSH port
    password: "your-password"  # For initial connection
    ssh_key_path: "~/.ssh/id_rsa"

  services:
    compose_dir: "/opt/app"    # Folder with docker-compose files
    systemd_services:
      - docker
      - tailscaled

  devices:
    laser:
      vendor_id: "0x0403"
      product_id: "0x90D9"
    sensor:
      vendor_id: "0x1234"
      product_id: "0x5678"
```

### Adding a New Device

1. Copy an existing device block in `inventory.yaml`
2. Change the name and connection details
3. Update services and devices as needed
4. Run: `python overall_diagnose.py --host <new-device>`

## Reports

Every diagnostic run creates a report in the `reports/` folder:

```
reports/
└── ocu4/
    └── 20241218_143052/
        ├── report.txt           # Human-friendly report
        ├── support_message.txt  # Ready to send to support
        └── container_*.log      # Logs from failed services
```

**Note:** Old reports are automatically deleted. Only the latest report is kept.

### Report Contents

The `report.txt` is written in plain language:

```
╔═══════════════════════════════════════════════════════════════╗
║              🔍 DEVICE HEALTH CHECK REPORT                    ║
╚═══════════════════════════════════════════════════════════════╝

📅 Date: December 18, 2024 at 14:30
🖥️  Device: ocu4

──────────────────────────────────────────────────────────────
🟢 OVERALL STATUS: ALL GOOD!
   Everything is working perfectly.
──────────────────────────────────────────────────────────────
```

## Status Indicators

| Status | Meaning |
|--------|---------|
| 🟢 ALL GOOD | Everything working perfectly |
| 🟡 MOSTLY OK | Working, but some things need attention |
| 🔴 PROBLEMS FOUND | Issues that need to be fixed |

### Service Status

| Status | Meaning | Action |
|--------|---------|--------|
| ✅ Running | App is working fine | None needed |
| ⚠️ Unhealthy | App running but has issues | Monitor it |
| ❌ Stopped | App has stopped | Needs restart |
| ❌ Restarting | App keeps crashing | **Contact support!** |

## SSH Key Bootstrap

The tool automatically handles SSH authentication:

1. **First run:** Connects with password, sets up SSH key
2. **Future runs:** Uses SSH key (no password needed)

This is automatic and safe - running multiple times won't cause issues.

## Project Structure

```
├── overall_diagnose.py      # Main tool
├── inventory.yaml           # Device configuration
├── requirements.txt         # Python dependencies
├── diagnostic/
│   ├── system.py           # System checks
│   ├── network.py          # Network checks
│   ├── services.py         # Docker/service checks
│   └── devices.py          # USB device checks
├── ssh_agent/
│   └── ssh_client.py       # SSH connection handling
└── reports/                # Generated reports
```

## Troubleshooting

### "Could not connect to device"

1. Check if the device is powered on
2. Verify VPN connection: `tailscale status`
3. Test manually: `ssh user@hostname`
4. Check credentials in `inventory.yaml`

### "Container keeps restarting"

This is a serious problem! The app is crashing repeatedly.
- Check the logs in `reports/<device>/<timestamp>/`
- Contact support with the report

### "USB device not found"

1. Check if the device is plugged in
2. Try a different USB port
3. Run with `--verbose` to see all detected devices

## Requirements

- Python 3.10+
- SSH access to edge devices
- For USB detection: `pyusb` (optional, needs root on Linux)

## Dependencies

```
click>=8.0.0      # CLI interface
paramiko>=3.0.0   # SSH connections
PyYAML>=6.0       # Configuration parsing
pyusb>=1.2.0      # USB device detection
```
