import os
import yaml
import subprocess

NOISE_LEVEL_DB = -127

class NIC:
    def __init__(self, mac_addr, bus_no, phy_no, noise_level=NOISE_LEVEL_DB):
        self.mac_addr = mac_addr
        self.bus_no = bus_no
        self.phy_no = phy_no
        self.ant1_rssi = NOISE_LEVEL_DB
        self.ant2_rssi = NOISE_LEVEL_DB
        self.noise = noise_level
        self.cleared = True
        self.on = False
        self.iface = get_interface_by_mac(self.mac_addr)
        self.start_pid = None

    def check_ap_status(self):
        # check if wlan-mon exists
        mon_iface = get_interface_by_mac(self.mac_addr, "mon")
        if mon_iface is None:
            return False
            # print(f"Interface {wlan_mon_name} found for MAC {self.mac_addr}")
        
        # check if ap pid is running
        pid_path = f"/root/wifi-framework/log/{self.iface}.pid"
        is_running = is_pidfile_running(pid_path)

        return is_running

    
    def start_ap_non_blocking(self):
        if self.check_ap_status():
            print(f"AP already started on {self.iface}")
            return
        
        wlanid = self.iface.split("wlan")[-1]
        # Build the command
        cmd = ["/root/wifi-framework/ap_start_wlanid.sh", wlanid]
        
        # Start the script using Popen to avoid blocking
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Print the PID of the process
        print(f"Started AP script for {wlanid}")
        self.start_pid = process.pid
        
        return 
    
    def update_rssi(self, ant1_rssi, ant2_rssi):
        self.ant1_rssi = ant1_rssi
        self.ant2_rssi = ant2_rssi
        if self.ant1_rssi != NOISE_LEVEL_DB or self.ant2_rssi != NOISE_LEVEL_DB:
            self.cleared = False
            self.on = True
    
    def clear_rssi(self):
        self.ant1_rssi = self.noise
        self.ant2_rssi = self.noise
        self.cleared = True
    
    def is_cleared(self):
        return self.cleared
    
    def __str__(self):
        return f"NIC {self.mac_addr} on bus {self.bus_no} with PHY {self.phy_no} has RSSI: {self.ant1_rssi}, {self.ant2_rssi}"

def get_interface_by_mac(mac_address, mon=False):
    cmd = "ip link show | grep -i -B1 " + f"{mac_address}"+ "| awk -F: '/^[0-9]/ {print $2}'"
    result = subprocess.check_output(cmd, shell=True).decode().strip()

    for line in result.split('\n'):
        if mon:
            if 'mon' in line:
                interface = line
                return interface
        else:
            if 'wlan' in line and "mon" not in line:
                interface = line
                return interface
    return None

def is_pid_running(pid):
    """
    Check if a process with the given PID is currently running and not a zombie.

    Parameters:
    pid (int): The process ID to check.

    Returns:
    bool: True if the process is running and not a zombie, False otherwise.
    """
    try:
        with open(f"/proc/{pid}/status", 'r') as f:
            status_info = f.read()
        
        # Check for the process state
        for line in status_info.splitlines():
            if line.startswith("State:"):
                state = line.split()[1]
                if state == 'Z':
                    print(f"Process with PID {pid} is a zombie.")
                    return False
                else:
                    return True
    except FileNotFoundError:
        # Process does not exist
        return False
    except Exception as e:
        print(f"An error occurred while checking the process: {e}")
        return False

def is_pidfile_running(pid_file_path):
    try:
        # Check if the PID file exists
        if not os.path.exists(pid_file_path):
            print(f"PID file {pid_file_path} does not exist.")
            return False

        # Read the PID from the file
        with open(pid_file_path, 'r') as pid_file:
            pid = int(pid_file.read().strip())
        
        return is_pid_running(pid)
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def nic_list_clear(nic_list):
    for nic in nic_list:
        nic.clear_rssi()

def nic_list_is_cleared(nic_list):
    for nic in nic_list:
        if nic.cleared:
            continue
        else:
            return False
    return True
         
def fetch_nic_config():
    pci_devices_path = '/sys/bus/pci/devices/'
    pattern = '0000:'
    config_data = []

    for device in os.listdir(pci_devices_path):
        if device.startswith(pattern) and device.endswith(':00.0'):
            bus_no_str = device.split(':')[1]
            bus_no = int(bus_no_str)

            ieee80211_path = os.path.join(pci_devices_path, device, 'ieee80211')
            if os.path.isdir(ieee80211_path):
                phy_dir = os.listdir(ieee80211_path)[0]
                phy_no_str = phy_dir.replace('phy', '')
                phy_no = int(phy_no_str)

                macaddress_path = os.path.join(ieee80211_path, phy_dir, 'macaddress')
                with open(macaddress_path, 'r') as mac_file:
                    mac = mac_file.read().strip()

                config_data.append({
                    'mac': mac,
                    'bus_no': bus_no,
                    'phy_no': phy_no
                })

    config_path = './data/realtime/hw_number.yaml'
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as file:
        yaml.dump(config_data, file, default_flow_style=False)

    return config_data


def create_nic_objects(config_data):
    return [NIC(config['mac'], config['bus_no'], config['phy_no'], NOISE_LEVEL_DB) for config in config_data]
