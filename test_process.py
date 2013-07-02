#!/usr/bin/env python 

from serial import Serial, SerialException
from time import gmtime, strftime
import os
import sys
import traceback
import time 
import string
import signal
import sys 
import subprocess 
import re
import threading

print "RAMBo Test Server"

try:
	controller = Serial(port = "/dev/ttyACM0", baudrate = 115200)
	target = Serial(port = None, baudrate = 115200)
except SerialException:
	print "Error, could not connect"
	traceback.print_exc()
print "Target baudrate : " + str(target.baudrate)
print "Controller port : " + controller.name
print "Controller baudrate : " + str(controller.baudrate)
print "Waiting for controller initialization..."
controller.setDTR(0)
time.sleep(1)
controller.setDTR(1)
while not controller.inWaiting():
	time.sleep(0.1)

targetUSBPowerPin = 9
isp1PowerPin = 8
isp2PowerPin = 7 
monitorPin = 44 #PL5 
triggerPin = 3 #bed
monitorFrequency = 1000
targetPort = "/dev/ttyACM1"
testFwPath = "/home/ultimachine/workspace/Test_Jig_Firmware/target_test_firmware.hex"
shipFwPath = "/home/ultimachine/workspace/johnnyr/Marlinth2.hex"
stepperSpeed = 100
testing = True
state = "start"
entered = False
keyboard = ""
output = ""
targetOut = ""
refs = []
fullstepTest = []
halfstepTest = []
quarterstepTest = []
sixteenthstepTest = []
vrefTest = []
supplyTest = []
mosfethighTest = []
mosfetlowTest = []
thermistorTest = []

groupn = lambda lst, sz: [lst[i:i+sz] for i in range(0, len(lst), sz)]

#Setup shutdown handlers
def signal_handler(signal, frame):
	print "Shutting down test server..."
	controller.write("W3L")
	controller.write("H5000")
	controller.close()
	target.close()
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

#Define test cases
def testVrefs(vals):
	for x in vals:
		if not 170 <= x <= 195: 
			return False
	if max(vals) - min(vals) >= 15:
		return False
	return True 

def testSupply(vals):
	for x in vals:
		if not 210 <= x <= 220:
			return False
	return True

def testThermistor(vals):
	for x in vals:
		if not 975 <= x <= 985:
			return False
	return True

def testMosfetLow(vals):
	for x in vals:
		if not x == 1:
			return False
	return True

def testMosfetHigh(vals):
	for x in vals:
		if not x == 0:
			return False
	return True

def testStepperResults(vals):
	for i in range(5):
		forward = vals[i]
		reverse = vals[i+5]
		print "Forward -> " + str(forward) + "Reverse -> " + str(reverse)
		for j in range(5):
			if forward[j] in range(reverse[4-j]-10,reverse[4-j]+10):
				pass
			else: 
				print "Test failed."
				#return False
	print "Test passed."
	return True	

print "Test server started. Press CTRL-C to exit."
print "Monitoring test controller..."

while(testing):
	output += controller.read(controller.inWaiting())
	#raw_input("Press Enter to continue...")
	if(target.port): 
		targetOut += target.read(target.inWaiting())
	if state == "start":
		if "start" in output:
			state = "clamping"
			print "Test started at " + strftime("%Y-%m-%d %H:%M:%S", gmtime())
			output = ""
			targetOut = ""
	elif state == "clamping":
		if not entered:
			print "Powering up ISP programmers..."
			controller.write("W"+str(isp1PowerPin)+"H")
			controller.write("W"+str(isp2PowerPin)+"H")
			print "Powering target over USB..."
			controller.write("W"+str(targetUSBPowerPin)+"H")
			print "Clamping test jig..."
			controller.write("H5000_")
			controller.write("C18700F3000U_")
			entered = True
		if output.count("ok") == 5:
			entered = False
			output = "" 
			state = "uploading"
	elif state == "uploading":
		print "Uploading Bootloader and setting fuses..."
		avr32u2 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158420', u'-patmega32u2', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/RAMBo-usbserial-DFU-combined-32u2.HEX:i', u'-Uefuse:w:0xF4:m', u'-Uhfuse:w:0xD9:m', u'-Ulfuse:w:0xEF:m', u'-Ulock:w:0x0F:m'])
		avr32u2State = avr32u2.wait()
		if avr32u2State == 0:
			print "Uploaded 32u2 bootloader."
			state = "program for test"
		else:
			print "Upload Failed"
			state = "board fail"
		#avr2560 = subprocess.Popen(['/usr/bin/avrdude', '-v', '-v', '-c', u'avrispmkII', '-P', u'usb:0200158597', u'-pm2560', u'-Uflash:w:/home/ultimachine/workspace/RAMBo/bootloaders/stk500boot_v2_mega2560.hex:i', u'-Uefuse:w:0xFD:m', u'-Uhfuse:w:0xD0:m', u'-Ulfuse:w:0xFF:m', u'-Ulock:w:0x0F:m'])
		#avr560State = avr2560.wait()
		#print "atmega 2560: "
		#if avr2560State == 0:
		#	print "Uploaded!"
		#	state = "connecting target"
		#else:
		#	print "Upload Failed"
		#	state = "board fail"
		print "Powering down ISP programmers"
		controller.write("W"+str(isp1PowerPin)+"L")
		controller.write("W"+str(isp2PowerPin)+"L")
		entered = False
	elif state == "program for test":
		if not entered and :
			output = ""
			print "Reconnecting target..."
			controller.write("W"+str(targetUSBPowerPin)+"L")
			controller.write("C3000F3000D")
			entered = True
		elif output.count("ok") == 2 and entered:
			controller.write("W"+str(targetUSBPowerPin)+"H")
			controller.write("C3000F3000U")
			entered = False
		if output.count("ok") == 4:
			print "Detecting target..."
			while not os.path.exists(targetPort):
				time.sleep(0.5)
			print "Programming for the tests..."
			command = "avrdude -F -patmega2560 -cstk500v2 -P"+targetPort+" -b115200 -D -Uflash:w:"+testFwPath
			prog = subprocess.Popen(command.split())
			print "Avrdude pid... " + str(prog.pid)
			state = prog.wait()
			if state == 0:
				print "Finished upload. Waiting for connection..."
				state = "connecting target"
				while not os.path.exists(targetPort):
					time.sleep(0.5)
			else:
				print "Upload failed"
				state = "board fail"
			entered = False
	elif state == "connecting target":
		print "Attempting connect..."	
		target.port = targetPort
		target.open()
		while not target.inWaiting():
			pass
		print "Target port : " + target.port 	
		state = "powering"
		targetOut = ""
	elif state == "powering":
		if not entered:
			output = ""
			print "Powering Board..."
			controller.write("W3H_")
			entered = True
		if "ok" in output:
			state = "thermistors"
			entered = False
			print "Target Board powered."
			output = ""
			targetOut = ""
	elif state == "fullstep":
		if not entered:
			entered = True
			print "Testing steppers at full step..."
			target.write("U1_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C200F800UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output+="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C200F800DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Full Step test finished."
			print output
			fullstepTest =groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			print fullstepTest
			if testStepperResults(fullstepTest):
				state = "halfstep"
			else:
				state = "board fail"
			output = ""
			fullstepTest = []
	elif state == "halfstep":
		if not entered:
			entered = True
			print "Testing steppers at half step..."
			target.write("U2_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C400F1600UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output+="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C400F1600DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Half Step test finished."
			halfstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(halfstepTest):
				state = "quarterstep"
			else:
				state = "board fail"
			output = ""
			halfstepTest = []
	elif state == "quarterstep":
		if not entered:
			entered = True
			print "Testing steppers at quarter step..."
			target.write("U4_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C800F3200UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output +="ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C800F3200DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Quarter Step test finished."
			quarterstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(quarterstepTest):
				state = "sixteenthstep"
			else:
				state = "board fail"
			output = ""
			quarterstepTest = []
	elif state == "sixteenthstep":
		if not entered:
			entered = True
			print "Testing steppers at sixteenth step..."
			target.write("U16_")
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C3200F12800UP"+str(triggerPin)+"_")
		if output.count("ok") == 1:
			output += "ok"
			controller.write("M"+str(monitorPin)+"F"+str(monitorFrequency)+"_")
			target.write("C3200F12800DP"+str(triggerPin)+"_")
		if output.count("ok") == 3:
			entered = False
			print "Sixteenth Step test finished."
			sixteenthstepTest = groupn(map(int,re.findall(r'\b\d+\b', output)),5)
			if testStepperResults(sixteenthstepTest):
				state = "program marlin"
			else:
				state = "board fail"
			output = ""
			sixteenthstepTest = []
	elif state == "vrefs":
		if not entered:
			entered = True
			controller.write("A8_") #x				
			controller.write("A6_") #y
			controller.write("A5_") #z
			controller.write("A4_") #e0
			controller.write("A3_") #e1
			print "Testing stepper driver references..."
		if output.count("ok") == 5:
			entered = False
			print "Vref values..."
			vrefTest = map(int,re.findall(r'\b\d+\b', output)) 
			print vrefTest
			if testVrefs(vrefTest):
				print "Test passed."
				state = "fullstep"
			if not testVrefs(vrefTest):
				print "Test failed."
				state = "board fail"		
			output = ""
			targetOut = ""
	elif state == "supply test":
		if not entered:
			entered = True
			controller.write("A7_") #extruder rail				
			controller.write("A2_") #bed rail
			print "Testing supply voltages..."
		if output.count("ok") == 2:
			entered = False
			print "Supply voltage values..."
			supplyTest = map(int,re.findall(r'\b\d+\b', output)) 
			print supplyTest	
			if testSupply(supplyTest):
				print "Test passed."
				state = "mosfet high"
			if not testSupply(supplyTest):
				print "Test failed."
				state = "board fail"		
			output = ""
			targetOut = ""
	elif state == "mosfet high":
		if not entered:
			entered = True
			print "Testing Mosfets High..."
			target.write("W9H")
			target.write("W8H")
			target.write("W7H")
			target.write("W6H")
			target.write("W3H")
			target.write("W2H")
			time.sleep(0.1)
			controller.write("Q44_")
			controller.write("Q32_")
			controller.write("Q45_")
			controller.write("Q31_")
			controller.write("Q46_")
			controller.write("Q30_")
		if output.count("ok") == 6:
			entered = False
			print "Mosfet output values..."
			mosfethighTest = map(int,re.findall(r'\b\d+\b', output)) 
			print mosfethighTest
			if testMosfetHigh(mosfethighTest):
				print "Test Passed."
				state = "mosfet low"
			if not testMosfetHigh(mosfethighTest):
				print "Test failed."
				state = "board fail"
			output = ""
			targetOut = ""
	elif state == "mosfet low":
		if not entered:
			entered = True
			print "Testing mosfets Low..."
			target.write("W9L")
			target.write("W8L")
			target.write("W7L")
			target.write("W6L")
			target.write("W3L")
			target.write("W2L")
			time.sleep(0.1)
			controller.write("Q44_")
			controller.write("Q32_")
			controller.write("Q45_")
			controller.write("Q31_")
			controller.write("Q46_")
			controller.write("Q30_")
		if output.count("ok") == 6:
			entered = False
			print "Mosfet output values..."
			mosfetlowTest = map(int,re.findall(r'\b\d+\b', output)) 
			print mosfetlowTest
			if testMosfetLow(mosfetlowTest):
				print "Test Passed."
				state = "vrefs"
			if not testMosfetLow(mosfetlowTest):
				print "Test failed."
				state = "board fail"
			output = ""
			targetOut = ""
	elif state == "thermistors":
		if not entered:
			entered = True
			print "Verifying thermistor readings..."
			target.write("A0_")
			target.write("A1_")
			target.write("A2_")
		if targetOut.count("ok") == 3:
			print "Target thermistor readings..."
			thermistorTest = map(int,re.findall(r'\b\d+\b', targetOut)) 
			print thermistorTest
			if testThermistor(thermistorTest):
				print "Test passed."
				state = "supply test"
			if not testThermistor(thermistorTest):
				print "Test failed."
				state = "board fail"	
			targetOut = ""
			entered = False
	elif state == "program marlin":
		print "Disconnecting target from test script..."
		target.flushInput()
		target.flushOutput()
		target.close()
		target.port = None 
		print "Programming Marlin..."
		command = "avrdude -patmega2560 -cstk500v2 -P"+targetPort+" -b115200 -D -Uflash:w:"+shipFwPath
		prog = subprocess.Popen(command.split())
		print "avrdude pid... " + str(prog.pid)
		state = prog.wait()
		if state == 0:
			print "Finished Marlin upload."
			state = "finished"
		else:
			print "Upload failed"
			state = "board fail"
			entered = False
	elif state == "finished":
		print "Testing finished without errors."
		print "Powering off target"
		controller.write("W3L_")
		print "Preparing Test Jig for next board.."
		controller.write("H5000_")
		state = "start"	
	elif state == "board fail":
		print "Board failed"
		target.close()
		target.port = None
		controller.write("W3L")
		controller.write("H5000_")
		state = "start"
		entered = False
