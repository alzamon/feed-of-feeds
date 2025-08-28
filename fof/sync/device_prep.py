"""Device preparation utilities for multi-device sync setup."""

import os
import logging
import subprocess
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from .peer_config import PeerConfig

logger = logging.getLogger(__name__)


class DevicePreparationManager:
    """Manages device preparation for multi-device sync."""
    
    def __init__(self):
        """Initialize device preparation manager."""
        self.ssh_dir = Path.home() / ".ssh"
        self.ssh_key_path = self.ssh_dir / "id_rsa"
        self.ssh_pub_key_path = self.ssh_dir / "id_rsa.pub"
    
    def check_ssh_key_exists(self) -> bool:
        """Check if SSH key pair exists."""
        return self.ssh_key_path.exists() and self.ssh_pub_key_path.exists()
    
    def generate_ssh_key(self, email: Optional[str] = None) -> bool:
        """
        Generate SSH key pair if it doesn't exist.
        Returns True if key was generated or already exists.
        """
        try:
            if self.check_ssh_key_exists():
                logger.info("SSH key pair already exists")
                return True
            
            # Ensure .ssh directory exists
            self.ssh_dir.mkdir(mode=0o700, exist_ok=True)
            
            # Generate SSH key
            comment = email or f"fof-sync@{os.uname().nodename}"
            
            cmd = [
                "ssh-keygen",
                "-t", "rsa",
                "-b", "2048",
                "-f", str(self.ssh_key_path),
                "-C", comment,
                "-N", ""  # No passphrase
            ]
            
            logger.info("Generating SSH key pair...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Set proper permissions
                self.ssh_key_path.chmod(0o600)
                self.ssh_pub_key_path.chmod(0o644)
                logger.info(f"SSH key pair generated: {self.ssh_key_path}")
                return True
            else:
                logger.error(f"Failed to generate SSH key: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error generating SSH key: {e}")
            return False
    
    def get_public_key(self) -> Optional[str]:
        """Get the public key content."""
        try:
            if not self.ssh_pub_key_path.exists():
                return None
                
            with open(self.ssh_pub_key_path, 'r') as f:
                return f.read().strip()
                
        except Exception as e:
            logger.error(f"Error reading public key: {e}")
            return None
    
    def copy_key_to_peer(self, peer: PeerConfig, password_prompt: bool = True) -> bool:
        """
        Copy SSH public key to a peer using ssh-copy-id.
        Returns True if successful.
        """
        try:
            if not self.check_ssh_key_exists():
                logger.error("SSH key pair does not exist. Generate keys first.")
                return False
            
            # Use ssh-copy-id to copy the key
            cmd = [
                "ssh-copy-id",
                "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-p", str(peer.port),
                f"{peer.user}@{peer.host}"
            ]
            
            logger.info(f"Copying SSH key to {peer.device_name} ({peer.user}@{peer.host}:{peer.port})")
            
            if password_prompt:
                print(f"You may be prompted for the password for {peer.user}@{peer.host}")
            
            # Run interactively so user can enter password
            result = subprocess.run(cmd)
            
            if result.returncode == 0:
                logger.info(f"Successfully copied SSH key to {peer.device_name}")
                return True
            else:
                logger.error(f"Failed to copy SSH key to {peer.device_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error copying key to {peer.device_name}: {e}")
            return False
    
    def check_ssh_server_running(self) -> bool:
        """Check if SSH server is running on this machine."""
        try:
            # Try multiple ways to check SSH service
            checks = [
                ["systemctl", "is-active", "ssh"],
                ["systemctl", "is-active", "sshd"], 
                ["service", "ssh", "status"],
                ["service", "sshd", "status"]
            ]
            
            for cmd in checks:
                try:
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            # Check if SSH port is listening
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', 22))
                sock.close()
                return result == 0
            except Exception:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking SSH server status: {e}")
            return False
    
    def start_ssh_server(self, use_sudo: bool = True) -> bool:
        """
        Attempt to start SSH server.
        Returns True if successful or already running.
        """
        try:
            if self.check_ssh_server_running():
                logger.info("SSH server is already running")
                return True
            
            # Try different commands to start SSH
            start_commands = []
            
            if use_sudo:
                start_commands.extend([
                    ["sudo", "systemctl", "start", "ssh"],
                    ["sudo", "systemctl", "start", "sshd"],
                    ["sudo", "service", "ssh", "start"],
                    ["sudo", "service", "sshd", "start"]
                ])
            
            # Also try without sudo (might work in some environments)
            start_commands.extend([
                ["systemctl", "start", "ssh"],
                ["systemctl", "start", "sshd"]
            ])
            
            for cmd in start_commands:
                try:
                    logger.info(f"Attempting to start SSH server: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # Verify it's actually running
                        if self.check_ssh_server_running():
                            logger.info("SSH server started successfully")
                            return True
                            
                except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
                    continue
            
            logger.error("Failed to start SSH server with any method")
            return False
            
        except Exception as e:
            logger.error(f"Error starting SSH server: {e}")
            return False
    
    def check_platform_compatibility(self) -> Tuple[bool, List[str]]:
        """
        Check platform compatibility and return status with any issues.
        Returns (is_compatible, list_of_issues).
        """
        issues = []
        
        # Check for required commands
        required_commands = ["ssh", "scp", "ssh-keygen"]
        for cmd in required_commands:
            if not shutil.which(cmd):
                issues.append(f"Required command not found: {cmd}")
        
        # Check SSH directory permissions
        if self.ssh_dir.exists():
            stat = self.ssh_dir.stat()
            if stat.st_mode & 0o077:  # Check if group/other have any permissions
                issues.append(f"SSH directory has insecure permissions: {oct(stat.st_mode)}")
        
        # Platform-specific checks
        try:
            import platform
            system = platform.system().lower()
            
            if system == "linux":
                # Check if we're in Termux
                if os.path.exists("/data/data/com.termux"):
                    # Termux-specific checks
                    if not shutil.which("openssh"):
                        issues.append("OpenSSH not installed in Termux (run: pkg install openssh)")
            
        except Exception as e:
            issues.append(f"Error checking platform: {e}")
        
        return len(issues) == 0, issues
    
    def prepare_device_interactive(self, peers: List[PeerConfig]) -> bool:
        """
        Interactive device preparation workflow.
        Returns True if preparation was successful.
        """
        print("=== FoF Multi-Device Sync Setup ===")
        print()
        
        # Check platform compatibility
        compatible, issues = self.check_platform_compatibility()
        if not compatible:
            print("Platform compatibility issues found:")
            for issue in issues:
                print(f"  - {issue}")
            print()
            
            response = input("Continue anyway? (y/N): ").lower()
            if response not in ['y', 'yes']:
                return False
        
        # Generate SSH keys if needed
        print("1. Checking SSH keys...")
        if not self.check_ssh_key_exists():
            print("SSH key pair not found. Generating new keys...")
            if not self.generate_ssh_key():
                print("Failed to generate SSH keys.")
                return False
            print("SSH keys generated successfully.")
        else:
            print("SSH key pair already exists.")
        
        # Show public key
        pub_key = self.get_public_key()
        if pub_key:
            print(f"Public key: {pub_key}")
        print()
        
        # Copy keys to peers
        if peers:
            print("2. Copying SSH key to peers...")
            for peer in peers:
                print(f"Copying key to {peer.device_name} ({peer.user}@{peer.host}:{peer.port})")
                if not self.copy_key_to_peer(peer):
                    print(f"Failed to copy key to {peer.device_name}")
                    return False
        else:
            print("2. No peers configured to copy keys to.")
        print()
        
        # Start SSH server
        print("3. Checking SSH server...")
        if not self.check_ssh_server_running():
            print("SSH server is not running. Attempting to start...")
            
            response = input("Start SSH server with sudo? (Y/n): ").lower()
            use_sudo = response not in ['n', 'no']
            
            if not self.start_ssh_server(use_sudo):
                print("Failed to start SSH server. You may need to start it manually.")
                return False
            print("SSH server started successfully.")
        else:
            print("SSH server is already running.")
        
        print()
        print("Device preparation completed successfully!")
        print("You can now use 'fof sync' commands to synchronize with other devices.")
        return True