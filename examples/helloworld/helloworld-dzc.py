#!/usr/bin/env python3

from pathlib import Path

import deepzoom

# Collection from local DZIs
images = [str(p) for p in Path(".").glob("output/*.dzi")]

creator = deepzoom.CollectionCreator()
creator.create(images, "output/helloworld-collection.dzc")

# Collection from DZIs on the web:
zoomhub_images = [
    "http://cache.zoom.it/content/L8wh.dzi",
    "http://cache.zoom.it/content/STK4.dzi",
    "http://cache.zoom.it/content/Xjce.dzi",
    "http://cache.zoom.it/content/8.dzi",
    "http://cache.zoom.it/content/h.dzi",
]
creator.create(zoomhub_images, "output/zoomhub-collection.dzc")

collection = deepzoom.DeepZoomCollection.from_file("output/helloworld-collection.dzc")
print(collection.doc.toprettyxml())
