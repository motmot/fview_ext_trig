/* Motmot camera trigger device
   http://code.astraw.com/projects/motmot
   Andrew Straw
*/

/* Camera trigger generator with synchronized analog input

Also includes digital trigger pulses to trigger other hardware.

Known bugs:

* The framestamp immediately after a camera trigger pulse has a
  rolled-over TCNT3 (a low value just above zero) while framecount_A
  is still indicating the previous frame. This can be worked around by
  ignoring all framestamp values where TCNT3 is low.

* The variable framecount_A ends up giving a reading of 2 for the
  first trigger pulse emitted.

*/

/*
  Copyright 2009  California Institute of Technology
  Copyright 2009  Dean Camera (dean [at] fourwalledcubicle [dot] com)

  Permission to use, copy, modify, and distribute this software
  and its documentation for any purpose and without fee is hereby
  granted, provided that the above copyright notice appear in all
  copies and that both that the copyright notice and this
  permission notice and warranty disclaimer appear in supporting
  documentation, and that the name of the author not be used in
  advertising or publicity pertaining to distribution of the
  software without specific, written prior permission.

  The author disclaim all warranties with regard to this
  software, including all implied warranties of merchantability
  and fitness.  In no event shall the author be liable for any
  special, indirect or consequential damages or any damages
  whatsoever resulting from loss of use, data or profits, whether
  in an action of contract, negligence or other tortious action,
  arising out of or in connection with the use or performance of
  this software.
*/

#include "camtrig.h"
#include "handler.h"
#include <stdint.h>
#include <util/delay.h>

#define FALSE 0
#define TRUE 1

/* globals */
uint8_t   send_data_back_to_host=FALSE;
volatile uint8_t trig_once_mode=0;
RingBuff_t Tx_Buffer; // analog samples

/* A simple buffer of the enabled ADC channels */
#define MAX_ADC_CHANS 4
uint8_t ADC_CHAN_IDX=0;
uint8_t ADC_N_CHANS=0;
uint8_t ADC_CHANS[MAX_ADC_CHANS];



/* Project Tags, for reading out using the ButtLoad project */
BUTTLOADTAG(ProjName,    "Camera Trigger");
BUTTLOADTAG(BuildTime,   __TIME__);
BUTTLOADTAG(BuildDate,   __DATE__);
BUTTLOADTAG(LUFAVersion, "LUFA V" LUFA_VERSION_STRING);

/* Scheduler Task List */
TASK_LIST
{
        { Task: USB_USBTask          , TaskStatus: TASK_RUN  },
	{ Task: USB_ControlDevice_Task          , TaskStatus: TASK_RUN  },
	{ Task: USB_AnalogSample_Task          , TaskStatus: TASK_RUN  },
};


void PWM_Init(void);
void PWM_Init() {
    /*

  n = 3 (timer3)

  Set frequency of PWM using ICRn to set TOP. (Not double-buffered,
  also, clear TCNT before setting.)

  Set compare value using OCRnA.

  WGMn3:0 = 14

  */

  // set output direction on pin
  PORTC &= 0x87; // pin C3-6 set low to start
  DDRC |= 0xFF; // enable output for all PORTC

  // Set output compare to mid-point
  OCR3A = 0x03e8;

  OCR3B = 0x0;
  OCR3C = 0x0;

  // Set TOP to 500 (if F_CLOCK = 1MHZ, this is 200 Hz)
  //ICR3= 5000;
  ICR3 = 0x2710;

  // ---- set TCCR3A ----------
  // set Compare Output Mode for Fast PWM
  // COM3A1:0 = 1,0 clear OC3A on compare match
  // COM3B1:0 = 1,0 clear OC3B on compare match
  // COM3C1:0 = 1,0 clear OC3C on compare match
  // WGM31, WGM30 = 1,0
  TCCR3A = 0xAA;

  // ---- set TCCR3B ----------
  // high bits = 0,0,0
  //WGM33, WGM32 = 1,1
  // CS1 = 0,0,1 (starts timer1) (clock select)
  // CS1 = 0,1,0 (starts timer1 CS=8) (clock select)
  TCCR3B = 0x1A;

  // really only care about timer3_compa_vect
  //TIMSK3 = (1 << OCIE3B) | (1 << OCIE3A) | (1 << TOIE3);
  TIMSK3 |= (1 << OCIE3A);
}

/*  ISR to handle the analog to digital conversion complete interrupt,
 *  fired each time the ADC converted a value. This stores the
 *  received data into the Tx_Buffer circular buffer for later
 *  transmission to the host.
 */

#define FRAMECOUNT_COMING_MARKER 0x04
#define OVERFLOW_MARKER 0x08
volatile uint8_t overflowed = 0;
uint8_t downsample_countdown_max=0;
volatile uint32_t framecount_A=0;

/* Use a 2nd variable for high bits of framecount_A to avoid crazy
 * slow code emitted by GCC for int64.
*/

volatile uint32_t epoch=0;

ISR(ADC_vect, ISR_BLOCK)
{
  // reads globals: downsample_countdown_max, framecount_A, epoch

  // writes globals: overflowed, Tx_Buffer

  static uint16_t check_previous_mask=0;
  uint16_t analog_value;
  uint8_t input_channel;

  static uint16_t timestamp_inc=0;

#define DOWNSAMPLE
#ifdef DOWNSAMPLE
  static uint8_t countdown=0;
  if (countdown>0) {
    countdown--; /* Don't do anything, just cycle until next sample ready. */
  } else {
    countdown=downsample_countdown_max;
#endif

#ifndef FAKEADC
    analog_value = ADC_GetResult();
#else
    static uint16_t fakeadc = 0;
    analog_value=(fakeadc<<6);
    fakeadc++;
    if (fakeadc>=(1<<10)) {
      fakeadc=0;
    }
#endif
  uint16_t tcnt3_copy = TCNT3; // grab early so it corresponds with time of sample
  input_channel = ADC_GetChannel() & 0x03; // only low 2 bits... we're only using first 4 channels

  //pack input channel into LSBs
  analog_value |= check_previous_mask;
  analog_value |= overflowed;        // set marker if necessary
  analog_value |= input_channel;     // low 2 bits set to input_channel

  check_previous_mask = ((analog_value>>2) & 0x30); // insert saved most LSBs, which are least likely to be correlated

  ADC_CHAN_IDX++;
  if ((ADC_CHAN_IDX) >= ADC_N_CHANS) {
    ADC_CHAN_IDX=0;
  }
  ADC_SetChannel( ADC_REFERENCE_AVCC | ADC_LEFT_ADJUSTED | ADC_CHANS[ADC_CHAN_IDX] );

  uint8_t send_framecount = 0;
  if (timestamp_inc>0) {
    timestamp_inc--;
  } else {
    timestamp_inc=250;
    send_framecount = 1;
    analog_value |= FRAMECOUNT_COMING_MARKER; // set marker in data stream
  }

  /* Analog sample received, store it into the buffer */
  if (!Buffer_StoreElement(&Tx_Buffer, analog_value)) { // Get left 10 bits plus markers
    // overflowed ring buffer
    overflowed = OVERFLOW_MARKER;
  }

#define SEND_FRAMECOUNT
#ifdef SEND_FRAMECOUNT
  if (send_framecount) {
    // we are in an interrupt, so we don't need to worry about being interrupted
    Buffer_StoreElement(&Tx_Buffer, (uint16_t)(framecount_A & 0xFFFF));
    Buffer_StoreElement(&Tx_Buffer, (uint16_t)((framecount_A >> 16) & 0xFFFF));
    Buffer_StoreElement(&Tx_Buffer, (uint16_t)(epoch & 0xFFFF));
    Buffer_StoreElement(&Tx_Buffer, (uint16_t)((epoch >> 16) & 0xFFFF));
    if (!Buffer_StoreElement(&Tx_Buffer, tcnt3_copy)) {
      // overflowed ring buffer
      overflowed = OVERFLOW_MARKER;
    }
  }
#endif

#ifdef DOWNSAMPLE
  }
#endif

}

/* ISR for the timer 3 compare vector. */
ISR(TIMER3_COMPA_vect, ISR_BLOCK)
{
  //reads/writes globals: trig_once_mode, framecount_A, epoch

  if (trig_once_mode) {

    TCCR3B = (TCCR3B & 0xF8) | (0 & 0x07); // low 3 bits sets CS to 0 (stop)

    trig_once_mode=0;
  }
  if ((framecount_A)!=0xFFFFFFFF) {
    framecount_A++;
  } else {
    // Wrap framecount to zero. This code won't be called very often.
    framecount_A++;
    epoch++;
    if (epoch>0x7FFFFFFF) {
      // Wrap epoch to zero. I guess this code will never be called. :)
      epoch=0;
    }
  }
}

void (*start_bootloader) (void)=(void (*)(void))0xf000;

/** Main program entry point. This routine configures the hardware required by the application, then
 *  starts the scheduler to run the application tasks.
 */
int main(void)
{
	/* Disable watchdog if enabled by bootloader/fuses */
	MCUSR &= ~(1 << WDRF);
	wdt_disable();

	/* Disable clock division */
	SetSystemClockPrescaler(0);

        Buffer_Initialize(&Tx_Buffer);

	/* Hardware initialization */
        DDRF = 0; // Set Port F to be all input (for analog input) //ADC_SetupChannel(1|2|3);
	//ADC_Init(ADC_FREE_RUNNING | ADC_PRESCALE_128 | ADC_INTERRUPT_ENABLE );
        ADC_N_CHANS=0;

        //#define STARTUP_ADC_CHAN2
#ifdef STARTUP_ADC_CHAN2
        ADC_CHANS[0] = 2;
        ADC_N_CHANS=1;
        ADC_CHAN_IDX = 0;
        /* Start the ADC conversion in free running mode */
        ADCSRA |= (1 << ADIE); /* enable adc interrupt */
        ADC_StartReading(ADC_REFERENCE_AVCC | ADC_LEFT_ADJUSTED | ADC_CHANS[ADC_CHAN_IDX]);
#endif

	LEDs_Init();

        PWM_Init();
        Handler_Init();

	/* Turn on interrupts */
	sei();

	/* Initialize Scheduler so that it can be used */
	Scheduler_Init();

	/* Initialize USB Subsystem */
	USB_Init();

	/* Scheduling - routine never returns, so put this last in the main function */
	Scheduler_Start();
}

EVENT_HANDLER(USB_ConfigurationChanged)
{
  /* Setup USB In and Out Endpoints */
  Endpoint_ConfigureEndpoint(CAMTRIGIN_EPNUM, EP_TYPE_BULK,
                             ENDPOINT_DIR_IN, CAMTRIGIN_EPSIZE,
                             ENDPOINT_BANK_SINGLE);

  Endpoint_ConfigureEndpoint(CAMTRIGOUT_EPNUM, EP_TYPE_BULK,
                             ENDPOINT_DIR_OUT, CAMTRIGOUT_EPSIZE,
                             ENDPOINT_BANK_SINGLE);

  /* Setup analog sample stream endpoint */
  Endpoint_ConfigureEndpoint(ANALOG_EPNUM, EP_TYPE_BULK,
                             ENDPOINT_DIR_IN, ANALOG_EPSIZE,
                             ENDPOINT_BANK_SINGLE);

}


#define trig1_on()  (PORTC |=  0x02)
#define trig1_off() (PORTC &= ~0x02)

#define trig2_on()  (PORTC |=  0x04)
#define trig2_off() (PORTC &= ~0x04)

#define trig3_on()  (PORTC |=  0x08)
#define trig3_off() (PORTC &= ~0x08)

void switchoff_trig1(void) {
  Reg_Handler( switchoff_trig1, 2, 0, FALSE);
  trig1_off();
}

void switchoff_trig2(void) {
  Reg_Handler( switchoff_trig2, 2, 1, FALSE);
  trig2_off();
}

void switchoff_trig3(void) {
  Reg_Handler( switchoff_trig3, 2, 2, FALSE);
  trig3_off();
}

static inline void reset_ain(void) {
  cli();
  overflowed=0;
  Buffer_Initialize(&Tx_Buffer);
  sei();
}

/* Task to listen to USB port, reading in commands from host
   computer, and updating self as desired.
*/
TASK(USB_ControlDevice_Task)
{
#define CAMTRIG_ENTER_DFU 0
#define CAMTRIG_NEW_TIMER3_DATA 1
#define CAMTRIG_DO_TRIG_ONCE 2
#define CAMTRIG_DOUT_HIGH 3
#define CAMTRIG_GET_DATA 4
#define CAMTRIG_RESET_FRAMECOUNT_A 5
#define CAMTRIG_SET_EXT_TRIG 6
#define CAMTRIG_AIN_SERVICE 7
#define CAMTRIG_GET_FRAMESTAMP_NOW 8
#define CAMTRIG_SET_LED_STATE 9

   uint8_t ext_trig_flags=0;
#define EXT_TRIG1 0x01
#define EXT_TRIG2 0x02
#define EXT_TRIG3 0x04

   uint8_t analog_cmd_flags=0;
#define ADC_START_STREAMING 0x01
#define ADC_STOP_STREAMING 0x02
#define ENABLE_ADC_CHAN0 0x04
#define ENABLE_ADC_CHAN1 0x08
#define ENABLE_ADC_CHAN2 0x10
#define ENABLE_ADC_CHAN3 0x20
#define ADC_RESET_AIN 0x40
   uint8_t analog_sample_bits = 0;

   uint8_t clock_select_timer3=0;

   uint16_t new_ocr3a=0;
   uint16_t new_ocr3b=0;
   uint16_t new_ocr3c=0;
   uint16_t new_icr3=0; // icr3 is TOP for timer3
   uint8_t command_class = 0;
   uint8_t send_data_now = 0;

   uint16_t tcnt3_copy;
   uint32_t framecount_A_copy;
   uint32_t epoch_copy;

  if (USB_IsConnected) {
    /* Select the camera trigger out endpoint */
    Endpoint_SelectEndpoint(CAMTRIGOUT_EPNUM);

    /* Check if the current endpoint can be read from (contains a packet) */
    if (Endpoint_ReadWriteAllowed())
      {
        command_class = Endpoint_Read_Byte(); // 0

        switch(command_class) {

        case CAMTRIG_NEW_TIMER3_DATA: // update timer3
          new_ocr3a =           Endpoint_Read_Byte()<<8; // 1 high byte
          new_ocr3a +=          Endpoint_Read_Byte();    // 2 low byte
          new_ocr3b =           Endpoint_Read_Byte()<<8; // 3 high byte
          new_ocr3b +=          Endpoint_Read_Byte();    // 4 low byte

          new_ocr3c =           Endpoint_Read_Byte()<<8; // 5 high byte
          new_ocr3c +=          Endpoint_Read_Byte();    // 6 low byte
          new_icr3  =           Endpoint_Read_Byte()<<8; // 7 high byte  // icr3 is TOP for timer3
          new_icr3 +=           Endpoint_Read_Byte();    // 8 low byte

          clock_select_timer3 = Endpoint_Read_Byte(); // 9

          // update timer3
          OCR3A=(new_ocr3a);
          OCR3B=(new_ocr3b);
          OCR3C=(new_ocr3c);
          ICR3=(new_icr3);  // icr3 is TOP for timer3

          TCNT3 = 0; // reset counter to zero

          TCCR3B = (TCCR3B & 0xF8) | (clock_select_timer3 & 0x07); // low 3 bits sets CS
          break;

        case CAMTRIG_DO_TRIG_ONCE:
          TCCR3B = (TCCR3B & 0xF8) | (0 & 0x07); // low 3 bits sets CS to 0 (stop)

          TCNT3=(0xFF00); // trigger overflow soon
          //OCR3A=(0xFE00);
          OCR3A=(0x00FF);
          ICR3=(0xFFFF);  // icr3 is TOP for timer3

          trig_once_mode=1;

          // start clock
          TCCR3B = (TCCR3B & 0xF8) | (1 & 0x07); // low 3 bits sets CS
          break;

        case CAMTRIG_RESET_FRAMECOUNT_A:
          cli();
          framecount_A = 0;
          epoch=0;
          sei();
          break;

        case CAMTRIG_DOUT_HIGH:
          /* XXX This is cruft left over from a long time ago. Don't call */

          // force output compare A
          OCR3A=(0xFE00U);
          //OCR3B=(new_ocr3b);
          //OCR3C=(new_ocr3c);
          ICR3=(0xFEFFU);
          TCNT3=(0xFFFFU);
          //Led0_on();
          TCCR3B = (TCCR3B & 0xF8) | (1 & 0x07); // start clock
          while (1) {
            // wait for timer to roll over and thus trigger output compare
            uint32_t tmp_tcnt = TCNT3;
            if (tmp_tcnt < 0xFFFFU) {
              break;
            }
          }
          //Led3_on();
          TCCR3B = (TCCR3B & 0xF8) | (0 & 0x07); // stop clock
          break;

        case CAMTRIG_SET_EXT_TRIG:
          ext_trig_flags = Endpoint_Read_Byte();

          if (ext_trig_flags & EXT_TRIG1) {
            trig1_on();
            Reg_Handler( switchoff_trig1, 2, 0, TRUE);
          }

          if (ext_trig_flags & EXT_TRIG2) {
            trig2_on();
            Reg_Handler( switchoff_trig2, 2, 1, TRUE);
          }

          if (ext_trig_flags & EXT_TRIG3) {
            trig3_on();
            Reg_Handler( switchoff_trig3, 2, 2, TRUE);
          }
          break;

        case CAMTRIG_ENTER_DFU:
          USB_ShutDown();

	  // shutdown timer3 and adc interrupts
	  ADCSRA &= ~(1 << ADIE); /* disable adc interrupt */
	  TIMSK3 = 0; /* disable timer3 interrupt */
	  // shutdown ADC device
	  ADC_Init(0);

          _delay_ms(200); // 200 msec delay to ensure host logs the disconnection

	  (*start_bootloader)();

          break;

        case CAMTRIG_AIN_SERVICE:
          analog_cmd_flags = Endpoint_Read_Byte();
          analog_sample_bits = Endpoint_Read_Byte();

          if (analog_cmd_flags & ADC_RESET_AIN) {
            reset_ain();
          }

          if (analog_cmd_flags & ADC_START_STREAMING) {
            cli(); /* We don't want the analog input interrupt happening during this */
            ADC_N_CHANS = 0;
            if (analog_cmd_flags & ENABLE_ADC_CHAN0) {
              ADC_CHANS[ADC_N_CHANS] = 0;
              ADC_N_CHANS++;
            }
            if (analog_cmd_flags & ENABLE_ADC_CHAN1) {
              ADC_CHANS[ADC_N_CHANS] = 1;
              ADC_N_CHANS++;
            }
            if (analog_cmd_flags & ENABLE_ADC_CHAN2) {
              ADC_CHANS[ADC_N_CHANS] = 2;
              ADC_N_CHANS++;
            }
            if (analog_cmd_flags & ENABLE_ADC_CHAN3) {
              ADC_CHANS[ADC_N_CHANS] = 3;
              ADC_N_CHANS++;
            }

            uint8_t adps_prescale_bits = (analog_sample_bits & 0x07); /* low 3 bits */
            downsample_countdown_max = (analog_sample_bits & 0xF8) >> 3; /* high 5 bits */
            ADC_Init(ADC_FREE_RUNNING | adps_prescale_bits | ADC_INTERRUPT_ENABLE );

            /* Do this MAX_ADC_CHANS times */
            sei();
            ADC_CHAN_IDX = 0;
            /* Start the ADC conversion in free running mode */
            ADCSRA |= (1 << ADIE); /* enable adc interrupt */
            ADC_StartReading(ADC_REFERENCE_AVCC | ADC_LEFT_ADJUSTED | ADC_CHANS[ADC_CHAN_IDX]);
          }

          if (analog_cmd_flags & ADC_STOP_STREAMING) {
            ADCSRA &= ~(1 << ADIE); /* disable adc interrupt */
          }
          break;

        case CAMTRIG_GET_FRAMESTAMP_NOW:
          send_data_now = 1;
          break;

        case CAMTRIG_SET_LED_STATE:
	  LEDs_SetAllLEDs(Endpoint_Read_Byte());
          break;

        default:

          /* Unknown command */

          break;
        }

        /* Acknowedge the packet, clear the bank ready for the next packet */
        Endpoint_ClearCurrentBank();
      }

    if (send_data_now) {
      /* Send requested framestamp data back to host */
      Endpoint_SelectEndpoint(CAMTRIGIN_EPNUM);

      ATOMIC_BLOCK(ATOMIC_RESTORESTATE)
      {
	tcnt3_copy= TCNT3;
	framecount_A_copy = framecount_A;
	epoch_copy = epoch;
      }

      while (!Endpoint_ReadWriteAllowed()) {} //spin

      Endpoint_Write_Byte((uint8_t)(framecount_A_copy & 0xFF));
      Endpoint_Write_Byte((uint8_t)((framecount_A_copy >> 8) & 0xFF));
      Endpoint_Write_Byte((uint8_t)((framecount_A_copy >> 16) & 0xFF));
      Endpoint_Write_Byte((uint8_t)((framecount_A_copy >> 24) & 0xFF));

      Endpoint_Write_Byte((uint8_t)(epoch_copy & 0xFF));
      Endpoint_Write_Byte((uint8_t)((epoch_copy >> 8) & 0xFF));
      Endpoint_Write_Byte((uint8_t)((epoch_copy >> 16) & 0xFF));
      Endpoint_Write_Byte((uint8_t)((epoch_copy >> 24) & 0xFF));

      Endpoint_Write_Byte((uint8_t)(tcnt3_copy & 0xFF));
      Endpoint_Write_Byte((uint8_t)((tcnt3_copy >> 8) & 0xFF));

      Endpoint_ClearCurrentBank(); // Send data over the USB
    }

  }
}

TASK(USB_AnalogSample_Task) {

  if (USB_IsConnected) {
		/* Select the Serial Tx Endpoint */
		Endpoint_SelectEndpoint(ANALOG_EPNUM);

                if (Endpoint_ReadWriteAllowed())
                  {
                    /* Check if the Tx buffer contains anything to be sent to the host */
                    if (Tx_Buffer.Elements)
                      {

			/* Write the transmission buffer contents to the received data endpoint */
			while (Tx_Buffer.Elements && ((Endpoint_BytesInEndpoint()+1) < ANALOG_EPSIZE)) {
			  uint16_t tmp = Buffer_GetElement(&Tx_Buffer);
			  Endpoint_Write_Word_LE(tmp);
			  //Endpoint_Write_Word_LE(Buffer_GetElement(&Tx_Buffer));
                        }

			/* Send the data */
			Endpoint_ClearCurrentBank();

                      }
                  }
  }
}

