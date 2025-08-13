# Client for Primitive Tractography

# Imports
import zmq
import time
import datetime
import threading
import uuid
import sys
import pickle
from pathlib import Path
import json
import subprocess

# Add RayStation scripts folder to path
rs_scripts_path = r"V:\Common\Staff Personal Folders\DanielH\RayStation_Scripts\Tractography".replace("\\","/")
sys.path.append(rs_scripts_path)

# Import necessary functions
from Subscripts.Visualization_Utils import show_tracts, show_wmpl 
from Subscripts.Preliminaries import get_base_dir, rs_get_info
from Subscripts.RS_Utils import export_rs_stuff, check_rois, check_pl_map, check_ct_planning
from DTI_CTV_Maker import dti_ctv_maker

## Define patient folder path
print("Defining base folder...")
base_dir = get_base_dir()

# Check if we can import from connect (RayStation) if we can't then we aren't calling from RayStation
try:
    # Import RayStation
    from connect import *
    # Set flag to true
    rs_flag = True
    # Environment setup parameters
    patient = get_current("Patient")
    case = get_current("Case")
except:
    # Set flag to false
    rs_flag = False
    pass # just carry forward

# Check if ROIs already saved
rois_flag = check_rois(base_dir)
if not rois_flag:
    if rs_flag:

        # Export RTStruct with ROIs, CT scans and MRIs with FA
        export_rs_stuff(patient, case, base_dir)

    elif not rs_flag:
        raise ValueError(f"No RayStation files found in {Path(base_dir / 'RayStation')}")

# Create context
context = zmq.Context()

# Define client ID
if rs_flag:
    client_id = str(patient.PatientID) + "-" + str(uuid.uuid4())[:8] # unique short ID
else:
    client_id = str(uuid.uuid4())[:8] # unique short ID

# Define ports
server_ip = "10.244.196.191"
main_port = "5560"
heartbeat_port = "5561"
stream_port = "5562"
data_port = "5563"

#  Socket for work
print(f"\n[{datetime.datetime.now()}] Connecting to PrimitiveTractography server...")
main_socket = context.socket(zmq.DEALER)
main_socket.linger = 0 # doesn't wait for anything when closing
main_socket.connect(f"tcp://{server_ip}:{main_port}")

# Socket for receiving terminal outputs
stream_socket = context.socket(zmq.PULL)
stream_socket.connect(f"tcp://{server_ip}:{stream_port}")

# Socket for receiving data
data_socket = context.socket(zmq.DEALER)
data_socket.connect(f"tcp://{server_ip}:{data_port}")

# Define heartbeat class
class HeartbeatManager:
    def __init__(self, context, server_ip, heartbeat_port, client_id):
        # Initialize by defining stuff
        self.context = context
        self.server_ip = server_ip
        self.heartbeat_port = heartbeat_port
        self.client_id = client_id
        self.poller = zmq.Poller()
        self.running = True
        self.connection_disconnects = 0

        # Create the socket
        self._create_socket()

    def _create_socket(self):
        # Create socket
        self.socket = self.context.socket(zmq.REQ)
        self.socket.linger = 0 # doesn't wait for anything when closing
        self.socket.connect(f"tcp://{self.server_ip}:{self.heartbeat_port}")
        self.poller.register(self.socket, zmq.POLLIN)

    def _recreate_socket(self):
        # Recreate socket (called when there's an error. REQ can't send without receiving first...)
        self.poller.unregister(self.socket) # Unregister from poller
        self.socket.close()
        self._create_socket()

    def start(self):
        # Start thread as daemon (background worker)
        self.thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.thread.start()

    def stop(self, called_from_thread=False):
        # Close the socket
        self.running = False
        if not called_from_thread:
            self.thread.join()
        self.socket.close()

    def _heartbeat_loop(self):
        # Send (and check for) heartbeats while running
        while self.running:
            try:
                # Send string
                self.socket.send_string(f"PING:{self.client_id}")
                if dict(self.poller.poll(timeout=15000)): # Check for heartbeat for 15 seconds
                    reply = self.socket.recv_string() # Receive string
                    if reply == "PONG":
                        # print(f"[{datetime.datetime.now()}] [Heartbeat] Received from server")
                        self.connection_disconnects = 0 # Reset disconnects to 0
                        time.sleep(10) # Wait 10 seconds between heartbeats
                    else:
                        print(f"[{datetime.datetime.now()}] [Heartbeat] Received from unexpected reply from server: {reply}")
                else:
                    # No reply. Recreate socket
                    print(f"[{datetime.datetime.now()}] [Heartbeat] No response! Reconnecting...")
                    self.connection_disconnects += 1 # add 1 to consecutive missed heartbeats
                    if self.connection_disconnects >= 3:
                        # Stop program if 3 missed heartbeats in a row
                        print(f"\n[{datetime.datetime.now()}] Connection with server unavailable. Stopping the program.")
                        # Close sockets and terminate context
                        global main_socket_active 
                        global stream_socket_active
                        global data_socket_active
                        main_socket_active = False # exit main socket loop
                        stream_socket_active = False # exit stream socket loop
                        data_socket_active = False # exit data socket loop
                        # time.sleep(0.1) # wait a bit

                        return # exit daemon function
                        # time.sleep(3) # wait for main socket to be done trying to receive 
                        # Let main socket be the one to close sockets

                        # main_socket.close()
                        # heartbeat.stop(called_from_thread=True) # Calls stop method in HeartbeatManager class
                        # context.term()
                        # sys.exit()
                    self._recreate_socket()

            except zmq.ZMQError as e:
                # Unexpected error. Recreate socket
                print(f"[{datetime.now()}] [Heartbeat] ZMQ error: {e}")
                self._recreate_socket()
                time.sleep(9) # Wait before retrying

# Initialize class and start
heartbeat = HeartbeatManager(context, server_ip, heartbeat_port, client_id)
heartbeat.start()

# Define function to receive stream socket outputs
def receive_stream():
    global stream_socket_active # access stream_socket_active flag
    global rs_flag
    while stream_socket_active:
        if dict(stream_poller.poll(timeout=3000)): # check for 3 seconds
            # Receive terminal outputs until script is done
            msg = stream_socket.recv_json()
            if msg["type"] == "stdout":
                print(f"[{datetime.datetime.now()}] REMOTE:", msg["data"])
            elif msg["type"] == "done":
                print(f"[{datetime.datetime.now()}] Script finished with code {msg['returncode']}")
                time.sleep(0.1) # Wait for main thread to say completed succesfully or with error
                if not rs_flag:
                    print(f"\n[{datetime.datetime.now()}] Stopping the program.")
                # Close sockets and terminate context
                global main_socket_active 
                global data_socket_active
                main_socket_active = False # exit main socket loop
                stream_socket_active = False # exit stream socket loop
                data_socket_active = False # exit data socket loop
                # time.sleep(5) # wait for main socket to be done trying to receive 
                # Let main socket be the one to close sockets

                return # end function

                # main_socket.close()
                # heartbeat.stop() # Calls stop method in HeartbeatManager class
                # context.term()
                # sys.exit()
                # break
        time.sleep(0.1) # Wait a bit to remove weird errors when shutting down

# Create poller for main socket
poller = zmq.Poller()
poller.register(main_socket, zmq.POLLIN)

# Create poller for stream socket
stream_poller = zmq.Poller()
stream_poller.register(stream_socket, zmq.POLLIN)

# Create poller for data socket
data_poller = zmq.Poller()
data_poller.register(data_socket, zmq.POLLIN)

# Define function to receive data and plot Fury
data_socket_active = True
def data_dealer():
    global data_socket_active
    global rs_flag
    global base_dir
    # First send base directory
    base_dir_json = json.dumps(str(base_dir)).encode('utf-8')
    data_socket.send_multipart([b'', base_dir_json])
    
    while data_socket_active:
        if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
            _, ds_msg = data_socket.recv_multipart()  # receive message
            ds_msg = ds_msg.decode('utf-8') # decode message

            if ds_msg == "Show Fury":
                # Show tracts
                show_tracts(base_dir)
            
            # Tell server Fury window closed
            data_socket.send_multipart([b'', b"Data received. Fury window closed"])

            # Wait for data from server to show WMPL map
            while data_socket_active:
                if dict(data_poller.poll(timeout=3000)): # check for 3 seconds
                    _, ds_msg = data_socket.recv_multipart()  # receive message
                    ds_msg = ds_msg.decode('utf-8') # decode message

                    if ds_msg == "Show Fury":
                        # Show WMPL map
                        show_wmpl(base_dir)

                    # Tell server Fury window closed
                    data_socket.send_multipart([b'', b"Data received. Fury window closed"])
                    
                    return # Function is finished
                
        time.sleep(1) # Wait 1 second to avoid error messages when exiting program

try:
    print(f"\n[{datetime.datetime.now()}] Sending request to server...")
    main_socket.send_multipart([b'', b"READY"])
    main_socket_active = True
    while main_socket_active:
        if dict(poller.poll(timeout=3000)): # Check for reply for 3 seconds
            #  Get the reply.
            _, message = main_socket.recv_multipart()
            message = message.decode()
            if message == "READY":
                print(f"\n[{datetime.datetime.now()}] Server available. Starting tractography...")
                main_socket.send_multipart([b'', b"RUN"])
                stream_socket_active = True
                threading.Thread(target=receive_stream, daemon=True).start() # start to receive from stream socket
                threading.Thread(target=data_dealer, daemon=True).start() # start to send/receive data
                while main_socket_active:
                    if dict(poller.poll(timeout=1000)): # Check for reply for 1 second
                        _, message = main_socket.recv_multipart()
                        message = message.decode()
                        if message == "FINISHED":
                            time.sleep(0.1) # Wait for "script ended with code 0"
                            print(f"[{datetime.datetime.now()}] Tractography and white matter path length map succesfully completed!")
                            break
                        elif message == "ERROR":
                            print(f"[{datetime.datetime.now()}] [ERROR] Error during tractography.")
                            break
                        else:
                            print(f"[{datetime.datetime.now()}] Unexpected returned message while performing tractography: {message}.")
                            break
            else:
                print(f"[{datetime.datetime.now()}] Unexpected returned message prior to commencing tractography: {message}")
                break
except Exception as e:
        print(f"[{datetime.datetime.now()}] Error: {e}")
finally:
    # Close sockets and terminate context
    time.sleep(3) # Wait a bit for threads to stop polling

    main_socket.close()
    stream_socket.close()
    data_socket.close()
    heartbeat.stop() # Calls stop method in HeartbeatManager class
    context.term()

if rs_flag:

    # Check if we already have a CT Planning examination and rename CT scan to CT Planning if not
    case = check_ct_planning(case)

    # Check if we have a PL map
    pl_map = check_pl_map(case)

    if not pl_map:

        print(f"[{datetime.datetime.now()}] Importing WMPL as examination...")

        # If running from RayStation, import WMPL
        wmpl_dir_dcm = base_dir / "WMPL/DICOM" # Path to WMPL DICOM

        # Extract info from files with pydicom
        files, _ = rs_get_info(wmpl_dir_dcm)
        # Load in MR data
        Sorted_MR_Files = sorted(files["MR_Files"], key=lambda file: float(file.ImagePositionPatient[2])) # sort files by z-axis. increasing towards the head
        # anatomical orientation type (0010,2210) absent so z-axis is increasing towards the head of the patient

        patient_id = str(Sorted_MR_Files[0].PatientID)
        study_instance_uid = str(Sorted_MR_Files[0].StudyInstanceUID)
        series_instance_uid = str(Sorted_MR_Files[0].SeriesInstanceUID)

        # Save before we import (required)
        patient.Save()

        # Import WMPL
        warnings = patient.ImportDataFromPath(
            Path = str(wmpl_dir_dcm),
            CaseName = str(case.CaseName),
            SeriesOrInstances = [{
                "PatientID":patient_id, "StudyInstanceUID":study_instance_uid, "SeriesInstanceUID":series_instance_uid
                }]
        )

        if warnings:
            print(f"[{datetime.datetime.now()}] Import warnings: ", warnings)
        else:
            print(f"[{datetime.datetime.now()}] Import successful.")

        # Rename new examination to PL Map
        for exam in case.Examinations:
            # Check if exam is same as the one we just made
            data = exam.GetAcquisitionDataFromDicom()
            if str(data['StudyModule']['StudyInstanceUID']) == study_instance_uid and str(data['SeriesModule']['SeriesInstanceUID']) == series_instance_uid:
                # Rename exam name and exit for loop
                print(f"Renamed '{exam.Name} to 'PL Map'")
                exam.Name = "PL Map"
                # Save change
                patient.Save()
                break
    
    # Set PL Map as the primary examination
    examination = case.Examinations["PL Map"]
    examination.SetPrimary()

    # Set CT Planning as the secondary examination
    examination = case.Examinations["CT Planning"]
    examination.SetSecondary()

    # Save patient
    patient.Save()

    # Prepare variables for DTI CTV Maker
    # Environment setup parameters
    db = get_current("PatientDB")
    machine_db = get_current("MachineDB")
    patient = get_current("Patient")
    case = get_current("Case")
    examination = get_current("Examination")
    structure_set = case.PatientModel.StructureSets[examination.Name]
    planning_examination = case.Examinations['CT Planning']
    plmap_examination = case.Examinations['PL Map']

    # Run DTI CTV Maker
    print("Running DTI CTV maker...")
    dti_ctv_maker(db, machine_db, patient, case, examination, structure_set, planning_examination, plmap_examination)
    print("DTI CTV maker completed!")

print(f"[{datetime.datetime.now()}] Stopping the program.")