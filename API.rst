****************************************************
:mod:`motmot.fview_ext_trig` - camera trigger device
****************************************************

.. module:: motmot.fview_ext_trig
  :synopsis: camera trigger device
.. index::
  module: fview_ext_trig
  single: fview_ext_trig
  single: analog input
  single: synchronization

This package provides Python access to the :ref:`motmot camera trigger
device <fview_ext_trig-overview>`. There are three modules within this
package:

* :mod:`motmot.fview_ext_trig.ttrigger` -- This is a Python module with
  traited__ classes to interact with the :ref:`camtrig <camtrig>`
  device. (lowest level)

* :mod:`motmot.fview_ext_trig.live_timestamp_modeler` -- This module provides
  a class, LiveTimestampModeler, that links the clocks of the camera
  and the host computer, keeping a running update of the relationship
  between the computer's clock and the current framenumber on the
  camera. The LiveTimestampModelerWithAnalogInput class also provides
  a time-locked data stream on up to four channels. (middle level)

* :mod:`motmot.fview_ext_trig.fview_ext_trig` -- This model implements a
  plugin for :mod:`fview` to use the
  LiveTimestampModelerWithAnalogInput class. (high level)

__ http://code.enthought.com/projects/traits/

Command-line commands
=====================

This package installs several command-line commands:

* :command:`trigger_set_frequency` -- Set the frequency of the camera
  sync trigger on the CamTrig device.

* :command:`trigger_check_device` -- Check for the presence of the
  CamTrig device. If the device is not found, it returns with a
  non-zero exit code.

* :command:`trigger_enter_dfu_mode` -- Reboot the CamTrig device into
  the DFU (Device Firmware Upload) mode. This can be used in
  conjunction with dfu_programmer or Atmel FLIP to flash the device
  with new firmware.

:mod:`motmot.fview_ext_trig.fview_ext_trig`
===========================================

This Python module implements a class, :class:`FviewExtTrig`, that
provides an :mod:`fview` plugin to use the :ref:`camtrig <camtrig>`
device. In the fview_ext_trig setup.py file, this class is registered
as an FView plugin (see :ref:`writing FView plugins
<fview-plugin-writing>`).

fview_ext_trig requirements
---------------------------

traits_, `remote_traits`_, pylibusb_

To use the fview plugin, you will also need chaco_.

.. _traits: http://code.enthought.com/projects/traits/
.. _remote_traits: http://github.com/astraw/remote_traits
.. _pylibusb: https://code.astraw.com/projects/pylibusb
.. _AT90USBKEY: http://www.atmel.com/dyn/products/tools_card.asp?tool_id=3879
.. _LUFA library: http://www.fourwalledcubicle.com/LUFA.php
.. _chaco: http://code.enthought.com/projects/chaco/docs/html/index.html
.. _dfu-programmer: http://dfu-programmer.sourceforge.net/
.. _FLIP: http://www.atmel.com/dyn/products/tools_card.asp?tool_id=3886
