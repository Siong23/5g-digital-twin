#!/usr/bin/env python3
"""
Simple UERANSIM Deployment Script for Open5GS Twinning Agent
Deploys UERANSIM configs to 192.168.0.115
"""

import paramiko
import scp
import tarfile
import os
import tempfile
import logging
import getpass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deploy_ueransim_configs():
    """Deploy UERANSIM configurations to 192.168.0.115"""
    
    # Configuration
    target_host = "192.168.0.115"
    target_port = 22
    
    print("=== UERANSIM Config Deployment ===")
    username = input("Username for 192.168.0.115: ")
    
    # Authentication method
    auth_method = input("Authentication method (password/key): ").lower()
    password = None
    private_key_path = None
    
    if auth_method == 'password':
        password = getpass.getpass("Password: ")
    else:
        private_key_path = input("Private key path (~/.ssh/id_rsa): ") or "~/.ssh/id_rsa"
        private_key_path = os.path.expanduser(private_key_path)
    
    destination_path = input("Destination path (/opt/ueransim): ") or "/opt/ueransim"
    
    try:
        # Check if UERANSIM configs exist
        if not os.path.exists("ueransim_configs"):
            logger.error("UERANSIM configs directory not found. Run the twinning agent first.")
            return False
        
        logger.info("Creating archive of UERANSIM configs...")
        
        # Create tar archive
        temp_dir = tempfile.mkdtemp()
        tar_path = os.path.join(temp_dir, "ueransim_configs.tar.gz")
        
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add("ueransim_configs", arcname="ueransim_configs")
        
        logger.info(f"Connecting to {target_host}...")
        
        # Create SSH connection
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if private_key_path and os.path.exists(private_key_path):
            ssh_client.connect(
                hostname=target_host,
                port=target_port,
                username=username,
                key_filename=private_key_path,
                timeout=30
            )
        elif password:
            ssh_client.connect(
                hostname=target_host,
                port=target_port,
                username=username,
                password=password,
                timeout=30
            )
        else:
            logger.error("No valid authentication method")
            return False
        
        logger.info("SSH connection established")
        
        # Create destination directory
        stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {destination_path}")
        stdout.channel.recv_exit_status()
        
        # Transfer archive
        logger.info("Transferring UERANSIM configs...")
        with scp.SCPClient(ssh_client.get_transport()) as scp_client:
            scp_client.put(tar_path, f"{destination_path}/ueransim_configs.tar.gz")
        
        logger.info("Extracting configs on target server...")
        
        # Extract and cleanup
        extract_cmd = f"cd {destination_path} && tar -xzf ueransim_configs.tar.gz && rm ueransim_configs.tar.gz"
        stdin, stdout, stderr = ssh_client.exec_command(extract_cmd)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status != 0:
            error_msg = stderr.read().decode()
            logger.error(f"Failed to extract configs: {error_msg}")
            return False
        
        # Set permissions
        chmod_cmd = f"chmod -R 755 {destination_path}/ueransim_configs"
        stdin, stdout, stderr = ssh_client.exec_command(chmod_cmd)
        stdout.channel.recv_exit_status()
        
        # List deployed files
        list_cmd = f"find {destination_path}/ueransim_configs -name '*.yaml' | wc -l"
        stdin, stdout, stderr = ssh_client.exec_command(list_cmd)
        file_count = stdout.read().decode().strip()
        
        ssh_client.close()
        
        # Cleanup
        os.remove(tar_path)
        os.rmdir(temp_dir)
        
        logger.info(f"✅ Successfully deployed {file_count} UERANSIM config files to {target_host}:{destination_path}")
        logger.info(f"📁 Configs location: {destination_path}/ueransim_configs/")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        return False

if __name__ == "__main__":
    deploy_ueransim_configs()