import fview_ext_trig.ttrigger as ttrigger
import time

if 1:
    trigdev = ttrigger.DeviceModel()
    trigdev.frames_per_second = 1
    dt = 1.0/trigdev.frames_per_second_actual/10.0
    prev = 0
    while 1:
        current = trigdev.get_framestamp()
        if current < prev:
            print current,'<------------'
        else:
            print current
        prev=current
        time.sleep(dt)
