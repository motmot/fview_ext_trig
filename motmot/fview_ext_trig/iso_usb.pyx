import ctypes
cimport stdlib

cdef extern from "Python.h":
    cdef void* PyLong_AsVoidPtr( object )

cdef extern from "libusb-1.0/libusb.h":
    struct libusb_device:
        pass

    struct libusb_device_handle:
        pass

    struct libusb_iso_packet_descriptor:
        unsigned int length
        unsigned int actual_length
        int status

    struct libusb_transfer:#" struct_libusb_transfer:
        libusb_device_handle * dev_handle
        #uint8_t flags
        unsigned char endpoint
        unsigned char type
        unsigned int timeout
        int status
        int length
        int actual_length
        int callback
        void* user_data
        unsigned char* buffer
        int num_iso_packets
        libusb_iso_packet_descriptor* iso_packet_desc

    #cdef void libusb_set_iso_packet_lengths( libusb_transfer*, int )
    cdef libusb_device* libusb_get_device( libusb_device_handle* )
    cdef int libusb_get_max_iso_packet_size(libusb_device*,int)
    cdef int usbhelp_get_actual_iso_size(  libusb_transfer*, int* )

cdef extern from "usbhelp.h":
    cdef void xx(libusb_transfer*)
    cdef void usbhelp_libusb_set_iso_packet_lengths(libusb_transfer*, int)

cdef void* ptr2pyx( object ctypes_ptr ):
    """convert a ctypes pointer into a Cython <void*>"""
    cdef object pyptr
    cdef void* c_void_p

    pyptr = ctypes.addressof( ctypes_ptr.contents )
    c_void_p = PyLong_AsVoidPtr( pyptr )
    return c_void_p


def get_int_ptr_value( ctypes_int_p ):
    return (<int*>ptr2pyx(ctypes_int_p))[0]

def print_transfer_info( ctypes_transfer_p ):
    cdef libusb_transfer* transfer_p
    cdef libusb_transfer transfer
    transfer_p = (<libusb_transfer*>ptr2pyx(ctypes_transfer_p))
    xx(transfer_p)
    if 1:
        return

    #transfer = transfer_p[0] # copy into heap
    print '---- start pyrex ----'
    print 'transfer_p at 0x%0x'%(<long>transfer_p,)
    print 'length',transfer_p.length
    print 'pyx num_iso_packets:',transfer_p.num_iso_packets
    print '  .num_iso_packets ',transfer_p.num_iso_packets
    print '  .iso_packet_desc ',<long>(<void*>transfer_p.iso_packet_desc)

    print '  allocated iso_packet_desc[0] at 0x%0x'%(<long> (transfer_p.iso_packet_desc),)

    print 'transfer_p.iso_packet_desc.length',transfer_p.iso_packet_desc.length
    #print '** set'
    #libusb_set_iso_packet_lengths( transfer_p, 256 )
    #print 'transfer_p.iso_packet_desc.length',transfer_p.iso_packet_desc.length
    print '---- stop pyrex ----'

def libusb_set_iso_packet_lengths( ctypes_transfer_p, int length ):
    cdef libusb_transfer* transfer_p
    transfer_p = (<libusb_transfer*>ptr2pyx(ctypes_transfer_p))
    usbhelp_libusb_set_iso_packet_lengths( transfer_p, length )

def get_all_iso_data( ctypes_transfer_p ):
    cdef unsigned char* buf
    cdef int sz
    cdef int err
    cdef libusb_transfer* transfer_p

    transfer_p = (<libusb_transfer*>ptr2pyx(ctypes_transfer_p))
    err = usbhelp_get_actual_iso_size( transfer_p, &sz )
    print 'got size',sz
    assert err==0
    buf = <unsigned char*>stdlib.malloc(sz)
    for i in range(sz):
        buf[i] = 0
    strbuf = str(buf)
    stdlib.free(buf)
    return strbuf

cdef class IsoAinState:
    cdef libusb_device_handle* dev_handle
    cdef int EPNUM
    def __init__(self,dev_handle,int EPNUM):
        cdef libusb_device* device
        cdef int max_sz

        self.dev_handle = <libusb_device_handle*>ptr2pyx( dev_handle )
        self.EPNUM = EPNUM

        device = libusb_get_device( self.dev_handle )
        max_sz = libusb_get_max_iso_packet_size(device,
                                                self.EPNUM)

        #print 'started ain state (max_sz = %d)!'%max_sz
