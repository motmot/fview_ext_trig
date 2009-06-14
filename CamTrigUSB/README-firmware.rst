.. _motmot-cam-trig:

Motmot camera trigger -- firmware build and install instructions
================================================================

This directory contains the source code for the motmot_ camera
trigger. As this firmware is built using the LUFA_ library, that
library is included in this source code tree. The motmot camera
trigger is in ``Projects/MotmotCamTrig``. The rest of the code here is
a direct copy of the LUFA repository.

.. _motmot: http://code.astraw.com/projects/motmot
.. _LUFA: http://www.fourwalledcubicle.com/LUFA.php

Building
--------

**Note**: the .hex file (encoded firmware machine code) is already
precompiled as `camtrig.hex`_ (using avr-gcc 4.3.2 on Ubuntu
Jaunty). Thus, you don't have to compile this code unless you want to
change something.

.. _camtrig.hex: http://github.com/motmot/fview_ext_trig/raw/master/CamTrigUSB/Projects/MotmotCamTrig/camtrig.hex

in linux
""""""""

To build the MotmotCamtrig firmware (``camtrig.hex``)::

  cd Projects
  rm -f MotmotCamTrig/*.hex MotmotCamTrig/*.o
  make -C MotmotCamTrig

in Windows
""""""""""

A rough sketch is: compile with WinAVR__. Follow the LUFA__ directions
for compilation.

__ http://winavr.sourceforge.net/
__ http://www.fourwalledcubicle.com/LUFA.php

Loading firmware onto AT90USBKEY
--------------------------------

dfu-programmer -- linux
"""""""""""""""""""""""

The firmware is loaded over the normal USB cable. You must boot your
AT90USBKEY into DFU mode. After doing so enter these commands::

  sudo dfu-programmer at90usb1287 erase
  sudo dfu-programmer at90usb1287 flash MotmotCamTrig/camtrig.hex
  sudo dfu-programmer at90usb1287 start

Atmel FLIP -- Windows
"""""""""""""""""""""

Use Atmel's GUI app to load the firmware (file
``MotmotCamTrig/camtrig.hex``) to the device.

Installation to OS
------------------

How to get USB device recognized by Linux
"""""""""""""""""""""""""""""""""""""""""

To get your linux system to recognize the device copy the udev
rules file to the appropriate location::

  sudo cp 99-motmot-cam-trig.rules /etc/udev/rules.d/

This will automatically allow users of the group "video" to access the
device without special permissions. These instructions assume the
video group exists and you are already a member. To check this, type::

  groups

If `video` appears in the output, you are already a member of the video group.

Finally, you will need for the above changes to take effect. The
easiest way is to reboot your computer. If you want to avoid that, try this::

  # Force udev to notice the new file specifying the group for the device
  sudo /etc/init.d/udev reload
  sudo /etc/init.d/udev restart

  # Start a new shell with membership in the new group - this console only!
  su $USER
  # (Enter your password)


How to get USB device recognized by Windows
"""""""""""""""""""""""""""""""""""""""""""

Follow the instructions here__, although please note that I have not
tried this. The Vendor ID is 0x1781 and the Product ID is 0x0baf for
this USB device.

__ http://libusb-win32.sourceforge.net/#installation
