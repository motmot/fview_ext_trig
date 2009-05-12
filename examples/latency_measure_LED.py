import pkg_resources
import motmot.cam_iface.choose as cam_iface_choose
import motmot.fview_ext_trig.ttrigger as ttrigger
import motmot.fview_ext_trig.live_timestamp_modeler as ltm

cam_iface = cam_iface_choose.import_backend( 'unity', 'ctypes' )

import time, sys, os, warnings
from optparse import OptionParser
import threading, Queue
import numpy as np

if sys.platform.startswith('linux'):
    time_func = time.time

def update_model(timestamp_modeler,dt):
    while 1:
        try:
            timestamp_modeler.update()
        except ltm.ImpreciseMeasurementError:
            pass
        time.sleep(dt)

def main():
    usage = '%prog [options]'

    parser = OptionParser(usage)

    parser.add_option("--mode-num", type="int",
                      help="mode number")

    parser.add_option("--trigger-mode", type="int",
                      help="set trigger mode",
                      default=None, dest='trigger_mode')

    parser.add_option("--fps", type="float",
                      help="frames per second",
                      default=None, dest='fps')

    (options, args) = parser.parse_args()

    if options.mode_num is not None:
        mode_num = options.mode_num
    else:
        mode_num = 0

    if options.fps is not None:
        fps = options.fps
    else:
        fps = 100.0

    doit(mode_num=mode_num,
         trigger_mode=options.trigger_mode,
         fps=fps)

def ensure_no_frame(cam,timeout):
    tstart = time_func()
    dur=0
    while dur<timeout:
        try:
            cam.grab_next_frame_blocking(timeout=timeout)
        except RuntimeError:
            raise
        except cam_iface.FrameTimeout:
            pass
        else:
            return False
        tstop = time_func()
        dur = tstop-tstart
    return True

def print_descriptive_stats(X,label='X'):
    min = np.min(X)
    max = np.max(X)
    median = np.median(X)
    mean = np.mean(X)
    std = np.std(X)
    print '%s: min - max: %.1f - %.1f   median: %.1f   mean: %.1f  std %.1f'%(
        label, min, max, median, mean, std)

def measure_mean_pixel_value_N_times(cam,N):
    framecount = 0
    samples = []
    while framecount < N:
        #sample N frames
        buf = cam.grab_next_frame_blocking()
        sample = np.mean(buf)
        samples.append(sample)
        framecount+=1
    samples = np.array(samples)
    return samples

def flush_incoming_frames(cam,trigdev,dur=0.3):
    # continue to attempt to get frames
    tstart = time_func()
    tstop = tstart+dur
    now = tstart
    while now < tstop:
        tremain = tstop-now
        try:
            cam.grab_next_frame_blocking(timeout=tremain)
        except cam_iface.FrameTimeout:
            pass
        now = time_func()

def LED_pulse_time_randomizer(trigdev,
                              LED_pulse_time_queue,
                              trigger_LED_on,
                              trigger_LED_off,
                              interval):
    """mainloop for thread to pulse LED on and off at random times

    Trigger LED onset with variable latency. This breaks any
    phase-locking that would happen if the LED was triggered
    immediately upon frame return from the camera.
    """
    # starts with LED off, wait for on command
    while 1:
        trigger_LED_on.wait()
        trigger_LED_on.clear()
        wait_dur = np.random.uniform(0.0,interval)
        time.sleep(wait_dur)
        LED_pulse_time = time_func()
        trigdev.led1 = True
        LED_pulse_time_queue.put(LED_pulse_time)

        trigger_LED_off.wait()
        trigger_LED_off.clear()
        wait_dur = np.random.uniform(0.0,interval)
        time.sleep(wait_dur)
        LED_pulse_time = time_func()
        trigdev.led1 = False
        LED_pulse_time_queue.put(LED_pulse_time)

def doit(device_num=0,
         mode_num=0,
         num_buffers=30,
         trigger_mode=None,
         fps=100.0,
         ):
    cam = cam_iface.Camera(device_num,num_buffers,mode_num)
    if trigger_mode is not None:
        cam.set_trigger_mode_number( trigger_mode )

    trigdev = ttrigger.DeviceModel()
    timestamp_modeler = ltm.LiveTimestampModeler()
    timestamp_modeler.set_trigger_device(trigdev)


    # query USB device this often
    dt = 0.5

    update_thread = threading.Thread(target=update_model,args=(timestamp_modeler,dt))
    update_thread.setDaemon(True)
    update_thread.start()

    trigdev.frames_per_second = fps

    cam.start_camera()

    # turn all LEDS off
    trigdev.led1 = False
    trigdev.led2 = False
    trigdev.led3 = False
    trigdev.led4 = False
    flush_incoming_frames(cam,trigdev)

    N_samples = 30

    samples_off = measure_mean_pixel_value_N_times(cam,N_samples)
    print_descriptive_stats(samples_off,'LED off')
    max_off = np.max(samples_off)

    # turn LED1 on
    trigdev.led1 = True
    flush_incoming_frames(cam,trigdev)

    samples_on = measure_mean_pixel_value_N_times(cam,N_samples)
    print_descriptive_stats(samples_on,'LED on')
    min_on = np.min(samples_on)

    if min_on < max_off:
        raise ValueError('cannot unambiguously determine if LED is on or off')
    threshold = (min_on + max_off)/2.0 # halfway between the two

    # turn all LEDS off
    trigdev.led1 = False
    flush_incoming_frames(cam,trigdev)

    LED_pulse_time_queue = Queue.Queue()
    trigger_LED_on = threading.Event()
    trigger_LED_off = threading.Event()

    interval = 1.0/fps
    LED_thread = threading.Thread( target=LED_pulse_time_randomizer,
                                   args=(trigdev,
                                         LED_pulse_time_queue,
                                         trigger_LED_on,
                                         trigger_LED_off,
                                         interval) )
    LED_thread.setDaemon(True)
    LED_thread.start()

    state = 'LED1 off, flushed'
    assert timestamp_modeler.has_ever_synchronized==False

    did_sync = False
    while 1:
        if not did_sync:
            timestamp_modeler.synchronize = True # fire event handlertimestamp_modeler.s
            did_sync = True
        try:
            buf = cam.grab_next_frame_blocking()
        except cam_iface.FrameDataMissing:
            print 'missing frame'
            continue

        now = time_func()
        framenumber = cam.get_last_framenumber()
        frame_timestamp = cam.get_last_timestamp()
        trigger_timestamp = timestamp_modeler.register_frame('cam',framenumber,frame_timestamp)

        if trigger_timestamp is None:
            #waiting for synchronization
            continue

        model_latency_sec = now-trigger_timestamp
        frame_mean = np.mean(buf)

        if state == 'LED1 off, flushed':
            trigger_LED_on.set()
            state = 'LED1 on, waiting'
        elif state == 'LED1 on, waiting':
            if frame_mean < threshold:
                # LED off
                pass # wait for first frame with LED on
            else:
                # LED on
                LED_pulse_time = LED_pulse_time_queue.get()
                latency_sec = now-LED_pulse_time
                print 'latency: %.1f msec (model: %.1f msec)'%(latency_sec*1e3,
                                                               model_latency_sec*1e3)

                trigger_LED_off.set()
                state = 'LED1 off, waiting'
        elif state == 'LED1 off, waiting':
            if frame_mean < threshold:
                # LED off
                LED_pulse_time = LED_pulse_time_queue.get()
                latency_sec = now-LED_pulse_time
                print 'latency: %.1f msec (model: %.1f msec)'%(latency_sec*1e3,
                                                               model_latency_sec*1e3)

                trigger_LED_on.set()
                state = 'LED1 on, waiting'
            else:
                # LED on
                pass # wait for first frame with LED off


#         if trigger_timestamp is None:
#             continue
#         latency = now-trigger_timestamp
#         print 'latency estimate: %.1f msec'%(latency*1e3,)
#     sys.stdout.write('\n')
#     sys.stdout.flush()

if __name__=='__main__':
    main()
