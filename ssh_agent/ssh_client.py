"""
SSH Agent with auto key bootstrap capability.
"""
import paramiko
import os
import subprocess
from pathlib import Path
from typing import Optional


class SSHAgent:
    def __init__(self, host: str, username: str, password: Optional[str] = None, 
                 key_path: Optional[str] = None, port: int = 22):
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self._connected = False

    def is_reachable_tailscale(self, timeout: int = 10) -> tuple[bool, str]:
        """Check if host is reachable via Tailscale VPN."""
        try:
            result = subprocess.run(
                ["tailscale", "ping", "-c", "1", self.host],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if "pong" in result.stdout.lower():
                return True, f"{self.host} reachable via Tailscale"
            else:
                return False, result.stderr.strip() or result.stdout.strip() or "Host not reachable"
        except FileNotFoundError:
            return False, "Tailscale is not installed"
        except subprocess.TimeoutExpired:
            return False, "Tailscale ping timed out"

    @staticmethod
    def ensure_ssh_key(key_path: str = "~/.ssh/id_rsa") -> str:
        """Ensure SSH key exists, create if not. Returns public key path."""
        key_path = os.path.expanduser(key_path)
        pub_key_path = f"{key_path}.pub"
        
        if os.path.exists(key_path) and os.path.exists(pub_key_path):
            return pub_key_path
        
        ssh_dir = os.path.dirname(key_path)
        Path(ssh_dir).mkdir(mode=0o700, exist_ok=True)
        
        key = paramiko.RSAKey.generate(4096)
        key.write_private_key_file(key_path)
        os.chmod(key_path, 0o600)
        
        with open(pub_key_path, 'w') as f:
            f.write(f"ssh-rsa {key.get_base64()} generated-by-diagnostic")
        os.chmod(pub_key_path, 0o644)
        
        return pub_key_path

    def connect(self) -> bool:
        """Connect using key (if provided) or password."""
        if self.key_path:
            key_path = os.path.expanduser(self.key_path)
            if os.path.exists(key_path):
                try:
                    pkey = paramiko.RSAKey.from_private_key_file(key_path, password=self.password)
                except:
                    try:
                        pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=self.password)
                    except:
                        pkey = paramiko.ECDSAKey.from_private_key_file(key_path, password=self.password)
                self.client.connect(self.host, port=self.port, username=self.username, pkey=pkey, timeout=10)
                self._connected = True
                return True
        
        if self.password:
            self.client.connect(self.host, port=self.port, username=self.username, 
                              password=self.password, timeout=10)
            self._connected = True
            return True
        
        raise Exception("No valid authentication method available")

    def connect_with_password(self) -> bool:
        """Force password authentication (for initial key copy)."""
        if not self.password:
            raise Exception("Password required for initial connection")
        self.client.connect(self.host, port=self.port, username=self.username, 
                          password=self.password, timeout=10)
        self._connected = True
        return True

    def disconnect(self):
        """Close SSH connection."""
        if self._connected:
            self.client.close()
            self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def execute_command(self, commands: list) -> tuple[int, str, str]:
        """Execute command(s) on remote host."""
        if isinstance(commands, str):
            commands = [commands]
        
        for command in commands:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            return exit_code, out, err
        
        return -1, "", "No commands provided"

    def execute_commands(self, commands: list) -> list:
        """Execute multiple commands and return list of results."""
        results = []
        for command in commands:
            stdin, stdout, stderr = self.client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()
            out = stdout.read().decode("utf-8", errors="ignore")
            err = stderr.read().decode("utf-8", errors="ignore")
            results.append((exit_code, out, err))
        return results

    def copy_id(self, pubkey_path: str = '~/.ssh/id_rsa.pub') -> bool:
        """Copy SSH public key to remote host's authorized_keys. Idempotent."""
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
        
        # Add key only if not already present (idempotent)
        code, out, err = self.execute_command(
            [f'grep -qF "{pubkey}" ~/.ssh/authorized_keys || echo "{pubkey}" >> ~/.ssh/authorized_keys']
        )
        return True

    def upload(self, local_path: str, remote_path: str):
        """Upload file to remote host."""
        sftp = self.client.open_sftp()
        sftp.put(local_path, remote_path)
        sftp.close()

    def download(self, remote_path: str, local_path: str):
        """Download file from remote host."""
        sftp = self.client.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()


class SSHBootstrap:
    """Handles SSH key bootstrap at session start."""
    
    def __init__(self, host: str, username: str, password: Optional[str] = None,
                 key_path: Optional[str] = None, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path or "~/.ssh/id_rsa"
        self.port = port
    
    def bootstrap_and_connect(self) -> tuple[SSHAgent, list[str]]:
        """
        Try to connect, bootstrap key if needed, return connected agent.
        Returns (agent, messages) where messages describe what happened.
        """
        messages = []
        agent = SSHAgent(self.host, self.username, self.password, self.key_path, self.port)
        
        # Try key-based auth first
        if self.key_path:
            key_path = os.path.expanduser(self.key_path)
            if os.path.exists(key_path):
                try:
                    agent.connect()
                    messages.append(f"✅ Connected using SSH key: {self.key_path}")
                    return agent, messages
                except Exception as e:
                    messages.append(f"⚠️ Key auth failed: {str(e)[:50]}")
        
        # Try password auth
        if self.password:
            try:
                agent.connect_with_password()
                messages.append("✅ Connected using password")
                
                # Bootstrap key for future connections
                try:
                    pub_key_path = SSHAgent.ensure_ssh_key(self.key_path)
                    agent.copy_id(pub_key_path)
                    messages.append(f"✅ SSH key bootstrapped: {pub_key_path}")
                except Exception as e:
                    messages.append(f"⚠️ Key bootstrap failed: {str(e)[:50]}")
                
                return agent, messages
            except Exception as e:
                messages.append(f"❌ Password auth failed: {str(e)[:50]}")
        
        # All methods failed
        messages.append("")
        messages.append("❌ Could not establish SSH connection")
        messages.append("")
        messages.append("WHAT TO DO:")
        messages.append("  1. Verify the host is reachable (ping, VPN status)")
        messages.append("  2. Check username and password in inventory.yaml")
        messages.append("  3. Ensure SSH is enabled on the remote host")
        messages.append(f"  4. Try manually: ssh {self.username}@{self.host}")
        
        raise ConnectionError("\n".join(messages))
