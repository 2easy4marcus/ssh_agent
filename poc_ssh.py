#!/usr/bin/env python3
"""
Edge Device SSH Proof of Concept
Automated setup and file transfer to edge devices with user-friendly feedback.
"""

from ssh_client import SSHAgent


def print_header():
    print("\n" + "=" * 65)
    print("        EDGE DEVICE CONNECTION & FILE TRANSFER TOOL")
    print("=" * 65)
    print("  This tool will help you connect to your edge device and")
    print("  transfer files securely using SSH.")
    print("-" * 65 + "\n")


def print_step(step: int, total: int, title: str):
    print(f"\n[Step {step}/{total}] {title}")
    print("-" * 40)


def print_success(message: str):
    print(f"  ✓ {message}")


def print_error(message: str):
    print(f"  ✗ {message}")


def print_hint(message: str):
    print(f"  💡 {message}")


def run_poc():
    """Main PoC flow with user-friendly output"""
    print_header()
    
    # Configuration
    HOSTNAME = "factory"
    USERNAME = "admin"
    PASSWORD = "123456"
    KEY_PATH = "~/.ssh/ansible"
    LOCAL_FILE = "README.md"
    
    print(f"  Target Device: {HOSTNAME}")
    print(f"  Username: {USERNAME}")
    print(f"  File to Transfer: {LOCAL_FILE}")
    
    agent = SSHAgent(HOSTNAME, USERNAME, PASSWORD, KEY_PATH)

    print_step(1, 5, "Checking Network Connection")
    print("  Verifying that your device is reachable on the VPN network...")
    
    reachable, message = agent.is_reachable_tailscale()
    
    if reachable:
        print_success("Device is online and reachable!")
        print_success("Your network connection is working correctly.")
    else:
        print_error("Cannot reach the edge device.")
        print()
        print("  WHAT THIS MEANS:")
        print("  The edge device is not responding on the network.")
        print()
        print("  WHAT TO DO:")
        print("  1. Make sure you are connected to the VPN (Tailscale)")
        print("  2. Check if the edge device is powered on")
        print("  3. Verify the device hostname/IP is correct")
        print("  4. Try running: tailscale status")
        print()
        print_hint("If the problem persists, contact technical support.")
        return False

    print_step(2, 5, "Preparing Security Credentials")
    print("  Checking for SSH authentication keys...")
    
    try:
        pub_key_path = SSHAgent.ensure_ssh_key(KEY_PATH)
        print_success("SSH key is ready for use.")
        print(f"       Key location: {pub_key_path}")
    except Exception as e:
        print_error("Failed to prepare SSH key.")
        print()
        print("  WHAT THIS MEANS:")
        print("  The system could not create or access the security key.")
        print()
        print("  WHAT TO DO:")
        print("  1. Check if you have write permissions to ~/.ssh/")
        print("  2. Ensure the .ssh folder exists in your home directory")
        print()
        print_hint("If the problem persists, contact technical support.")
        return False
    
    print_step(3, 5, "Registering with Edge Device")
    print("  Setting up secure access to the device...")
    
    try:
        agent.connect_with_password()
        agent.copy_id(pub_key_path)
        agent.disconnect()
        print_success("Security key registered successfully!")
        print_success("Future connections will not require a password.")
    except Exception as e:
        print_error("Could not register security key with the device.")
        print()
        print("  WHAT THIS MEANS:")
        print("  The system could not authenticate with the edge device.")
        print()
        print("  WHAT TO DO:")
        print("  1. Verify the username and password are correct")
        print("  2. Check if SSH is enabled on the edge device")
        print("  3. Ensure the device allows password authentication")
        print()
        print_hint(f"Technical details: {e}")
        return False
    
    # =========================================================================
    # STEP 4: Verify Secure Connection
    # =========================================================================
    print_step(4, 5, "Verifying Secure Connection")
    print("  Testing password-free authentication...")
    
    try:
        agent.connect()
        code, out, err = agent.execute_command('echo "connection successful"')
        
        if "successful" not in out:
            raise Exception("Connection test failed")
        
        print_success("Secure connection established!")
        print_success("Password-free authentication is working.")
    except Exception as e:
        print_error("Secure connection could not be verified.")
        print()
        print("  WHAT THIS MEANS:")
        print("  The key-based authentication is not working properly.")
        print()
        print("  WHAT TO DO:")
        print("  1. Try running the tool again")
        print("  2. Check if the SSH key permissions are correct (600)")
        print("  3. Verify the authorized_keys file on the device")
        print()
        print_hint(f"Technical details: {e}")
        return False
    
    # =========================================================================
    # STEP 5: Transfer File
    # =========================================================================
    print_step(5, 5, "Transferring File to Device")
    print(f"  Uploading '{LOCAL_FILE}' to the edge device...")
    
    try:
        code, home_dir, err = agent.execute_command('echo $HOME')
        remote_path = f"{home_dir.strip()}/{LOCAL_FILE}"
        agent.upload(LOCAL_FILE, remote_path)
        print_success(f"File transferred successfully!")
        print(f"       Local file:  {LOCAL_FILE}")
        print(f"       Remote path: {remote_path}")
    except FileNotFoundError:
        print_error(f"Local file '{LOCAL_FILE}' not found.")
        print()
        print("  WHAT TO DO:")
        print(f"  1. Make sure '{LOCAL_FILE}' exists in the current directory")
        print("  2. Check the file name for typos")
        agent.disconnect()
        return False
    except Exception as e:
        print_error("File transfer failed.")
        print()
        print("  WHAT THIS MEANS:")
        print("  The file could not be copied to the edge device.")
        print()
        print("  WHAT TO DO:")
        print("  1. Check if there is enough disk space on the device")
        print("  2. Verify you have write permissions on the device")
        print()
        print_hint(f"Technical details: {e}")
        agent.disconnect()
        return False
    
    agent.disconnect()
    
    # =========================================================================
    # SUCCESS
    # =========================================================================
    print("\n" + "=" * 65)
    print("                    ✓ ALL STEPS COMPLETED!")
    print("=" * 65)
    print()
    print("  SUMMARY:")
    print("  ---------")
    print(f"  • Connected to edge device: {HOSTNAME}")
    print(f"  • Secure authentication: Configured")
    print(f"  • File transferred: {LOCAL_FILE}")
    print()
    print("  NEXT STEPS:")
    print("  ------------")
    print(f"  You can now connect to the device without a password:")
    print(f"    ssh {USERNAME}@{HOSTNAME}")
    print()
    print("  THE FILE HAS BEEN COPIED SUCCESSFULLY.")
    print("  NOW WE HAVE A PROOF OF CONCEPT!")
    print()
    print("=" * 65 + "\n")
    
    return True


if __name__ == "__main__":
    success = run_poc()
    exit(0 if success else 1)
