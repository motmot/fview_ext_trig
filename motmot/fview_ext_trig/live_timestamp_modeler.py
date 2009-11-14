import pkg_resources
import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group, TextEditor, ListEditor, \
     InstanceEditor, Spring
import ttrigger
import time
import numpy as np
import cDecode
from enthought.chaco.chaco_plot_editor import ChacoPlotItem
import warnings

class ImpreciseMeasurementError(Exception):
    pass

class AnalogDataOverflowedError(Exception):
    pass

def myformat(x):
    if x is None:
        return ''
    return "%.5g"%x

def myformat2(x):
    if x is None:
        return ''
    return "%.3f"%x

class LiveTimestampModeler(traits.HasTraits):
    _trigger_device = traits.Instance(ttrigger.DeviceModel)

    sync_interval = traits.Float(2.0)
    has_ever_synchronized = traits.Bool(False,transient=True)

    frame_offset_changed = traits.Event

    timestamps_framestamps = traits.Array(
        shape=(None,2),
        dtype=np.float)

    timestamp_data = traits.Any()
    block_activity = traits.Bool(False,transient=True)

    synchronize = traits.Button(label='Synchronize')
    synchronizing_info = traits.Any(None)

    gain_offset_residuals = traits.Property(
        depends_on = ['timestamps_framestamps'] )

    residual_error = traits.Property(
        depends_on = 'gain_offset_residuals' )

    gain = traits.Property(
        depends_on = 'gain_offset_residuals' )

    offset = traits.Property(
        depends_on = 'gain_offset_residuals' )

    frame_offsets = traits.Dict()
    last_frame = traits.Dict()

    view_time_model_plot = traits.Button

    traits_view = View(Group(Item( name='gain',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat),
                                   ),
                             Item( name='offset',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat2),
                                   ),
                             Item( name='residual_error',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat),
                                   ),
                             Item( 'synchronize', show_label = False ),
                             Item( 'view_time_model_plot', show_label = False ),
                             ),
                       title = 'Timestamp modeler',
                       )

    def _block_activity_changed(self):
        if self.block_activity:
            print('Do not change frame rate or AIN parameters. '
                  'Automatic prevention of doing '
                  'so is not currently implemented.')
        else:
            print('You may change frame rate again')

    def _view_time_model_plot_fired(self):
        raise NotImplementedError('')

    def _synchronize_fired(self):
        if self.block_activity:
            print('Not synchronizing because activity is blocked. '
                  '(Perhaps because you are saving data now.')
            return

        orig_fps = self._trigger_device.frames_per_second_actual
        self._trigger_device.set_frames_per_second_approximate( 0.0 )
        self._trigger_device.reset_framecount_A = True # trigger reset event
        self.synchronizing_info = (time.time()+self.sync_interval+0.1,
                                   orig_fps)

    @traits.cached_property
    def _get_gain( self ):
        result = self.gain_offset_residuals
        if result is None:
            # not enought data
            return None
        gain,offset,residuals = result
        return gain

    @traits.cached_property
    def _get_offset( self ):
        result = self.gain_offset_residuals
        if result is None:
            # not enought data
            return None
        gain,offset,residuals = result
        return offset

    @traits.cached_property
    def _get_residual_error( self ):
        result = self.gain_offset_residuals
        if result is None:
            # not enought data
            return None
        gain,offset,residuals = result
        if residuals is None or len(residuals)==0:
            # not enought data
            return None
        assert len(residuals)==1
        return residuals[0]

    @traits.cached_property
    def _get_gain_offset_residuals( self ):
        if self.timestamps_framestamps is None:
            return None

        timestamps = self.timestamps_framestamps[:,0]
        framestamps = self.timestamps_framestamps[:,1]

        if len(timestamps)<2:
            return None

        # like model_remote_to_local in flydra.analysis
        remote_timestamps = framestamps
        local_timestamps = timestamps

        a1=remote_timestamps[:,np.newaxis]
        a2=np.ones( (len(remote_timestamps),1))
        A = np.hstack(( a1,a2))
        b = local_timestamps[:,np.newaxis]
        x,resids,rank,s = np.linalg.lstsq(A,b)

        gain = x[0,0]
        offset = x[1,0]
        return gain,offset,resids

    def set_trigger_device(self,device):
        self._trigger_device = device
        self._trigger_device.on_trait_event(self._on_trigger_device_reset_AIN_overflow_fired,
                                            name='reset_AIN_overflow')

    def _on_trigger_device_reset_AIN_overflow_fired(self):
        self.ain_overflowed = 0

    def _get_now_framestamp(self,max_error_seconds=0.003,full_output=False):
        count = 0
        while count <= 10:
            now1 = time.time()
            try:
                results = self._trigger_device.get_framestamp(full_output=full_output)
            except ttrigger.NoDataError:
                raise ImpreciseMeasurementError(
                    'no data available')
            now2 = time.time()
            if full_output:
                framestamp, framecount, tcnt = results
            else:
                framestamp = results
            count += 1
            measurement_error = abs(now2-now1)
            if framestamp%1.0 < 0.1:
                warnings.warn('workaround of TCNT race condition on MCU...')
                continue
            if measurement_error < max_error_seconds:
                break
            time.sleep(0.01) # wait 10 msec before trying again
        if not measurement_error < max_error_seconds:
            raise ImpreciseMeasurementError(
                'could not obtain low error measurement')
        if framestamp%1.0 < 0.1:
            raise ImpreciseMeasurementError(
                'workaround MCU bug')

        now = (now1+now2)*0.5
        if full_output:
            results = now, framestamp, now1, now2, framecount, tcnt
        else:
            results = now, framestamp
        return results

    def clear_samples(self,call_update=True):
        self.timestamps_framestamps = np.empty( (0,2))
        if call_update:
            self.update()

    def update(self,return_last_measurement_info=False):
        """call this function fairly often to pump information from the USB device"""
        if self.synchronizing_info is not None:
            done_time, orig_fps = self.synchronizing_info
            # suspended trigger pulses to re-synchronize
            if time.time() >= done_time:
                # we've waited the sync duration, restart
                self._trigger_device.set_frames_per_second_approximate(orig_fps)
                self.clear_samples(call_update=False) # avoid recursion
                self.synchronizing_info = None
                self.has_ever_synchronized = True

        results = self._get_now_framestamp(full_output=return_last_measurement_info)
        now, framestamp = results[:2]
        if return_last_measurement_info:
            start_timestamp, stop_timestamp, framecount, tcnt = results[2:]

        self.timestamps_framestamps = np.vstack((self.timestamps_framestamps,
                                                 [now,framestamp]))

        # If more than 100 samples,
        if len(self.timestamps_framestamps) > 100:
            # keep only the most recent 50.
            self.timestamps_framestamps = self.timestamps_framestamps[-50:]

        if return_last_measurement_info:
            return start_timestamp, stop_timestamp, framecount, tcnt

    def get_frame_offset(self,id_string):
        return self.frame_offsets[id_string]

    def register_frame(self, id_string, framenumber, frame_timestamp, full_output=False):
        """note that a frame happened and return start-of-frame time"""

        # This may get called from another thread (e.g. the realtime
        # image processing thread).

        # An important note about locking and thread safety: This code
        # relies on the Python interpreter to lock data structures
        # across threads. To do this internally, a lock would be made
        # for each variable in this instance and acquired before each
        # access. Because the data structures are simple Python
        # objects, I believe the operations are atomic and thus this
        # function is OK.

        if frame_timestamp is not None:
            last_frame_timestamp = self.last_frame.get(id_string,-np.inf)
            this_interval = frame_timestamp-last_frame_timestamp

            did_frame_offset_change = False
            if this_interval > self.sync_interval:
                if self.block_activity:
                    print('changing frame offset is disallowed, but you attempted to do it. ignoring.')
                else:
                    # re-synchronize camera

                    # XXX need to figure out where frame offset of two comes from:
                    self.frame_offsets[id_string] = framenumber-2
                    did_frame_offset_change = True

            self.last_frame[id_string] = frame_timestamp

            if did_frame_offset_change:
                self.frame_offset_changed = True # fire any listeners

        result = self.gain_offset_residuals
        if result is None:
            # not enough data
            if full_output:
                results = None, None, did_frame_offset_change
            else:
                results = None
            return results

        gain,offset,residuals = result
        corrected_framenumber = framenumber-self.frame_offsets[id_string]
        trigger_timestamp = corrected_framenumber*gain + offset

        if full_output:
            results = trigger_timestamp, corrected_framenumber, did_frame_offset_change
        else:
            results = trigger_timestamp
        return results

class AnalogInputChannelViewer(traits.HasTraits):
    index = traits.Array(dtype=np.float)
    data = traits.Array(dtype=np.float)
    device_channel_num = traits.Int(label='ADC')

    traits_view = View(
        Group(
                Item('device_channel_num',style='readonly'),
        ChacoPlotItem('index','data',
                      #x_label = "elapsed time (sec)",
                      x_label = "index",
                      y_label = "data",
                      show_label=False,
                      y_bounds=(-1,2**10+1),
                      y_auto=False,
                      resizable=True,
                      title = 'Analog input',
                      ),
        ),
        resizable=True,
        width=800, height=200,
        )

class AnalogInputViewer(traits.HasTraits):
    channels = traits.List
    usb_device_number2index = traits.Property(depends_on='channels')

    @traits.cached_property
    def _get_usb_device_number2index(self):
        result = {}
        for i,channel in enumerate(self.channels):
            result[channel.device_channel_num]=i
        return result

    traits_view = View(
        Group(
        Item('channels',style='custom',
             editor=ListEditor(rows = 3,
                               editor=InstanceEditor(),
                               style='custom'),
             resizable=True,
             )),
        resizable=True,
        width=800, height=600,
        title='Analog Input',
        )
    def __init__(self,*args,**kwargs):
        super(AnalogInputViewer,self).__init__(*args,**kwargs)
        for usb_channel_num in [0,1,2,3]:
            self.channels.append(AnalogInputChannelViewer(
                device_channel_num=usb_channel_num))

class LiveTimestampModelerWithAnalogInput(LiveTimestampModeler):
    view_AIN = traits.Button(label='view analog input (AIN)')
    viewer = traits.Instance(AnalogInputViewer)

    # the actual analog data (as a wordstream)
    ain_data_raw = traits.Array(dtype=np.uint16,transient=True)
    old_data_raw = traits.Array(dtype=np.uint16,transient=True)

    timer3_top = traits.Property() # necessary to calculate precise timestamps for AIN data
    channel_names = traits.Property()
    Vcc = traits.Property(depends_on='_trigger_device')
    ain_overflowed = traits.Int(0,transient=True) # integer for display (boolean readonly editor ugly)

    ain_wordstream_buffer = traits.Any()
    traits_view = View(Group(Item( 'synchronize', show_label = False ),
                             Item( 'view_time_model_plot', show_label = False ),
                             Item('ain_overflowed',style='readonly'),
                             Item( name='gain',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat),
                                   ),
                             Item( name='offset',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat2),
                                   ),
                             Item( name='residual_error',
                                   style='readonly',
                                   editor=TextEditor(evaluate=float,
                                                     format_func=myformat),
                                   ),
                             Item( 'view_AIN', show_label = False ),
                             ),
                       title = 'Timestamp modeler',
                       )

    @traits.cached_property
    def _get_Vcc(self):
        return self._trigger_device.Vcc

    def _get_timer3_top(self):
        return self._trigger_device.timer3_top

    def _get_channel_names(self):
        return self._trigger_device.enabled_channel_names

    def update_analog_input(self):
        """call this function frequently to avoid overruns"""
        new_data_raw = self._trigger_device.get_analog_input_buffer_rawLE()
        data_raw = np.hstack((new_data_raw,self.old_data_raw))
        self.ain_data_raw = new_data_raw
        newdata_all = []
        chan_all = []
        any_overflow = False
        #cum_framestamps = []
        while len(data_raw):
            result = cDecode.process( data_raw )
            (N,samples,channels,did_overflow,framestamp)=result
            if N==0:
                # no data was able to be processed
                break
            data_raw = data_raw[N:]
            newdata_all.append( samples )
            chan_all.append( channels )
            if did_overflow:
                any_overflow = True
            # Save framestamp data.
            # This is not done yet:
            ## if framestamp is not None:
            ##     cum_framestamps.append( framestamp )
        self.old_data_raw = data_raw # save unprocessed data for next run

        if any_overflow:
            # XXX should move to logging the error.
            self.ain_overflowed = 1
            raise AnalogDataOverflowedError()

        if len(chan_all)==0:
            # no data
            return
        chan_all=np.hstack(chan_all)
        newdata_all=np.hstack(newdata_all)
        USB_channel_numbers = np.unique(chan_all)
        #print len(newdata_all),'new samples on channels',USB_channel_numbers

        ## F_OSC = 8000000.0 # 8 MHz
        ## adc_prescaler = 128
        ## downsample = 20 # maybe 21?
        ## n_chan = 3
        ## F_samp = F_OSC/adc_prescaler/downsample/n_chan
        ## dt=1.0/F_samp
        ## ## print '%.1f Hz sampling. %.3f msec dt'%(F_samp,dt*1e3)
        ## MAXLEN_SEC=0.3
        ## #MAXLEN = int(MAXLEN_SEC/dt)
        MAXLEN = 5000 #int(MAXLEN_SEC/dt)
        ## ## print 'MAXLEN',MAXLEN
        ## ## print

        for USB_chan in USB_channel_numbers:
            vi=self.viewer.usb_device_number2index[USB_chan]
            cond = chan_all==USB_chan
            newdata = newdata_all[cond]

            oldidx = self.viewer.channels[vi].index
            olddata = self.viewer.channels[vi].data

            if len(oldidx):
                baseidx = oldidx[-1]+1
            else:
                baseidx = 0.0
            newidx = np.arange(len(newdata),dtype=np.float)+baseidx

            tmpidx = np.hstack( (oldidx,newidx) )
            tmpdata = np.hstack( (olddata,newdata) )

            if len(tmpidx) > MAXLEN:
                # clip to MAXLEN
                self.viewer.channels[vi].index = tmpidx[-MAXLEN:]
                self.viewer.channels[vi].data = tmpdata[-MAXLEN:]
            else:
                self.viewer.channels[vi].index = tmpidx
                self.viewer.channels[vi].data = tmpdata

    def _view_AIN_fired(self):
        self.viewer.edit_traits()
