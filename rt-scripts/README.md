# Real-time Direction Finding Scripts

This directory contains shell scripts for managing real-time direction finding operations on Raspberry Pi or embedded systems.

## Overview

The Wi²SAR system can operate in real-time mode to continuously monitor Wi-Fi signals and estimate target direction. These scripts manage the lifecycle of two Python processes that work together:

1. **RSSI Collection** (`main_get_rssi.py`): Monitors network interfaces and collects RSSI measurements
2. **Direction Finding** (`main.py`): Processes RSSI data in real-time and estimates target direction

## Scripts

### df_start.sh

Starts the real-time direction finding system.

**What it does:**
1. Stops any existing processes (calls `df_stop.sh`)
2. Cleans up shared directories for RSSI and prediction data
3. Starts `main_get_rssi.py` for RSSI collection
4. Starts `main.py` for direction finding and analysis
5. Assigns each process to a dedicated CPU core for optimal performance
6. Creates PID files for process management

**Usage:**
```bash
cd rt-scripts
bash df_start.sh
```

**Process Management:**
- `main_get_rssi.py` → CPU core 1 → PID stored in `main_get_rssi.pid`
- `main.py` → CPU core 2 → PID stored in `main.pid`
- Both processes run in background with output redirected to log files

**CPU Affinity:**
The script uses `taskset` to pin each process to a specific CPU core, reducing context switching and improving real-time performance:
- RSSI collection on core 1 (lighter workload)
- Direction finding on core 2 (heavier computational load)

### df_stop.sh

Safely stops the real-time direction finding system.

**What it does:**
1. Terminates `main_get_rssi.py` process
2. Terminates `main.py` process
3. Cleans up shared directories
4. Removes PID files

**Usage:**
```bash
cd rt-scripts
bash df_stop.sh
```

**Safety Features:**
- Verifies PIDs before terminating to prevent killing wrong processes
- Matches process names to ensure correct processes are stopped
- Graceful shutdown using SIGTERM (not SIGKILL)

## System Requirements

### Hardware
- **Platform**: Raspberry Pi 4 or similar embedded Linux system
- **CPU**: Multi-core processor (2+ cores recommended)
- **Memory**: 2GB+ RAM
- **Network**: Multiple Wi-Fi network interfaces (specified in layout configuration)

### Software
- **OS**: Linux (tested on Raspberry Pi OS)
- **Python**: 3.8+ with Wi²SAR dependencies installed
- **Privileges**: Root or sudo access for network interface control
- **Dependencies**:
  - `taskset` (CPU affinity control)
  - `nohup` (background process management)
  - Standard shell utilities (`ps`, `kill`, `rm`, etc.)

## Configuration

### Environment Setup

The scripts assume the following Python environment:
```bash
/root/mambaforge/envs/wisar/bin/python
```

**To customize the Python path:**
Edit both scripts and update the Python interpreter path on lines containing `nohup`.

### Data Directories

The scripts use these shared directories (must exist with write permissions):
- `/shared/realtime/rssi/` - RSSI measurement files
- `/shared/realtime/predicted/` - Direction prediction output

**To customize directories:**
1. Create your desired directories
2. Edit both scripts and update the paths
3. Ensure the user has read/write permissions

### Layout Configuration

The RSSI collection uses a layout prefix to select antenna configurations:
```bash
--layout-prefix=TR
```

## Monitoring

### Check Running Status

```bash
# Check if processes are running
ps aux | grep "main.py\|main_get_rssi.py"

# Check PID files
cat main.pid main_get_rssi.pid

# Check CPU affinity
taskset -cp $(cat main.pid)
taskset -cp $(cat main_get_rssi.pid)
```

### View Logs

```bash
# Real-time log monitoring
tail -f ../main.log
tail -f ../main_get_rssi.log

# View full logs
less ../main.log
less ../main_get_rssi.log
```

### Monitor Output

```bash
# Check RSSI data collection
ls -lah /shared/realtime/rssi/

# Check direction predictions
ls -lah /shared/realtime/predicted/
```

## Troubleshooting

### Processes Won't Start

**Issue:** Scripts run but processes don't start

**Solutions:**
1. Check Python environment exists:
   ```bash
   ls /root/mambaforge/envs/wisar/bin/python
   ```

2. Verify permissions on shared directories:
   ```bash
   ls -ld /shared/realtime/rssi/ /shared/realtime/predicted/
   ```

3. Check for port conflicts or locked resources

4. Review log files for error messages

### Processes Keep Dying

**Issue:** Processes start but immediately terminate

**Solutions:**
1. Check system resources:
   ```bash
   free -h  # Memory
   df -h    # Disk space
   ```

2. Verify network interfaces are available:
   ```bash
   ip link show
   ```

3. Check for Python errors in log files

4. Ensure data files exist in `../data/case5-3d/`

### High CPU Usage

**Issue:** System becomes sluggish

**Solutions:**
1. Verify CPU affinity is set correctly:
   ```bash
   taskset -cp $(cat main.pid)
   ```

2. Consider reducing logging level from DEBUG to INFO:
   Edit `df_start.sh` and change `--log DEBUG` to `--log INFO`

3. Monitor actual CPU usage:
   ```bash
   top -p $(cat main.pid),$(cat main_get_rssi.pid)
   ```

### Permission Denied Errors

**Issue:** Cannot write to shared directories

**Solutions:**
1. Create directories with correct permissions:
   ```bash
   sudo mkdir -p /shared/realtime/{rssi,predicted}
   sudo chmod 777 /shared/realtime/{rssi,predicted}
   ```

2. Or run scripts with sudo:
   ```bash
   sudo bash df_start.sh
   ```

### Scripts Won't Execute

**Issue:** Permission denied when running scripts

**Solution:**
```bash
chmod +x df_start.sh df_stop.sh
```

## Performance Tuning

### Optimize for Raspberry Pi 4

1. **Increase process priority** (uncomment lines in scripts):
   ```bash
   renice -20 -p "$RSSI_PID"
   renice -20 -p "$MAIN_PID"
   ```

2. **Disable unnecessary services** to free resources:
   ```bash
   sudo systemctl disable bluetooth
   sudo systemctl stop bluetooth
   ```

3. **Overclock** (if using active cooling):
   Edit `/boot/config.txt` and add:
   ```
   over_voltage=6
   arm_freq=2000
   ```

### Adjust CPU Affinity

For different hardware configurations, modify CPU assignments in `df_start.sh`:
```bash
taskset -cp 0 "$RSSI_PID"  # Use core 0 instead of 1
taskset -cp 1,2,3 "$MAIN_PID"  # Use cores 1-3 for direction finding
```

## Integration with Main System

### Autostart on Boot

Create a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/wisar-df.service
```

Add content:
```ini
[Unit]
Description=Wi2SAR Direction Finding Service
After=network.target

[Service]
Type=forking
User=root
WorkingDirectory=/path/to/wisar_website
ExecStart=/path/to/wisar_website/rt-scripts/df_start.sh
ExecStop=/path/to/wisar_website/rt-scripts/df_stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable wisar-df
sudo systemctl start wisar-df
```

### Remote Management

Use SSH to manage the system remotely:
```bash
ssh pi@raspberry-pi-address
cd /path/to/wisar_website/rt-scripts
bash df_start.sh
```

## Reference

For more information about the main scripts:
- `main.py` - See main project [README](../README.md)
- `main_get_rssi.py` - RSSI collection module
- Data formats - See [data/case5-3d/README.md](../data/case5-3d/) (if available)

---

**Project:** Wi²SAR - "Take Me Home, Wi-Fi Drone"  
**Organization:** HKU AIoT Lab  
**Website:** https://aiot-lab.github.io/Wi2SAR
