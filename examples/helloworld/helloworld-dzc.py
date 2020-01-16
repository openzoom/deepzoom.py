#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import deepzoom


images = []
directory = "."
for filename in os.listdir(directory):
    if filename.endswith(".dzi"):
        absolute_path = os.path.abspath(os.path.join(directory, filename))
        images.append(f"file://{absolute_path}")

creator = deepzoom.CollectionCreator()
creator.create(images, "helloworld-collection.dzc")


collection = deepzoom.DeepZoomCollection.from_file(
    f"file://{os.path.abspath('helloworld-collection.dzc')}"
)
print(collection.doc.toprettyxml())
