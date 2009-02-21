Motmot camera trigger
=====================

Part of the motmot_ project.

.. _motmot: http://code.astraw.com/projects/motmot

For more information, see :ref:`fview_ext_trig-overview`.

Layout of the source tree
-------------------------

To facilitate integration with the LUFA_ project, this source code
tree has the same layout, with a couple additions. Only these
additions are part of the motmot camtrig package.

The motmot camtrig files are:

* ``README.rst`` - you are reading it
* ``OVERVIEW.rst`` - overview 
* ``motmot.fview_ext_trig/`` - a Python package to interact with the device
* ``Projects/MotmotCamTrig/`` - the LUFA-based firmware for the trigger device

The remainder of the files are inherited from the LUFA project.

Building and installing
-----------------------

(To build and install the firmware, read :ref:`motmot-cam-trig`.)

You will require Cython_ in addition to a standard C compiler
(e.g. gcc). Once these are installed, type::

  cd motmot.fview_ext_trig
  cython motmot/fview_ext_trig/cDecode.pyx
  python setup.py install

.. _Cython: http://www.cython.org/

