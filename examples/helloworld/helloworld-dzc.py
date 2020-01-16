#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import deepzoom


# Collection from local DZIs
images = []
directory = "."
for filename in os.listdir(directory):
    if filename.endswith(".dzi"):
        images.append(os.path.join(directory, filename))

creator = deepzoom.CollectionCreator()
creator.create(images, "helloworld-collection.dzc")

# Collection from DZIs on the web:
zoomhub_images = [
    "http://cache.zoom.it/content/L8wh.dzi",
    "http://cache.zoom.it/content/STK4.dzi",
    "http://cache.zoom.it/content/Xjce.dzi",
    "http://cache.zoom.it/content/8.dzi",
    "http://cache.zoom.it/content/h.dzi",
]
creator.create(zoomhub_images, "zoomhub-collection.dzc")

collection = deepzoom.DeepZoomCollection.from_file("helloworld-collection.dzc")
print(collection.doc.toprettyxml())
