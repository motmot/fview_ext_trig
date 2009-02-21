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
 *  Header file for Descriptors.c.
 */

#ifndef _DESCRIPTORS_H_
#define _DESCRIPTORS_H_

	/* Includes: */
		#include <LUFA/Drivers/USB/USB.h>

		#include <avr/pgmspace.h>

	/* Type Defines: */
		/** Type define for the device configuration descriptor structure. This must be defined in the
		 *  application code, as the configuration descriptor contains several sub-descriptors which
		 *  vary between devices, and which describe the device's usage to the host.
		 */

		typedef struct
		{
			USB_Descriptor_Configuration_Header_t Config; /**< Configuration descriptor header structure */
			USB_Descriptor_Interface_t            Interface; /**< Interface descriptor, required for the device to enumerate */
                        USB_Descriptor_Endpoint_t             CameraTriggerOutEndpoint;
                        USB_Descriptor_Endpoint_t             CameraTriggerInEndpoint;
                        USB_Descriptor_Endpoint_t             AnalogDataInEndpoint;
		} USB_Descriptor_Configuration_t;

	/* Macros: */
		/** Endpoint number of the Camera Trigger OUT endpoint. */
		#define CAMTRIGOUT_EPNUM               0x06

                /** Size in bytes of the Camera Trigger OUT endpoint. */
		#define CAMTRIGOUT_EPSIZE              16

		/** Endpoint number of the Camera Trigger IN endpoint. */
		#define CAMTRIGIN_EPNUM               0x82

                /** Size in bytes of the Camera Trigger IN endpoint. */
		#define CAMTRIGIN_EPSIZE              16

		/** Endpoint number of the Analog Data IN endpoint. */
                #define ANALOG_EPNUM       1

		/** Endpoint size in bytes of the Audio isochronous streaming data endpoint. The Windows audio stack requires
		 *  at least 192 bytes for correct output, thus the smaller 128 byte maximum endpoint size on some of the smaller
		 *  USB AVR models will result in unavoidable distorted output.
		 */
		#define ANALOG_EPSIZE          ENDPOINT_MAX_SIZE(ANALOG_EPNUM)

	/* Function Prototypes: */
		uint16_t USB_GetDescriptor(const uint16_t wValue, const uint8_t wIndex, void** const DescriptorAddress)
		                           ATTR_WARN_UNUSED_RESULT ATTR_NON_NULL_PTR_ARG(3);

#endif
