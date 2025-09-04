# Introduction

The project I been doing is developing a Network Digital Twin (NDT). NDT is a virtual clone of a physical network that capturing its architecture, components, and real-time state. NDT is important as it provide a safe, risk-free environment for simulating, analyzing, and optimizing network performance before making change on the live network.

# Objective

The objective of this project is to develop a 5G Standalone (5G SA) NDT for a physical network to help with simulate, analyze, and optimize network performance with the implementation of the AI models and apply the simulated result back to live network to help with improvement of the 5G SA Network.

# Milestones
## Milestone 1

### Preparation

Before starting with the development of NDT, I have first created 3 virtual machines (VMs) using Oracle VirtualBox and downloaded Ubuntu 22.04.5 (Jammy Jellyfish) from Ubuntu website to separate the 5G Cores, the Radio Access Network(RAN) using Next Generation Nobe B (gNB), and the User Equipment (UE). For the 5G Cores, I have selected Open5GS, an open-source project for building a personal NR/LTE network, and for the gNB and UE, I have selected UERANSIM, an open source state-of-the-art 5G UE and RAN simulator.

### Installation

For the installation of Ubuntu Jammy, you can [click here](https://releases.ubuntu.com/jammy) for the installation step of Ubuntu Jammy.\
For the installation of Open5GS, you can [click here](https://open5gs.org/open5gs/docs/guide/01-quickstart) for the installation step of Open5GS.\
For the installation of UERANSIM, you can [click here](https://github.com/aligungr/UERANSIM/wiki/Installation) for the installation step of UERANSIM.

### Configuration

### Open5GS

After done with the installation of Open5GS on the 5G Cores VM, I have start with the configuration of 5G cores to build a 5G SA network that can be connected from others VM. On default, the configuration of 5G Cores provided by Open5GS will all be set in loopback address. So we will need to apply a Host-only Adapter on the VM to obtain a new VM IP that can be communicate between VMs, the ip are automatically assigned are 192.168.56.XXX . Here are the table for each of the IP assigned on the VMs, you can check the IP address using 'ip a' and look for the 'inet' inside 'enp0s8'.

| Virtual Machines No. | Representing | IP Address |
| --- | --- | --- |
| VM1 | Open5GS Core | 192.168.56.101 |
| VM2 | UERANSIM gNB | 192.168.56.104 |
| VM3 | UERANSIM UE | 192.168.56.102 |

To setup a 5G SA Network, there are some necessary network functions (NFs) need to set up, mainly are NRF, AMF, SMF, AUSF, UDM, UDR, PCF, and UPF. Each of them are required to bind on the Open5GS VM IP with unique port. Here are the table for each of the NFs and their port assigned:

| Network Functions | IP Address | Assigned Port |
| --- | --- | --- |
| NRF | 192.168.56.101 | 7777 |
| AMF | 192.168.56.101 | 7778 |
| SMF | 192.168.56.101 | 7779 |
| AUSF | 192.168.56.101 | 7780 |
| UDM | 192.168.56.101 | 7781 |
| UDR | 192.168.56.101 | 7782 |
| PCF | 192.168.56.101 | 7783 |
| UPF | 192.168.56.101 | 9090 |

Apart from giving them unique port, it is also important to make change inside their own .yaml file if there is existence of other NFs inside it to ensure there is communication between it.

### UERANSIM gNB

After we have done with the configuration of 5G SA NFs, we will move to our RAN, it is very simple to configure the RAN using the preset configuration file given when installing UERANSIM, all it need is just some simple changes:

open5gs-gnb.yaml
```
--- mcc: '999'          # Mobile Country Code value
--- mnc: '70'           # Mobile Network Code value (2 or 3 digits)
+++ mcc: '001'
+++ mnc: '01'

nci: '0x000000010'  # NR Cell Identity (36-bit)
idLength: 32        # NR gNB ID length in bits [22...32]
tac: 1              # Tracking Area Code

--- linkIp: 127.0.0.1   # gNB's local IP address for Radio Link Simulation (Usually same with local IP)
--- ngapIp: 127.0.0.1   # gNB's local IP address for N2 Interface (Usually same with local IP)
--- gtpIp: 127.0.0.1    # gNB's local IP address for N3 Interface (Usually same with local IP)
+++ linkIp: 192.168.56.104
+++ ngapIp: 192.168.56.104
+++ gtpIP: 192.168.56.104

# List of AMF address information
amfConfigs:
---  - address: 127.0.0.5
+++ - address: 192.168.56.101
    port: 38412

# List of supported S-NSSAIs by this gNB
slices:
  - sst: 1

# Indicates whether or not SCTP stream number errors should be ignored.
ignoreStreamIds: true
```

All it need to do is make change on mcc and mnc, it is ok to use the default setting '999' and '70' but '001' and '01' is the generally used for testing, remember if you updated these 2 values, you will also need to update it on the Open5GS NFs if its .yaml configuration have mentioned mcc and mnc. Then, update linkIp, ngapIp, gtpIp to the device own assigned IP Address since default is on loopback addresses. Lastly, make change on the address inside 'amfConfigs' to match with the VM IP that AMF is located. After doing all of that, the configuration of gNB is completed.

### UERANSIM UE

Moving on from gNB, you will need to create a UE to simulate connection, similar to gNB configuration, the file are also prepared when installing UERANSIM and just need to make some simple change:

open5gs-ue.yaml
```
# IMSI number of the UE. IMSI = [MCC|MNC|MSISDN] (In total 15 digits)
--- supi: 'imsi-999700000000001'
+++ supi: 'imst-001010000000001'
# Mobile Country Code value of HPLMN
--- mcc: '999'
+++ mcc: '001'
# Mobile Network Code value of HPLMN (2 or 3 digits)
--- mnc: '70'
+++ mnc: '01'
# SUCI Protection Scheme : 0 for Null-scheme, 1 for Profile A and 2 for Profile B
protectionScheme: 0
# Home Network Public Key for protecting with SUCI Profile A
homeNetworkPublicKey: '5a8d38864820197c3394b92613b20b91633cbd897119273bf8e4a6f4eec0a650'
# Home Network Public Key ID for protecting with SUCI Profile A
homeNetworkPublicKeyId: 1
# Routing Indicator
routingIndicator: '0000'

# Permanent subscription key
key: '465B5CE8B199B49FAA5F0A2EE238A6BC'
# Operator code (OP or OPC) of the UE
op: 'E8ED289DEBA952E4283B54E88E6183CA'
# This value specifies the OP type and it can be either 'OP' or 'OPC'
opType: 'OPC'
# Authentication Management Field (AMF) value
amf: '8000'
# IMEI number of the device. It is used if no SUPI is provided
imei: '356938035643803'
# IMEISV number of the device. It is used if no SUPI and IMEI is provided
imeiSv: '4370816125816151'

# Network mask used for the UE's TUN interface to define the subnet size  
tunNetmask: '255.255.255.0'

# List of gNB IP addresses for Radio Link Simulation
gnbSearchList:
---  - 127.0.0.1
+++  - 192.168.56.104
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
---    apn: 'internet'
+++    dnn: 'internet'
    slice:
      sst: 1

# Configured NSSAI for this UE by HPLMN
configured-nssai:
  - sst: 1

# Default Configured NSSAI for this UE
default-nssai:
  - sst: 1
    sd: 1

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
```

Like gNB, the mcc and mnc were changed to '001' and '01', the first 5 or 6 digit of imsi represent the mcc and mnc assigned, note that mnc '01' and mnc '001' are completely different things when making configuration, and the behind digit are the subscriber number. For gnbSearchList, it is changed to the gNB VM IP, which is 192.168.56.104, and the initial PDU session change the network type from apn to dnn as apn is only used in a loopback address, while dnn is used when connecting across VMs.

### Building gNB and UE

After we done with the configuration of gNB and UE, it is time for us to build it. To build the gnb, you just need to type the following command:

```
cd/UERANSIM
./nr-gnb -c ../config/your_gnb_filename.yaml
```

Same goes to UE:
```
cd/UERANSIM
sudo ./nr-ue -c ../config/your_ue_filename.yaml
```

To verify it is successfully built, you can check the log outcome generated when creating them, look for the line **NG Setup procedure is successful** for gNB and **Connection setup for PDU session[1] is successful, TUN interface[uesismtun0, 10.45.X.X] is up** for UE.

If you wish to create multiple UE at once then you can run this command:
```
sudo ./nr-ue -c ../config/your_ue_filename.yaml -n <number>
```

## Connectivity test

To test connection to network existed in UE, we can use ping or curl to the network to verify the connection. Here are some example of connectivity test using ping and curl to the internet.
```
ping -I uesimtun0 8.8.8.8
```
or
```
sudo curl --interface uesimtun0 google.com
```

## Summary

In summary, the first milestone of this project is to create a functional network digital twin, after successfully created the network digital twin, I will be moving to creating the twinning agent for both physical and digital side components, as well as UE mirroring will be implemented afterward.

## Milestone 2

### Target goal

To develop twinning agent for physical testbed and virtual testbed and connect both of them using Mosquitto MQTT, Eclipse Mosquitto. The use of twinning agent is to ensure there is a communication link between both testbed. 

In this milestone stage, the work completed were automize UE registration, synchronize traffic data, and create monitoring tools, these combined are the concept of twinning agent. Each work progress will be explain in details later. The whole procress is necessary as it is needed for achieving ZeroTouch Network & Service Management (ZSM). 

### UE Registration

To start with recording the UE Register, we need to start both twinning agent on the testbeds, with main.py running on the physical Open5GS server to be the MQTT Broker and digital_twin_listener_Open5GS.py and digital_twin_listner_UERANSIM.py running on their own machine to act as a MQTT Receiver. When physical Open5GS have recorded a subscriber data inside its database, it will convert the contents into a snapshot saved in json file and sent to the receiver, this process is done every 1 minute. For NDT Open5GS when it receive the subscribers snapshot json it will read the content inside and insert the details into the database so subscriber details like imsi, key, opc, etc. will also be duplicated to NDT Open5GS database from physical Open5GS database. For NDT UERANSIM, it will generate the UE.yaml files based on the subscriber snapshot json it received, the yaml file generated are exactly the same based on the template given in UERANSIM WIKI. Then after the UE creation it will give a 30 seconds delay to bootup each UE to avoid conflicting in assigning IP to each UE.

So to use it, user will first enter their imsi into physical Open5GS database through the Open5GS webui so the network will recognize the UE and clone the details in NDT Open5GS database, then connect the physical UE to the RAN (srsRAN), when connection is established, it will also tell the UE created in NDT UERANSIM to boot up the UE with the same imsi. Thus, the UE mirrored session is established.

### Traffic Data

After the UE mirrored session is established, user can start with some simple data traffic test like iperf3 or ping, the MQTT broker will then sent the process to the listener and it will automatically translate the process that is recognized by the UERANSIM UE, for iperf3 it will be translated to run using nr-binder instead, and for ping it will bind the uesimtunX to the targeted IP. Currently both process are directed to their personal Open5GS to achieve synchronized process, but the result will be different due to the application on both testbed are in a different environment setup.

### Monitoring 

To achieve this, the tools used for the visualizing the metrics is the combination of Prometheus and Grafana. Each machine (mainly RAN and Open5GS Server) were installed with Node Exporter to retrieve all metrics inside the machine and Prometheus is used to retrieve all the metrics from Node Exporter into it. To allow Prometheus to retrieve metrics from Node Exporter, you will need to create prometheus.yml file in /etc/prometheus directory, the sample of prometheus.yml is like this:

prometheus.yml
```
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "physical"
    static_configs:
      - targets: ["192.168.0.190:9100"] # Physical Open5GS
        labels:
          env: "physical"
          role: "open5gs"
      - targets: ["192.168.0.126:9100"] # Physical gNB
        labels:
          env: "physical"
          role: "gnb"

  - job_name: "ndt"
    static_configs:
      - targets: ["192.168.0.115:9100"] # NDT Open5GS
        labels:
          env: "ndt"
          role: "open5gs"
      - targets: ["192.168.0.189:9100"] # NDT UERANSIM gNB
        labels:
          env: "ndt"
          role: "gnb"
```

Then, we will go to the Grafana web page, **http://localhost:3000**, to login as admin and setup Grafana to set Prometheus as data source to display the metrics inside Prometheus and fill the URL with the default shown inside Grafana **http://localhost:9090**. The setting can be found on clicking the Grafana Logo on the top-right corner -> Connection -> Data Sources. After that, we will need to create the dashboard, to access there we will be clicking the "+" button on the top-left corner -> import dashboard and use the built in dashboard ID for Node Exporter, 1960, and select the Prometheus data sources created recently. Now, you will see the dashboard UI displayed and you can edit the metrics to be observed based on your preference.

## Summary

To summarize up, the second milesstone basically tell the deployment of twinning agent with their built in functions and step to set up the monitoring tools. For next milestone, I will be implement the AI Analysis tools to help with network optimisation.
