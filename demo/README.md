# Demo Workflow: 5G Digital Twin Final Showcase
## 🎯 Objective
Demonstrate real-time synchronization and interaction between a physical 5G standalone (SA) network and its digital twin, highlighting:
- State mirroring
- Command reflection
- AI-driven monitoring or control feedback

![your-UML-diagram-name](http://www.plantuml.com/plantuml/proxy?cache=no&src=https://raw.githubusercontent.com/Siong23/5g-digital-twin/refs/heads/main/demo/plantuml.puml)

## 🧵 Workflow Steps
### Initialization
  - ✅ Start the physical 5G network (USRP + srsRAN + Open5GS) on edge node.
  - ✅ Boot up digital twin environment (UERANSIM + Open5GS) in a virtualized/cloud environment.
  - ✅ Launch MQTT-based twinning agents on both sides to establish a control and data exchange channel.

### Device Connection
  - 📱 Connect real UE(s) (smartphone, PC) to the physical network.
  - 🖥️ Launch virtual UE(s) in UERANSIM to simulate load or mirror sessions.
  - 🔄 Twinning agent syncs UE session states (e.g., registration, PDU session, mobility events) to the digital twin.

### Session Emulation and Telemetry
  - 📶 In the physical network, initiate a data session (e.g., video stream or file download).
  - 🔁 MQTT twinning agent publishes session stats (e.g., throughput, latency, packet loss) to digital twin.
  - 📡 Digital twin replicates the session or simulates it based on mirrored parameters.

### Real-Time Monitoring
  - 📊 Use Prometheus/Grafana dashboards to visualize metrics from both physical and digital networks.
  - 🧠 Optionally, activate an AI-based inference module to analyze KPIs and detect anomalies or suggest reconfiguration (e.g., scaling UPF, changing slice priority).

### Control Feedback Loop (Optional)
  - ⚙️ AI/Analytics engine in the twin triggers a control command (e.g., scale a CNF, reconfigure a bearer).
  - 🔄 Control signal is sent via MQTT to the physical twinning agent.
  - 🔧 The physical 5G testbed applies changes via srsRAN CLI/API or Open5GS reconfigurations.

### Wrap-Up and Summary
  - 📽️ Highlight the twin synchronization with logs/metrics.
  - 📁 Show comparative performance between physical and digital networks.
  - 💡 Discuss how this setup can enable safer, scalable testing of future 5G services.

