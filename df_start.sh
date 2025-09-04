#!/bin/bash
./df_stop.sh
echo "Stop df first"

# Define the paths for the PID files
RSSI_PID_FILE="main_get_rssi.pid"
MAIN_PID_FILE="main.pid"

rm /shared/realtime/rssi/*
echo "Clean /shared/realtime/rssi/*"

rm /shared/realtime/predicted/*
echo "Clean /shared/realtime/predicted/*"

# Check and start main_get_rssi.py
if [ -f "$RSSI_PID_FILE" ]; then
    RSSI_PID=$(cat "$RSSI_PID_FILE")
    # Check if the PID is running and is the intended main_get_rssi.py script
    if ps -p "$RSSI_PID" -o cmd= | grep -q "main_get_rssi.py"; then
        echo "main_get_rssi.py is already running with PID $RSSI_PID"
    else
        rm "$RSSI_PID_FILE"
    fi
fi

if [ ! -f "$RSSI_PID_FILE" ]; then
    nohup /root/mambaforge/envs/wisar/bin/python main_get_rssi.py --layout-prefix=TR > main_get_rssi.log 2>&1 &
    echo $! > $RSSI_PID_FILE
    sleep 1  # Give it a moment to start
    RSSI_PID=$(cat "$RSSI_PID_FILE")
    if ps -p "$RSSI_PID" > /dev/null; then
        taskset -cp 1 "$RSSI_PID"
        echo "main_get_rssi.py started on CPU 1 with PID $RSSI_PID"
        # renice -20 -p "$RSSI_PID"
    else
        echo "Failed to start main_get_rssi.py"
    fi
fi

# Check and start main.py
if [ -f "$MAIN_PID_FILE" ]; then
    MAIN_PID=$(cat "$MAIN_PID_FILE")
    # Check if the PID is running and is the intended main.py script
    if ps -p "$MAIN_PID" -o cmd= | grep -q "main.py"; then
        echo "main.py is already running with PID $MAIN_PID"
    else
        rm "$MAIN_PID_FILE"
    fi
fi

if [ ! -f "$MAIN_PID_FILE" ]; then
    nohup /root/mambaforge/envs/wisar/bin/python main.py --log DEBUG --data-dir ./data/case5-3d --realtime --calibration --pos-elevation --no-plot > main.log 2>&1 &
    echo $! > $MAIN_PID_FILE
    sleep 1  # Give it a moment to start
    MAIN_PID=$(cat "$MAIN_PID_FILE")
    if ps -p "$MAIN_PID" > /dev/null; then
        taskset -cp 2 "$MAIN_PID"
        echo "main.py started on CPU 2 with PID $MAIN_PID"
        # renice -20 -p "$MAIN_PID"
    else
        echo "Failed to start main.py"
    fi
fi
