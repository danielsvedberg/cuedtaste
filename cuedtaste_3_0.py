"""
Created on Mon Sep  9 14:15:36 2019

@author: Daniel Svedberg (dsvedberg@brandeis.edu)
"""
import time
import multiprocessing as mp
import RPi.GPIO as GPIO
import os
import datetime
# import random
import configparser
import json
import csv
import socket


########################################################################################################################
### SECTION 1: CLASSES ###

# NosePoke is a class that controls the physical nose poke device in the rig. Input variable light = GPIO pin for
# controlling LED in the nosepoke (1 = on, 0 = off). Input variable beam = GPIO pin receiving input from IR
# beam-break sensor inside nose poke device (1 = uncrossed, 0 = crossed)
class NosePoke:
    def __init__(self, light, beam):
        self.exit = None
        self.light = light
        self.beam = beam
        self.endtime = time.time() + 1200  # endtime is a class-wide condition to help the program exit when the task
        # is over. Usually this variable is changed when a behavioral task program is initiated
        GPIO.setup(self.light, GPIO.OUT)
        GPIO.setup(self.beam, GPIO.IN) 

    def shutdown(self):
        print("blink shutdown")
        self.exit.set()

    def flash_on(self):  # turn the light on
        GPIO.output(self.light, 1)

    def flash_off(self):  # turn the light off
        GPIO.output(self.light, 0)

    

    def flash(self, hz, run):  # bink on and of at frequency hz (LED has physical limit of 3.9)
        print("flashing "+str(self.light)+" start")
        while time.time() < self.endtime:
            if run.value == 1:
                GPIO.output(self.light, 1)
            if run.value == 1:
                time.sleep(2 / hz)            # try to consolidate 
                GPIO.output(self.light, 0)    # test
            if run.value == 1:
                time.sleep(2 / hz)
            if run.value == 0:
                GPIO.output(self.light, 0)
            if run.value == 2:
                GPIO.output(self.light, 1)
        print("flashing "+str(self.light)+" start")

    def is_crossed(self):  # report if beam is crossed
        if GPIO.input(self.beam) == 0:
            return True
        else:
            return False

    def keep_out(self, wait):  # report when the animal has stayed out of the nosepoke for duration of [wait] seconds
        print("keep out start")
        start = time.time()
        while True and time.time() < self.endtime:
            if self.is_crossed():
                start = time.time()
            elif time.time() - start > wait:
                break
        print("keep out end")

    def kill(self):  # kind of useless method
        GPIO.output(self.light, 0)


def send_cue(val):
    UDP_IP = "129.64.50.48"
    #when on phone
    #UDP_IP = "172.20.10.8"
    UDP_PORT = 5005

    MESSAGE = val.to_bytes(2, 'big')
    print("val: ", val)
    print("UDP target IP:", UDP_IP)
    print("UDP target port:", UDP_PORT)
    print("message:", MESSAGE)

    sock = socket.socket(socket.AF_INET, #internet
                        socket.SOCK_DGRAM) # UDP
    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))


# class TasteLine controls an individual taste-valve and its associated functions: clearouts,
# calibrations, and deliveries. Use TasteLine by declaring a TasteLine object, using clearout() to clear-out,
# and then running calibrate() to set the opentime value. This opentime will be saved and used whenever deliver() is
# run.
class TasteLine:
    def __init__(self, valve, intanOut, opentime, taste):
        self.valve = valve  # GPIO pin number corresponding to the valve controlling taste delivery
        self.intanOut = intanOut  # GPIO pin number used to send a signal to our intan neural recording system
        # whenever a taste is delivered.
        self.opentime = opentime  # how long the valve stays open for one single delivery
        self.taste = taste  # string containing name of the corresponding taste, used for datalogging in record()

        # generating a tasteLine object automatically sets up the GPIO pins:
        GPIO.setup(self.valve, GPIO.OUT)
        GPIO.setup(self.intanOut, GPIO.OUT)

    def clearout(self):  # when starting up the rig, we need to clear the air from the tubes leading to the taste
        # delivery system, and clean out the tubes when we are done. clearout() prompts user to input how long the
        # valve should be open to clear the tube, and then clears out the tube for that duration.
        dur = float(input("enter a clearout time to start clearout, or enter '0' to cancel: "))
        print("clearout = " + str(dur) + "s")
        if dur == 0:
            print("clearout canceled")
            return
        print("clearout started")
        GPIO.output(self.valve, 1)
        time.sleep(dur)
        GPIO.output(self.valve, 0)
        print("clearout complete")

    def calibrate(self):  # when starting the rig, we need to calibrate how long valves should stay open for each
        # delivery, to ensure amount of liquid delivered is consistent from session to session. calibrate() prompts
        # user to input a calibration time, and then opens the valve 5 times for that time, so the user can weigh out
        # how much liquid is dispensed per delivery.
        opentime = float(input("enter an opentime (like 0.05) to start calibration: "))
        while True:
            # Open ports
            for rep in range(5):
                GPIO.output(self.valve, 1)
                time.sleep(opentime)
                GPIO.output(self.valve, 0)
                time.sleep(3)
            ans = input('keep this calibration? (y/n): ')
            if ans == 'y':
                self.opentime = opentime
                print("opentime saved")
                break
            else:
                opentime = int(input('enter new opentime: '))

    def deliver(self):  # deliver() is used in the context of a task to open the valve for the saved opentime to
        # deliver liquid through the line
        print("taste "+str(self.valve)+" open")
        GPIO.output(self.valve, 1)
        GPIO.output(self.intanOut, 1)
        time.sleep(self.opentime)
        GPIO.output(self.valve, 0)
        GPIO.output(self.intanOut, 0)
        print("taste "+str(self.valve)+" closed")

    def kill(self):
        GPIO.output(self.valve, 0)
        GPIO.output(self.intanOut, 0)

    @property                                                             # what is property doing here? (comment this out and test it)
    def is_open(self):  # reports if valve is open
        if GPIO.input(self.valve):
            return True
        else:
            return False


### SECTION 2: MISC. FUNCTIONS

# record() logs sensor and valve data to a .csv file. Typically instantiated as a multiprocessing.process
def record(poke1, poke2, lines, starttime, endtime, anID):
    print("recording started")
    now = datetime.datetime.now()
    d = now.strftime("%m%d%y_%Hh%Mm")
    localpath = os.getcwd()
    filepath = localpath + "/" + anID + "_" + d + ".csv"
    with open(filepath, mode='w') as record_file:
        fieldnames = ['Time', 'Poke1', 'Poke2', 'Line1', 'Line2', 'Line3', 'Line4']
        record_writer = csv.writer(record_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        record_writer.writerow(fieldnames)
        while time.time() < endtime:
            t = round(time.time() - starttime, 2)
            data = [str(t), str(poke1.is_crossed()), str(poke2.is_crossed())]
            for item in lines:
                if item.is_open:
                    valvestate = True
                else:
                    valvestate = False
                data.append(str(valvestate))
            record_writer.writerow(data)
            time.sleep(0.005)
    print("recording ended")


# main_menu() shows the user the main menu and receives input
def main_menu():
    options = ["clearout a line", "calibrate a line", "cuedtaste",
               "exit"]
    print(67 * "-")
    print("MAIN MENU")
    for idx, item in enumerate(options):
        print(str(idx + 1) + ". " + item)
    print(67 * "-")
    choice = int(input("Enter your choice [1-" + str(len(options)) + "]: "))
    print("option "+str(choice) + " selected")
    return choice


# clearout_menu() runs a submenu of main_menu() for navigating clearouts of taste tubes.
def clearout_menu():
    while True:
        for x in range(1, 5):
            print(str(x) + ". clearout line " + str(x))
        print("5. main menu")
        line = int(input("enter your choice: "))
        if line in range(1, 6):
            print("line "+str(line)+" selected")
            return (line - 1)
        else:
            print("enter a valid menu option")


# calibration_menu() runs a submenu of main_menu() for navigating calibration of taste valves.
def calibration_menu():
    while True:
        for x in range(1, 5):
            print(str(x) + ". calibrate line " + str(x))
        print("5. main menu")
        line = int(input("enter your choice: "))
        if line in range(1, 6):
            return line - 1
        else:
            print("enter a valid menu option")


# system_report() prints a system report of calibrations and tastes
def system_report():
    line_no = 1
    print(67 * "-")
    print("SYSTEM REPORT:")
    for i in lines:
        print("line: " + str(line_no) + "    opentime: " + str(i.opentime) + " s" + "   taste: " + str(i.taste))
        line_no = line_no + 1


### SECTION 3: BEHAVIORAL TASK PROGRAMS ###

##cuedtaste is the central function that runs the behavioral task.
def cuedtaste():
    anID = str(input("enter animal ID: "))
    runtime = int(input("enter runtime in minutes: "))
    starttime = time.time()  # start of task
    endtime = starttime + runtime * 60  # end of task
    rew.endtime = endtime
    trig.endtime = endtime
    iti = 5  # inter-trial-interval
    wait = 1  # how long rat has to poke trigger to activate
    Hz = 3.9  # poke lamp flash frequency
    crosstime = 10  # how long rat has to cross from trigger to rewarder after activating trigger/arming rewrader.

    # setting up parallel multiprocesses for light flashing and data logging
    rew_run = mp.Value("i", 0)
    trig_run = mp.Value("i", 0) # 'i' is for integer, datatype.

    rew_flash = mp.Process(target=rew.flash, args=(Hz, rew_run,))
    trig_flash = mp.Process(target=trig.flash, args=(Hz, trig_run,))
    recording = mp.Process(target=record, args=(rew, trig, lines, starttime, endtime, anID,))

    rew_flash.start()
    trig_flash.start()
    recording.start()

    state = 0  # [state] controls state of task. Refer to PDF of hand-drawn diagram for visual guide

    # this loop controls the task as it happens, when [endtime] is reached, loop exits and task program closes out
    #TODO: create array of blocked trials
    
    def timer():
        return time.time() < endtime
    
    while timer(): ##should we set up a delay and an "if" control for the rat to make sure the rat follows times?
        #BASELINE STATE
        if state == 0:
            send_cue(state)
        while state == 0 and timer():  # state 0: base-state
            print("state 0")
            rew_keep_out = mp.Process(target=rew.keep_out, args=(iti,))     # reminder: target = target function; args = inter-trial-interval (5sec) 
            trig_keep_out = mp.Process(target=trig.keep_out, args=(iti,))
            rew_keep_out.start()
            trig_keep_out.start()

           # line = random.randint(0, 3)  # select random taste
           # line = random.randint(0,2)
           # line = 3 # for just water
            rew_keep_out.join()
            trig_keep_out.join()  # if rat stays out of both nose pokes, state 1 begins
            trig_run.value = 1
            state = 1
            send_cue(1)
            print("new trial")
            
        while state == 1 and timer():  # state 1: new trial started/arming Trigger
            if trig.is_crossed():  # once the trigger-nosepoke is crossed, move to state 2
                trig_run.value = 2  # trigger light goes from blinking to just on
                send_cue(2)
                state = 2
                start = time.time()
        
        #Trial started, cue playin
        while state == 2 and timer():  # state 2: Trigger activated/arming Rewarder
            if trig.is_crossed() and time.time() > wait + start:  # if rat trips sensor for 1 sec. continuously,                
                # move to state 3
                rew_run.value = 1  # blink rewarder
                trig_run.value = 0 # stop blinking trigger
                deadline = time.time() + crosstime # rat has 10 sec to activate rewarder
                lines[1].deliver() #TODO 01/16/22: replace this with a success chime/tone
                print("trigger activated")
                send_cue(0)
                state = 3

            if not trig.is_crossed():  # rat pulled out too early, return to state 0
                trig_run.value = 0
                state = 0
                print("state 0")

        while state == 3 and timer():  # state 3: Activating rewarder/delivering taste.
            #print("state 3")
            if not rew.is_crossed():
                start = time.time()
            if rew.is_crossed() and time.time() > start + wait/10:  # if rat crosses rewarder beam, deliver taste
                rew_run.value = 0
                lines[0].deliver() # for water only
               # lines[line].deliver()
                print("reward delivered")
                state = 0
            if time.time() > deadline:  # if rat misses reward deadline, return to state 0
                rew_run.value = 0
                state = 0
                
    send_cue(0)

    recording.join()  # wait for data logging and light blinking processes to commit seppuku when session is over
    rew_flash.join()
    trig_flash.join()
    print("assay completed")

########################################################################################################################

### SECTION 4: Menu control/"GUI", everything below runs on startup ###

if __name__=="__main__":
    # set up raspi GPIO board.
    GPIO.setwarnings(False)
    GPIO.cleanup() #turn off any GPIO pins that might be on
    GPIO.setmode(GPIO.BOARD)

    # load configs
    config = configparser.ConfigParser()  # initialize configparser to read config file
    config.read("cuedtaste_config.ini")  # read config file
    opentimes = json.loads(config.get("tastelines", "opentimes"))  # load into array times to open valves when taste delivered
    tastes = json.loads(config.get("tastelines", "tastes"))  # load taste labels into list

    ## initialize objects used in task:
    # initialize tastelines w/tones
    tasteouts = [31, 33, 35, 37]  # GPIO pin outputs to taste valves. Opens the valve while "1" is emitted from GPIO,
    # closes automatically with no voltage/ "0"
    intanouts = [24, 26, 19, 21]  # GPIO pin outputs to intan board (for marking taste deliveries in neural data). Sends
    # signal to separate device while "1" is emitted.
    #tones = ["1000hz_sine.wav", "3000hz_square.wav", "5000hz_saw.wav", "7000hz_unalias.wav"]  # filenames of tones
    # initialize taste-tone objects:
    lines = [TasteLine(tasteouts[i], intanouts[i], opentimes[i], tastes[i]) for i in range(4)]

    # initialize nosepokes:
    rew = NosePoke(36, 11)  # initialize "reward" nosepoke. "Rew" uses GPIO pins 38 as output for the light, and 11 as
    # input for the IR sensor. For the light, 1 = On, 0 = off. For the sensor, 1 = uncrossed, 0 = crossed.
    trig = NosePoke(38, 13)  # initialize "trigger". GPIO pin 38 = light output,
    # 13 = IR sensor input. Trigger is a special NosePoke class with added methods to control a tone.
    rew.flash_off()  # for some reason these lights come on by accident sometimes, so this turns off preemptively
    trig.flash_off()  # for some reason these lights come on by accident sometimes, so this turns off preemptively

    # This loop executes the main menu and menu-options
    while True:
        ## While loop which will keep going until loop = False
        system_report()  # Displays valve opentimes and taste-line assignments
        choice = main_menu()  # Displays menu options
        try:
            if choice == 1:  # run clearout menu & clearout programs
                while True:
                    line = clearout_menu()
                    if line in range(4):
                        lines[line].clearout()
                    elif line == 4:
                        break
            elif choice == 2:  # run calibration menu & calibration programs
                while True:
                    line = calibration_menu()
                    if line in range(4):
                        lines[line].calibrate()
                    elif line == 4:
                        break
                    else:
                        print("input a valid line number")
                        break

                    opentimes[line] = lines[line].opentime
                    config.set('tastelines', 'opentimes', str(opentimes))
                    with open('cuedtaste_config.ini',
                            'w') as configfile:  # in python 3+, 'w' follows filename, while in python 2+ it's 'wb'
                        config.write(configfile)

            elif choice == 3:  # run the actual program
                print("starting cuedTaste")
                cuedtaste()
            elif choice == 4:
                print("program exit")
                GPIO.cleanup()
                break

        except ValueError:
            print("please enter a number: ")
