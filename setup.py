#!/usr/bin/env python

from distutils.core import setup

setup(name="DeepZoomTools",
      version="0.9.3",
      description="Python tools for generating Deep Zoom images (DZI) and collections (DZC) for the use with Silverlight Deep Zoom, Seadragon Ajax, Seadragon Mobile and OpenZoom.",
      author="Daniel Gasienica",
      author_email="daniel@gasienica.ch",
      download_url="http://https://github.com/openzoom/deepzoom.py/archives/0.9.3",
      keywords="deepzoom seadragon dzi dzc seadragonajax seadragonmobile silverlightdeepzoom microsoft openzoom",
      url="http://github.com/openzoom/deepzoom.py",
      py_modules=["deepzoom"],
      classifiers=["Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Utilities",
                   "Topic :: Multimedia :: Graphics",
                   "Topic :: Multimedia :: Graphics :: Graphics Conversion"])
