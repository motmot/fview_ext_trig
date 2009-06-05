#emacs, this is -*-Python-*- mode
import numpy as np
cimport numpy as np
import sys
import cython

# The wordstream is little-endian and we assume the processor is, too.
assert sys.byteorder=='little', 'This module assumes a little-endian system'

cdef extern from "stdint.h":
     ctypedef unsigned char uint8_t
     ctypedef unsigned short uint16_t
     ctypedef long int64_t

cdef extern from "decode.h":
     ctypedef struct decode_return_t:
          uint8_t N
          uint8_t channel
          uint16_t sample
          uint8_t prev_sample_lsbs
          int64_t framecount
          uint16_t tcnt3
          uint8_t did_overflow

     ctypedef enum decode_err_t:
          DECODE_NO_ERROR
          DECODE_NOT_IMPLEMENTED

     cdef decode_err_t decode_bytestream( uint16_t* buf, uint16_t len, decode_return_t *result) nogil

cdef extern from "string.h":
     ctypedef int size_t

@cython.boundscheck(False)
def process(np.ndarray[uint16_t, ndim=1] buf, int check_LSB_errors=1 ):
     """decode an ADC wordstream

     This will read until a framecount/tcnt pair is found or the
     buffer is exhausted, whichever comes first.

     If a framecount/tcnt pair is encountered, processing will stop,
     and the framecount/tcnt pair can be correctly assumed to be from
     the moment immediately following the last sample.

     returns
     -------
     N : integer
         the number of elements of the wordstream that were processed
     samples : array
         the sample data (uint16)
     channels : array
         the channels of the sample data
     did_overflow : boolean
         Whether the USB device overflowed its internal buffer,
         indicating that data has been lost.
     framestamp : None or tuple of (framecount,tcnt)
         None if not present. Otherwise, a tuple indicating the moment
         the last sample ended.

     """
     cdef decode_return_t inner_loop_result

     cdef int cum_samples_done
     cdef decode_err_t err=DECODE_NO_ERROR
     cdef int N=0
     cdef int sampno=0
     cdef char* data_start=buf.data
     cdef size_t stride0=buf.strides[0]
     cdef uint16_t* sample_ptr
     cdef uint8_t* channel_ptr
     cdef size_t data_len=buf.shape[0]
     cdef double alloced_len=data_len
     cdef np.ndarray[uint16_t,ndim=1] samples
     cdef np.ndarray[uint8_t,ndim=1] channels
     cdef np.ndarray[uint8_t,ndim=1] prev_sample_lsbs

     # pesimistically make length maximum possible -- trim later
     samples = np.empty((data_len,),dtype=np.uint16)
     prev_sample_lsbs = np.empty((data_len,),dtype=np.uint8)
     channels = np.empty((data_len,),dtype=np.uint8)
     sample_ptr = <uint16_t*>samples.data
     channel_ptr = <uint8_t*>channels.data

     with nogil:
          while data_len>0:
               err = decode_bytestream( <uint16_t*>data_start, data_len, &inner_loop_result )
               if err!=DECODE_NO_ERROR:
                    break
               if (inner_loop_result.N)==0:
                    break
               data_start += (stride0*inner_loop_result.N)
               data_len -= inner_loop_result.N
               N += inner_loop_result.N
               sample_ptr[sampno] = inner_loop_result.sample
               channel_ptr[sampno] = inner_loop_result.channel
               prev_sample_lsbs[sampno] = inner_loop_result.prev_sample_lsbs
               sampno+=1
               if inner_loop_result.N==6: # this is true iff a framecount is found
                    break
     if err!=DECODE_NO_ERROR:
          if err==DECODE_NOT_IMPLEMENTED:
               raise NotImplementedError('decode.c not implemented error')
          else:
               raise RuntimeError('unknown error')

     # trim length of output arrays to only the number of samples aquired
     samples = samples[:sampno]
     channels = channels[:sampno]

     if alloced_len > 5000 and (<double>sampno)/alloced_len < 0.8:
          # Copy into smaller array and deallocate original memory.
          samples = np.array(samples,copy=True)
          channels = np.array(channels,copy=True)

     prev_sample_lsbs = prev_sample_lsbs[:sampno]
     if check_LSB_errors and sampno>1:
          # perform check on least significant bits
          test_samps = (samples[:-1] & 0x03)
          test_lsbs = prev_sample_lsbs[1:]
          bad_cond = test_samps!=test_lsbs
          if np.any(bad_cond):
               raise ValueError('Corrupt USB data: LSBs do not match')

     framestamp = None
     if inner_loop_result.N==6: # this is true iff a framecount is found
          framestamp = (inner_loop_result.framecount, inner_loop_result.tcnt3)
     result = (N,samples,channels,bool(inner_loop_result.did_overflow),framestamp)
     return result

