#!/usr/bin/env python3

#
#  Deep Zoom Tools
#
#  Copyright (c) 2008-2019, Daniel Gasienica <daniel@gasienica.ch>
#  Copyright (c) 2008-2011, OpenZoom <http://openzoom.org>
#  Copyright (c) 2010, Boris Bluntschli <boris@bluntschli.ch>
#  Copyright (c) 2008, Kapil Thangavelu <kapil.foss@gmail.com>
#  All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without modification,
#  are permitted provided that the following conditions are met:
#
#      1. Redistributions of source code must retain the above copyright notice,
#         this list of conditions and the following disclaimer.
#
#      2. Redistributions in binary form must reproduce the above copyright
#         notice, this list of conditions and the following disclaimer in the
#         documentation and/or other materials provided with the distribution.
#
#      3. Neither the name of OpenZoom nor the names of its contributors may be used
#         to endorse or promote products derived from this software without
#         specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#  ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#  WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#  DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
#  ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import io
import logging
import math
import optparse
import os
import shutil
from collections import deque, namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import sys
import time
import urllib.request
import xml.dom.minidom

import PIL.Image


logger = logging.getLogger(__name__)

NS_DEEPZOOM = "http://schemas.microsoft.com/deepzoom/2008"

DEFAULT_RESIZE_FILTER = PIL.Image.LANCZOS
DEFAULT_IMAGE_FORMAT = "jpg"

# How often `ImageCreator.create` logs progress
PROGRESS_STEP_PERCENT = 10

RESIZE_FILTERS = {
    "bilinear": PIL.Image.BILINEAR,
    "bicubic": PIL.Image.BICUBIC,
    "nearest": PIL.Image.NEAREST,
    "lanczos": PIL.Image.LANCZOS,
}

IMAGE_FORMATS = {
    "jpg": "jpg",
    "png": "png",
}


def morton_decode(z_order):
    """Returns position (column, row) from given Z-order (Morton number)."""
    column = 0
    row = 0
    for i in range(0, 32, 2):
        offset = i // 2
        # column
        column_offset = i
        column_mask = 1 << column_offset
        column_value = (z_order & column_mask) >> column_offset
        column |= column_value << offset
        # row
        row_offset = i + 1
        row_mask = 1 << row_offset
        row_value = (z_order & row_mask) >> row_offset
        row |= row_value << offset
    return int(column), int(row)


def morton_encode(column, row):
    """Returns the Z-order (Morton number) from given position."""
    z_order = 0
    for i in range(32):
        z_order |= (column & 1 << i) << i | (row & 1 << i) << (i + 1)
    return z_order


def collection_tile_position(z_order, level, tile_size):
    """Returns which collection tile (column, row) a given item lands in."""
    level_size = 2 ** level
    x, y = morton_decode(z_order)
    return (
        int(math.floor((x * level_size) / tile_size)),
        int(math.floor((y * level_size) / tile_size)),
    )


def collection_paste_position(z_order, level, tile_size):
    """Returns the (x, y) pixel position of an item within its collection tile."""
    level_size = 2 ** level
    images_per_tile = int(math.floor(tile_size / level_size))
    column, row = morton_decode(z_order)
    x = (column % images_per_tile) * level_size
    y = (row % images_per_tile) * level_size
    return (x, y)


PlacementStep = namedtuple(
    "PlacementStep",
    [
        "level",
        # (column, row) of the collection tile file
        "collection_tile",
        # (x, y) pixel offset of the item within that tile
        "paste_position",
    ],
)


def compute_placement_plan(z_order, max_level, tile_size):
    """Returns where an item goes in a collection, as one `PlacementStep` per
    level from `max_level` down to 0."""
    return [
        PlacementStep(
            level=level,
            collection_tile=collection_tile_position(z_order, level, tile_size),
            paste_position=collection_paste_position(z_order, level, tile_size),
        )
        for level in reversed(range(max_level + 1))
    ]


def item_source_tile_path(source, level, tile_format):
    """Returns the path of the tile a collection item is built from at
    `level`, assuming the item fits into a single tile at that level."""
    return "%s/%s/%s_%s.%s" % (_get_files_path(source), level, 0, 0, tile_format)


class DeepZoomImageDescriptor(object):
    def __init__(
        self, width=None, height=None, tile_size=254, tile_overlap=1, tile_format="jpg"
    ):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.tile_format = tile_format
        self._num_levels = None

    def open(self, source):
        """Intialize descriptor from an existing descriptor file."""
        doc = xml.dom.minidom.parse(safe_open(source))
        image = doc.getElementsByTagName("Image")[0]
        size = doc.getElementsByTagName("Size")[0]
        self.width = int(size.getAttribute("Width"))
        self.height = int(size.getAttribute("Height"))
        self.tile_size = int(image.getAttribute("TileSize"))
        self.tile_overlap = int(image.getAttribute("Overlap"))
        self.tile_format = image.getAttribute("Format")

    def save(self, destination):
        """Save descriptor file."""
        file = open(destination, "wb")
        doc = xml.dom.minidom.Document()
        image = doc.createElementNS(NS_DEEPZOOM, "Image")
        image.setAttribute("xmlns", NS_DEEPZOOM)
        image.setAttribute("TileSize", str(self.tile_size))
        image.setAttribute("Overlap", str(self.tile_overlap))
        image.setAttribute("Format", str(self.tile_format))
        size = doc.createElementNS(NS_DEEPZOOM, "Size")
        size.setAttribute("Width", str(self.width))
        size.setAttribute("Height", str(self.height))
        image.appendChild(size)
        doc.appendChild(image)
        descriptor = doc.toxml(encoding="UTF-8")
        file.write(descriptor)
        file.close()

    @classmethod
    def remove(self, filename):
        """Remove descriptor file (DZI) and tiles folder."""
        _remove(filename)

    @property
    def num_levels(self):
        """Number of levels in the pyramid."""
        if self._num_levels is None:
            max_dimension = max(self.width, self.height)
            self._num_levels = int(math.ceil(math.log(max_dimension, 2))) + 1
        return self._num_levels

    def get_scale(self, level):
        """Scale of a pyramid level."""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        max_level = self.num_levels - 1
        return math.pow(0.5, max_level - level)

    def get_dimensions(self, level):
        """Dimensions of level (width, height)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        scale = self.get_scale(level)
        width = int(math.ceil(self.width * scale))
        height = int(math.ceil(self.height * scale))
        return (width, height)

    def get_num_tiles(self, level):
        """Number of tiles (columns, rows)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        w, h = self.get_dimensions(level)
        return (
            int(math.ceil(float(w) / self.tile_size)),
            int(math.ceil(float(h) / self.tile_size)),
        )

    def get_tile_bounds(self, level, column, row):
        """Bounding box of the tile (x1, y1, x2, y2)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        offset_x = 0 if column == 0 else self.tile_overlap
        offset_y = 0 if row == 0 else self.tile_overlap
        x = (column * self.tile_size) - offset_x
        y = (row * self.tile_size) - offset_y
        level_width, level_height = self.get_dimensions(level)
        w = self.tile_size + (1 if column == 0 else 2) * self.tile_overlap
        h = self.tile_size + (1 if row == 0 else 2) * self.tile_overlap
        w = min(w, level_width - x)
        h = min(h, level_height - y)
        return (x, y, x + w, y + h)


class DeepZoomCollection(object):
    def __init__(
        self,
        filename,
        image_quality=0.8,
        max_level=7,
        tile_size=256,
        tile_format="jpg",
        tile_background_color="#000000",
        items=[],
    ):
        # Items are laid out on a grid of `2 ** level` sized cells, so a tile
        # must hold a whole number of them at every level. Otherwise items
        # overlap, or there is no room for a single item
        if tile_size < 1 or tile_size & (tile_size - 1) != 0:
            raise ValueError("tile_size must be a power of two: %s" % tile_size)
        if 2 ** max_level > tile_size:
            raise ValueError(
                "max_level %s items (%s px) don’t fit into tile_size %s"
                % (max_level, 2 ** max_level, tile_size)
            )
        self.source = filename
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.tile_background_color = tile_background_color
        self.items = deque(items)
        self.next_item_id = len(self.items)
        # XML
        self.doc = xml.dom.minidom.Document()
        collection = self.doc.createElementNS(NS_DEEPZOOM, "Collection")
        collection.setAttribute("xmlns", NS_DEEPZOOM)
        collection.setAttribute("MaxLevel", str(self.max_level))
        collection.setAttribute("TileSize", str(self.tile_size))
        collection.setAttribute("Format", str(self.tile_format))
        collection.setAttribute("Quality", str(self.image_quality))
        # TODO: Append items passed in as argument
        items = self.doc.createElementNS(NS_DEEPZOOM, "Items")
        collection.appendChild(items)
        collection.setAttribute("NextItemId", str(self.next_item_id))
        self.doc.appendChild(collection)

    @classmethod
    def from_file(self, filename):
        """Open collection descriptor."""
        doc = xml.dom.minidom.parse(safe_open(filename))
        collection = doc.getElementsByTagName("Collection")[0]
        image_quality = float(collection.getAttribute("Quality"))
        max_level = int(collection.getAttribute("MaxLevel"))
        tile_size = int(collection.getAttribute("TileSize"))
        tile_format = collection.getAttribute("Format")
        items = [
            DeepZoomCollectionItem.from_xml(item)
            for item in doc.getElementsByTagName("I")
        ]

        collection = DeepZoomCollection(
            filename,
            image_quality=image_quality,
            max_level=max_level,
            tile_size=tile_size,
            tile_format=tile_format,
            items=items,
        )
        return collection

    @classmethod
    def remove(self, filename):
        """Remove collection file (DZC) and tiles folder."""
        _remove(filename)

    def append(self, source):
        descriptor = DeepZoomImageDescriptor()
        descriptor.open(source)
        self.append_item(source, descriptor.width, descriptor.height)

    def append_item(self, source, width, height):
        """Append an item with known dimensions, skipping the descriptor fetch."""
        item = DeepZoomCollectionItem(
            source, width, height, id=self.next_item_id
        )
        self.items.append(item)
        self.next_item_id += 1

    def _prefetch_batch(self, batch, max_workers):
        """Prefetch .dzi descriptors and max_level tiles for a batch in parallel."""
        # Phase 1: fetch all .dzi descriptors
        dzi_urls = [item.source for item in batch]
        logger.info("Prefetching %d descriptors…", len(dzi_urls))
        self._parallel_fetch(dzi_urls, max_workers)

        # Phase 2: parse descriptors to get tile format, then fetch max_level tiles
        tile_urls = []
        for item in batch:
            if item.source not in _fetch_cache:
                continue
            doc = xml.dom.minidom.parse(safe_open(item.source))
            image = doc.getElementsByTagName("Image")[0]
            tile_format = image.getAttribute("Format")
            tile_urls.append(
                item_source_tile_path(item.source, self.max_level, tile_format)
            )

        logger.info("Prefetching %d tiles…", len(tile_urls))
        self._parallel_fetch(tile_urls, max_workers)

    def _parallel_fetch(self, urls, max_workers):
        """Fetch a list of URLs in parallel, populating _fetch_cache."""
        total = len(urls)
        done = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_url, url): url for url in urls}
            for future in as_completed(futures):
                url = futures[future]
                done += 1
                try:
                    _fetch_cache[url] = future.result()
                    if done % 50 == 0 or done == total:
                        logger.info("  fetched %d/%d", done, total)
                except Exception as exception:
                    logger.warning("Failed to prefetch %s: %s", url, exception)

    def save(self, pretty_print_xml=False, max_workers=8, batch_size=100):
        """Save collection descriptor."""
        collection = self.doc.getElementsByTagName("Collection")[0]
        items = self.doc.getElementsByTagName("Items")[0]
        total = len(self.items)
        logger.info("Saving collection: %d items, tile_size=%d, max_level=%d",
                     total, self.tile_size, self.max_level)

        count = 0
        while len(self.items) > 0:
            # Prefetch the next batch
            batch = []
            for _ in range(min(batch_size, len(self.items))):
                batch.append(self.items.popleft())

            if max_workers > 1:
                self._prefetch_batch(batch, max_workers)
                logger.info("Cache size: %d entries, ~%.1f MB",
                            len(_fetch_cache),
                            sum(len(v) for v in _fetch_cache.values()) / 1e6)

            for item in batch:
                count += 1
                logger.info("[%d/%d] Appending item %d: %s (%dx%d)",
                            count, total, item.id, item.source,
                            item.width, item.height)
                i = self.doc.createElementNS(NS_DEEPZOOM, "I")
                i.setAttribute("Id", str(item.id))
                i.setAttribute("N", str(item.id))
                i.setAttribute("Source", item.source)
                # Size
                size = self.doc.createElementNS(NS_DEEPZOOM, "Size")
                size.setAttribute("Width", str(item.width))
                size.setAttribute("Height", str(item.height))
                i.appendChild(size)
                items.appendChild(i)
                start = time.time()
                self._append_image(item.source, item.id)
                elapsed = time.time() - start
                logger.info("[%d/%d] Done in %.2fs", count, total, elapsed)

            # Free cache for this batch
            _fetch_cache.clear()

        collection.setAttribute("NextItemId", str(self.next_item_id))
        with open(self.source, "wb") as f:
            if pretty_print_xml:
                xml = self.doc.toprettyxml(encoding="UTF-8")
            else:
                xml = self.doc.toxml(encoding="UTF-8")
            f.write(xml)
        logger.info("Collection saved to %s", self.source)

    def _append_image(self, path, i):
        descriptor = DeepZoomImageDescriptor()
        try:
            descriptor.open(path)
        except Exception as exception:
            logger.warning("Skipped item %d, failed to open descriptor: %s", i, exception)
            return
        logger.debug("Item %d: descriptor loaded, %d levels", i, descriptor.num_levels)
        files_path = _get_or_create_path(_get_files_path(self.source))
        plan = compute_placement_plan(i, self.max_level, self.tile_size)
        for step in plan:
            level = step.level
            level_path = _get_or_create_path("%s/%s" % (files_path, level))
            column, row = step.collection_tile
            tile_path = "%s/%s_%s.%s" % (level_path, column, row, self.tile_format)
            if not os.path.exists(tile_path):
                tile_image = PIL.Image.new(
                    "RGB", (self.tile_size, self.tile_size), self.tile_background_color
                )
                if self.tile_format == "jpg":
                    jpeg_quality = int(self.image_quality * 100)
                    tile_image.save(tile_path, "JPEG", quality=jpeg_quality)
                else:
                    tile_image.save(tile_path)
            tile_image = PIL.Image.open(tile_path)
            source_path = item_source_tile_path(path, level, descriptor.tile_format)
            # Local
            if os.path.exists(source_path):
                try:
                    source_image = PIL.Image.open(safe_open(source_path))
                except IOError:
                    logger.warning("Skipped invalid level: %s", source_path)
                    continue
            # Remote
            else:
                if level == self.max_level:
                    try:
                        source_image = PIL.Image.open(safe_open(source_path))
                    except IOError:
                        logger.warning("Skipped invalid image: %s", source_path)
                        return
                    # Expected width & height of the tile
                    e_w, e_h = descriptor.get_dimensions(level)
                    # Actual width & height of the tile
                    w, h = source_image.size
                    # Correct tile because of IIP bug where low-level tiles have
                    # wrong dimensions (they are too large)
                    if w != e_w or h != e_h:
                        # Resize incorrect tile to correct size
                        source_image = source_image.resize(
                            (e_w, e_h), DEFAULT_RESIZE_FILTER
                        )
                        # Store new dimensions
                        w, h = e_w, e_h
                else:
                    # Resize to the exact Deep Zoom level size (rounded up).
                    # thumbnail() keeps the aspect ratio and can come out a
                    # pixel smaller, so viewers sampling the spec size read
                    # past the item into the tile background.
                    w, h = descriptor.get_dimensions(level)
                    source_image = source_image.resize((w, h), DEFAULT_RESIZE_FILTER)
            tile_image.paste(source_image, step.paste_position)
            tile_image.save(tile_path)

    def get_position(self, z_order):
        """Returns position (column, row) from given Z-order (Morton number.)"""
        return morton_decode(z_order)

    def get_z_order(self, column, row):
        """Returns the Z-order (Morton number) from given position."""
        return morton_encode(column, row)

    def get_tile_position(self, z_order, level, tile_size):
        return collection_tile_position(z_order, level, tile_size)


class DeepZoomCollectionItem(object):
    def __init__(self, source, width, height, id=0):
        self.id = id
        self.source = source
        self.width = width
        self.height = height

    @classmethod
    def from_xml(cls, xml):
        id = int(xml.getAttribute("Id"))
        source = xml.getAttribute("Source")
        size = xml.getElementsByTagName("Size")[0]
        width = int(size.getAttribute("Width"))
        height = int(size.getAttribute("Height"))
        return DeepZoomCollectionItem(source, width, height, id)


class ImageCreator(object):
    """Creates Deep Zoom images."""

    def __init__(
        self,
        tile_size=254,
        tile_overlap=1,
        tile_format="jpg",
        image_quality=0.8,
        resize_filter=None,
        copy_metadata=False,
    ):
        self.tile_size = int(tile_size)
        self.tile_format = tile_format
        self.tile_overlap = _clamp(int(tile_overlap), 0, 10)
        self.image_quality = _clamp(image_quality, 0, 1.0)
        if not tile_format in IMAGE_FORMATS:
            self.tile_format = DEFAULT_IMAGE_FORMAT
        self.resize_filter = resize_filter
        self.copy_metadata = copy_metadata

    def get_image(self, level):
        """Returns the bitmap image at the given level."""
        assert (
            0 <= level and level < self.descriptor.num_levels
        ), "Invalid pyramid level"
        width, height = self.descriptor.get_dimensions(level)
        # don't transform to what we already have
        if self.descriptor.width == width and self.descriptor.height == height:
            return self.image
        if (self.resize_filter is None) or (self.resize_filter not in RESIZE_FILTERS):
            return self.image.resize((width, height), DEFAULT_RESIZE_FILTER)
        return self.image.resize((width, height), RESIZE_FILTERS[self.resize_filter])

    def tiles(self, level):
        """Iterator for all tiles in the given level. Returns (column, row) of a tile."""
        columns, rows = self.descriptor.get_num_tiles(level)
        for column in range(columns):
            for row in range(rows):
                yield (column, row)

    def create(self, source, destination):
        """Creates Deep Zoom image from source file and saves it to destination."""
        if isinstance(source, PIL.Image.Image):
            self.image = source
        else:
            self.image = PIL.Image.open(safe_open(source))
        width, height = self.image.size
        self.descriptor = DeepZoomImageDescriptor(
            width=width,
            height=height,
            tile_size=self.tile_size,
            tile_overlap=self.tile_overlap,
            tile_format=self.tile_format,
        )
        # Report progress by share of all tiles: each level has about four
        # times the tiles of the one before, so most time goes to the last
        max_level = self.descriptor.num_levels - 1
        total_tiles = sum(
            columns * rows
            for columns, rows in map(
                self.descriptor.get_num_tiles, range(self.descriptor.num_levels)
            )
        )
        logger.info(
            "Creating %s: %d × %d, %d levels, %d tiles",
            destination, width, height, self.descriptor.num_levels, total_tiles,
        )
        start = time.time()
        done_tiles = 0
        next_report_percent = 0
        # Create tiles
        image_files = _get_or_create_path(_get_files_path(destination))
        for level in range(self.descriptor.num_levels):
            level_dir = _get_or_create_path(os.path.join(image_files, str(level)))
            logger.debug("Resizing level %d/%d…", level, max_level)
            level_image = self.get_image(level)
            for (column, row) in self.tiles(level):
                bounds = self.descriptor.get_tile_bounds(level, column, row)
                tile = level_image.crop(bounds)
                format = self.descriptor.tile_format
                tile_path = os.path.join(level_dir, "%s_%s.%s" % (column, row, format))
                if self.descriptor.tile_format == "jpg":
                    jpeg_quality = int(self.image_quality * 100)
                    tile.save(tile_path, "JPEG", quality=jpeg_quality)
                else:
                    tile.save(tile_path)
                done_tiles += 1
                percent = 100 * done_tiles // total_tiles
                if percent >= next_report_percent:
                    logger.info(
                        "%3d%% (%d/%d tiles, level %d/%d)",
                        percent, done_tiles, total_tiles, level, max_level,
                    )
                    next_report_percent = (
                        percent // PROGRESS_STEP_PERCENT + 1
                    ) * PROGRESS_STEP_PERCENT
        # Create descriptor
        self.descriptor.save(destination)
        logger.info("Saved %s in %.1fs", destination, time.time() - start)


class CollectionCreator(object):
    """Creates Deep Zoom collections."""

    def __init__(
        self,
        image_quality=0.8,
        tile_size=256,
        max_level=7,
        tile_format="jpg",
        copy_metadata=False,
        tile_background_color="#000000",
    ):
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.tile_background_color = tile_background_color
        # TODO
        self.copy_metadata = copy_metadata

    def create(self, images, destination):
        """Creates a Deep Zoom collection from a list of images."""
        collection = DeepZoomCollection(
            destination,
            image_quality=self.image_quality,
            max_level=self.max_level,
            tile_size=self.tile_size,
            tile_format=self.tile_format,
            tile_background_color=self.tile_background_color,
        )
        for image in images:
            collection.append(image)
        collection.save()


################################################################################


def retry(attempts, backoff=2):
    """Retries a function or method until it returns or
    the number of attempts has been reached."""

    if backoff <= 1:
        raise ValueError("backoff must be greater than 1")

    attempts = int(math.floor(attempts))
    if attempts < 0:
        raise ValueError("attempts must be 0 or greater")

    def deco_retry(f):
        def f_retry(*args, **kwargs):
            last_exception = None
            for attempt in range(attempts):
                try:
                    return f(*args, **kwargs)
                except Exception as exception:
                    last_exception = exception
                    if attempt < attempts - 1:
                        delay = backoff ** attempt
                        logger.debug("Retry %d/%d in %ds: %s",
                                     attempt + 1, attempts, delay, exception)
                        time.sleep(delay)
            raise last_exception

        return f_retry

    return deco_retry


def _get_or_create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def _clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    return val


def _get_files_path(path):
    return os.path.splitext(path)[0] + "_files"


def _remove(path):
    os.remove(path)
    tiles_path = _get_files_path(path)
    shutil.rmtree(tiles_path)


_fetch_cache = {}


@retry(3)
def _fetch_url(path):
    """Fetch a URL or local path and return its bytes."""
    # `urllib` in Python 2 supported both local paths as well as URLs. Read
    # local paths directly: `urlparse` mistakes Windows drive letters (`C:\…`)
    # for URL schemes, and `#` or `%` in a naive `file://` URL get misread
    if os.path.exists(path) or not urlparse(path).scheme:
        with open(path, "rb") as f:
            return f.read()
    return urllib.request.urlopen(path).read()


def safe_open(path):
    if path in _fetch_cache:
        return io.BytesIO(_fetch_cache[path])
    return io.BytesIO(_fetch_url(path))


################################################################################


def main():
    parser = optparse.OptionParser(usage="Usage: %prog [options] filename")

    parser.add_option(
        "-d",
        "--destination",
        dest="destination",
        help="Set the destination of the output.",
    )
    parser.add_option(
        "-s",
        "--tile_size",
        dest="tile_size",
        type="int",
        default=254,
        help="Size of the tiles. Default: 254",
    )
    parser.add_option(
        "-f",
        "--tile_format",
        dest="tile_format",
        default=DEFAULT_IMAGE_FORMAT,
        help="Image format of the tiles (jpg or png). Default: jpg",
    )
    parser.add_option(
        "-o",
        "--tile_overlap",
        dest="tile_overlap",
        type="int",
        default=1,
        help="Overlap of the tiles in pixels (0-10). Default: 1",
    )
    parser.add_option(
        "-q",
        "--image_quality",
        dest="image_quality",
        type="float",
        default=0.8,
        help="Quality of the image output (0-1). Default: 0.8",
    )
    parser.add_option(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Log progress while creating tiles.",
    )
    parser.add_option(
        "-r",
        "--resize_filter",
        dest="resize_filter",
        default=DEFAULT_RESIZE_FILTER,
        help="Type of filter for resizing (bicubic, nearest, bilinear, lanczos (best). Default: lanczos",
    )

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(1)

    source = args[0]

    if options.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not options.destination:
        if os.path.exists(source):
            options.destination = os.path.splitext(source)[0] + ".dzi"
        else:
            options.destination = os.path.splitext(os.path.basename(source))[0] + ".dzi"
    if options.resize_filter and options.resize_filter in RESIZE_FILTERS:
        options.resize_filter = RESIZE_FILTERS[options.resize_filter]

    creator = ImageCreator(
        tile_size=options.tile_size,
        tile_format=options.tile_format,
        image_quality=options.image_quality,
        resize_filter=options.resize_filter,
    )
    creator.create(source, options.destination)


if __name__ == "__main__":
    main()
