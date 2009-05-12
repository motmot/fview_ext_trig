import cDecode
import numpy as np

def test_decode_stalled():
    a = np.array( [0x04, # 0 sample (chan 0), framecount coming
                   ], dtype=np.uint16)
    result = cDecode.process( a )
    (N,samples,channels,did_overflow,framestamp)=result
    assert N==0
    assert len(samples)==0
    assert len(channels)==0
    assert did_overflow==0
    assert framestamp is None

def test_decode1():
    a = np.array( [0x00, # 0 sample (chan 0)
                   0x04, # 0 sample (chan 0), framecount coming
                   0x01, # framecount word 1
                   0x00, # framecount word 2
                   0x00, # framecount word 3
                   0x00, # framecount word 4
                   0x02, # tcnt word
                   0x00, # 0 sample (chan 0)
                   ], dtype=np.uint16)
    result = cDecode.process( a )
    (N,samples,channels,did_overflow,framestamp)=result
    assert N==7
    expected_samples = np.array([0,0],dtype=np.uint16)
    expected_channels = np.array([0,0],dtype=np.uint8)

    assert np.allclose(samples,expected_samples)
    assert samples.shape==expected_samples.shape
    assert samples.dtype==expected_samples.dtype

    assert np.allclose(channels,expected_channels)
    assert channels.shape==expected_channels.shape
    assert channels.dtype==expected_channels.dtype

