#/user/bin/env python3
"""
stepper_motor.py

Provides a stepper motor class for the ULN2003 motor driver 
and Raspberry Pi to accurately control with smooth movement.
"""

import RPi.GPIO as GPIO
from time import sleep


class StepperMotor:
    """Represents a stepper motor"""

    def __init__(self, in1, in2, in3, in4):
        """
        Intialises the 4 step pins of the stepper and setups the movement seqeunce

        Parameters:
            in1 (int): GPIO pin connect to in1 on motor driver
            in2 (int): GPIO pin connect to in2 on motor driver
            in3 (int): GPIO pin connect to in3 on motor driver
            in4 (int): GPIO pin connect to in4 on motor driver
        """
        
        self.control_pins = [in1, in2, in3, in4]

        for pin in self.control_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, 0)

        self.cw_halfstep_seq = [
          [1,0,0,0],
          [1,1,0,0],
          [0,1,0,0],
          [0,1,1,0],
          [0,0,1,0],
          [0,0,1,1],
          [0,0,0,1],
          [1,0,0,1]
        ]

    def cycle(self, step_speed, reverse=False):
        """
        Executes one halfstep cycle on the stepper motor

        Parameters:
            step_speed (float): time to wait inbetween each halfstep
            reverse (bool, optional): set true to move counterclockwise
        """

        # 8 halfsteps in one cycle
        for halfstep in range(8):
            # update pin output for each halfstep
            for pin in range(4):
                # spin correct way with cw being forward
                if not reverse:
                    GPIO.output(self.control_pins[pin], self.cw_halfstep_seq[halfstep][pin])
                else:
                    GPIO.output(self.control_pins[pin], self.cw_halfstep_seq[-(halfstep)][pin])
            sleep(step_speed)
             
    def rotate(self, degrees, rotation_speed, reverse=False):
        """
        Rotates the motor for a certain amount of degrees.
        Uses cycles as steps, with there being 512 steps per one revolution

        Parameters:
            degrees (int): number of degrees to turn the motor
            rotation_speed (float): speed in rotations per minute 
            reverse (bool, optional): set true to turn counterclockwise
        """

        # state variables   
        target_speed = rotation_speed
        curr_speed = 0
        curr_accel = 0

        # constants
        MIN_SPEED = 5
        ACCEL_MAX = 15000
        JERK_MAX = 8e5
        dt = 10e-5

        # keep track of how many cycles it took to accelerate
        accel_cycles = 0
        
        # convert degress to cycles with 512 cycles per 360 degrees
        cycles = int(degrees / 360 * 512)

        for i in range(cycles):

            # check for when target speed is reached
            if(curr_speed >= target_speed and accel_cycles == 0):
                accel_cycles = i
                curr_accel = 0

            # standstill speed to avoid pull in stall
            if curr_speed == 0 and target_speed != 0:
                curr_speed = MIN_SPEED

            else:

                # accelerate if speed hasn't reached deceleration point
                if i <= cycles - accel_cycles:
                    # only need to accelerate if target speed is not reached
                    if curr_speed < target_speed: 
                        curr_accel = min(curr_accel+JERK_MAX*dt, ACCEL_MAX)
                    curr_speed = min(curr_speed+curr_accel*dt, target_speed)
                else:
                    # once deceleration point is reached begin slowing down for symmetrical movement
                    curr_accel = min(curr_accel+JERK_MAX*dt, ACCEL_MAX)
                    curr_speed = max(curr_speed-curr_accel*dt, MIN_SPEED)                    
           
            # convert RPM to time per step by dividing timer per cycle by 8 steps
            step_speed = (60 / (curr_speed * 512)) / 8

            self.cycle(step_speed, reverse)
            
            # sleep some amount to avoid consuming excess resources
            # keeps calculations accurate 
            sleep(dt)

           

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)

    try:
        motor = StepperMotor(21, 20, 16, 12)

        motor.rotate(360, 30)
        sleep(0.5)
        motor.rotate(360, 30, True)

    finally:
        GPIO.cleanup()
