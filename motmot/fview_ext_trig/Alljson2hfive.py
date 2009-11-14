import sys,os
import tables
import numpy as np
# Use simplejson or Python 2.6 json, prefer simplejson.
try:
    import simplejson as json
except ImportError:
    import json

import data_format

AnalogInputWordstreamDescription = data_format.AnalogInputWordstreamDescription
AnalogInputWordstream_dtype =  tables.Description(
    AnalogInputWordstreamDescription().columns)._v_nestedDescr

TimeDataDescription = data_format.TimeDataDescription
TimeData_dtype =  tables.Description(
    TimeDataDescription().columns)._v_nestedDescr

def doit(filename):
    base,ext = os.path.splitext(filename)
    output_fname = base+'.h5'
    print 'converting %s to %s'%(filename,output_fname)
    contents = open(filename).read()
    input = json.loads(contents)

    h5 = tables.openFile( output_fname, mode='w')
    stream_ain_table = h5.createTable(
        h5.root,'ain_wordstream',AnalogInputWordstreamDescription,
        "AIN data")

    stream_ain_table.attrs.channel_names = input["ain_wordstream"]["channel_names"]
    stream_ain_table.attrs.Vcc = input["ain_wordstream"]["Vcc"]
    wordstream = input["ain_wordstream"]["data"]
    buf = np.array(wordstream,dtype=np.uint16)
    recarray = np.rec.array( [buf], dtype=AnalogInputWordstream_dtype)
    stream_ain_table.append( recarray )
    stream_ain_table.flush()

    stream_time_data_table = h5.createTable(
                h5.root,'time_data',TimeDataDescription,
                "time data")
    stream_time_data_table.attrs.top = input["time_data"]["top"]
    tsfss = input["time_data"]["timestamps_framestamps"]
    bigarr = np.array(tsfss)
    timestamps = bigarr[:,0]
    framestamps = bigarr[:,1]
    recarray = np.rec.array( [timestamps,framestamps], dtype=TimeData_dtype)
    stream_time_data_table.append( recarray )
    stream_time_data_table.flush()
    h5.close()

def main():
    dir_name = sys.argv[1]
    fileList=os.listdir(dir_name)
    
    for file in fileList:
         fileExt = os.path.splitext(file)[-1]
         if '.json' == fileExt:
            filename =  os.path.join(dir_name,file)
            doit(filename)

if __name__=='__main__':
    main()
