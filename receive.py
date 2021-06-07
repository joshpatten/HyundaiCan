#!/usr/bin/python3
import os
import can # pip install can
import cantools # pip install cantools
import json
import pulsectl # pip install pulsectl
import sys
from time import sleep
from datetime import datetime, timedelta
from queue import Queue
from threading import Thread
import subprocess
import configparser


class G:
	config = None
	db = None
	candev = None
	max_vol = None
	output_device = None # PulseAudio Index (RUN receive.py listaudio to show devices)
	input_device = None # PulseAudio Index
	veh_off_wait = None
	can_bitrate = None
	pulse = pulsectl.Pulse('can-audio')
	canint = None
	q = Queue()

# Consts
VEH_POWER_OFF = 0
VEH_POWER_ON = 2
MUTE_ON = 1
MUTE_OFF = 0
NO_OP = "NoOp"
HU_VOLUME_STATUS = "HU_VolumeStatus"
HU_VEHICLE_POWER = "HU_VehiclePwr"
HU_MUTE_STATUS = "HU_MuteStatus"
INPUT = 'input'
OUTPUT = 'output'

def get_pulse_info():
	return (
		G.pulse.sink_list(),
		G.pulse.source_list(),
		G.pulse.server_info().default_sink_name
	)

def volume_level(level: int, max_level: int) -> float:
	return level/max_level

def set_vol(inttype = OUTPUT, index = 0, level = 0.0):
	try:
		if inttype == OUTPUT:
			sink = G.pulse.sink_list()[index]
		elif inttype == INPUT:
			sink = G.pulse.source_list()[index]
		G.pulse.volume_set_all_chans(sink, level)
	except Exception as e:
		print(f"Couldn't set volume for {inttype} index {index}: {e}")
	return
		
def set_default_sink(index = 0):
	try:
		sink = G.pulse.sink_list()[index]
		G.pulse.default_set(sink)
	except Exception as e:
		print(f"Couldn't set default sink: {e}")
	return

def set_default_source(index = 0):
	try:
		psource = G.pulse.source_list()[index]
		G.pulse.default_set(psource)
	except Exception as e:
		print(f"Couldn't set default source: {e}")
	return

def can_init(device: str) -> bool:
	os.system(f'sudo ifconfig {device} down')
	os.system(f'sudo ip link set {device} type can bitrate {G.can_bitrate}')
	os.system(f'sudo ifconfig {device} up')
	try:
		G.canint = can.interface.Bus(channel = device, bustype = 'socketcan_ctypes')
		return True
	except Exception as e:
		print(f"Error initializing device {device}: {e}")
		return False

def sys_shutdown():
	os.system("sudo systemctl poweroff")
	sys.exit()

def action_thread():
	volume = 0
	mute = 0
	vpower = 9
	vtimer = datetime.now()
	while True:
		data = G.q.get()
		if data is None:
			sleep(.05)
		else:
			if NO_OP in data:
				print("No operation received.")
			if HU_VEHICLE_POWER in data:
				if int(data[HU_VEHICLE_POWER]) == VEH_POWER_OFF and int(data[HU_VEHICLE_POWER]) != vpower:
					print(f"Vehicle power off detected. Waiting for {G.veh_off_wait} seconds to see if vehicle is started up again, otherwise powering off")
					vpower = VEH_POWER_OFF
					vtimer = datetime.now()
				elif int(data[HU_VEHICLE_POWER]) != VEH_POWER_OFF and vpower == VEH_POWER_OFF:
					print("Vehicle power off cancelled")
					vpower = int(data[HU_VEHICLE_POWER])
				else:
					vpower = int(data[HU_VEHICLE_POWER])
			if vpower == VEH_POWER_OFF:
				if (datetime.now() - timedelta(seconds=G.veh_off_wait) > vtimer):
					print(f"Vehicle has been powered off for more than {G.veh_off_wait} seconds, shutting down...")
					sys_shutdown()
			if HU_VOLUME_STATUS in data:
				if int(data[HU_VOLUME_STATUS]) != volume:
					print(f"Volume changed from {volume} to {data[HU_VOLUME_STATUS]}")
					set_vol(
						index=G.output_device,
						level=volume_level(
							int(
								data[HU_VOLUME_STATUS]
							),
							G.max_vol
						)
					)
					volume = data[HU_VOLUME_STATUS]
			if HU_MUTE_STATUS in data:
				if int(data[HU_MUTE_STATUS]) != mute:
					print(f"Mute changed from {mute} to {data[HU_MUTE_STATUS]}")
					# Set to previous volume level
					if int(data[HU_MUTE_STATUS]) == MUTE_OFF:
						set_vol(
							index=G.output_device,
							level=volume_level(
								volume,
								G.max_vol
							)
						)
					else:
						set_vol(
							index=G.output_device,
							level=0.0
						)
					mute = int(data[HU_MUTE_STATUS])

def listen_loop(test):
	#msg = can.Message(arbitration_id=0x123, data=[0, 1, 2, 3, 4, 5, 6, 7], extended_id=False)
	#msg = can.Message(arbitration_id=0x2015, data=[2, 1, 17, 0, 0, 0, 0, 0], extended_id=False)
	#G.canint.send(msg)
	# Default starting values
	
	if test:
		G.q.put({NO_OP: 0})
		sleep(5)
		G.q.put({HU_VEHICLE_POWER: 0})
		sleep(5)
		G.q.put({HU_VOLUME_STATUS: 20})
		sleep(5)
		G.q.put({HU_VOLUME_STATUS: 30})
		sleep(5)
		G.q.put({HU_MUTE_STATUS: 1})
		sleep(5)
		G.q.put({HU_MUTE_STATUS: 0})
		sleep(5)
		G.q.put({HU_VEHICLE_POWER: 2})
		sleep(5)
		return
		
	
	while True:
		msg = G.canint.recv(10.0)
		try:
			data = G.db.decode_message(msg.arbitration_id, msg.data)
			G.q.put(data)
		except (KeyError, AttributeError):
			pass
		if msg is None:
			G.q.put({NO_OP: 0})
	
def main(test=False):
	G.db = cantools.database.load_file(G.config.get('General', 'can_file'))
	G.candev = G.config.get('General', 'candev')
	G.max_vol = int(G.config.get('General', 'max_vol'))
	G.output_device = int(G.config.get('General', 'output_device')) # PulseAudio Index (RUN receive.py listaudio to show devices)
	G.input_device = int(G.config.get('General', 'input_device')) # PulseAudio Index
	G.veh_off_wait = int(G.config.get('General', 'veh_off_wait'))
	G.can_bitrate = int(G.config.get('General', 'can_bitrate'))
	try:
		os.system('killall pareceive')
		set_default_sink(index=G.output_device)
		set_default_source(index=G.input_device)
		devname = str(source[G.input_device].name)
		proc = subprocess.Popen(["pareceive"])
		success = can_init(G.candev)
		if not success:
			sys.exit(1)
		d = Thread(target=action_thread)
		d.daemon = True
		d.start()
		listen_loop(test)
		proc.kill()
	except KeyboardInterrupt:
		print("Exiting...")
		proc.kill()
		os.system('sudo ifconfig can0 down')

G.config = configparser.ConfigParser()

sink, source, pulse = get_pulse_info()
if len(sys.argv) < 2:
	print("Error: no argument specified.")
	print("Valid usage:")
	print("	receive.py listaudio")
	print("	receive.py {INI_FILE}")
	print("	receive.py {INI_FILE} test")
	sys.exit(1)
else:
	if sys.argv[1] == 'listaudio':
		print("==========OUTPUTS==========")
		for row in sink:
			print(row)
			print("------------")
		print("===========================")
		print("==========INPUTS===========")
		for row in source:
			print(row)
			print("------------")
		print("===========================")
		print("======DEFAULT OUTPUT=======")
		print(pulse)
		print("===========================")
		sys.exit(0)
	else:
		inifile = sys.argv[1]
		G.config.read(inifile)
		try:
			testval = sys.argv[2]
			if testval == 'test':
				testval = True
			else:
				testval = False
		except IndexError:
			testval = False
sys.exit(main(test=testval))
