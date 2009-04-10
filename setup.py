#!/usr/bin/env python

from distutils.core import setup

setup(name="deep-zoom-tools",
      version="0.1.0",
      description="Python tools for generating Deep Zoom images (DZI) and collections (DZC) for the use with Silverlight Deep Zoom, Seadragon Ajax, Seadragon Mobile and OpenZoom.",
      author="Daniel Gasienica",
      author_email="daniel@gasienica.ch",
      download_url="http://open-zoom.googlecode.com/files/deep-zoom-tools-0.1.0.zip",
      keywords="deepzoom seadragon dzi dzc seadragonmobile seadragonajax silverlightdeepzoom microsoft openzoom",
      url="http://code.google.com/p/open-zoom/",
      py_modules=["deepzoom"],
      classifiers=["Development Status :: 3 - Alpha",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Utilities",
                   "Topic :: Multimedia :: Graphics",
                   "Topic :: Multimedia :: Graphics :: Graphics Conversion"])