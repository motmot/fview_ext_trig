import pkg_resources
import motmot.cam_iface.choose as cam_iface_choose
import motmot.fview_ext_trig.ttrigger as ttrigger
import motmot.fview_ext_trig.live_timestamp_modeler as ltm

cam_iface = cam_iface_choose.import_backend( 'unity', 'ctypes' )

import time, sys, os
from optparse import OptionParser
import threading

if sys.platform.startswith('linux'):
    time_func = time.time

def update_model(timestamp_modeler):
    while 1:
        try:
            timestamp_modeler.update()
        except ltm.ImpreciseMeasurementError,err:
            print 'ignoring error',err
        time.sleep(0.5)

def main():
    usage = '%prog [options]'

    parser = OptionParser(usage)

    parser.add_option("--mode-num", type="int",
                      help="mode number")

    parser.add_option("--frames", type="int",
                      help="number of frames (default = infinite)",
                      default = None)

    parser.add_option("--trigger-mode", type="int",
                      help="set trigger mode",
                      default=None, dest='trigger_mode')

    (options, args) = parser.parse_args()

    if options.mode_num is not None:
        mode_num = options.mode_num
    else:
        mode_num = 0
    doit(mode_num=mode_num,
         max_frames = options.frames,
         trigger_mode=options.trigger_mode,)

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

def doit(device_num=0,
         mode_num=0,
         num_buffers=30,
         max_frames=None,
         trigger_mode=None,
         ):
    cam = cam_iface.Camera(device_num,num_buffers,mode_num)
    if trigger_mode is not None:
        cam.set_trigger_mode_number( trigger_mode )

    trigdev = ttrigger.DeviceModel()
    timestamp_modeler = ltm.LiveTimestampModeler()
    timestamp_modeler.set_trigger_device(trigdev)


    update_thread = threading.Thread(target=update_model,args=(timestamp_modeler,))
    update_thread.setDaemon(True)
    update_thread.start()

    trigdev.frames_per_second = 100
    cam.start_camera()
    print 'running at %.1f FPS'%(trigdev.frames_per_second,)

    tstart = time_func()
    dur = 20 # seconds
    tsync = tstart+1 # seconds
    did_sync = False
    tstop = tstart+dur
    now = tstart
    print 'running for %.1f seconds'%dur
    while now < tstop:
        if not did_sync and now >= tsync:
            print 'synchronizing...'
            timestamp_modeler.synchronize = True # fire event handlertimestamp_modeler.s
            did_sync = True
        cam.grab_next_frame_blocking()
        sys.stdout.write('.')
        sys.stdout.flush()

        framenumber = cam.get_last_framenumber()
        frame_timestamp = cam.get_last_timestamp()
        trigger_timestamp = timestamp_modeler.register_frame('cam',framenumber,frame_timestamp)
        now = time_func()

        if trigger_timestamp is None:
            continue
        latency = now-trigger_timestamp
        print 'latency estimate: %.1f msec'%(latency*1e3,)
    sys.stdout.write('\n')
    sys.stdout.flush()

if __name__=='__main__':
    main()
