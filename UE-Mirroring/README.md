# How to use?
## ue_listener.py

User will need to run this on their UERANSIM UE. This python code is required to run together with **open5gs_log_listner.py** on the twinning agent. This python code
is mainly used in mirroring the physical UE. It will receive a specific wording from the twinning agent and it will start/stop the virtual UE with the same IMSI
as the physical UE.

Using another UERANSIM UE as an example of physical UE, user will need to run the UE using **sudo ./nr-ue -c <../config/ue1.yaml>**. Then it will connected to a gNB
and Open5GS AMF log will update and record the connected UE IMSI, then twinning agent will retrieve and sent that line to the NDT UERANSIM and it will start the
UE with the same IMSI mentioned

For disconnecting the physical UE, user are required to use **./nr-cli <imsi-001010000000001> and it will enter the cli of the UE, user can check what they can do
using **commands**. For disconnecting, user will run this in the cli, **deregister switch-off** and it will shut down the UE gracefully. We do not use Ctrl+C to
shutdown the physical UE because the action happen too immediate and Open5GS AMF log are unable to update until a new UE is connected. After the physical UE is
gracefully disconnected, the NDT UERANSIM UE will also disconnect from the NDT UERANSIM gNB.
