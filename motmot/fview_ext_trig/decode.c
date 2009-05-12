#include "decode.h"
#include <string.h>

#define FRAMECOUNT_COMING_MARKER 0x04
#define OVERFLOW_MARKER 0x08

decode_err_t decode_bytestream( uint16_t *buf, uint16_t len, decode_return_t *result) {
  uint16_t buf0 = buf[0];
  uint8_t N=0;
  //  int i;
  int64_t* framecount_ptr;
  memset((void*)result, 0, sizeof(decode_return_t));

  if (buf0 & OVERFLOW_MARKER) {
    result->did_overflow=1;
  }

  if (buf0 & FRAMECOUNT_COMING_MARKER) {
    /* bytes 1:6 have framecount+tcnt, current byte is a sample */
    if (len < 6) {
      return DECODE_NO_ERROR; /* wait for 6 or more values */
    } else {
      /*  for (i=1; i<5; i++) {
        printf("%d: %d\n",i,buf[i]);
        }*/
      framecount_ptr = (int64_t*)(&(buf[1]));
      result->framecount=*(framecount_ptr);
      //      printf("%d\n",result->framecount);
      result->tcnt3 = buf[5];
      N=5;
    }
  }

  result->channel = buf0 & 0x03; /* channel mask */
  result->prev_sample_lsbs = ((buf0>>4)&(0x03)); /* previous sample LSBs mask */
  result->sample = buf0 >> 6;    /* make left-aligned value right aligned */
  N++;
  result->N = N;
  return DECODE_NO_ERROR;
}
