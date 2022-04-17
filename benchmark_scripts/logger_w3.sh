#!/usr/bin/env bash
if [ "$1" != "" ]; then
	LOG_DIR="$1"
	mkdir -p $LOG_DIR
else
	LOG_DIR="."
fi
LOG_DIR=$1
CPU_LOG_FILENAME=$LOG_DIR/cpu_util_3.log
DISK_LOG_FILENAME=$LOG_DIR/disk_util_3.log
NW_LOG_FILENAME=$LOG_DIR/nw_util_3.log
while true;
do
	datestr=`date "+%Y-%m-%d %H:%M:%S"`
	cpu="$[100-$(vmstat 1 2|tail -1|awk '{print $15}')]%"
	mem=$(free | grep Mem | awk '{print $3/$2 * 100.0 "%"}')
	echo -e "${datestr}\n${cpu},${mem}" >> $CPU_LOG_FILENAME;
	disk_log=$(iostat -dm 1 1 | sed '1,2d')
	echo -e "${datestr}\n${disk_log}" >> $DISK_LOG_FILENAME;
	msg_control=$(sudo sar -n DEV 1 1 | grep eno1 | tail -n 1 | gawk '{print "eno1: "$2", rxpck/s: "$3", txpck/s: "$4", rxkB/s: "$5", txkB/s: "$6", rxcmp/s: "$7", txcmp/s: "$8", rxmcst/s: "$9", %ifutil: "$10}')
	echo -e "${datestr}\n${msg_control}" >> $NW_LOG_FILENAME;
	sleep 1;
done
