#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 19 11:44:50 2020
bugs fixed
@author: dsvedberg || emmabarash

EVERYTHING WITH THE TAG: ################ dec. 2021 IS NEW
"""
# visit https://github.com/pygame/pygame/blob/main/examples/aliens.py for an example of how I think sounds could be implemented
# To try the aliens example, enter: python3 -m pygame.examples.aliens into terminal 
#
# Instructions for using cueplayer: 
# cd to the directory containing the folder containing cueplayer.py and audio files. 
# Enter: python3 cueplayer.py into terminal. 
# Click x or esc to exit.   

from typing import overload
import pygame as pg
import os
import multiprocessing as mp
import socket
import random 
 
# Define some colors
BLACK = (  0,   0,   0)
WHITE = (255, 255, 255)
RED   = (255,   0,   0)


# Set the height and width of the screen
screen_w = 800
screen_h = 480

# get the signal from the other RPi
def receive(signal):
    #home
    # UDP_IP = "10.0.0.166"
    # UDP_IP = "10.0.0.115"
    # at school
    UDP_IP = "129.64.50.48"
    # black oak
    # UDP_IP = "10.100.11.143"
    # when on phone
    # UDP_IP = "172.20.10.8"
    UDP_PORT = 5005

    sock = socket.socket(socket.AF_INET, # internet
                        socket.SOCK_DGRAM) #UDP

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((UDP_IP, UDP_PORT)) 

    while True:
            data, addr = sock.recvfrom(1024) #buffer size is 1024 bytes
            if data:
                # send this to function that initiates tone/replace keyboard values
                signal.value = int.from_bytes(data, "big", signed="True")
                sig_ID.value = sig_ID.value + 1 # sets up a unique ID for each value received ################ dec. 2021
                print("received message:", signal.value, "ID", sig_ID.value)
            
class Block(pg.sprite.Sprite):
    """
    This class represents the ball.
    It derives from the "Sprite" class in pg.
    """
    def __init__(self, color, width, speed):
        """ Constructor. Pass in the color of the block,
        and its size. """
 
        # Call the parent class (Sprite) constructor
        super().__init__()
 
        # Create an image of the block, and fill it with a color.
        # This could also be an image loaded from the disk.
        self.width = width
        self.height = screen_h
        self.image = pg.Surface([width, self.height])
        self.speed = speed
        self.image.fill(color)

        # Update the position of this object by setting the values
        # of rect.x and rect.y
        self.rect = self.image.get_rect()
        self.origin_x = self.rect.x
        self.origin_y = self.rect.y
    
    # if self.speed is positive, blocks move right, and if it's negative, blocks move left
    def update(self):
        self.rect = self.rect.move(self.speed, 0)
        if self.speed < 0 and self.rect.left <= self.origin_x - self.width*2:
            self.rect.left = self.origin_x
        elif self.speed > 0 and self.rect.right >= self.origin_x + self.width*2:
            self.rect.right = self.origin_x

#blocket is now modified to make a large block pass through the screen very fast to appear as flashing, rather than many bars moving
def Blockset(number, speed): #instead of number of blocks, number now determines how long block is, which you modulate to change frequency
    spritelist = pg.sprite.Group() 
    width = screen_w*(number*10)
    for i in range(2):
        # This represents a block
        block = Block(BLACK, width, speed)
        # Set location for the block
        block.rect.x = width*2*i
        block.rect.y = 0
        block.origin_x = block.rect.x
        block.origin_y = block.rect.y
        # Add the block to the list of objects
        spritelist.add(block)
    return spritelist

#TODO 01/13/21: Currently unused. Should use this to load sounds and associate with each cue. Check pygame example "aliens" for demo. 
def load_sound(file):
    if not pg.mixer:
        return None
    try:
        sound = pg.mixer.Sound(file)
        return sound
    except pg.error:
        print("Warning, unable to load, %s" % file)
    return None

if __name__ == "__main__":
    # Initialize Pygame
    pg.init()
     
    manager = mp.Manager()
    sig_ID = manager.Value('i', 0) # transfers the unique ID from receive function to main program
    ################################ dec. 2021
     
    signal = mp.Value("i", 0)
    tone_values = mp.Process(target = receive, args = (signal,))
    tone_values.start()
    screen = pg.display.set_mode((0, 0), pg.FULLSCREEN)
    # created a dictionary containing the .wav files
    audio_dict = {1: "pink_noise.wav", 2: "1000hz_sine.wav", 3: "3000hz_square.wav", 4: "5000hz_saw.wav", 5: "7000hz_unalias.wav"}
    # iterates through the dictionary to load the sound-values that correspond to the keys
    for key, value in audio_dict.items():
            audio_dict[key] = load_sound(value)
            
            
    # function called in the main loop to play new sound according to keypress, which is the "num" parameter
    # @run_once
    def pause_play(num):
        if num != 0:
            pg.mixer.stop()
            audio_dict[num].play(-1)
        else:
            pg.mixer.stop()
     
    # This is a list of 'sprites.' Each block in the program is
    # added to this list. The list is managed by a class called 'Group.
    #TODO 01/13/21: example of using load sound from pygame, implement for every cue
    #audio_0 = load_sound("pink_noise.wav")
    vis_cues = [Blockset(0,0),
                Blockset(1,0),
                Blockset(1.25,-1000), #smaller value for "number" = faster flashing
                Blockset(1.35,-1000), #bare minimum speed needed for flashing is 1000
                Blockset(1.75,-1000),
                Blockset(2,-1000)]
                
    # Loop until the user clicks the close button.
    done = False
     
    # Used to manage how fast the screen updates
    clock = pg.time.Clock()
    old_value = signal.value
    old_ID = sig_ID.value ################ dec. 2021
    cue = vis_cues[0]
    in_flag = 0 #in flag is used to condition the if statements below so that pause_play() is triggered only once when states change
    # -------- Main Program Loop -----------
    while not done:
        # Clear the screen
        screen.fill(WHITE)
        # This for-loop checks for key presses that changes the cue, and also to quit the program. 
        for event in pg.event.get(): 
            if event.type == pg.QUIT: 
                done = True
            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                done = True
                
        state = signal.value
        if in_flag == 0:
            pause_play(state)
            in_flag = 1
        # Go ahead and update the screen with what we've drawn.
        vis_cues[state].update()
        vis_cues[state].draw(screen)
        pg.display.flip()
        old_value = signal.value
        old_ID = sig_ID.value # exchanges old ID value ################ dec. 2021
        # Limit to 60 frames per second
        clock.tick(60)
        # #if there's any situation where the signal.value changes without triggering signal.value == 5, this statement changes in_flag
        # if signal.value != old_value:
        if sig_ID.value != old_ID or signal.value != old_value: 
            print(sig_ID.value, "old", old_ID)
            in_flag = 0
        if in_flag == 0: ############################### PRINT TO CONSOLE TEST ################ dec. 2021
            print("old value", old_value, "get signal", signal.value, "old ID", old_ID, "new ID", sig_ID.value)
            
    pg.quit()
    tone_values.join()