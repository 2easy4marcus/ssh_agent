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

### inventory.yaml Configuration

The `inventory.yaml` file defines all your edge devices and what to check on each one. Create this file in your project root.

#### Complete Example

```yaml
# Production edge device
ocu4:
  connection:
    hostname: "100.64.0.14"           # Tailscale IP or regular IP/hostname
    username: "admin"                 # SSH username
    port: 22                          # SSH port (default: 22)
    password: "initial-password"      # For first-time connection only
    ssh_key_path: "~/.ssh/id_rsa"    # SSH key location (optional)

  services:
    compose_dir: "/opt/app"           # Directory containing docker-compose files
    systemd_services:                 # System services to monitor
      - docker                        # Docker daemon
      - tailscaled                    # Tailscale VPN
      - nginx                         # Web server
      - postgresql                    # Database

  devices:
    laser_scanner:                    # Friendly name for device
      vendor_id: "0x0403"            # USB Vendor ID (hex format)
      product_id: "0x90D9"           # USB Product ID (hex format)
    temperature_sensor:
      vendor_id: "0x1234"
      product_id: "0x5678"
    camera:
      vendor_id: "0x046d"            # Logitech
      product_id: "0x085b"

# Development/test device
edge-dev:
  connection:
    hostname: "192.168.1.100"
    username: "pi"
    password: "raspberry"
    port: 22

  services:
    compose_dir: "/home/pi/docker"
    systemd_services:
      - docker
      - ssh

  devices:
    test_device:
      vendor_id: "0x2341"            # Arduino
      product_id: "0x0043"

# Minimal device (only system checks)
simple-node:
  connection:
    hostname: "edge-simple.local"
    username: "user"
    ssh_key_path: "~/.ssh/edge_key"
  # No services or devices sections = only system checks
```

#### Configuration Sections

##### **connection** (Required)
| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `hostname` | ✅ | IP address or hostname | `"100.64.0.14"`, `"edge1.local"` |
| `username` | ✅ | SSH username | `"admin"`, `"pi"`, `"ubuntu"` |
| `password` | ⚠️ | Password for initial connection | `"your-password"` |
| `ssh_key_path` | ❌ | Path to SSH private key | `"~/.ssh/id_rsa"` |
| `port` | ❌ | SSH port (default: 22) | `22`, `2222` |

**Authentication Notes:**
- First run: Uses password, automatically sets up SSH key
- Future runs: Uses SSH key (no password needed)
- If no password provided, must have working SSH key already

##### **services** (Optional)
| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `compose_dir` | ❌ | Directory with docker-compose files | `"/opt/app"`, `"/home/user/docker"` |
| `systemd_services` | ❌ | List of systemd services to check | `["docker", "nginx", "postgresql"]` |

**Service Discovery:**
- Tool automatically finds all containers in compose files
- Checks if Docker daemon is running first
- Monitors both Docker containers and system services

##### **devices** (Optional)
Each device needs a friendly name and USB identifiers:

```yaml
devices:
  friendly_name:                    # Your choice of name
    vendor_id: "0x1234"            # USB Vendor ID (hex with 0x prefix)
    product_id: "0x5678"           # USB Product ID (hex with 0x prefix)
```

**Finding USB Device IDs:**
```bash
# On Linux
lsusb
# Output: Bus 001 Device 003: ID 046d:085b Logitech, Inc. C925e

# On Windows
# Use Device Manager > Properties > Hardware Ids
# VID_046D&PID_085B

# In the tool (verbose mode)
python overall_diagnose.py --host mydevice --check devices --verbose
```

#### Configuration Examples by Use Case

##### **Basic Edge Device**
```yaml
basic-edge:
  connection:
    hostname: "192.168.1.50"
    username: "admin"
    password: "admin123"
  # Only system and network checks
```

##### **Docker-Heavy Device**
```yaml
docker-node:
  connection:
    hostname: "100.64.0.20"
    username: "deploy"
    ssh_key_path: "~/.ssh/deploy_key"
  
  services:
    compose_dir: "/opt/services"
    systemd_services:
      - docker
      - docker-compose
      - tailscaled
```

##### **IoT Device with Sensors**
```yaml
iot-gateway:
  connection:
    hostname: "iot-gw.local"
    username: "iot"
    password: "sensor123"
  
  services:
    systemd_services:
      - mosquitto          # MQTT broker
      - node-red           # IoT flows
      - influxdb           # Time series DB
  
  devices:
    zigbee_coordinator:
      vendor_id: "0x10c4"
      product_id: "0xea60"
    lora_gateway:
      vendor_id: "0x0403"
      product_id: "0x6015"
```

#### Best Practices

1. **Security**
   - Use strong passwords for initial setup
   - Let the tool manage SSH keys automatically
   - Consider using non-standard SSH ports

2. **Organization**
   - Use descriptive hostnames in your network
   - Group similar devices with consistent naming
   - Document device purposes in comments

3. **Monitoring**
   - Start with basic system checks, add services gradually
   - Use verbose mode to discover available containers/services
   - Test new devices individually before adding to production monitoring

4. **Maintenance**
   - Keep inventory.yaml in version control
   - Update device lists when hardware changes
   - Review and clean up unused entries regularly

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
