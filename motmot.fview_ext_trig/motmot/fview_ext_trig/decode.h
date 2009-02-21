#include <stdint.h>

typedef struct {
  uint8_t N;
  uint8_t channel;
  uint16_t sample;
  uint8_t prev_sample_lsbs;
  int64_t framecount;
  uint16_t tcnt3;
  uint8_t did_overflow;
} decode_return_t;

typedef enum {
  DECODE_NO_ERROR=0,
  DECODE_NOT_IMPLEMENTED
} decode_err_t;

decode_err_t decode_bytestream( uint16_t *buf, uint16_t len, decode_return_t *result);

