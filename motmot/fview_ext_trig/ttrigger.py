from __future__ import with_statement
import pylibusb as usb
import ctypes
import sys, time, os, threading, warnings, re
import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group
import numpy as np
from optparse import OptionParser

ENDPOINT_DIR_IN = 0x80
ANALOG_EPNUM = 0x01

# keep in sync with defines in camtrig.c
CAMTRIG_ENTER_DFU = 0
CAMTRIG_NEW_TIMER3_DATA = 1
CAMTRIG_DO_TRIG_ONCE = 2
CAMTRIG_DOUT_HIGH = 3
CAMTRIG_GET_DATA = 4
CAMTRIG_RESET_FRAMECOUNT_A = 5
CAMTRIG_SET_EXT_TRIG = 6
CAMTRIG_AIN_SERVICE = 7
CAMTRIG_GET_FRAMESTAMP_NOW = 8
CAMTRIG_SET_LED_STATE = 9

EXT_TRIG1 = 0x01
EXT_TRIG2 = 0x02
EXT_TRIG3 = 0x04

ADC_START_STREAMING = 0x01
ADC_STOP_STREAMING = 0x02
ENABLE_ADC_CHAN0 = 0x04
ENABLE_ADC_CHAN1 = 0x08
ENABLE_ADC_CHAN2 = 0x10
ENABLE_ADC_CHAN3 = 0x20

ADC_RESET_AIN = 0x40

LEDS_LED1 = 1 << 4 # for the Atmel USBKEY port D
LEDS_LED2 = 1 << 5 # for the Atmel USBKEY port D
LEDS_LED3 = 1 << 7 # for the Atmel USBKEY port D
LEDS_LED4 = 1 << 6 # for the Atmel USBKEY port D

def debug(*args):
    if 0:
        print >> sys.stderr, ' '.join([str(arg) for arg in args])

class NoDataError(Exception):
    pass

class RemoteFpsFloat(traits.BaseFloat):
    """a floating point number that validates any attempted change"""
    info_text = 'a float'

    def validate ( self, obj, name, value ):
        """validate the new number to ensure the trigger device is set"""
        value = super(RemoteFpsFloat, self).validate(obj, name, value)
        try:
            if obj._lock is None:
                # not initialized
                return value
            obj.set_frames_per_second_approximate(value)

            actual_value = obj.frames_per_second_actual
            return actual_value
        except Exception,err:
            print 'error in validate: %s'%err
        self.error( obj, name, value )

class DeviceTimer3State(traits.HasTraits):
    """encapsulate all (relevant) timer3 state on the device

    Making these variables a member of their own HasTraits class means
    that updates to the device can be treated in an atomic way.
    """
    # Timer/Counter3 state
    timer3_top = traits.Int(200)
    # The conversion from a clock select (CS) prescaler bit code.
    timer3_CS = traits.Trait(64, { 0.0:   0x00, # off
                                   1.0:   0x01,
                                   8.0:   0x02,
                                   64.0:  0x03,
                                   256.0: 0x04,
                                   1024.0:0x05})
    ocr3a = traits.Int
    ocr3b = traits.Int
    ocr3c = traits.Int

class DeviceAnalogInState(traits.HasTraits):
    """encapsulate all (relevant) analog input state on the device

    Making these variables a member of their own HasTraits class means
    that updates to the device can be treated in an atomic way.
    """
    # Analog input state
    AIN0_enabled = traits.Bool(False)
    AIN0_name = traits.String("AIN0")
    AIN1_enabled = traits.Bool(False)
    AIN1_name = traits.String("AIN1")
    AIN2_enabled = traits.Bool(True)
    AIN2_name = traits.String("AIN2")
    AIN3_enabled = traits.Bool(False)
    AIN3_name = traits.String("AIN3")
    trigger_device = traits.Instance('DeviceModel',transient=True)

    adc_prescaler = traits.Trait(128.0,{
        128.0:0x07,64.0: 0x06,
        # According to Atmel's at90usb1287 manual, faster than this is
        # too fast to get good measurements with 8MHz crystal.
        ## '32': 0x05,'16': 0x04,'8': 0x03,
        ## '4': 0x02,'2': 0x00, # also 0x01
        })
    downsample_bits = traits.Range(low=0,high=2**5-1,value=0)
    AIN_running = traits.Bool(False)
    sample_rate_total = traits.Property(label='Sample rate (Hz), all channels',
                                        depends_on=['adc_prescaler',
                                                    'trigger_device',
                                                    'downsample_bits'])
    sample_rate_chan = traits.Property(label='each channel',
                                       depends_on=['sample_rate_total',
                                                   'AIN0_enabled','AIN1_enabled',
                                                   'AIN2_enabled','AIN3_enabled',])

    # but useful when plotting/saving data
    Vcc = traits.Float(3.3)

    traits_view = View(Group(Group(Item('AIN_running'),
                                   Item(
        'Vcc',
        tooltip=('This does not set Vcc on the AT90USBKEY. Use to record the '
                 'value of Vcc. (default = 3.3V)')),
                                   orientation='horizontal'),
                                   Group(Item('AIN0_enabled',padding=0),
                                         Item('AIN0_name',padding=0),
                                         Item('AIN1_enabled',padding=0),
                                         Item('AIN1_name',padding=0),
                                         padding=0,
                                         orientation='horizontal'),
                                   Group(Item('AIN2_enabled',padding=0),
                                         Item('AIN2_name',padding=0),
                                         Item('AIN3_enabled',padding=0),
                                         Item('AIN3_name',padding=0),
                                         padding=0,
                                         orientation='horizontal'),
                             Group(Item('adc_prescaler'),
                                   Item('downsample_bits'),
                                   orientation='horizontal'),
                             Group(Item('sample_rate_total',
                                        #show_label=False,
                                        style='readonly',
                                        ),
                                   Item('sample_rate_chan',
                                        #show_label=False,
                                        style='readonly',
                                        ),
                                   orientation='horizontal'),
                             ))

    @traits.cached_property
    def _get_sample_rate_total(self):
        input_frequency = self.trigger_device.FOSC/self.adc_prescaler
        if input_frequency < 50*1e3:
            warnings.warn('ADC sample frequency is too slow to get good sampling')
        if input_frequency > 200*1e3:
            warnings.warn('ADC sample frequency is too fast to get good sampling')
        #print 'input_frequency %.1f (kHz)'%(input_frequency/1000.0,)
        clock_cycles_per_sample = 13.0
        clock_adc = input_frequency/clock_cycles_per_sample
        downsample_factor = self.downsample_bits+1
        downsampled_clock_adc = clock_adc/downsample_factor
        return downsampled_clock_adc

    @traits.cached_property
    def _get_sample_rate_chan(self):
        n_chan = sum(map(int,[self.AIN0_enabled,self.AIN1_enabled,
                              self.AIN2_enabled,self.AIN3_enabled]))
        rate = self.sample_rate_total/float(n_chan)
        return rate

class DeviceModel(traits.HasTraits):
    """Represent the trigger device in the host computer, and push any state

    We keep a local copy of the state of the device in memory on the
    host computer, and any state changes to the device to through this
    class, also allowing us to update our copy of the state.

    """
    # Private runtime details
    _libusb_handle = traits.Any(None,transient=True)
    _lock = traits.Any(None,transient=True) # lock access to the handle
    real_device = traits.Bool(False,transient=True) # real USB device present
    FOSC = traits.Float(8000000.0,transient=True)

    ignore_version_mismatch = traits.Bool(False, transient=True)

    # A couple properties
    frames_per_second = RemoteFpsFloat
    frames_per_second_actual = traits.Property(depends_on='_t3_state')
    timer3_top = traits.Property(depends_on='_t3_state')

    # Timer 3 state:
    _t3_state = traits.Instance(DeviceTimer3State) # atomic updates

    # LEDs state
    _led_state = traits.Int

    led1 = traits.Property(depends_on='_led_state')
    led2 = traits.Property(depends_on='_led_state')
    led3 = traits.Property(depends_on='_led_state')
    led4 = traits.Property(depends_on='_led_state')

    # Event would be fine for these, but use Button to get nice editor
    reset_framecount_A = traits.Button
    reset_AIN_overflow = traits.Button
    do_single_frame_pulse = traits.Button

    ext_trig1 = traits.Button
    ext_trig2 = traits.Button
    ext_trig3 = traits.Button

    # Analog input state:
    _ain_state = traits.Instance(DeviceAnalogInState) # atomic updates
    Vcc = traits.Property(depends_on='_ain_state')

    AIN_running = traits.Property(depends_on='_ain_state')
    enabled_channels = traits.Property(depends_on='_ain_state')
    enabled_channel_names = traits.Property(depends_on='_ain_state')

    # The view:
    traits_view = View(Group( Group(Item('frames_per_second',
                                         label='frame rate',
                                         ),
                                    Item('frames_per_second_actual',
                                         show_label=False,
                                         style='readonly',
                                         ),
                                    orientation='horizontal',),
                              Group(Item('ext_trig1',show_label=False),
                                    Item('ext_trig2',show_label=False),
                                    Item('ext_trig3',show_label=False),
                                    orientation='horizontal'),
                              Item('_ain_state',show_label=False,
                                   style='custom'),
                              Item('reset_AIN_overflow',show_label=False),
                              ))

    def __init__(self,*a,**k):
        super(DeviceModel,self).__init__(*a,**k)
        self._t3_state = DeviceTimer3State()
        self._ain_state = DeviceAnalogInState(trigger_device=self)

    def __new__(cls,*args,**kwargs):
        """Set the transient object state

        This must be done outside of __init__, because instances can
        get created without calling __init__. In particular, when
        being loaded from a pickle.
        """
        self = super(DeviceModel, cls).__new__(cls,*args,**kwargs)
        self._lock = threading.Lock()
        self._open_device()
        # force the USBKEY's state to our idea of its state
        self.__led_state_changed()
        self.__t3_state_changed()
        self.__ain_state_changed()
        self.reset_AIN_overflow = True # reset ain overflow
        return self

    def _set_led_mask(self,led_mask,value):
        if value:
            self._led_state = self._led_state | led_mask
        else:
            self._led_state = self._led_state & ~led_mask

    def __led_state_changed(self):
        buf = ctypes.create_string_buffer(2)
        buf[0] = chr(CAMTRIG_SET_LED_STATE)
        buf[1] = chr(self._led_state)
        self._send_buf(buf)

    @traits.cached_property
    def _get_led1(self):
        return bool(self._led_state & LEDS_LED1)
    def _set_led1(self,value):
        self._set_led_mask(LEDS_LED1,value)

    @traits.cached_property
    def _get_led2(self):
        return bool(self._led_state & LEDS_LED2)
    def _set_led2(self,value):
        self._set_led_mask(LEDS_LED2,value)

    @traits.cached_property
    def _get_led3(self):
        return bool(self._led_state & LEDS_LED3)
    def _set_led3(self,value):
        self._set_led_mask(LEDS_LED3,value)

    @traits.cached_property
    def _get_led4(self):
        return bool(self._led_state & LEDS_LED4)
    def _set_led4(self,value):
        self._set_led_mask(LEDS_LED4,value)

    @traits.cached_property
    def _get_Vcc(self):
        return self._ain_state.Vcc

    @traits.cached_property
    def _get_AIN_running(self):
        return self._ain_state.AIN_running

    @traits.cached_property
    def _get_enabled_channels(self):
        result = []
        if self._ain_state.AIN0_enabled:
            result.append(0)
        if self._ain_state.AIN1_enabled:
            result.append(1)
        if self._ain_state.AIN2_enabled:
            result.append(2)
        if self._ain_state.AIN3_enabled:
            result.append(3)
        return result

    @traits.cached_property
    def _get_enabled_channel_names(self):
        result = []
        if self._ain_state.AIN0_enabled:
            result.append(self._ain_state.AIN0_name)
        if self._ain_state.AIN1_enabled:
            result.append(self._ain_state.AIN1_name)
        if self._ain_state.AIN2_enabled:
            result.append(self._ain_state.AIN2_name)
        if self._ain_state.AIN3_enabled:
            result.append(self._ain_state.AIN3_name)
        return result

    @traits.cached_property
    def _get_timer3_top(self):
        return self._t3_state.timer3_top

    @traits.cached_property
    def _get_frames_per_second_actual(self):
        if self._t3_state.timer3_CS==0:
            return 0
        return self.FOSC/self._t3_state.timer3_CS/self._t3_state.timer3_top

    def set_frames_per_second_approximate(self,value):
        """Set the framerate as close as possible to the desired value"""
        new_t3_state = DeviceTimer3State()
        if value==0:
            new_t3_state.timer3_CS=0
        else:
            # For all possible clock select values
            CSs = np.array([1.0,8.0,64.0,256.0,1024.0])
            # find the value of top that to gives the desired framerate
            best_top = np.clip(np.round(self.FOSC/CSs/value),0,2**16-1).astype(np.int)
            # and find the what the framerate would be at that top value
            best_rate = self.FOSC/CSs/best_top
            # and choose the best one.
            idx = np.argmin(abs(best_rate-value))
            expected_rate = best_rate[idx]
            new_t3_state.timer3_CS = CSs[idx]
            new_t3_state.timer3_top = best_top[idx]

            ideal_ocr3a = 0.02 * new_t3_state.timer3_top # 2% duty cycle
            ocr3a = int(np.round(ideal_ocr3a))
            if ocr3a==0:
                ocr3a=1
            if ocr3a >= new_t3_state.timer3_top:
                ocr3a-=1
                if ocr3a <= 0:
                    raise ValueError('impossible combination for ocr3a')
            new_t3_state.ocr3a = ocr3a
        self._t3_state = new_t3_state # atomic update

    def get_framestamp(self,full_output=False):
        """Get the framestamp and the value of PORTC

        The framestamp includes fraction of IFI until next frame.

        The inter-frame counter counts up from 0 to self.timer3_top
        between frame ticks.
        """
        if not self.real_device:
            now = time.time()
            if full_output:
                framecount = now//1
                tcnt3 = now%1.0
                results = now, framecount, tcnt3
            else:
                results = now
            return results
        buf = ctypes.create_string_buffer(1)
        buf[0] = chr(CAMTRIG_GET_FRAMESTAMP_NOW)
        self._send_buf(buf)
        data = self._read_buf()
        if data is None:
            raise NoDataError('no data available from device')
        framecount = 0
        for i in range(8):
            framecount += ord(data[i]) << (i*8)
        tcnt3 = ord(data[8]) + (ord(data[9]) << 8)
        frac = tcnt3/float(self._t3_state.timer3_top)
        if frac>1:
            print('In ttriger.DeviceModel.get_framestamp(): '
                  'large fractional value in framestamp. resetting')
            frac=1
        framestamp = framecount+frac
        if full_output:
            results = framestamp, framecount, tcnt3
        else:
            results = framestamp
        return results

    def get_analog_input_buffer_rawLE(self):
        if not self.real_device:
            outbuf = np.array([],dtype='<u2') # unsigned 2 byte little endian
            return outbuf
        EP_LEN = 256
        INPUT_BUFFER = ctypes.create_string_buffer(EP_LEN)

        bufs = []
        got_bytes = False
        timeout = 50 # msec
        while 1:
            # keep pumping until no more data
            try:
                with self._lock:
                    n_bytes = usb.bulk_read(self._libusb_handle, (ENDPOINT_DIR_IN|ANALOG_EPNUM), INPUT_BUFFER, timeout)
            except usb.USBNoDataAvailableError:
                break
            n_elements = n_bytes//2
            buf = np.fromstring(INPUT_BUFFER.raw,dtype='<u2') # unsigned 2 byte little endian
            buf = buf[:n_elements]
            bufs.append(buf)
            if n_bytes < EP_LEN:
                break # don't bother waiting for data to dribble in
        if len(bufs):
            outbuf = np.hstack(bufs)
        else:
            outbuf = np.array([],dtype='<u2') # unsigned 2 byte little endian
        return outbuf

    def __t3_state_changed(self):
        # A value was assigned to self._t3_state.
        # 1. Send its contents to device
        self._send_t3_state()
        # 2. Ensure updates to it also get sent to device
        if self._t3_state is None:
            return
        self._t3_state.on_trait_change(self._send_t3_state)

    def _send_t3_state(self):
        """ensure our concept of the device's state is correct by setting it"""
        t3 = self._t3_state # shorthand
        if t3 is None:
            return
        buf = ctypes.create_string_buffer(10)
        buf[0] = chr(CAMTRIG_NEW_TIMER3_DATA)

        buf[1] = chr(t3.ocr3a//0x100)
        buf[2] = chr(t3.ocr3a%0x100)
        buf[3] = chr(t3.ocr3b//0x100)
        buf[4] = chr(t3.ocr3b%0x100)

        buf[5] = chr(t3.ocr3c//0x100)
        buf[6] = chr(t3.ocr3c%0x100)
        buf[7] = chr(t3.timer3_top//0x100) # icr3a
        buf[8] = chr(t3.timer3_top%0x100)  # icr3a

        buf[9] = chr(t3.timer3_CS_)
        self._send_buf(buf)

    def __ain_state_changed(self):
        # A value was assigned to self._ain_state.
        # 1. Send its contents to device
        self._send_ain_state()
        # 2. Ensure updates to it also get sent to device
        if self._ain_state is None:
            return
        self._ain_state.on_trait_change(self._send_ain_state)

    def _send_ain_state(self):
        """ensure our concept of the device's state is correct by setting it"""
        ain_state = self._ain_state # shorthand
        if ain_state is None:
            return
        if ain_state.AIN_running:
            # analog_cmd_flags
            channel_list = 0
            if ain_state.AIN0_enabled:
                channel_list |= ENABLE_ADC_CHAN0
            if ain_state.AIN1_enabled:
                channel_list |= ENABLE_ADC_CHAN1
            if ain_state.AIN2_enabled:
                channel_list |= ENABLE_ADC_CHAN2
            if ain_state.AIN3_enabled:
                channel_list |= ENABLE_ADC_CHAN3
            analog_cmd_flags = ADC_START_STREAMING | channel_list
            analog_sample_bits = ain_state.adc_prescaler_ | (ain_state.downsample_bits<<3)
        else:
            analog_cmd_flags = ADC_STOP_STREAMING
            analog_sample_bits = 0

        buf = ctypes.create_string_buffer(3)
        buf[0] = chr(CAMTRIG_AIN_SERVICE)
        buf[1] = chr(analog_cmd_flags)
        buf[2] = chr(analog_sample_bits)
        self._send_buf(buf)

    def enter_dfu_mode(self):
        buf = ctypes.create_string_buffer(1)
        buf[0] = chr(CAMTRIG_ENTER_DFU)
        self._send_buf(buf)

    def _do_single_frame_pulse_fired(self):
        buf = ctypes.create_string_buffer(1)
        buf[0] = chr(CAMTRIG_DO_TRIG_ONCE)
        self._send_buf(buf)

    def _ext_trig1_fired(self):
        buf = ctypes.create_string_buffer(2)
        buf[0] = chr(CAMTRIG_SET_EXT_TRIG)
        buf[1] = chr(EXT_TRIG1)
        self._send_buf(buf)

    def _ext_trig2_fired(self):
        buf = ctypes.create_string_buffer(2)
        buf[0] = chr(CAMTRIG_SET_EXT_TRIG)
        buf[1] = chr(EXT_TRIG2)
        self._send_buf(buf)

    def _ext_trig3_fired(self):
        buf = ctypes.create_string_buffer(2)
        buf[0] = chr(CAMTRIG_SET_EXT_TRIG)
        buf[1] = chr(EXT_TRIG3)
        self._send_buf(buf)

    def _reset_framecount_A_fired(self):
        buf = ctypes.create_string_buffer(1)
        buf[0] = chr(CAMTRIG_RESET_FRAMECOUNT_A)
        self._send_buf(buf)

    def _reset_AIN_overflow_fired(self):
        buf = ctypes.create_string_buffer(3)
        buf[0] = chr(CAMTRIG_AIN_SERVICE)
        buf[1] = chr(ADC_RESET_AIN)
        # 3rd byte doesn't matter
        self._send_buf(buf)

    def _send_buf(self,buf):
        if not self.real_device:
            return
        with self._lock:
            val = usb.bulk_write(self._libusb_handle, 0x06, buf, 9999)

    def _read_buf(self):
        if not self.real_device:
            return None
        buf = ctypes.create_string_buffer(16)
        timeout = 1000
        with self._lock:
            try:
                val = usb.bulk_read(self._libusb_handle, 0x82, buf, timeout)
            except usb.USBNoDataAvailableError:
                return None
        return buf

    def _open_device(self):
        require_trigger = int(os.environ.get('REQUIRE_TRIGGER','1'))
        if require_trigger:

            usb.init()
            if not usb.get_busses():
                usb.find_busses()
                usb.find_devices()

            busses = usb.get_busses()

            found = False
            for bus in busses:
                for dev in bus.devices:
                    debug('idVendor: 0x%04x idProduct: 0x%04x'%
                          (dev.descriptor.idVendor,dev.descriptor.idProduct))
                    if (dev.descriptor.idVendor == 0x1781 and
                        dev.descriptor.idProduct == 0x0BAF):
                        found = True
                        break
                if found:
                    break
            if not found:
                raise RuntimeError("Cannot find device. (Perhaps run with "
                                   "environment variable REQUIRE_TRIGGER=0.)")
        else:
            self.real_device = False
            return
        with self._lock:
            self._libusb_handle = usb.open(dev)

            manufacturer = usb.get_string_simple(self._libusb_handle,dev.descriptor.iManufacturer)
            product = usb.get_string_simple(self._libusb_handle,dev.descriptor.iProduct)
            serial = usb.get_string_simple(self._libusb_handle,dev.descriptor.iSerialNumber)

            assert manufacturer == 'Strawman', 'Wrong manufacturer: %s'%manufacturer
            valid_product = 'Camera Trigger 1.0'
            if product == valid_product:
                self.FOSC = 8000000.0
            elif product.startswith('Camera Trigger 1.01'):
                osc_re = r'Camera Trigger 1.01 \(F_CPU = (.*)\)\w*'
                match = re.search(osc_re,product)
                fosc_str = match.groups()[0]
                if fosc_str.endswith('UL'):
                    fosc_str = fosc_str[:-2]
                self.FOSC = float(fosc_str)
            else:
                errmsg = 'Expected product "%s", but you have "%s"'%(
                    valid_product,product)
                if self.ignore_version_mismatch:
                    print 'WARNING:',errmsg
                else:
                    raise ValueError(errmsg)

            interface_nr = 0
            if hasattr(usb,'get_driver_np'):
                # non-portable libusb extension
                name = usb.get_driver_np(self._libusb_handle,interface_nr)
                if name != '':
                    usb.detach_kernel_driver_np(self._libusb_handle,interface_nr)

            if dev.descriptor.bNumConfigurations > 1:
                debug("WARNING: more than one configuration, choosing first")

            config = dev.config[0]
            usb.set_configuration(self._libusb_handle, config.bConfigurationValue)
            usb.claim_interface(self._libusb_handle, interface_nr)
        self.real_device = True

class DeviceModelAnyVersion(DeviceModel):
    """Allow opening of device when firmware version does not match expectations

    This should only be done in special cases, such as to upgrade the firmware.
    """
    ignore_version_mismatch = traits.Bool(True, transient=True)

def enter_dfu_mode():
    import sys
    from optparse import OptionParser
    usage = '%prog [options]'
    parser = OptionParser(usage)
    parser.add_option("--ignore-version-mismatch", action='store_true',
                      default=False)
    (options, args) = parser.parse_args()
    if options.ignore_version_mismatch:
        cls = DeviceModelAnyVersion
    else:
        cls = DeviceModel
    dev = cls()
    dev.enter_dfu_mode()

def check_device():
    dev = DeviceModel()
    dev.led1 = False
    dev.led2 = False
    dev.led3 = False
    dev.led4 = False

    sleep_dur = 0.01
    time.sleep(sleep_dur)
    dev.led1 = True
    for i in range(2):
        time.sleep(sleep_dur)
        dev.led1 = False
        dev.led2 = True

        time.sleep(sleep_dur)
        dev.led2 = False
        dev.led3 = True

        time.sleep(sleep_dur)
        dev.led3 = False
        dev.led4 = True

        time.sleep(sleep_dur)
        dev.led4 = False
        dev.led1 = True
    dev.led1 = False

def set_frequency():
    usage = '%prog [options]'
    parser = OptionParser(usage)

    parser.add_option("--freq", type="float",
                      metavar="FREQ")
    parser.add_option("--ignore-version-mismatch", action='store_true',
                      default=False)
    (options, args) = parser.parse_args()
    if len(args):
        parser.print_help()
        sys.exit(1)

    if options.freq is None:
        print >> sys.stderr, ('No requency specified. Use '
                              '--freq=XX where XX is the frequency')
        sys.exit(1)

    if options.ignore_version_mismatch:
        cls = DeviceModelAnyVersion
    else:
        cls = DeviceModel
    dev = cls()

    dev.set_frames_per_second_approximate( 0.0 )
    dev.reset_framecount_A = True
    dev.set_frames_per_second_approximate( options.freq )
    t_start = time.time()
    n_secs = 5.0
    t_stop = t_start+n_secs
    while time.time() < t_stop:
        # busy wait for accurate timing
        pass
    framestamp = dev.get_framestamp()
    fps = framestamp/n_secs
    #print 'framecount, tct3,fps',framecount, tcnt3,fps
    theory = dev.frames_per_second_actual
    measured = fps
    print 'theoretical fps',theory
    print 'measured fps',measured

def get_time():
    if sys.platform.startswith('win'):
        return time.clock()
    else:
        return time.time()

if __name__=='__main__':
    dm=DeviceModel()
