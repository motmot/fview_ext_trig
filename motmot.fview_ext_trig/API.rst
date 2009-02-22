*********************************************
:mod:`fview_ext_trig` - camera trigger device
*********************************************

.. module:: fview_ext_trig
  :synopsis: camera trigger device
.. index::
  module: fview_ext_trig
  single: fview_ext_trig
  single: analog input
  single: synchronization

This package provides Python access to the :ref:`motmot camera trigger
device <fview_ext_trig-overview>`. There are three top-level modules:

* :mod:`fview_ext_trig.ttrigger` -- This is a Python module with
  traited__ classes to interact with the :ref:`camtrig <camtrig>`
  device. (lowest level)

* :mod:`fview_ext_trig.live_timestamp_modeler` -- This module provides
  a class, LiveTimestampModeler, that links the clocks of the camera
  and the host computer, keeping a running update of the relationship
  between the computer's clock and the current framenumber on the
  camera. The LiveTimestampModelerWithAnalogInput class also provides
  a time-locked data stream on up to four channels. (middle level)

* :mod:`fview_ext_trig.fview_ext_trig` -- This model implements a
  plugin for :mod:`fview` to use the
  LiveTimestampModelerWithAnalogInput class. (high level)

__ http://code.enthought.com/projects/traits/

fview_ext_trig
==============

This is the Python package to interact with the :ref:`camtrig <camtrig>` device.

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
