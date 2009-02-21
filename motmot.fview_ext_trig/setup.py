from setuptools import setup, find_packages, Extension

setup(name='motmot.fview_ext_trig',
      version='0.01',
      packages = find_packages(),
      author='Andrew Straw',
      author_email='strawman@astraw.com',
      zip_safe=True,
      ext_modules=[Extension(name="motmot.fview_ext_trig.cDecode",
                             sources=['motmot/fview_ext_trig/cDecode.c',
                                      'motmot/fview_ext_trig/decode.c'])],
      entry_points = {
    'motmot.fview.plugins':'fview_ext_trig = motmot.fview_ext_trig.fview_ext_trig:FviewExtTrig',
    'console_scripts': [
        'trigger_enter_dfu_mode = motmot.fview_ext_trig.ttrigger:enter_dfu_mode',
        'trigger_check_device = motmot.fview_ext_trig.ttrigger:check_device',
        'trigger_set_frequency = motmot.fview_ext_trig.ttrigger:set_frequency',
        ]},
      )
