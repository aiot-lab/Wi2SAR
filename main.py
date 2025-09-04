"""
Main Module
===========
This module serves as the entry point for running the signal processing and plotting.
"""

import argparse
# import logging
from loguru import logger
import os
import time
import numpy as np
import yaml
import pickle
import glob
import sys

from datetime import datetime
from module.data_processing import (
    load_layout, load_signals, construct_beam_pattern,
    read_measured_rssi_from_file,
    recalculate_rssi_calibration
)
from module.evaluation import calculate_similarity_matrix, performance_judge, timeit
from module.basic_classes import BeamPattern, Location, normalize_angles
from module.plot import plot_beam_pattern_2d, plot_beam_pattern_3d, plot_similarity_matrix, wait_for_user

log_filename = None

RSSI_SAVE_ROOT = "/shared/realtime/rssi"
RC_SAVE_ROOT = "/shared/realtime/rc"

IWCH_MAC = "e2:b0:1b:21:fd:b8"
IP06_MAC = "54:9f:13:92:15:8a"
IP15_MAC = "42:0c:dd:c4:07:6c"
RDMI_MAC = "c2:ea:bb:73:96:29"
IP11_MAC = "26:ae:bf:af:ee:e8"
IPAD_MAC = "0e:8d:41:37:42:d4"
HONR_MAC = "fc:ab:90:2e:f5:f9"
RMN5_MAC = "20:a6:0c:20:5f:b2"
OPPO_MAC = "9c:5f:5a:a4:03:2f"
IP13_MAC = "16:b7:62:99:8b:a2"

MAC_PHONE_MAP = {
    IP15_MAC: "IPH15",
    RDMI_MAC: "RMN10",
    IP11_MAC: "IPH11",
    IPAD_MAC: "IPAD",
    HONR_MAC: "HONOR",
    RMN5_MAC: "RMN5",
    IWCH_MAC: "Watch",
    IP06_MAC: "IPH6",
    OPPO_MAC: "OPPO",
    IP13_MAC: "IP13",
}

# timeit decorator
def timeit_decorator(method):
    def timed(*args, **kw):
        global log_filename
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        write_log(log_file=log_filename, message=f"{method.__name__} took: {te - ts} sec")
        return result

    return timed


def write_log(log_file, message):
    message = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}"
    with open(log_file, 'a') as f:
        print(message)
        f.write(message + '\n')

def output_drone_status(log_filename, record_on_idle=False):
    # when there is no RSSI, record only in 1Hz
    # use a timer to record the recording interval
    if "last_time" not in output_drone_status.__dict__.keys():
        output_drone_status.last_time = time.time()
    else:
        if record_on_idle:
            # record the first time
            if time.time() - output_drone_status.last_time < 1:
                # if the time interval is less than 1 second, return, no need to record
                return
            else:
                output_drone_status.last_time = time.time()
                # update the last time and continue to record
        else:
            output_drone_status.last_time = time.time()
            # update the last time and continue to record
            
    drone_log_str = f"record_on_idle: {record_on_idle}\n" if record_on_idle else ""
    with open("/shared/realtime/drone/euler", "r") as f:
        drone_log_str += "euler\n"
        drone_log_str += f.read()

    with open("/shared/realtime/drone/gpsPosition", "r") as f:
        drone_log_str += "gpsPosition:\n"
        drone_log_str += f.read()

    with open("/shared/realtime/drone/quaternion", "r") as f:
        drone_log_str += "quaternion:\n"
        drone_log_str += f.read()

    with open("/shared/realtime/drone/velocity", "r") as f:
        drone_log_str += "velocity:\n"
        drone_log_str += f.read()

    write_log(log_filename, drone_log_str)
    
@timeit_decorator
def direction_finding(measure_file_path, interpolated_beam_pattern_avg, layout, log_filename,
                      alg_list=["a_BcRxB", "a_ScRxB"], no_plot=True,
                      realtime=False, pos_elevation=True):
    mac = os.path.basename(measure_file_path).split(".")[0]
    
    write_log(log_filename, f"Reading measured RSSI from {measure_file_path}")
    # if it is real-time, we don't want to plot the figure
    no_plot = no_plot or realtime

    measured_rssi_list, measured_layout = read_measured_rssi_from_file(measure_file_path, layout)
    predicted_angles = []
    true_angles = []
    if layout.is_3d:
        alg_pred_list = {}
        
        for true_angle, measured_rssi in measured_rssi_list:
            print(f"True angle: {true_angle} for {mac}")
            
            
            
            result, measured_rssi_calibrated = calculate_similarity_matrix(measured_layout, measured_rssi,
                                                 interpolated_beam_pattern_avg, plot_fig=not no_plot,
                                                 algorithm_list=alg_list,
                                                 std_method="z-score-nonzero",
                                                 pos_elevation=pos_elevation)
            
            true_angles.append(true_angle)
            for alg in alg_list:
                if alg not in alg_pred_list:
                    alg_pred_list[alg] = []
                this_pred = result[alg]["pred"][2]
                alg_pred_list[alg].append(Location(this_pred[0], this_pred[1]))

        if None not in true_angles:
            for alg in alg_list:
                predicted_angles = alg_pred_list[alg]
                score = performance_judge(true_angles, predicted_angles)
                normalized_score = score / len(true_angles)
                write_log(log_filename, f"{alg} Score: {score}/{len(true_angles)} ({normalized_score:.2f})")
        else:
            write_log(log_filename, "True angles are not provided.")
            for alg in alg_list:
                write_log(log_filename, f"{alg} Predicted angles: {alg_pred_list[alg]}")

            if realtime:
                # write the predicted angles to a file
                with open(f"/shared/realtime/predicted/{mac}.angle", "w+") as f:
                    for alg in alg_list:
                        f.write(f"Pred:{alg_pred_list[alg][0]}")
                
                output_drone_status(log_filename)
                
                if "a_BcRxB" in alg_pred_list.keys():
                    return alg_pred_list["a_BcRxB"][0]
    else:
        for true_angle, measured_rssi in measured_rssi_list:
            similarity_matrix = calculate_similarity_matrix(measured_layout, measured_rssi,
                                                            interpolated_beam_pattern_avg,
                                                            algorithm_list=alg_list,
                                                            plot_fig=not no_plot,
                                                            pos_elevation=pos_elevation)

            predicted_angle = max(similarity_matrix, key=similarity_matrix.get)
            predicted_angle = Location(predicted_angle, 0)
            true_angles.append(true_angle)
            predicted_angles.append(predicted_angle)

        if None not in true_angles:
            score = performance_judge(true_angles, predicted_angles)
            normalized_score = score / len(true_angles)
            write_log(log_filename, f"Score: {score}/{len(true_angles)} ({normalized_score:.2f})")
            print(true_angles, predicted_angles)
        else:
            write_log(log_filename, "True angles are not provided.")
            write_log(log_filename, f"Predicted angles: {predicted_angles}")


def check_if_same_or_empty(file_path, log_filename):
    mac = os.path.basename(file_path).split(".")[0]
    check_same_result = False
    
    with open(file_path, 'r') as f:
        current_content = f.read()
    
    # if file is empty, return True
    if current_content.strip() == "":
        # file empty no need to process
        check_same_result = True
    else:
        # check if the function attribute exists
        if not hasattr(check_if_same_or_empty, "prev_content"):
            check_if_same_or_empty.prev_content = {}
            check_if_same_or_empty.prev_content[mac] = current_content
            check_same_result = False
        else:
            if mac not in check_if_same_or_empty.prev_content.keys():
                check_if_same_or_empty.prev_content[mac] = ""
                check_if_same_or_empty.prev_content[mac] = current_content
                check_same_result = False
            else:
                # Check if the file content is  the same as the previous content
                if current_content == check_if_same_or_empty.prev_content[mac]:
                    check_same_result = True
                else:
                    # Update function attribute to current content
                    check_if_same_or_empty.prev_content[mac] = current_content
                    check_same_result = False
    
    if check_same_result == False:
        write_log(log_filename, f"New content detected in {file_path}\n{current_content}")
    
    return check_same_result

def update_predicted_on_rc(target_mac_result):
    basename = "all_predicted.angle"
    filename = os.path.join(RC_SAVE_ROOT, basename)
    with open(filename, "w+") as o:
        for key, value in target_mac_result.items():
            if key in MAC_PHONE_MAP.keys():
                name = MAC_PHONE_MAP[key]
            else:
                name = key[:2]
            print(key, name, value)
            o.write(f"{name}: {value}\n")

def update_rssi_predicted_on_rc(target_mac_result):
    output_basename = "all_target.info"
    output_filename = os.path.join(RC_SAVE_ROOT, output_basename)
    
    info_basename = "all_antenna.status"
    info_filename = os.path.join(RC_SAVE_ROOT, info_basename)
    
    info = {}
    with open(info_filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            mac = line.split(": ")[0].strip()
            status = line.split(": ")[1].strip()
            if mac in MAC_PHONE_MAP.keys():
                name = MAC_PHONE_MAP[mac]
            else:
                name = mac[:2]
                if name in info.keys():
                    name = mac
            
            info[name] = {}
            info[name]["status"] = status
    
    for mac, value in target_mac_result.items():
        if mac in MAC_PHONE_MAP.keys():
            name = MAC_PHONE_MAP[mac]
        else:
            name = mac[:2]
        
        if name not in info.keys():
            info[name] = {}
        
        info[name]["angle"] = value
        
    with open(output_filename, "w+") as o:
        for name in info.keys():
            if "status" in info[name].keys() and "angle" in info[name].keys():
                print(name, info[name]["status"], info[name]["angle"])
                o.write(f"{info[name]['status']} {name}:{info[name]['angle']}\n")
            
def main(data_dir, realtime, calibration, no_plot, pos_elevation):
    """
    Main function to run signal processing and plotting.

    Parameters
    ----------
    data_dir : str
        The directory containing layout and signal files.
    realtime : bool
        Flag to enable real-time mode for input.
    calibrate : bool
        Flag to enable recalibration of the RSSI calibration.
    no_plot : bool
        Flag to disable plotting.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    global log_filename
    if realtime:
        log_filename = f'./data/realtime/real_time_{timestamp}.log'
    else:
        log_filename = f'./data/currect_batch.log'

    layout_path = os.path.join(data_dir, 'layout.yaml')
    sheet_path = os.path.join(data_dir, 'sheet.tsv')

    layout = load_layout(layout_path)

    if os.path.exists(os.path.join(data_dir, 'beam_pattern.pkl')):
        beam_pattern = BeamPattern(data_dir=data_dir)
    else:
        print("No beam pattern file found. Recalculating beam pattern.")
        dataset, bp_rssi_calibration, bp_layout = load_signals(sheet_path, layout)
        logger.info(f"bp_rssi_calibration: {bp_rssi_calibration}")
        beam_pattern = construct_beam_pattern(dataset, bp_layout, bp_rssi_calibration, calibration=calibration)
        beam_pattern.save(data_dir)

    interpolated_beam_pattern_avg = beam_pattern.interpolated_beam_pattern

    try:
        if realtime:
            logger.info("Entering real-time mode.")
            
            target_mac_result = {}
            while True:
                # find all *.tsv under RSSI_SAVE_ROOT and record file name as mac
                rssi_list = glob.glob(os.path.join(RSSI_SAVE_ROOT, "*.tsv"))
                target_mac_list = []
                for rssi_file in rssi_list:
                    mac = os.path.basename(rssi_file).split(".")[0]
                    target_mac_list.append(mac)
                
                for mac in target_mac_result.keys():
                    if mac not in target_mac_list:
                        del target_mac_result[mac]
                    
                for real_time_data_path in rssi_list:
                    mac = os.path.basename(real_time_data_path).split(".")[0]
                    try:
                        if check_if_same_or_empty(real_time_data_path, log_filename):
                            output_drone_status(log_filename, record_on_idle=True)
                            time.sleep(0.001)
                            continue

                        predicted_angle = direction_finding(real_time_data_path, interpolated_beam_pattern_avg, layout, log_filename,
                                        alg_list=["a_BcRxB"], no_plot=no_plot, realtime=realtime, 
                                        pos_elevation=pos_elevation)
                        
                        target_mac_result[mac] = predicted_angle
                        update_rssi_predicted_on_rc(target_mac_result)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        write_log(log_filename, f"Error in real-time processing: {e}")

        else:
            logger.info("Running batch processing.")
            measure_file_path = os.path.join(data_dir, 'test.tsv')
            direction_finding(measure_file_path, interpolated_beam_pattern_avg, layout, log_filename,
                            alg_list=["a_BcRxB"],
                            no_plot=no_plot, realtime=realtime,
                            pos_elevation=pos_elevation)

        if not no_plot:
            wait_for_user()

    except KeyboardInterrupt:
        write_log(log_filename, "Process interrupted by user.")
    finally:
        write_log(log_filename, "Shutting down.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run signal processing and plotting.")
    parser.add_argument('--log', default='INFO', help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    parser.add_argument('--data-dir', default='./data/case2', help="The directory containing layout and signal files")
    parser.add_argument('--realtime', action='store_true', help="Enable real-time mode for input")
    parser.add_argument('--calibration', action='store_true', help="Calibrate the RSSI")
    parser.add_argument('--no-plot', action='store_true', help="Disable plotting")
    parser.add_argument('--pos-elevation', action='store_true', help="Only consider the positive elevation angles")
    args = parser.parse_args()
    
    # set logger level
    logger.remove()
    logger.add(sys.stdout, level=args.log.upper())
    
    main(args.data_dir, args.realtime, args.calibration, args.no_plot, args.pos_elevation)
