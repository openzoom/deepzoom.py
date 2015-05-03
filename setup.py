#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

setup(name='DeepZoomTools',
      version='1.0.0',
      description='Python tools for generating Deep Zoom images (DZI) and \
collections (DZC) for the use with Silverlight Deep Zoom, Seadragon Ajax, \
Seadragon Mobile and OpenZoom.',
      author='Daniel Gasienica',
      author_email='daniel@gasienica.ch',
      download_url='https://github.com/openzoom/deepzoom.py/archives/0.9.4',
      keywords='deepzoom seadragon dzi dzc seadragonajax seadragonmobile silverlightdeepzoom microsoft openzoom',
      url='http://github.com/openzoom/deepzoom.py',
      py_modules=['deepzoom'],
      install_requires=['pillow', 'six'],
      classifiers=['Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Utilities',
                   'Topic :: Multimedia :: Graphics',
                   'Topic :: Multimedia :: Graphics :: Graphics Conversion'])
