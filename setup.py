from setuptools import setup, find_packages, Extension
import sys,os

# Make this source code directory first in import order to get version.
sys.path.insert(0,os.path.join('motmot','fview_ext_trig'))
from version import __version__

setup(name='motmot.fview_ext_trig',
      description='Camera trigger device with precise timing and analog input',
      version=__version__,
      packages = find_packages(),
      author='Andrew Straw',
      author_email='strawman@astraw.com',
      url='http://code.astraw.com/projects/motmot/camtrig/motmot.fview_ext_trig/API.html',
      ext_modules=[Extension(name="motmot.fview_ext_trig.cDecode",
                             sources=['motmot/fview_ext_trig/cDecode.c',
                                      'motmot/fview_ext_trig/decode.c'])],
      entry_points = {
    'motmot.fview.plugins':'fview_ext_trig = motmot.fview_ext_trig.fview_ext_trig:FviewExtTrig',
    'console_scripts': [
        'trigger_enter_dfu_mode = motmot.fview_ext_trig.ttrigger:enter_dfu_mode',
        'trigger_check_device = motmot.fview_ext_trig.ttrigger:check_device',
        'trigger_set_frequency = motmot.fview_ext_trig.ttrigger:set_frequency',
        'fview_ext_trig_json2h5 = motmot.fview_ext_trig.json2hfive:main',
        'fview_ext_trig_plot_h5 = motmot.fview_ext_trig.plot_h5:main',
        ]},
      )
