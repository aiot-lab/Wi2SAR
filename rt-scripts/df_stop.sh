#!/bin/bash

# Define the paths for the PID files
RSSI_PID_FILE="main_get_rssi.pid"
MAIN_PID_FILE="main.pid"

# Function to safely terminate a process
terminate_process() {
    local pid_file=$1
    local process_name=$2

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        # Check if the process with the PID is running and matches the process name
        if ps -p "$pid" -o cmd= | grep -q "$process_name"; then
            echo "Stopping $process_name with PID $pid"
            kill "$pid"
            rm "$pid_file"
        else
            echo "Process with PID $pid not running or not $process_name"
            rm "$pid_file"
        fi
    else
        echo "$pid_file not found."
    fi
}

# Safely terminate main_get_rssi.py
terminate_process "$RSSI_PID_FILE" "main_get_rssi.py"

# Safely terminate main.py
terminate_process "$MAIN_PID_FILE" "main.py"

# Clean up directories
rm -rf /shared/realtime/rssi/*
echo "Cleaned /shared/realtime/rssi/*"

rm -rf /shared/realtime/predicted/*
echo "Cleaned /shared/realtime/predicted/*"
