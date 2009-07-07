import pkg_resources
import pylab
import numpy as np

import sys
import tables
import motmot.fview_ext_trig.easy_decode as easy_decode

import matplotlib.ticker as mticker
from optparse import OptionParser
import pytz, datetime, time
pacific = pytz.timezone('US/Pacific')

def format_date(x, pos=None):
    return str(datetime.datetime.fromtimestamp(x,pacific))

def doit(fname,options):
    fname = sys.argv[1]
    h5 = tables.openFile(fname,mode='r')

    time_data=h5.root.time_data[:]
    gain,offset,resids = easy_decode.get_gain_offset_resids(
        input=time_data['framestamp'],
        output=time_data['timestamp'])
    top = h5.root.time_data.attrs.top

    wordstream = h5.root.ain_wordstream[:]
    wordstream = wordstream['word'] # extract into normal numpy array
    print 'wordstream.shape',wordstream.shape

    r=easy_decode.easy_decode(wordstream,gain,offset,top)
    chans = r.dtype.fields.keys()
    chans.sort()
    chans.remove('timestamps')

    names = h5.root.ain_wordstream.attrs.channel_names
    if hasattr(h5.root.ain_wordstream.attrs,'Vcc'):
        Vcc = h5.root.ain_wordstream.attrs.Vcc
        print 'Vcc read from file at',Vcc
    else:
        Vcc=3.3
        print 'Vcc guessed at',Vcc
    ADCmax = (2**10)-1
    analog_gain = Vcc/ADCmax

    n_adc_samples = len(r['timestamps'])
    dt = r['timestamps'][1]-r['timestamps'][0]
    samps_per_sec = 1.0/dt
    adc_duration = n_adc_samples*dt
    print '%d samples at %.1f samples/sec = %.1f seconds'%(n_adc_samples,
                                                           samps_per_sec,
                                                           adc_duration)
    t0 = r['timestamps'][0]
    total_duration = adc_duration

    if options.timestamps:
        t_offset = 0
        t_plot_start = t0
    else:
        t_offset = t0
        t_plot_start = 0

    ax=None
    for i in range(len(chans)):
        ax = pylab.subplot(len(chans),1,i+1,sharex=ax)
        try:
            label = names[int(chans[i])]
        except Exception, err:
            print 'ERROR: ingnoring exception %s'%(err,)
            label = 'channel %s'%chans[i]
        ax.plot(r['timestamps']-t_offset,r[chans[i]]*analog_gain,
                label=label)
        ax.set_ylabel('V')
        ax.legend()
        if options.timestamps:
            ax.xaxis.set_major_formatter(
                mticker.FuncFormatter(format_date))
        else:
            ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))
        ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))
    ax.set_xlabel('Time (sec)')
    ax.set_xlim((t_plot_start,t_plot_start+total_duration))
    if options.timestamps:
        pylab.gcf().autofmt_xdate()

    pylab.show()

def main():
    usage = '%prog [options] FILE'

    parser = OptionParser(usage)

    parser.add_option("--timestamps", action='store_true',
                      default=False)

    (options, args) = parser.parse_args()
    fname = args[0]
    doit(fname,options)

if __name__=='__main__':
    main()

