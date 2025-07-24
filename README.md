# 5g-digital-twin

🚀 **5g-digital-twin** is a research-driven project to create a digital twin of a physical 5G standalone (SA) network. It enables synchronized experimentation and simulation using real-time data exchange between a physical 5G testbed and its virtual replica. This twin architecture allows researchers and engineers to prototype, test, and monitor 5G applications and network functions in a safe, repeatable, and flexible environment.

---

## 🧠 Key Features

- **Physical 5G Testbed** with real smartphones/PCs, USRP SDRs, `srsRAN`, and `Open5GS`.
- **Digital Twin** using `UERANSIM` and `Open5GS` to simulate UEs and core functions.
- **Twinning Agents** using lightweight `MQTT` protocol for state synchronization and command exchange.
- Support for 5G core features including AMF/SMF, user plane routing, and mobility management.
- Enables **closed-loop control, analytics, and AI-driven experimentation**.

---
## 🏗️ Architecture
```
                          +-----------------------------------------+
                          |        5G Network Digital Twin          |
                          |      (Simulation + Real Integration)    |
                          +-------------------+---------------------+
                                              |
         +------------------------------------+-------------------------------------+
         |                                                                          |
         |                                                                          |
  +------+---------+                                                      +----------+-------+
  |  Physical Twin |                                                      |   Digital Twin   |
  |(Real RAN & 5GC)|                                                      | (Simulated RAN)  |
  +----------------+                                                      +------------------+
  |                |                                                      |                  |
  | +------------+ |                   +-------------+                    |  +------------+  |
  | |  srsRAN    | |------------------>| MQTT broker |------------------> |  | UERANSIM   |  |
  | | (gNB + DU) | |                   +-------------+                    |  | (gNB + UE) |  |
  | +------------+ |                                                      |  +------------+  |
  |                |                                                      |                  |
  | +------------+ |                                                      |  +------------+  |
  | | Open5GS    | |                                                      |  |  Open5GS   |  |
  | | (5G Core)  | |                                                      |  |  (5G Core) |  |
  | +------------+ |                                                      |  +------------+  |
  +----------------+                                                      +------------------+

```
Notes:
- srsRAN is used to provide a physical 5G RAN environment (e.g., SDR + gNB stack).
- UERANSIM acts as the digital twin's simulated gNB and UE, emulating traffic and scenarios.
- External interfaces (e.g., for orchestration, monitoring, or AI analysis) can be layered on top.

---

## 🔧 Components

| Component           | Description                                         |
|---------------------|-----------------------------------------------------|
| **srsRAN**          | Software radio access network for gNB (5G base station) |
| **Open5GS**         | Open-source 5G core network                         |
| **UERANSIM**        | User Equipment and gNB simulator for 5G SA         |
| **MQTT**            | Messaging protocol for twin synchronization        |
| **Twinning Agent**  | Custom script to collect and relay UE/session state |

---

## 📁 Repository Structure

```
5g-digital-twin/
├── physical/               # Setup scripts for real testbed (srsRAN, Open5GS)
├── digital/                # Setup for digital twin (UERANSIM, Open5GS)
├── twin-agents/            # MQTT-based synchronization scripts
├── configs/                # Network configurations and profiles
├── docs/                   # Diagrams, documentation, and setup guides
├── scripts/                # Utility scripts for monitoring, logging, etc.
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

---

## 📦 Getting Started

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/5g-digital-twin.git
   cd 5g-digital-twin
   ```

2. **Set Up Physical Network**
   - Install `srsRAN`, `Open5GS`, and configure USRP SDR.

3. **Set Up Digital Twin**
   - Launch `UERANSIM` and `Open5GS` using provided configs.

4. **Run Twinning Agents**
   ```bash
   python twin-agents/sync_agent.py --config configs/mqtt_physical.yaml
   python twin-agents/sync_agent.py --config configs/mqtt_digital.yaml
   ```

5. **Visualize or Control from Dashboard**
   - Access Web UI (optional) or monitor via logs/terminal.

---

## 🧪 Use Cases

- Compare behavior between real and simulated 5G sessions
- Replay test cases in the digital twin environment
- Analyze anomalies or conduct failure simulations
- AI/ML testing for network optimization and security

---

## 📚 Documentation

See the [docs/](./docs/) folder for:

- Step-by-step setup guides
- Configuration examples
- Architecture and MQTT message formats
