#!/usr/bin/env python3
"""
Open5GS Database Twinning Agent - Fixed Credentials Version

This agent retrieves Open5GS database from a physical 5G network,
creates a mirrored database, and generates UERANSIM UE configurations.
"""

import pymongo
import json
import logging
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib
import paramiko
import scp
import tarfile
import tempfile
import getpass
import subprocess
import shutil
import re
import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('twinning_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SubscriberData:
    """Open5GS Subscriber data structure"""
    imsi: str
    msisdn: str
    security: Dict[str, Any]
    ambr: Dict[str, Any]
    slice: List[Dict[str, Any]]
    
@dataclass
class UERANSIMConfig:
    """UERANSIM UE Configuration structure"""
    ue_id: str
    imsi: str
    key: str
    op: str
    op_type: str
    amf: str
    apn: str
    slice_id: str
    slice_sst: int

class Open5GSTwinningAgent:
    """Open5GS Database Twinning Agent"""
    CONFIG_FILE = "twinning_config.json"

    def __init__(self, source_ip: str = "192.168.0.190", source_port: int = 27017,
                 target_ip: str = "localhost", target_port: int = 27017):
        """
        Initialize the twinning agent
        
        Args:
            source_ip: IP address of source Open5GS database
            source_port: Port of source MongoDB
            target_ip: IP address for target database
            target_port: Port for target MongoDB
        """
        self.source_ip = source_ip
        self.source_port = source_port
        self.target_ip = target_ip
        self.target_port = target_port
        
        # Deployment targets
        self.ndt_server_ip = "192.168.0.132"
        self.ueransim_server_ip = "192.168.0.115"
        
        self.source_client = None
        self.target_client = None
        self.source_db = None
        self.target_db = None
        
        # Credentials cache - persistent across cycles
        self.credentials = {}
        self.credentials_initialized = False

    def save_config(self):
        """Save current configuration to JSON file"""
        config = {
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
            "ndt_server_ip": self.ndt_server_ip,
            "ueransim_server_ip": self.ueransim_server_ip,
        }
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {self.CONFIG_FILE}")

    def load_config(self):
        """Load configuration from JSON file if available"""
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, "r") as f:
                config = json.load(f)
                self.source_ip = config.get("source_ip", self.source_ip)
                self.source_port = config.get("source_port", self.source_port)
                self.target_ip = config.get("target_ip", self.target_ip)
                self.target_port = config.get("target_port", self.target_port)
                self.ndt_server_ip = config.get("ndt_server_ip", self.ndt_server_ip)
                self.ueransim_server_ip = config.get("ueransim_server_ip", self.ueransim_server_ip)
            logger.info(f"Loaded configuration from {self.CONFIG_FILE}")

        
    def configure_targets(self):
        """Configure source and deployment target addresses"""
        print("\n=== Configuration Setup ===")
        
        # Source database configuration
        print("\n--- Source Database Configuration ---")
        new_source_ip = input(f"Source Open5GS database IP ({self.source_ip}): ").strip()
        if new_source_ip:
            self.source_ip = new_source_ip
            
        new_source_port = input(f"Source MongoDB port ({self.source_port}): ").strip()
        if new_source_port:
            try:
                self.source_port = int(new_source_port)
            except ValueError:
                logger.warning("Invalid port number, keeping default")
        
        # Target database configuration
        print("\n--- Local Target Database Configuration ---")
        new_target_ip = input(f"Local target database IP ({self.target_ip}): ").strip()
        if new_target_ip:
            self.target_ip = new_target_ip
            
        new_target_port = input(f"Local target MongoDB port ({self.target_port}): ").strip()
        if new_target_port:
            try:
                self.target_port = int(new_target_port)
            except ValueError:
                logger.warning("Invalid port number, keeping default")
        
        # Deployment targets configuration
        print("\n--- Deployment Targets Configuration ---")
        new_ndt_ip = input(f"NDT Open5GS server IP ({self.ndt_server_ip}): ").strip()
        if new_ndt_ip:
            self.ndt_server_ip = new_ndt_ip
            
        new_ueransim_ip = input(f"UERANSIM server IP ({self.ueransim_server_ip}): ").strip()
        if new_ueransim_ip:
            self.ueransim_server_ip = new_ueransim_ip
        
        # Summary
        print(f"\n--- Configuration Summary ---")
        print(f"Source Database: {self.source_ip}:{self.source_port}")
        print(f"Local Target Database: {self.target_ip}:{self.target_port}")
        print(f"NDT Open5GS Server: {self.ndt_server_ip}")
        print(f"UERANSIM Server: {self.ueransim_server_ip}")
        
        confirm = input("\nConfirm configuration? (y/N): ").lower()
        if confirm != 'y':
            print("Configuration cancelled.")
            return 
            
        self.save_config()
        logger.info("Configuration updated successfully")
        return True

    def _get_credentials(self, username_prompt, ip):
        """Prompt for credentials if not cached, otherwise return cached ones."""
        if ip in self.credentials:
            logger.info(f"Using cached credentials for {ip}")
            return self.credentials[ip]

        creds = {}
        print(f"\n{username_prompt} ({ip})")
        username = input("Username: ").strip()
        creds["username"] = username
        method = input("Authentication method (password/key): ").strip().lower()

        if method == "password":
            creds["method"] = "password"
            creds["password"] = getpass.getpass("Password: ")
            creds["private_key"] = None  # ensure key exists for consistency

        elif method == "key":
            creds["method"] = "key"
            key_path = input("Private key path (~/.ssh/id_rsa): ").strip()
            if not key_path:
                key_path = "~/.ssh/id_rsa"
            key_path = os.path.expanduser(key_path)

            if not os.path.exists(key_path):
                print(f"⚠️ Key file not found: {key_path}, falling back to password.")
                creds["method"] = "password"
                creds["password"] = getpass.getpass("Password: ")
                creds["private_key"] = None
            else:
                creds["private_key"] = key_path
                creds["password"] = None  # keep consistent

        else:
            print("⚠️ Invalid method, falling back to password.")
            creds["method"] = "password"
            creds["password"] = getpass.getpass("Password: ")
            creds["private_key"] = None

        # Cache credentials for this IP
        self.credentials[ip] = creds
        logger.info(f"Cached credentials for {ip}")
        return creds

    def initialize_credentials(self):
        """Initialize credentials for all deployment targets once"""
        if self.credentials_initialized:
            return
        
        print("\n=== Initializing Deployment Credentials ===")
        print("Please provide credentials for deployment targets.")
        print("These will be cached for the session to avoid repeated prompts.")
        
        # Get NDT credentials
        self._get_credentials("=== NDT Open5GS Server Credentials ===", self.ndt_server_ip)
        
        # Get UERANSIM credentials
        self._get_credentials("=== UERANSIM Server Credentials ===", self.ueransim_server_ip)
        
        self.credentials_initialized = True
        logger.info("All deployment credentials initialized and cached")
        
    def connect_to_databases(self) -> bool:
        """Connect to both source and target MongoDB instances"""
        try:
            # Connect to source database
            source_uri = f"mongodb://{self.source_ip}:{self.source_port}/"
            self.source_client = pymongo.MongoClient(source_uri, serverSelectionTimeoutMS=5000)
            self.source_db = self.source_client.open5gs
            
            # Test source connection
            self.source_client.admin.command('ismaster')
            logger.info("Successfully connected to source Open5GS database")
            
            # Connect to target database
            target_uri = f"mongodb://{self.target_ip}:{self.target_port}/"
            self.target_client = pymongo.MongoClient(target_uri, serverSelectionTimeoutMS=5000)
            self.target_db = self.target_client.open5gs_twin
            
            # Test target connection
            self.target_client.admin.command('ismaster')
            logger.info("Successfully connected to target database")
            
            return True
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def retrieve_subscribers(self) -> List[Dict[str, Any]]:
        """Retrieve all subscriber data from source Open5GS database"""
        try:
            subscribers_collection = self.source_db.subscribers
            subscribers = list(subscribers_collection.find({}))
            logger.info(f"Retrieved {len(subscribers)} subscribers from source database")
            return subscribers
            
        except Exception as e:
            logger.error(f"Failed to retrieve subscribers: {e}")
            return []
    
    def mirror_database(self) -> bool:
        """Create a complete mirror of the Open5GS database"""
        try:
            # Get all collection names from source
            collections = self.source_db.list_collection_names()
            logger.info(f"Found collections: {collections}")
            
            for collection_name in collections:
                source_collection = self.source_db[collection_name]
                target_collection = self.target_db[collection_name]
                
                # Drop existing collection in target
                target_collection.drop()
                
                # Copy all documents
                documents = list(source_collection.find({}))
                if documents:
                    target_collection.insert_many(documents)
                    logger.info(f"Mirrored {len(documents)} documents in {collection_name}")
                
                # Copy indexes
                indexes = source_collection.list_indexes()
                for index in indexes:
                    if index['name'] != '_id_':  # Skip default _id index
                        try:
                            target_collection.create_index(
                                list(index['key'].items()), 
                                name=index['name']
                            )
                        except Exception as idx_e:
                            logger.warning(f"Could not create index {index['name']}: {idx_e}")
            
            logger.info("Database mirroring completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database mirroring failed: {e}")
            return False
    
    def clean_key_value(self, key_value: str) -> str:
        """Clean key value by removing spaces and ensuring proper format"""
        if not key_value:
            return ""
        
        # Remove all spaces and whitespace
        cleaned = re.sub(r'\s+', '', str(key_value))
        
        # Ensure it's proper hex format (only 0-9, a-f, A-F)
        if re.match(r'^[0-9a-fA-F]+$', cleaned):
            return cleaned.upper()  # Return uppercase
        else:
            logger.warning(f"Invalid key format detected: {key_value}, cleaned to: {cleaned}")
            return cleaned.upper()  # Return uppercase
    
    def extract_op_value(self, security: Dict[str, Any]) -> tuple[str, str]:
        """Extract OP/OPC value and determine type from security data"""
        # Check for OPC first (more common in Open5GS)
        if 'opc' in security and security['opc']:
            opc_value = self.clean_key_value(security['opc'])
            if opc_value:
                return opc_value, 'OPC'
        
        # Check for OP
        if 'op' in security and security['op']:
            op_value = self.clean_key_value(security['op'])
            if op_value:
                return op_value, 'OP'
        
        # Default fallback if neither found
        logger.warning("No OP/OPC found in security data, using default")
        return '63BFA50EE6523365FF14C1F45F88737D', 'OPC'  # Common test OPC value
    
    def generate_ueransim_configs(self, subscribers: List[Dict[str, Any]]) -> List[UERANSIMConfig]:
        """Generate UERANSIM UE configurations based on subscriber data"""
        ue_configs = []
        
        for idx, subscriber in enumerate(subscribers):
            try:
                imsi = subscriber.get('imsi', '')
                if not imsi:
                    logger.warning(f"Subscriber {idx} missing IMSI, skipping")
                    continue
                
                # Extract and clean security information
                security = subscriber.get('security', {})
                
                # Clean the K value
                key = self.clean_key_value(security.get('k', ''))
                if not key:
                    logger.warning(f"Subscriber {imsi} missing or invalid K value, using default")
                    key = '465B5CE8B199B49FAA5F0A2EE238A6BC'  # Default test key
                
                # Extract OP/OPC value and type
                op_value, op_type = self.extract_op_value(security)
                
                # Extract AMF value
                amf = security.get('amf', '8000')
                if isinstance(amf, dict):
                    amf = '8000'  # Default if AMF is object
                amf = self.clean_key_value(str(amf)) or '8000'
                
                # Extract slice information
                slice_data = subscriber.get('slice', [])
                slice_info = slice_data[0] if slice_data else {}
                
                s_nssai = slice_info.get('s_nssai', {})
                sst = s_nssai.get('sst', 1)
                sd = s_nssai.get('sd', '000001')
                
                # Ensure SD is properly formatted as hex string
                if isinstance(sd, int):
                    sd = f"{sd:06x}"
                elif isinstance(sd, str):
                    # Remove any non-hex characters and ensure 6 digits
                    sd = re.sub(r'[^0-9a-fA-F]', '', sd)
                    sd = sd.zfill(6) if len(sd) <= 6 else sd[:6]
                
                # Extract APN/DNN information
                session = slice_info.get('session', [])
                apn = 'internet'  # default
                if session and len(session) > 0:
                    session_data = session[0]
                    apn = session_data.get('name', 'internet')
                
                # Create UE configuration
                ue_config = UERANSIMConfig(
                    ue_id=f"ue_{idx + 1:03d}",  # Format as ue_001, ue_002, etc.
                    imsi=imsi,
                    key=key,
                    op=op_value,
                    op_type=op_type,
                    amf=amf,
                    apn=apn,
                    slice_id=sd,  # Keep as hex string
                    slice_sst=sst
                )
                
                ue_configs.append(ue_config)
                logger.info(f"Generated UE config for IMSI: {imsi} (Key: {key[:8]}..., OP: {op_value[:8]}..., Type: {op_type})")
                
            except Exception as e:
                logger.error(f"Error generating UE config for subscriber {idx}: {e}")
                continue
        
        logger.info(f"Successfully generated {len(ue_configs)} UE configurations")
        return ue_configs
    
    def create_ueransim_yaml_configs(self, ue_configs: List[UERANSIMConfig], 
                                   output_dir: str = "ueransim_configs") -> bool:
        """Create UERANSIM YAML configuration files"""
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            for ue_config in ue_configs:
                # Extract MCC and MNC from IMSI
                imsi = ue_config.imsi
                mcc = imsi[:3]  # First 3 digits
                
                # MNC extraction logic: if 6th digit is 0, then MNC is 4th-5th digits, else 4th-6th digits
                if len(imsi) >= 6:
                    if imsi[5] == '0':
                        mnc = imsi[3:5]  # 2-digit MNC (4th-5th digits)
                    else:
                        mnc = imsi[3:6]  # 3-digit MNC (4th-6th digits)
                else:
                    mnc = imsi[3:5] if len(imsi) >= 5 else "01"  # fallback
                
                # Create YAML content with exact format specified
                yaml_content = f"""# IMSI number of the UE. IMSI = [MCC|MNC|MSISDN] (In total 15 digits)
supi: 'imsi-{imsi}'
# Mobile Country Code value of HPLMN
mcc: '{mcc}'
# Mobile Network Code value of HPLMN (2 or 3 digits)
mnc: '{mnc}'
# SUCI Protection Scheme : 0 for Null-scheme, 1 for Profile A and 2 for Profile B
protectionScheme: 0
# Home Network Public Key for protecting with SUCI Profile A
homeNetworkPublicKey: '5a8d38864820197c3394b92613b20b91633cbd897119273bf8e4a6f4eec0a650'
# Home Network Public Key ID for protecting with SUCI Profile A
homeNetworkPublicKeyId: 1
# Routing Indicator
routingIndicator: '0000'
# Permanent subscription key
key: '{ue_config.key}'
# Operator code (OP or OPC) of the UE
op: '{ue_config.op}'
# This value specifies the OP type and it can be either 'OP' or 'OPC'
opType: '{ue_config.op_type}'
# Authentication Management Field (AMF) value
amf: '{ue_config.amf}'
# IMEI number of the device. It is used if no SUPI is provided
imei: '356938035643803'
# IMEISV number of the device. It is used if no SUPI and IMEI is provided
imeiSv: '4370816125816151'
# List of gNB IP addresses for Radio Link Simulation
gnbSearchList:
  - 192.168.0.115
# UAC Access Identities Configuration
uacAic:
  mps: false
  mcs: false
# UAC Access Control Class
uacAcc:
  normalClass: 0
  class11: false
  class12: false
  class13: false
  class14: false
  class15: false
# Initial PDU sessions to be established
sessions:
  - type: 'IPv4'
    dnn: '{ue_config.apn}'
    slice:
      sst: {ue_config.slice_sst}
# Configured NSSAI for this UE by HPLMN
configured-nssai:
  - sst: {ue_config.slice_sst}
# Default Configured NSSAI for this UE
default-nssai:
  - sst: {ue_config.slice_sst}
    sd: {ue_config.slice_id}
# Supported integrity algorithms by this UE
integrity:
  IA1: true
  IA2: true
  IA3: true
# Supported encryption algorithms by this UE
ciphering:
  EA1: true
  EA2: true
  EA3: true
# Integrity protection maximum data rate for user plane
integrityMaxRate:
  uplink: 'full'
  downlink: 'full'
"""
                
                # Write UE configuration file
                config_filename = os.path.join(output_dir, f'{ue_config.ue_id}.yaml')
                with open(config_filename, 'w') as f:
                    f.write(yaml_content)
                
                logger.info(f"Created UERANSIM config: {config_filename} (MCC: {mcc}, MNC: {mnc})")
            
            # Create a summary file
            summary = {
                'total_ues': len(ue_configs),
                'created_at': datetime.now().isoformat(),
                'ue_list': [asdict(ue) for ue in ue_configs]
            }
            
            with open(os.path.join(output_dir, 'ue_summary.json'), 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Created {len(ue_configs)} UERANSIM configurations")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create UERANSIM configs: {e}")
            return False
    
    def run_twinning_cycle(self) -> bool:
        """Execute complete twinning cycle"""
        logger.info("Starting Open5GS twinning cycle...")
        
        try:
            # Step 1: Connect to databases
            if not self.connect_to_databases():
                return False
            
            # Step 2: Retrieve subscriber data
            subscribers = self.retrieve_subscribers()
            if not subscribers:
                logger.warning("No subscribers found in source database")
                return False
            
            # Step 3: Mirror the database
            if not self.mirror_database():
                return False
            
            # Step 4: Generate UERANSIM configurations
            ue_configs = self.generate_ueransim_configs(subscribers)
            if not ue_configs:
                logger.warning("No UE configurations generated")
                return False
            
            # Step 5: Create UERANSIM YAML files
            if not self.create_ueransim_yaml_configs(ue_configs):
                return False
            
            logger.info("Twinning cycle completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Twinning cycle failed: {e}")
            return False
        finally:
            # Clean up connections
            if self.source_client:
                self.source_client.close()
            if self.target_client:
                self.target_client.close()
    
    def _create_ssh_connection(self, ip: str) -> paramiko.SSHClient:
        """Create SSH connection using cached credentials"""
        creds = self.credentials.get(ip)
        if not creds:
            raise Exception(f"No cached credentials found for {ip}")
        
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if creds["method"] == "key" and creds["private_key"]:
            ssh_client.connect(
                hostname=ip,
                port=22,
                username=creds["username"],
                key_filename=creds["private_key"],
                timeout=30
            )
        elif creds["method"] == "password" and creds["password"]:
            ssh_client.connect(
                hostname=ip,
                port=22,
                username=creds["username"],
                password=creds["password"],
                timeout=30
            )
        else:
            raise Exception(f"Invalid authentication method for {ip}")
        
        return ssh_client
    
    def deploy_database_to_ndt_open5gs(self, ndt_ip: str = None) -> bool:
        """Deploy Open5GS database to NDT Open5GS server"""
        try:
            # Use configured IP if none provided
            if ndt_ip is None:
                ndt_ip = self.ndt_server_ip

            logger.info(f"Starting database deployment to NDT Open5GS at {ndt_ip}...")
            
            # Get database configuration (only prompt once, not for credentials)
            if not hasattr(self, 'ndt_mongo_config'):
                print(f"\n=== NDT Open5GS Database Configuration ===")
                mongo_port = int(input("MongoDB port on NDT server (27017): ") or 27017)
                database_name = input("Database name (open5gs): ") or "open5gs"
                self.ndt_mongo_config = {
                    'port': mongo_port,
                    'database': database_name
                }
            else:
                mongo_port = self.ndt_mongo_config['port']
                database_name = self.ndt_mongo_config['database']
            
            # Create database dump
            dump_dir = tempfile.mkdtemp()
            dump_path = os.path.join(dump_dir, "open5gs_dump")
            
            logger.info("Creating database dump...")
            dump_cmd = [
                "mongodump",
                "--host", f"{self.target_ip}:{self.target_port}",
                "--db", "open5gs_twin",
                "--out", dump_path
            ]
            
            result = subprocess.run(dump_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"mongodump failed: {result.stderr}")
                return False
            
            # Create tar archive
            tar_path = os.path.join(dump_dir, "open5gs_dump.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(dump_path, arcname="open5gs_dump")
            
            logger.info("Connecting to NDT Open5GS server...")
            
            # Create SSH connection using cached credentials
            ssh_client = self._create_ssh_connection(ndt_ip)
            
            # Transfer dump to NDT server
            logger.info("Transferring database dump...")
            with scp.SCPClient(ssh_client.get_transport()) as scp_client:
                scp_client.put(tar_path, "/tmp/open5gs_dump.tar.gz")
            
            logger.info("Extracting and restoring database on NDT server...")
            
            # Extract and restore commands
            commands = [
                "cd /tmp && tar -xzf open5gs_dump.tar.gz",
                f"mongorestore --host localhost:{mongo_port} --db {database_name} --drop /tmp/open5gs_dump/open5gs_twin/",
                "rm -rf /tmp/open5gs_dump*"
            ]
            
            for cmd in commands:
                stdin, stdout, stderr = ssh_client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status != 0:
                    error_msg = stderr.read().decode()
                    logger.error(f"Command failed: {cmd}\nError: {error_msg}")
                    ssh_client.close()
                    return False
                else:
                    logger.info(f"Executed: {cmd}")
            
            # Verify deployment
            verify_cmd = f"mongo --host localhost:{mongo_port} {database_name} --eval 'db.subscribers.count()'"
            stdin, stdout, stderr = ssh_client.exec_command(verify_cmd)
            subscriber_count = stdout.read().decode().strip()
            
            ssh_client.close()
            
            # Cleanup local files
            shutil.rmtree(dump_dir)
            
            logger.info(f"✅ Database successfully deployed to NDT Open5GS at {ndt_ip}")
            logger.info(f"📊 Subscribers in deployed database: {subscriber_count}")
            return True
            
        except Exception as e:
            logger.error(f"❌ NDT database deployment failed: {e}")
            return False
    
    def deploy_ueransim_configs_to_server(self, server_ip: str = None) -> bool:
        """Deploy UERANSIM configurations to server"""
        try:
            # Use configured IP if none provided
            if server_ip is None:
                server_ip = self.ueransim_server_ip

            logger.info(f"Starting UERANSIM configs deployment to {server_ip}...")
            
            if not os.path.exists("ueransim_configs"):
                logger.error("UERANSIM configs directory not found")
                return False
            
            # Get destination configuration (only prompt once, not for credentials)
            if not hasattr(self, 'ueransim_deploy_config'):
                print(f"\n=== UERANSIM Deployment Configuration ===")
                destination_path = input("Destination path (/opt/ueransim): ") or "/opt/ueransim"
                self.ueransim_deploy_config = {
                    'destination_path': destination_path
                }
            else:
                destination_path = self.ueransim_deploy_config['destination_path']
            
            # Create tar archive
            temp_dir = tempfile.mkdtemp()
            tar_path = os.path.join(temp_dir, "ueransim_configs.tar.gz")
            
            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add("ueransim_configs", arcname="ueransim_configs")
            
            logger.info("Connecting to UERANSIM server...")
            
            # Create SSH connection using cached credentials
            ssh_client = self._create_ssh_connection(server_ip)
            
            # Create destination directory
            stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {destination_path}")
            stdout.channel.recv_exit_status()
            
            # Transfer configs
            logger.info("Transferring UERANSIM configs...")
            with scp.SCPClient(ssh_client.get_transport()) as scp_client:
                scp_client.put(tar_path, f"{destination_path}/ueransim_configs.tar.gz")
            
            # Extract configs
            logger.info("Extracting configs on server...")
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
            
            # Count deployed files
            list_cmd = f"find {destination_path}/ueransim_configs -name '*.yaml' | wc -l"
            stdin, stdout, stderr = ssh_client.exec_command(list_cmd)
            file_count = stdout.read().decode().strip()
            
            ssh_client.close()
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            logger.info(f"✅ Successfully deployed {file_count} UERANSIM configs to {server_ip}:{destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ UERANSIM deployment failed: {e}")
            return False

    def collect_traffic_data_from_physical(self) -> bool:
        """Collect traffic data from physical Open5GS and deploy to NDT"""
        try:
            logger.info(f"Starting traffic data collection from {self.source_ip}...")
            
            # Get traffic collection configuration (only prompt once)
            if not hasattr(self, 'traffic_config'):
                print(f"\n=== Traffic Data Collection Configuration ===")
                physical_data_path = input("Physical network data path (/home/ubuntu/Desktop): ") or "/home/ubuntu/Desktop"
                ndt_data_path = input("NDT destination path (/srv/ndt_data): ") or "/srv/ndt_data"
                
                self.traffic_config = {
                    'physical_path': physical_data_path,
                    'ndt_path': ndt_data_path
                }
            else:
                physical_data_path = self.traffic_config['physical_path']
                ndt_data_path = self.traffic_config['ndt_path']
            
            # Create destination directory with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_dir = f"run{timestamp}"
            
            # Files to collect from physical network
            traffic_files = [
                f"{physical_data_path}/core_traffic.pcap",
                f"{physical_data_path}/core_traffic.csv",
                f"{physical_data_path}/core_ifstat.log"
            ]
            
            logger.info("Connecting to physical Open5GS server...")
            
            # Create SSH connection to physical Open5GS (same IP as source database)
            ssh_client = self._create_ssh_connection(self.source_ip)
            
            # Create temporary local directory
            temp_dir = tempfile.mkdtemp()
            local_collected = []
            
            # Collect files from physical server
            logger.info("Collecting traffic data files...")
            with scp.SCPClient(ssh_client.get_transport()) as scp_client:
                for remote_file in traffic_files:
                    try:
                        local_file = os.path.join(temp_dir, os.path.basename(remote_file))
                        scp_client.get(remote_file, local_file)
                        local_collected.append(local_file)
                        logger.info(f"Collected: {os.path.basename(remote_file)}")
                    except Exception as e:
                        logger.warning(f"Could not collect {remote_file}: {e}")
            
            ssh_client.close()
            
            if not local_collected:
                logger.error("No traffic files were collected")
                shutil.rmtree(temp_dir)
                return False
            
            # Create tar archive of collected data
            tar_path = os.path.join(temp_dir, "traffic_data.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                for file in local_collected:
                    tar.add(file, arcname=os.path.basename(file))
            
            logger.info(f"Deploying traffic data to NDT Open5GS at {self.ndt_server_ip}...")
            
            # Connect to NDT server
            ndt_ssh = self._create_ssh_connection(self.ndt_server_ip)
            
            # Create destination directory on NDT
            mkdir_cmd = f"mkdir -p {ndt_data_path}/{dest_dir}"
            stdin, stdout, stderr = ndt_ssh.exec_command(mkdir_cmd)
            stdout.channel.recv_exit_status()
            
            # Transfer tar archive to NDT
            logger.info("Transferring traffic data archive...")
            with scp.SCPClient(ndt_ssh.get_transport()) as scp_client:
                scp_client.put(tar_path, f"/tmp/traffic_data.tar.gz")
            
            # Extract on NDT server
            extract_cmd = f"cd {ndt_data_path}/{dest_dir} && tar -xzf /tmp/traffic_data.tar.gz && rm /tmp/traffic_data.tar.gz"
            stdin, stdout, stderr = ndt_ssh.exec_command(extract_cmd)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error_msg = stderr.read().decode()
                logger.error(f"Failed to extract traffic data: {error_msg}")
                ndt_ssh.close()
                shutil.rmtree(temp_dir)
                return False
            
            # Convert PCAP to CSV on NDT if needed
            logger.info("Converting PCAP to CSV on NDT server...")
            convert_cmd = f"""
            cd {ndt_data_path}/{dest_dir} && \
            if [ -f core_traffic.pcap ]; then \
                tshark -r core_traffic.pcap -T fields \
                -e frame.time -e ip.src -e ip.dst -e gtp.teid -e frame.len \
                -E separator=$'\\t' > core_traffic.csv 2>/dev/null || true; \
            fi
            """
            stdin, stdout, stderr = ndt_ssh.exec_command(convert_cmd)
            stdout.channel.recv_exit_status()
            
            # List files to verify
            list_cmd = f"ls -lh {ndt_data_path}/{dest_dir}"
            stdin, stdout, stderr = ndt_ssh.exec_command(list_cmd)
            file_list = stdout.read().decode()
            
            ndt_ssh.close()
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            logger.info(f"Traffic data deployed to {self.ndt_server_ip}:{ndt_data_path}/{dest_dir}")
            logger.info(f"Files:\n{file_list}")
            return True
            
        except Exception as e:
            logger.error(f"Traffic data collection failed: {e}")
            return False

    def run_periodic_twinning(self, interval: int = 60, collect_traffic: bool = True):
        """Run twinning + deployment periodically with optional traffic collection."""
        logger.info(f"Starting periodic twinning every {interval} seconds...")
        if collect_traffic:
            logger.info("Traffic data collection enabled")
        
        # Initialize credentials once before starting the loop
        self.initialize_credentials()

        try:
            cycle_count = 0
            while True:
                cycle_count += 1
                logger.info(f"Running scheduled twinning cycle #{cycle_count}...")
                
                # Step 1: Run twinning cycle (database + configs)
                success = self.run_twinning_cycle()
                
                if success:
                    logger.info("Twinning cycle successful, deploying...")
                    
                    # Step 2: Deploy database
                    db_deployed = self.deploy_database_to_ndt_open5gs()
                    
                    # Step 3: Deploy UERANSIM configs
                    configs_deployed = self.deploy_ueransim_configs_to_server()
                    
                    # Step 4: Collect and deploy traffic data (if enabled)
                    if collect_traffic:
                        logger.info("Collecting traffic data from physical network...")
                        traffic_collected = self.collect_traffic_data_from_physical()
                        if traffic_collected:
                            logger.info("Traffic data collection successful")
                        else:
                            logger.warning("Traffic data collection failed")
                    
                    if db_deployed and configs_deployed:
                        logger.info(f"Cycle #{cycle_count} completed successfully")
                    else:
                        logger.warning(f"Cycle #{cycle_count} completed with some failures")
                else:
                    logger.warning(f"Twinning cycle #{cycle_count} failed, skipping deployment")

                logger.info(f"Sleeping for {interval} seconds before next cycle...")
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info(f"Periodic twinning stopped by user after {cycle_count} cycles")

def main():
    """Main function to run the twinning agent"""
    print("=== Open5GS Database Twinning Agent ===")
    print("0. Configure target destinations")
    print("1. Process data only (retrieve, mirror, generate configs)")
    print("2. Deploy database to NDT Open5GS")
    print("3. Deploy UERANSIM configs to server")
    print("4. Collect traffic data from physical network and deploy to NDT")
    print("5. Run periodic automated twinning (fetch + process + deploy + traffic)")

    choice = input("\nSelect option (0-5): ")

    agent = Open5GSTwinningAgent(
        source_ip="192.168.0.188",
        source_port=27017,
        target_ip="localhost",
        target_port=27017
    )

    agent.load_config()
    logger.info(f"Twinning Agent initialized - Source: {agent.source_ip}:{agent.source_port}")

    if choice == "0":
        success = agent.configure_targets()
        if success:
            print("\n✅ Configuration completed successfully!")
            print(f"- Source Database: {agent.source_ip}:{agent.source_port}")
            print(f"- Local Target Database: {agent.target_ip}:{agent.target_port}")
            print(f"- NDT Open5GS Server: {agent.ndt_server_ip}")
            print(f"- UERANSIM Server: {agent.ueransim_server_ip}")

    elif choice == "1":
        if agent.run_twinning_cycle():
            print("\n✅ Data processing completed successfully!")

    elif choice == "2":
        agent.initialize_credentials()
        if agent.deploy_database_to_ndt_open5gs():
            print("\n✅ Database deployed to NDT Open5GS!")

    elif choice == "3":
        agent.initialize_credentials()
        if agent.deploy_ueransim_configs_to_server():
            print("\n✅ UERANSIM configs deployed successfully!")
    
    elif choice == "4":
        agent.initialize_credentials()
        if agent.collect_traffic_data_from_physical():
            print("\n✅ Traffic data collected and deployed to NDT!")

    elif choice == "5":
        try:
            interval = int(input("Enter interval in seconds (default 60): ") or "60")
        except ValueError:
            interval = 60
        
        collect_traffic = input("Enable traffic data collection? (Y/n): ").lower() != 'n'
        agent.run_periodic_twinning(interval, collect_traffic)

    else:
        print("❌ Invalid choice. Exiting.")


if __name__ == "__main__":
    main()