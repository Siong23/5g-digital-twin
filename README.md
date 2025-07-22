# 5g-digital-twin

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
  | (Real RAN & 5GC)|                                                     | (Simulated RAN)  |
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
- Both twins connect via N2/N3 interfaces to Open5GS.
- External interfaces (e.g., for orchestration, monitoring, or AI analysis) can be layered on top.
