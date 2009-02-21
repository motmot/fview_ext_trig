.. _fview_ext_trig-overview:

**********************************************************
Camera trigger device with precise timing and analog input
**********************************************************

.. index::
  single: fview_ext_trig
  single: analog input
  single: synchronization

.. _camtrig:

camtrig -- Camera trigger device firmware
=========================================

**camtrig** - firmware for precisely timed trigger generation with
synchronized analog input

Why
---

Triggering your camera is useful to synchronize it with other
devices. These other devices can be other cameras, so that images are
taken simultaneously, or a computer, so that the images can be
correlated with other activity.

What
----

Camtrig is firmware for the $30 AT90USBKEY__ USB development board
that:

__ http://atmel.com/dyn/products/tools_card.asp?tool_id=3879

1. generates trigger pulses to feed into the external trigger input of
   digital video cameras.  The pulses are generated with a 16-bit
   hardware timer using an 8 MHz crystal oscillator to produce very
   regular timing.
2. communicates synchronization information with software running on a
   PC. By repeatedly querying for timestamps from the USB device, the
   PC is able to make a model of the gain and offset of the two clocks
   with computed precision.
3. acquires analog voltage streams. The AT90USBKEY has a multiplexed
   10-bit analog-to-digital converter (ADC), which can sample from
   0.0 to 3.3 volts and operates up to 9.6 KHz using pycamtrig.
4. produces digital pulses to trigger other hardware.
5. provides a GUI plugin to :mod:`fview` that includes a display like a
   strip-chart recorder.

How
---

The device is accessed using the Python :mod:`fview_ext_trig` package.

Camtrig is built with GCC-AVR using the `LUFA library`__ for the
AT90USBKEY. To load the firmware onto the device, use
`dfu-programmer`__ or FLIP__ to transfer the hex file `camtrig.hex`_
to the device in Device Firmware Upload (DFU) mode.

__ http://www.fourwalledcubicle.com/LUFA.php
__ http://dfu-programmer.sourceforge.net/
__ http://www.atmel.com/dyn/products/tools_card.asp?tool_id=3886

.. _camtrig.hex: XXX

.. toctree::
  :maxdepth: 1

  firmware/README.rst
