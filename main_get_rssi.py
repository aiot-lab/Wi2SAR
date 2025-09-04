import os
import time
import json
import yaml
import argparse
import subprocess
import glob
from contextlib import contextmanager


from module.rssi_update import fetch_nic_config, create_nic_objects, nic_list_clear, nic_list_is_cleared, NOISE_LEVEL_DB, is_pid_running

def load_nic_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.load(file, Loader=yaml.FullLoader)

SKIP_TIMEIT_OUTPUT = False

@contextmanager
def timeit(name=""):
    start = time.time()  # Record the start time
    try:
        yield  # Yield control back to the block using the context
    finally:
        end = time.time()  # Record the end time
        if not SKIP_TIMEIT_OUTPUT:
            print(f"[{name}] Time elapsed: {end - start:.2f} seconds")
            
NIC_SEL = ["8c", "6c", "4c", "c0", "60"]
MAX_MPDU_BACK = 4
MAX_LINE_BACK = 400

RESTART_AP_ON_ERROR = True

# Path
AP_TARGET_MAC_ROOT = "/shared/realtime/ap/target/"
RSSI_SAVE_ROOT = "/shared/realtime/rssi"

def output_rssi_data(target, mpdu_seq_num, data_dict):
    for bus_no, (energy_a, energy_b) in data_dict[mpdu_seq_num].items():
        for nic in nics:
            if nic.bus_no == bus_no:
                nic.update_rssi(energy_a, energy_b)
                break
    
    if not nic_list_is_cleared(nics):
        # save_rssi_data(args, nics, './data/realtime/rssi.tsv', angle=[])
        save_rssi_data(args, nics, f'{RSSI_SAVE_ROOT}/{target}.tsv', angle=[])
        save_ant_status(target, nics, '/shared/realtime/rc/all_antenna.status')

def monitor_dmesg(args, nics):
    try:
        target_list = None
        old_target_list = None

        while True:
            target_list = [
                os.path.splitext(os.path.basename(f))[0] 
                for f in os.listdir(AP_TARGET_MAC_ROOT) 
                if os.path.isfile(os.path.join(AP_TARGET_MAC_ROOT, f))
            ]
            
            if old_target_list != target_list and target_list:
                old_target_list = target_list
                print(f"Target: {target_list}")
            
            if not target_list:
                continue
            with timeit("one round RSSI"):
                with timeit("read dmesg"):
                    dmesg_output = os.popen('dmesg').read().strip().split('\n')[::-1]
            
                # target_seq_bus_num_dict[MAC2][seq][bus] = (rssi_a, rssi_b)
                target_seq_bus_num_dict = {}
                for target in target_list:
                    target_seq_bus_num_dict[target] = {}
                    
                nic_list_clear(nics)
                data_line = 0
                
                for line in dmesg_output:
                    if 'iwl_mvm_rx_mpdu_mq' in line:
                        try:
                            timestamp, json_data = line.split('] ')
                            try:
                                json_data = json_data.strip()
                            except:
                                print("Next line")
                            data = json.loads(json_data)

                            addr1 = data['iwl_mvm_rx_mpdu_mq']['addr1']
                            addr2 = data['iwl_mvm_rx_mpdu_mq']['addr2']
                            addr3 = data['iwl_mvm_rx_mpdu_mq']['addr3']

                            # if not (addr1 == addr3 and
                            #         addr2 in target_list and
                            #         addr1[:2] in NIC_SEL):
                            #     continue
                            
                            if not (addr2 in target_list):
                                continue
                            target = addr2
                            data_line += 1
                                
                            mpdu_seq_num = data['iwl_mvm_rx_mpdu_mq']['mpdu_seq_num']
                            bus_no = data['iwl_mvm_rx_mpdu_mq']['bus_no']
                            energy_a = data['iwl_mvm_rx_mpdu_mq']['energy_a']
                            energy_b = data['iwl_mvm_rx_mpdu_mq']['energy_b']

                            this_target_seq_bus_num_dict = target_seq_bus_num_dict[target]
                            if mpdu_seq_num not in this_target_seq_bus_num_dict:
                                this_target_seq_bus_num_dict[mpdu_seq_num] = {}

                            this_target_seq_bus_num_dict[mpdu_seq_num][bus_no] = (energy_a, energy_b)
                            
                            target_seq_bus_num_dict[target] = this_target_seq_bus_num_dict

                            ##################################
                            # Check if this target can be removed
                            ##################################
                            
                            # if this_target_seq_bus_num_dict[mpdu_seq_num] reach len(NIC_SEL) output when mpdu_seq_num is
                            # max_seq_num, otherwise continue
                            if len(this_target_seq_bus_num_dict[mpdu_seq_num]) == len(NIC_SEL):
                                print(f"{target} reach len(NIC_SEL)")
                                max_seq_num = max(this_target_seq_bus_num_dict.keys())
                                if mpdu_seq_num == max_seq_num:
                                    # if mpdu_seq_num 
                                    # for bus_no, (energy_a, energy_b) in this_target_seq_bus_num_dict[mpdu_seq_num].items():
                                    #     for nic in nics:
                                    #         if nic.bus_no == bus_no:
                                    #             nic.update_rssi(energy_a, energy_b)
                                    #             break
                                    
                                    # if not nic_list_is_cleared(nics):
                                    #     # save_rssi_data(args, nics, './data/realtime/rssi.tsv', angle=[])
                                    #     save_rssi_data(args, nics, f'{RSSI_SAVE_ROOT}/{addr2}.tsv', angle=[])
                                    #     save_ant_status(target, nics, '/shared/realtime/rc/all_antenna.status')
                                    
                                    output_rssi_data(target, mpdu_seq_num, this_target_seq_bus_num_dict)
                                    # remove target from target_seq_bus_num_dict
                                    del target_seq_bus_num_dict[target]
                                    # go on next record
                                    break
                            
                            if len(this_target_seq_bus_num_dict.keys()) == MAX_MPDU_BACK or data_line == MAX_LINE_BACK:
                                if data_line == MAX_LINE_BACK:
                                    print(f"{target} reach MAX_LINE_BACK")
                                else:
                                    print(f"{target} reach MAX_MPDU_BACK")
                                    
                                # print(seq_num_dict)
                                for k, v in this_target_seq_bus_num_dict.items():
                                    print(f"{k}:{v}")
                                
                                # second_max_seq_num = sorted(seq_num_dict.keys())[-2]
                                max_len_seq_num = max((k 
                                                    for k in this_target_seq_bus_num_dict 
                                                    if len(this_target_seq_bus_num_dict[k]) == max(len(v) for v in this_target_seq_bus_num_dict.values())), key=lambda k: (len(this_target_seq_bus_num_dict[k]), k))
                                print(f"Save {max_len_seq_num}", len(this_target_seq_bus_num_dict[max_len_seq_num].items()))
                                
                                # for bus_no, (energy_a, energy_b) in this_target_seq_bus_num_dict[max_len_seq_num].items():
                                #     for nic in nics:
                                #         if nic.bus_no == bus_no:
                                #             nic.update_rssi(energy_a, energy_b)
                                #             break
                                
                                # if not nic_list_is_cleared(nics):
                                #     # save_rssi_data(args, nics, './data/realtime/rssi.tsv', angle=[])
                                #     save_rssi_data(args, nics, f'{RSSI_SAVE_ROOT}/{addr2}.tsv', angle=[])
                                #     save_ant_status(target, nics, '/shared/realtime/rc/all_antenna.status')
                                
                                output_rssi_data(target, max_len_seq_num, this_target_seq_bus_num_dict)
                                # remove target from target_seq_bus_num_dict
                                del target_seq_bus_num_dict[target]
                                # go on next record
                                break
                            
                        except Exception as e:
                            print(f"Error: {e}")
                            continue
                    
                    if len(target_seq_bus_num_dict.keys()) == 0:
                        # if all targets are removed
                        print("All target updated")
                        break
                    
                time.sleep(0.001)

    except KeyboardInterrupt:
        print("Terminated by user")

def save_ant_status(target, nics, output_file):
    rssi_list = glob.glob(os.path.join(RSSI_SAVE_ROOT, "*.tsv"))
    
    target_mac_list = []
    for rssi_file in rssi_list:
        mac = os.path.basename(rssi_file).split(".")[0]
        target_mac_list.append(mac)
     
    # write to output file
    if "nic_status" not in save_ant_status.__dict__:
        save_ant_status.nic_status = {}
    
    # if any of nic is not cleared, write a * to indicate that
    # else write a x to indicate that
    status_str = f""
    for nic in nics:
        if not nic.is_cleared():
            status_str += "*"
        else:
            if nic.check_ap_status():
                # ap is on, no signal
                status_str += "0"
            else:
                # ap is off, restart it
                if RESTART_AP_ON_ERROR:
                    if nic.start_pid is None or not is_pid_running(nic.start_pid):
                        nic.start_ap_non_blocking()
                    status_str += "R"
                else:
                    # ap is dead
                    status_str += "x"
            
    save_ant_status.nic_status[target] = status_str
    
    for mac in save_ant_status.nic_status.keys():
        if mac not in target_mac_list:
            del save_ant_status.nic_status[mac]  
              
    with open(output_file, 'w+') as file:
        for target, status in save_ant_status.nic_status.items():
            file.write(f"{target}: {status}\n")


def save_rssi_data(args, nics, output_file, angle=None):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    if angle is None:
        headers = []
        rssi_values = []
    elif angle == []:
        headers = ["A", "E"]
        rssi_values = ["N", "N"]
    elif isinstance(angle, tuple):
        headers = ["A", "E"]
        rssi_values = [f"{angle[0]}", f"{angle[1]}"]
        
    with open(output_file, 'w') as file:
        for nic in nics:
            headers.append(f"{args.layout_prefix}{nic.mac_addr[:2]}_1")
            headers.append(f"{args.layout_prefix}{nic.mac_addr[:2]}_2")
        file.write("\t".join(headers) + "\n")
        
        for nic in nics:
            ant1_rssi = nic.ant1_rssi if nic.ant1_rssi is not None else NOISE_LEVEL_DB
            ant2_rssi = nic.ant2_rssi if nic.ant2_rssi is not None else NOISE_LEVEL_DB
            rssi_values.append(str(ant1_rssi))
            rssi_values.append(str(ant2_rssi))
        file.write("\t".join(rssi_values) + "\n")

def is_hostap_running():
    # Check if there is a running process with the command `python3 ./hostap.py`
    try:
        # Using pgrep to find the process ID(s) of the running python3 ./hostap.py
        process = subprocess.run(['pgrep', '-f', 'python3 ./hostap.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return process.returncode == 0  # Return True if process found, False otherwise
    except Exception as e:
        print(f"An error occurred while checking the process: {e}")
        return False
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NIC Configuration and Real-time Monitoring")
    parser.add_argument('--layout-prefix', type=str, default="", help="Layout prefix") 
    args = parser.parse_args()

    RESTART_AP_ON_ERROR = RESTART_AP_ON_ERROR and is_hostap_running()
    
    # python3 ./hostap.py
    config_data = fetch_nic_config()
    nics = create_nic_objects(config_data)
    nics = [nic for nic in nics if nic.mac_addr[:2] in NIC_SEL]
    print([nic.mac_addr for nic in nics])

    monitor_dmesg(args, nics)
