# How to Use?

To replay a data traffic, you must first retrieve a traffic data file from physical network. You can retrieve it using the **open5gs_twinning_agent.py** on the
twinning agent to retrieve the traffic file needed.

Here are some references for how to create a traffic data:

```
Run all of this in their /Desktop/traffic_data
5GC VM
sudo tcpdump -i ogstun -w core_traffic.pcap host 10.45.0.X
ifstat -i ogstun 1 > core_ifstat.log

gNB VM
# see UE packets directly
sudo tcpdump -i enp0s9 -w gnb_gtp.pcap udp port 2152

UE VM
ping -I uesimtun0 8.8.8.8 -i 0.2 -s 64 -D -c 500 > ue_ping.log
```

## parse_traffic.py

This is use to parse the traffic collected from the physical network traffic data test. It is used to create a plot for the core bandwidth, gNB bandwidth, and
UE RTT and jitter. To use it you had to provide the path destination of the physical network traffic data test when running and it will track for the file it
need, if there is no file or the file name is incorrect it will show the error.

## traffic_replayer.py

This is used to generate the script that will replicate the traffic data collected from the physical network and push it to the NDT Open5GS and NDT UERANSIM, you
will need to enter the path destinaton of the physical network traffic data so it will be able to generate 3 new scripts **replay_traffic.sh**, **replay_traffic.py**,
and **inject_attacks.py**. More instructions will be given after all 3 scripts are generated.

### replay_traffic.sh

This is used to replay the traffic of the physical data, however it is not exactly accurate as the delay it used is calculated by mean rather than using the exact
timestamps as what ran on the physical network traffic data test and the bandwidth it generated is flat.

### replay_traffic.py

Similar to **replay_traffic.sh** but is more accurate as it use the exact same timestamps of the physical network traffic data test. The bandwidth it generated are
not exactly the same but rather similar of how it will look like on the physical network traffic data test.

### inject_attacks.py

It is used to inject network attack while running traffic replay on the UERANSIM UE. It will start network attacks based on the mode you selected on. User can learn
more information of how to use it by typing **inject_attacks.py -h**.

## collect_ndt_run.sh

After the replay is complete, user can run this shell scripts and it will retrieve the replay pcap and ue_log from the NDT side. It will be stored to the
**gnb_core_replay** by default and create a new folder every new day.

## parse_traffic_NDT.py

Same as the **parse_traffic.py** but it is used for parsing the replayed traffic run on the NDT.
