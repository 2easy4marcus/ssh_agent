import paramiko
import os
import subprocess
from pathlib import Path


class SSHAgent:
    def __init__(self, host, username, password=None, key_path=None):
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self._connected = False

    def is_reachable_tailscale(self, timeout: int = 10) -> tuple[bool, str]:
        """Check if host is reachable via Tailscale VPN"""
        try:
            result = subprocess.run(
                ["tailscale", "ping", "-c", "1", self.host],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            # Check for "pong" in output - that means it worked
            if "pong" in result.stdout.lower():
                return True, f"{self.host} erreichbar via Tailscale"
            else:
                return False, result.stderr.strip() or result.stdout.strip() or "Host nicht erreichbar"
        except FileNotFoundError:
            return False, "Tailscale ist nicht installiert"
        except subprocess.TimeoutExpired:
            return False, "Zeitüberschreitung bei Tailscale-Ping"

    @staticmethod
    def ensure_ssh_key(key_path: str = "~/.ssh/id_rsa") -> str:
        key_path = os.path.expanduser(key_path)
        pub_key_path = f"{key_path}.pub"
        
        if os.path.exists(key_path) and os.path.exists(pub_key_path):
            return pub_key_path
        
        # Ensure .ssh directory exists
        ssh_dir = os.path.dirname(key_path)
        Path(ssh_dir).mkdir(mode=0o700, exist_ok=True)
        
        # Generate RSA key
        key = paramiko.RSAKey.generate(4096)
        key.write_private_key_file(key_path)
        os.chmod(key_path, 0o600)
        
        # Write public key
        with open(pub_key_path, 'w') as f:
            f.write(f"ssh-rsa {key.get_base64()} generated-by-poc")
        os.chmod(pub_key_path, 0o644)
        
        return pub_key_path

    def connect(self):
        """Connect using key (if provided) or password"""
        if self.key_path:
            key_path = os.path.expanduser(self.key_path)
            # Try RSA first, then Ed25519
            try:
                pkey = paramiko.RSAKey.from_private_key_file(key_path, password=self.password)
            except:
                pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=self.password)
            self.client.connect(self.host, username=self.username, pkey=pkey, timeout=10)
        else:
            self.client.connect(self.host, username=self.username, password=self.password, timeout=10)
        self._connected = True

    def connect_with_password(self):
        """Force password authentication (for initial key copy)"""
        self.client.connect(self.host, username=self.username, password=self.password, timeout=10)
        self._connected = True

    def disconnect(self):
        self.client.close()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def execute_command(self, command: str) -> tuple[int, str, str]:
        """Execute a single command and return (exit_code, stdout, stderr)"""
        stdin, stdout, stderr = self.client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        return exit_code, out, err

    def execute_commands(self, commands: list) -> list:
        """Execute multiple commands and return list of results"""
        results = []
        for command in commands:
            results.append(self.execute_command(command))
        return results

    def copy_id(self, pubkey_path='~/.ssh/id_rsa.pub') -> bool:
        """Copy SSH public key to remote host's authorized_keys"""
        pubkey_path = os.path.expanduser(pubkey_path)
        with open(pubkey_path, 'r') as f:
            pubkey = f.read().strip()
        
        # Setup .ssh directory
        commands = [
            'mkdir -p ~/.ssh',
            'chmod 700 ~/.ssh',
            'touch ~/.ssh/authorized_keys',
            'chmod 600 ~/.ssh/authorized_keys',
        ]
        self.execute_commands(commands)
        
        # Add key only if not already present
        code, out, err = self.execute_command(
            f'grep -q "{pubkey}" ~/.ssh/authorized_keys || echo "{pubkey}" >> ~/.ssh/authorized_keys'
        )
        return True

    def upload(self, local_path, remote_path):
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

    def download(self, remote_path, local_path):
        sftp = self.client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
