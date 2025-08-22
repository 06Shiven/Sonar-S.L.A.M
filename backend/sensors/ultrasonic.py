#/usr/bin/env python3
"""
ultrasonic.py

Provides an Ultrasonic sensor class for Raspberry Pi to measure distances.
"""

import RPi.GPIO as GPIO
import numpy as np
from time import sleep, perf_counter


class Ultrasonic:
    """
    Represents an ultrsonic distance sensor

    Attributes:
        trig_pin (int): GPIO pin used for the trigger signal
        echo_pin (int): GPIO pin used for the echo signal
    """

    def __init__(self, trig_pin, echo_pin, GPIO_mode=GPIO.BCM):
        """
        Initalises the trig and echo pin and the sensor for reading values

        Parameters:
            trig_pin (int): GPIO pin used for trigger signal
            echo_pin (int): GPIO pin used for echo signal
        """

        self.trig_pin = trig_pin
        self.echo_pin = echo_pin
            
        # set correct pin mode for trig and echo    
        GPIO.setup(trig_pin, GPIO.OUT)
        GPIO.setup(echo_pin, GPIO.IN)

        # delay to correctly init sensor before using
        sleep(1e-5)

    def send_sonar_signal(self):
        """Sends 10 millisecond HIGH signal to trig pin to trigger sonar"""
        
        # set trig pin to low for 2 microsec to ensure its low
        GPIO.output(self.trig_pin, GPIO.LOW)
        sleep(2 / 1e6)

        # set trig pin high for more than 10 microsec to trigger 8 pulse cycle
        GPIO.output(self.trig_pin, GPIO.HIGH)
        sleep(11 / 1e6)

        # set low for next run
        GPIO.output(self.trig_pin, GPIO.LOW)
        sleep(2 / 1e6)

    def travel_duration(self):
        """
        Calculates duration it took signal to reach the sensor
        
        Returns:
            float: total duration period between sending and recieving signal
        """

        # max time to wait based on the max range of the sensor
        reading_timeout = 0.04

        # sensor timeout for misfires
        sensor_timeout = 0.04
        init_time = perf_counter()

        # wait till echo is set high by the sensor 
        while not GPIO.input(self.echo_pin):
            # if echo does not go high after trigger return None
            if perf_counter() - init_time > sensor_timeout:
                return None

        # setup timer for if signal is out of range
        start_time = perf_counter()

        # wait till echo is low meaning signal is recieved or until timeout
        while GPIO.input(self.echo_pin) and perf_counter() - start_time < reading_timeout:
            sleep(1e-6)

        duration = perf_counter() - start_time

        return duration

    def distance(self):
        """
        Measure the distance from the sensor

        Returns:
            float or None: Distance in meters if measurement is valid, otherwise None
        """

        # send signal 
        self.send_sonar_signal()
        
        # get duration of travel
        duration = self.travel_duration()

        # return None for misfires
        if duration == None: return None

        # convert to metres
        distance = duration * 343 / 2

        return distance

    def filtered_distance(self, min_dist=0.02, max_dist=0.65, samples=4):
        """
        Filters raw distance value from the sensor for less noisy values

        Parameters:
            min_dist (float, optional): minimum useable value in metres
            max_dist (float, optional): maximum useable value in metres
            samples (int optional): Number of samples for calculating average

        Returns:
            float or None: filtered distance in meteres if sensor is not continously misfiring, otherwise None
        """
        
        raw_dists = []
        
        # collect a sample of points skipping over misfires
        for i in range(samples):
            raw_distance = self.distance()
            if raw_distance == None:
                continue
            raw_dists.append(raw_distance)

        # calculate percentile intervals to find outliers
        Q1 = np.percentile(raw_dists, 25)
        Q3 = np.percentile(raw_dists, 75)

        # calculate outliers with interquartile range (IQR)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR        

        # filter out values in the outlier range
        raw_dists = [dist for dist in raw_dists if dist >= lower_bound and dist <= upper_bound]
    
        # find the average of distances 
        filtered_distance = sum(raw_dists) / len(raw_dists)

        # check if filtered_dist is within limits
        if filtered_distance < min_dist: filtered_distance = min_dist
        elif filtered_distance > max_dist: filtered_distance = max_dist

        # return filtered and averaged result
        return round(filtered_distance, 4)


if __name__ == "__main__":
    
    GPIO.setmode(GPIO.BCM)

    dist_sensor = Ultrasonic(27,17)

    distance = dist_sensor.filtered_distance()

    try:

        while True:
            distance = dist_sensor.filtered_distance()
            print(f"Distance (m): {distance}")
            sleep(0.0001)
    finally:
        print("sensor cleanup")
        GPIO.cleanup()
        
