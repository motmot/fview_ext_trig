import cDecode
import numpy as np
import scipy

def get_gain_offset_resids(input=None,output=None):

    a1=input[:,np.newaxis]
    a2=np.ones( (len(input),1))
    A = np.hstack(( a1,a2))
    b = output[:,np.newaxis]
    x,resids,rank,s = np.linalg.lstsq(A,b)

    gain = x[0,0]
    offset = x[1,0]
    return gain,offset,resids

def easy_decode(data_raw,gain,offset,top):

    newdata_all = []
    chan_all = []
    any_overflow = False
    cum_timestamps = []
    timestamp_idxs = []
    current_index = 0

    prevdata = None
    prevchan = None

    # Decode all data in this loop
    while len(data_raw):
        result = cDecode.process( data_raw )
        (N,samples,channels,did_overflow,framestamp)=result
        if N==0:
            # no data was able to be processed
            print 'no data break'
            break
        data_raw = data_raw[N:]
        newdata_all.append( samples )
        chan_all.append( channels )
        current_index += len(samples)

        if framestamp is not None:
            frame, tcnt = framestamp
            f = frame + float(tcnt)/float(top)
            cum_timestamps.append(f*gain+offset)
            timestamp_idxs.append(current_index-1) # index of last sample
        if did_overflow:
            any_overflow = True

    newdata_all = np.hstack(newdata_all)
    chan_all = np.hstack(chan_all)

    # Now sanitize the results

    cum_timestamps = np.array(cum_timestamps)
    timestamp_idxs = np.array(timestamp_idxs)
    # XXX this assumes that no samples are missing... do piecewise if not true.
    gain2,offset2,resids2=get_gain_offset_resids(input=timestamp_idxs,
                                                 output=cum_timestamps)
    timestamps_all = np.arange(len(newdata_all))*gain2+offset2
    USB_channels = np.unique(chan_all).tolist()
    USB_channels.sort()

    arrays = []
    names = []
    shortest = np.inf
    timestamps = None
    for chan in USB_channels:
        cond = chan_all==chan
        if timestamps is None:
            # Ignore the minute timestamp differences between channels
            timestamps = timestamps_all[cond]
        this_data = newdata_all[cond]

        shortest = min(shortest,len(this_data))

        arrays.append( this_data )
        names.append(str(chan))

    arrays.append(timestamps)
    names.append('timestamps')

    for i in range(len(arrays)):
        if len(arrays[i])> shortest:
            arrays[i] = arrays[i][:shortest] # trim all to same length
    r = np.core.records.fromarrays(arrays,names=names)
    return r
