# How to use?
## open5gs_twinning_agent.py
In order to run the twinning agent, you must first create a **twinning_config.json** for configure your physical Open5GS IP and MongoDB port, twinning agent IP and MongoDB port, NDT Open5GS IP, and NDT UERANSIM IP.
These configuration are being used to pinpoint the destination, you can run **open5gs_twinning_agent.py** and it will show a selection panel like this:

```
=== Open5GS Database Twinning Agent ===
0. Configure target destinations
1. Process data only (retrieve, mirror, generate configs)
2. Deploy database to NDT Open5GS
3. Deploy UERANSIM configs to server
4. Collect traffic data from physical network and deploy to NDT
5. Run periodic automated twinning (fetch + process + deploy + traffic)
```

Then you can proceed with other step. For the 1. function, it is used to retrieve the physical Open5GS database data and save to local database, and it will create
configured UERANSIM UE based on the data retrieved from the database. 

Move on to 2. to 4. functions, these functions are manual way of deployment to their target, it will ask for credentials like the machine username and its password
as it used SSH to help with the transportation of data, user can also use SSH key instead if they have one prepared on the twinning agent.

For the last function, it is used to run process 2. to 4. periodically, user are able to set the timer for each new period happening, the default is set on 60 seconds.
Every time when it reached the target clock, it will automatically do all the fetching, processing, and sending process.

A **twinning_agent.log** are also generated, user are able to keep track the past action of the twinning agent.

## open5gs_log_listener.py
This python3 mainly run to support the **ue_listner.py** located in the **UE-Mirroring** folder, what it does is to retrieve the physical Open5GS AMF and SMF log
messages so when it detect a new UE connected on the physical side, it will display the specific wording from the log and tell the NDT to bootup the UE with the
same IMSI as the physical UE.
