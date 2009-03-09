import pkg_resources
import motmot.cam_iface.choose as cam_iface_choose
import motmot.fview_ext_trig.ttrigger as ttrigger

cam_iface = cam_iface_choose.import_backend( 'unity', 'ctypes' )

import time, sys, os
from optparse import OptionParser

if sys.platform.startswith('linux'):
    time_func = time.time

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

    trigdev.frames_per_second = 0 # pause trigger
    cam.start_camera()

    # clear any pending frames
    count = 0
    while not ensure_no_frame(cam,0.1):
        if count >= 10:
            sys.stderr.write('ERROR: 10 frames were counted, but no pulse was given. '
                             'Please set your camera on external trigger mode using the '
                             '--trigger-mode=<mode_num> command line argument\n')
            sys.exit(1)
        else:
            count += 1

    while 1:
        # get frame ASAP
        tstart = time_func()
        trigdev.do_single_frame_pulse = True # generate trigger pulse
        cam.grab_next_frame_blocking(timeout=0.1)
        tstop = time_func()

        latency = tstop-tstart
        print 'upper bound on single frame latency: %.1f msec'%(latency*1e3,)

if __name__=='__main__':
    main()
