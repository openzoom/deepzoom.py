#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="DeepZoomTools",
    version="2.0.0",
    author="Daniel Gasienica",
    author_email="daniel@gasienica.ch",
    description="Python tools for generating Deep Zoom images (DZI) and \
collections (DZC) for the use with Silverlight Deep Zoom, Seadragon Ajax, \
Seadragon Mobile, and OpenZoom.",
    keywords="deepzoom seadragon dzi dzc seadragonajax seadragonmobile silverlightdeepzoom microsoft openzoom",
    packages=find_packages(),
    license="BSD 3-Clause License",
    install_requires=["Pillow>=6"],
    url="https://github.com/openzoom/deepzoom.py",
    include_package_data=True,
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Utilities",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
    ],
)
