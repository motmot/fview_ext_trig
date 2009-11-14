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

    ax = pylab.subplot(2,1,1)
    ax.plot(time_data['timestamp'],
            time_data['framestamp'],'o',label='data')

    interp = time_data['framestamp']*gain + offset
    ax.plot(interp,time_data['framestamp'],'-',label='fit')

    ax.set_ylabel('framestamp')
    if options.timestamps:
        ax.xaxis.set_major_formatter(
            mticker.FuncFormatter(format_date))
    else:
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))
    ax.legend()

    ax = pylab.subplot(2,1,2,sharey=ax)
    ax.plot(time_data['timestamp']-interp,
            time_data['framestamp'],'-',label='residuals')
    ax.set_xlabel('residuals')

    ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%s"))

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

