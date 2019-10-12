# Libraries
import RPi.GPIO as GPIO
import time
import math
import systemd.daemon

from picamera import PiCamera
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from subprocess import Popen, PIPE

# GPIO Mode (BOARD / BCM)
GPIO.setmode(GPIO.BCM)

# set GPIO Pins
GPIO_TRIGGER = 18
GPIO_ECHO = 24

# set GPIO direction (IN / OUT)
GPIO.setup(GPIO_TRIGGER, GPIO.OUT)
GPIO.setup(GPIO_ECHO, GPIO.IN)


def distance():
    # set Trigger to HIGH
    GPIO.output(GPIO_TRIGGER, True)

    # set Trigger after 0.01ms to LOW
    time.sleep(0.00001)
    GPIO.output(GPIO_TRIGGER, False)

    start_time = time.time()
    stop_time = time.time()

    # save StartTime
    while GPIO.input(GPIO_ECHO) == 0:
        start_time = time.time()

    # save time of arrival
    while GPIO.input(GPIO_ECHO) == 1:
        stop_time = time.time()

    # time difference between start and arrival
    time_elapsed = stop_time - start_time
    # multiply with the sonic speed (34300 cm/s)
    # and divide by 2, because there and back
    distance_found = (time_elapsed * 34300) / 2

    return math.ceil(distance_found)


def takepicture():
    camera = PiCamera()
    camera.rotation = 180
    camera.start_preview()
    time.sleep(5)
    camera.capture('/tmp/mail.jpg')
    camera.stop_preview()


def sendemail(distdiff):
    fromemail = 'ravsliberen@ravsliberen.dk'
    toemail = 'sumo.da.killer@gmail.com'
    msg = MIMEMultipart()
    msg['Subject'] = 'Post i postkassen :)'
    msg['From'] = fromemail
    msg['To'] = toemail
    msg.preamble = 'Afstand aendret med ' + distdiff + ' cm'
    fp = open('/tmp/mail.jpg', 'rb')
    img = MIMEImage(fp.read())
    fp.close()
    msg.attach(img)
    p = Popen(["/usr/sbin/sendmail", "-t", "-oi"], stdin=PIPE)
    p.communicate(msg.as_string())


if __name__ == '__main__':
    try:
        # Give the sensor a couple of seconds to settle
        time.sleep(2)
        # Tell systemd that our service is ready
        systemd.daemon.notify('READY=1')
        old_dist = 0
        triggered_dist = 0
        while True:
            dist = distance()
            if old_dist == 0:
                old_dist = dist
            if triggered_dist > 0 and triggered_dist != dist:
                triggered_dist = 0
            elif triggered_dist == dist:
                # Mail is probably in front of sensor, so don't send mails
                continue
            # It seem that the distance sometimes changes without any mail, but so far only by 1
            if dist < old_dist and (old_dist - dist) > 1:
                print("Distance changed from " + str(old_dist) + " to " + str(dist) + " cm")
                takepicture()
                sendemail(str(old_dist - dist))
                if triggered_dist == 0:
                    triggered_dist = dist

            time.sleep(0.1)

        # Reset by pressing CTRL + C
    except KeyboardInterrupt:
        print("Measurement stopped by User")
        GPIO.cleanup()
