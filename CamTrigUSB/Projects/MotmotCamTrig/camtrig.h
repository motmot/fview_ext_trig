/* Motmot camera trigger device
   http://code.astraw.com/projects/motmot
   Andrew Straw
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

/** \file
 *
 *  Header file for camtrig.c.
 */

#ifndef _CAMTRIG_H_
#define _CAMTRIG_H_

	/* Includes: */
		#include <avr/io.h>
		#include <avr/interrupt.h>
		#include <avr/wdt.h>

                #include "Descriptors.h"

		#include <LUFA/Version.h>                               // Library Version Information
		#include <LUFA/Drivers/USB/USB.h>                       // USB Functionality
		#include <LUFA/Scheduler/Scheduler.h>                   // Simple scheduler for task management
//		#include <LUFA/MemoryAllocator/DynAlloc.h>              // Auto-defragmenting Dynamic Memory allocation
		#include <LUFA/Common/ButtLoadTag.h>                    // PROGMEM tags readable by the ButtLoad project
		#include <LUFA/Drivers/AT90USBXXX/ADC.h>                // ADC driver
		#include <LUFA/Drivers/Board/LEDs.h>                    // LED driver
                #include <RingBuff.h>

	/* Task Definitions: */
                TASK(USB_ControlDevice_Task);
                TASK(USB_AnalogSample_Task);

	/* Event Handlers: */
		/** Indicates that this module will catch the USB_Connect event when thrown by the library. */
		HANDLES_EVENT(USB_Connect);

		/** Indicates that this module will catch the USB_Disconnect event when thrown by the library. */
		HANDLES_EVENT(USB_Disconnect);

		/** Indicates that this module will catch the USB_ConfigurationChanged event when thrown by the library. */
		HANDLES_EVENT(USB_ConfigurationChanged);

		/** Indicates that this module will catch the USB_UnhandledControlPacket event when thrown by the library. */
		HANDLES_EVENT(USB_UnhandledControlPacket);

#endif
