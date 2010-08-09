#include <libusb-1.0/libusb.h>
#include <stdio.h>
#include <stdlib.h>

#define DEVICE_OUT_EPNUM 0x06
#define DEVICE_IN_EPNUM 0x82
#define ANALOG_IN_EPNUM 0x81

#define DEVICE_VID 0x1781
#define DEVICE_PID 0x0BAF

#define NZ(m) {								\
    if ((m)!=0) {							\
      fprintf(stderr,"result was %d not 0 at %s, line %d.\n",(m),__FILE__,__LINE__); \
      exit(1);								\
    }									\
  }

void my_callback(struct libusb_transfer *transfer) {
  int *x;

  printf("I got a callback!, actual length = %d\n",
	 transfer->actual_length);
  x = transfer->user_data;
  *x = 1;
}


void iso_callback(struct libusb_transfer *transfer) {
  int *x;
  int i,j;
  unsigned char* buf_p;
  char buf2[256];

  for (i=0; i<5; i++) {
    buf_p = libusb_get_iso_packet_buffer_simple( transfer, i );
    //memcpy(buf2,buf_p,256); // check for segfaults
    for (j=0; j<256; j++) {
      printf("0x%02x ",buf_p[i]);
    }
  }

  printf("ISO!\n");
  x = transfer->user_data;
  *x = 1;
}


int main(int argc, char **argv) {
  char *buffer;
  struct libusb_transfer *transfer;
  int iso_packets;
  libusb_device_handle *dev_handle;
  libusb_device *device;
  libusb_context *ctx;
  int* user_data;
  unsigned int timeout;
  int max_packet_size;
  libusb_transfer_cb_fn callback;
  int config;
  int n_devices;
  libusb_device **list;

  // Open the device.

  NZ(libusb_init(&ctx));
  libusb_set_debug(ctx,3);



  dev_handle = libusb_open_device_with_vid_pid(ctx, DEVICE_VID, DEVICE_PID);
  NZ(!dev_handle);


  device = libusb_get_device(dev_handle);


  iso_packets = 5;
  max_packet_size = libusb_get_max_iso_packet_size(
					 device,
					 ANALOG_IN_EPNUM);
  printf("max packet size %d\n",max_packet_size);

  printf("LIBUSB_ERROR_NOT_FOUND %d\n",LIBUSB_ERROR_NOT_FOUND);
  printf("LIBUSB_ERROR_OTHER %d\n",LIBUSB_ERROR_OTHER);
  if (max_packet_size <0) {
    exit(1);
  }

  buffer = malloc(iso_packets*max_packet_size);
  NZ(!(int)buffer);


  NZ(libusb_get_configuration(dev_handle, &config ));


  // put it in analog input mode
  transfer = libusb_alloc_transfer(iso_packets);
  
  user_data = malloc(sizeof(int));
  NZ(!(int)user_data);
  *user_data = 0;
  timeout = 9999;
  callback = my_callback;
  buffer[0] = 0x8; // get framestamp, use_FOSC
  libusb_fill_bulk_transfer(transfer,
			    dev_handle, 
			    DEVICE_OUT_EPNUM,
			    buffer, 
			    1, 
			    callback,
			    user_data, 
			    timeout);
  printf("submitting\n");
  NZ(libusb_submit_transfer(transfer));

  while (*user_data == 0) {
    libusb_handle_events(ctx);
  }

  *user_data = 0;




  transfer->endpoint = DEVICE_IN_EPNUM;
  transfer->length = 16;

  printf("getting input\n");
  NZ(libusb_submit_transfer(transfer));

  while (*user_data == 0) {
    libusb_handle_events(ctx);
  }
  *user_data = 0;




  transfer->endpoint = DEVICE_OUT_EPNUM;
  transfer->length = 3;
  buffer[0] = 0x7;
  buffer[1] = 0x40;
  buffer[2] = 0x0; // reset ain overflow

  printf("reset ain overflow\n");
  NZ(libusb_submit_transfer(transfer));

  while (*user_data == 0) {
    libusb_handle_events(ctx);
  }
  *user_data = 0;



  
  //  0x1 0x0 0x0 0x0    0x0 0x0 0x0 0x0   0xc8 0x3   set t3 state

  transfer->endpoint = DEVICE_OUT_EPNUM;
  transfer->length = 10;

  buffer[0] = 0x1;
  buffer[1] = 0x0;
  buffer[2] = 0x0;
  buffer[3] = 0x0;

  buffer[4] = 0x0;
  buffer[5] = 0x0;
  buffer[6] = 0x0;
  buffer[7] = 0x0;

  buffer[8] = 0xc8;
  buffer[9] = 0x3;

  printf("set t3 state\n");
  NZ(libusb_submit_transfer(transfer));

  while (*user_data == 0) {
    libusb_handle_events(ctx);
  }
  *user_data = 0;



  transfer->endpoint = DEVICE_OUT_EPNUM;
  transfer->length = 3;
  buffer[0] = 0x7;
  buffer[1] = 0x2;
  buffer[2] = 0x0; // send_ain_state(self)

  printf("send_ain_state(self)\n");
  NZ(libusb_submit_transfer(transfer));

  while (*user_data == 0) {
    libusb_handle_events(ctx);
  }
  *user_data = 0;


  // now grab iso data
  transfer->type = LIBUSB_TRANSFER_TYPE_ISOCHRONOUS;
  transfer->endpoint = ANALOG_IN_EPNUM;
  transfer->callback = iso_callback;
  transfer->num_iso_packets = iso_packets;
  transfer->length = iso_packets*max_packet_size;
  libusb_set_iso_packet_lengths(transfer, max_packet_size);
  
  printf("getting ISO\n");
  NZ(libusb_submit_transfer(transfer));

  while (1) {
    while (*user_data == 0) {
      libusb_handle_events(ctx);
    }
    *user_data = 0;
    NZ(libusb_submit_transfer(transfer));
  }


  libusb_free_transfer(transfer);
  libusb_close(dev_handle);

  libusb_exit(ctx);
  free(user_data);
  free(buffer);
}
