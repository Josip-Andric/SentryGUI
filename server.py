import subprocess
import signal
import atexit
from flask import Flask, render_template, redirect, url_for
import os
import psutil
import RPi.GPIO as GPIO
import time



app = Flask(__name__)

config_path = os.path.join(os.path.dirname(__file__), "/home/fluo/mediamtx.yml")

config_path = "/home/fluo/mediamtx.yml"
stream_process = None
mediamtx_path = "/home/fluo/mediamtx"


def start_stream():
    global stream_process
    if stream_process and stream_process.poll() is None:
        return "Stream je već pokrenut!"
    
    stream_process = subprocess.Popen([mediamtx_path, config_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return "Stream pokrenut!"


def stop_stream():
    global stream_process
    if stream_process and stream_process.poll() is None:  
        parent = psutil.Process(stream_process.pid)
        for child in parent.children(recursive=True):  
            child.terminate()
        parent.terminate()

        try:
            parent.wait(timeout=5)  
        except psutil.TimeoutExpired:
            parent.kill()  

atexit.register(stop_stream)



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/capture")
def capture():
    os.system("libcamera-still --raw -o /home/fluo/shared/capture_$(date +\%M\%S).jpg")
    return "Snimljena fotografija!", 200

@app.route("/record")
def record():
    os.system("libcamera-vid --level 4.2 --framerate 60 --width 1280 --height 720  -o /home/fluo/shared/video_$(date +\%M\%S).264 -t 10000 --denoise cdn_off -n")  # Snima 5 sekundi
    return "Snimljen video!", 200

@app.route("/long_expo")
def long_expo():
    os.system("libcamera-still -o /home/fluo/shared/long_expo_$(date +\%M\%S).jpg --shutter 5000000 --gain 1 --awbgains 1,1 --immediate")
    return "Snimljen long expo" , 200

@app.route("/experimental")
def experimental():
    os.system("libcamera-still --shutter 1000000   --output /home/fluo/shared/experimental_$(date +\%M\%S).raw")
    return "Snimljen experimental" , 200



SERVO_LR_PIN = 22  # Servo za lijevo/desno
SERVO_UD_PIN = 18  # Servo za gore/dolje

STEP = 15 
MIN_ANGLE = 0
MAX_ANGLE = 180

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_LR_PIN, GPIO.OUT)
GPIO.setup(SERVO_UD_PIN, GPIO.OUT)

pwm_lr = GPIO.PWM(SERVO_LR_PIN, 50)  # 50 Hz
pwm_ud = GPIO.PWM(SERVO_UD_PIN, 50)  # 50 Hz

pwm_lr.start(0)
pwm_ud.start(0)

current_angle_lr = 90  
current_angle_ud = 90

def set_angle(pwm, angle):
    duty_cycle = 2 + (angle / 18)  
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.3)  
    pwm.ChangeDutyCycle(0)  

set_angle(pwm_lr, current_angle_lr)
set_angle(pwm_ud, current_angle_ud)

@app.route('/left', methods=['POST'])
def move_left():
    global current_angle_lr
    if current_angle_lr > MIN_ANGLE:
        current_angle_lr -= STEP
        set_angle(pwm_lr, current_angle_lr)
    return '', 204

@app.route('/right', methods=['POST'])
def move_right():
    global current_angle_lr
    if current_angle_lr < MAX_ANGLE:
        current_angle_lr += STEP
        set_angle(pwm_lr, current_angle_lr)
    return '', 204

@app.route('/center', methods=['POST'])
def center_servo():
    global current_angle_lr, current_angle_ud
    current_angle_lr = 90
    current_angle_ud = 90
    set_angle(pwm_lr, current_angle_lr)
    set_angle(pwm_ud, current_angle_ud)
    return '', 204

@app.route('/up', methods=['POST'])
def move_up():
    global current_angle_ud
    if current_angle_ud < MAX_ANGLE:
        current_angle_ud += STEP
        set_angle(pwm_ud, current_angle_ud)
    return '', 204

@app.route('/down', methods=['POST'])
def move_down():
    global current_angle_ud
    if current_angle_ud > MIN_ANGLE:
        current_angle_ud -= STEP
        set_angle(pwm_ud, current_angle_ud)
    return '', 204


@app.route("/kill_stream", methods=["POST"])
def kill_stream():
    stop_stream()  
    return redirect(url_for('index'))  

@app.route("/start")
def start():
    start_stream()
    return redirect(url_for('index'))


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        pwm_lr.stop()
        pwm_ud.stop()
        GPIO.cleanup()
