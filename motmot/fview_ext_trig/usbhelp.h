#include <libusb-1.0/libusb.h>

void xx(struct libusb_transfer* transfer_p);

void usbhelp_libusb_set_iso_packet_lengths(struct libusb_transfer *transfer_p, unsigned int length);

int usbhelp_get_actual_iso_size( struct libusb_transfer*transfer_p, int* cumsize);
int usbhelp_copy_transfer_packets( struct libusb_transfer*transfer_p, char *buf, int sz );
