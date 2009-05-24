#
#  Deep Zoom Tools
#
#  Copyright (c) 2008-2009, OpenZoom <http://openzoom.org/>
#  Copyright (c) 2008-2009, Daniel Gasienica <daniel@gasienica.ch>
#  Copyright (c) 2008,      Kapil Thangavelu <kapil.foss@gmail.com>
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

import math
import optparse
import os
import PIL.Image
import sys
import xml.dom.minidom

NS_DEEPZOOM = "http://schemas.microsoft.com/deepzoom/2008"

resize_filter_map = {
    "cubic": PIL.Image.CUBIC,
    "bilinear": PIL.Image.BILINEAR,
    "bicubic": PIL.Image.BICUBIC,
    "nearest": PIL.Image.NEAREST,
    "antialias": PIL.Image.ANTIALIAS,
    }

image_format_map = {
    "jpg": "jpg",
    "png": "png",
    }

class DeepZoomImageDescriptor(object):
    def __init__(self, width=None, height=None,
                 tile_size=254, tile_overlap=1, tile_format="jpg"):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.tile_format = tile_format
        self._num_levels = None

    def open(self, source):
        """Intialize descriptor from an existing descriptor file."""
        doc = xml.dom.minidom.parse(source)
        image = doc.getElementsByTagName("Image")[0]
        size = doc.getElementsByTagName("Size")[0]

        self.width = int(size.getAttribute("Width"))
        self.height = int(size.getAttribute("Height"))
        self.tile_size = int(image.getAttribute("TileSize"))
        self.tile_overlap = int(image.getAttribute("Overlap"))
        self.tile_format = image.getAttribute("Format")

    def save(self, destination):
        """Save descriptor file."""
        file = open(destination, "w")

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
#        descriptor = doc.toprettyxml(indent="    ", encoding="UTF-8")

        file.write(descriptor)
        file.close()

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
        w, h = self.get_dimensions( level )
        return (int(math.ceil(float(w) / self.tile_size)),
                int(math.ceil(float(h) / self.tile_size)))

    def get_tile_bounds(self, level, column, row):
        """Bounding box of the tile (x1, y1, x2, y2)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"

        offset_x = 0 if column == 0 else self.tile_overlap
        offset_y = 0 if row    == 0 else self.tile_overlap
        x = (column * self.tile_size) - offset_x
        y = (row    * self.tile_size) - offset_y

        level_width, level_height = self.get_dimensions(level)
        w = self.tile_size + (1 if column == 0 else 2) * self.tile_overlap
        h = self.tile_size + (1 if row    == 0 else 2) * self.tile_overlap
        w = min(w, level_width  - x)
        h = min(h, level_height - y)

        return (x, y, x + w, y + h)


class Image(object):
    """Represents a Deep Zoom image."""
    def __init__(self, path):
        self.path = path

    viewportOrigin = (0.0, 0.0)
    viewportWidth = 1.0
    max_viewport_width = None
    min_viewport_width = None


class ImageCreator(object):
    """Creates Deep Zoom images."""
    def __init__(self, tile_size=254, tile_overlap=1, tile_format="jpg",
                 image_quality=0.95, resize_filter=None):
        self.tile_size = int(tile_size)
        self.tile_format = tile_format
        self.tile_overlap = _clamp(int(tile_overlap), 0, 10)
        self.image_quality = _clamp(image_quality, 0, 1.0)
        if not tile_format in image_format_map:
            self.tile_format = "jpg"
        self.resize_filter = resize_filter

    def get_image(self, level):
        """Returns the bitmap image at the given level."""
        assert 0 <= level and level < self.descriptor.num_levels, "Invalid pyramid level"
        width, height = self.descriptor.get_dimensions(level)
        # don't transform to what we already have
        if self.descriptor.width == width and self.descriptor.height == height:
            return self.image
        if (self.resize_filter is None) or (self.resize_filter not in resize_filter_map):
            return self.image.resize((width, height), PIL.Image.ANTIALIAS)
        return self.image.resize((width, height), resize_filter_map[self.resize_filter])

    def tiles(self, level):
        """Iterator for all tiles in the given level. Returns (column, row) of a tile."""
        columns, rows = self.descriptor.get_num_tiles(level)
        for column in xrange(columns):
            for row in xrange(rows):
                yield (column, row)

    def create(self, source, destination):
        """Creates Deep Zoom image from source file and saves it to destination."""
        self.image = PIL.Image.open(source)
        width, height = self.image.size
        self.descriptor = DeepZoomImageDescriptor(width=width,
                                        height=height,
                                        tile_size=self.tile_size,
                                        tile_overlap=self.tile_overlap,
                                        tile_format=self.tile_format)
        destination = _expand(destination)
        image_name = os.path.splitext(os.path.basename(destination))[0]
        dir_name = os.path.dirname(destination)
        image_files = _ensure(os.path.join(_ensure(dir_name), "%s_files"%image_name))

        # Create tiles
        for level in xrange(self.descriptor.num_levels):
            level_dir = _ensure(os.path.join(image_files, str(level)))
            level_image = self.get_image(level)
            for (column, row) in self.tiles(level):
                bounds = self.descriptor.get_tile_bounds(level, column, row)
                tile = level_image.crop(bounds)
                format = self.descriptor.tile_format
                tile_path = os.path.join(level_dir,
                                         "%s_%s.%s"%(column, row, format))
                tile_file = open(tile_path, "wb")
                if self.descriptor.tile_format == "jpg":
                    tile.save(tile_file, "JPEG",
                              quality=int(self.image_quality * 100))
                tile.save(tile_file)

        # Create descriptor
        self.descriptor.save(destination)


class CollectionCreator(object):
    """Creates Deep Zoom collections."""
    def __init__(self, image_quality=0.95, tile_size=254,
                 max_level=8, tile_format="jpg", copy_metadata=True):
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.copy_metadata = copy_metadata #unused

    def _get_position(self, z_order):
        """Returns position (column, row) from given Z-order (Morton number.)"""
        column = 0
        row = 0
        for i in xrange(0, 32, 2):
            offset = i / 2
            # column
            column_offset = i
            column_mask = 1 << column_offset
            column_value = (z_order & column_mask) >> column_offset
            column |= column_value << offset
            #row
            row_offset = i + 1
            row_mask = 1 << row_offset
            row_value = (z_order & row_mask) >> row_offset
            row |= row_value << offset
        return int(column), int(row)

    def _get_z_order(self, column, row):
        """Returns the Z-order (Morton number) from given position."""
        z_order = 0
        for i in xrange(32):
            z_order |= (column & 1 << i) << i | (row & 1 << i) << (i + 1)
        return z_order

    def _get_tile_position(self, z_order, level, tile_size):
        level_size = 2**level
        x, y = self._get_position(z_order)
        return (int(math.floor((x * level_size) / tile_size)),
                int(math.floor((y * level_size) / tile_size)))

    def create(self, images, destination):
        """Creates a Deep Zoom collection from a list of images."""
        self._create_pyramid(images, destination)
        self._create_descriptor(images, destination)

    def _create_pyramid(self, images, destination):
        """Creates a Deep Zoom collection pyramid from a list of images."""
        pyramid_path = os.path.splitext(destination)[0] + "_files"
        if not os.path.exists(pyramid_path):
            os.mkdir(pyramid_path)

        for level in xrange(self.max_level + 1):
            level_size = 2**level
            level_path = pyramid_path + "/" + str(level)
            if not os.path.exists(level_path):
                os.mkdir(level_path)

            for i in xrange(len(images)):
                path = images[i]
                descriptor = DeepZoomImageDescriptor()
                descriptor.open(path)
                column, row = self._get_tile_position(i, level, self.tile_size)
                tile_path = level_path + "/%s_%s.%s"%(column, row, self.tile_format)
                if not os.path.exists(tile_path):
                    tile_image = PIL.Image.new("RGB", (self.tile_size, self.tile_size))
                    tile_image.save(tile_path, "JPEG", quality=int(self.image_quality * 100))
                tile_image = PIL.Image.open(tile_path)
                source_path = open(os.path.splitext(path)[0] + "_files/" + str(level) + "/%s_%s.%s"%(0, 0, descriptor.tile_format))
                source_image = PIL.Image.open(source_path)
                images_per_tile = int(math.floor(self.tile_size / level_size))
                column, row = self._get_position(i)
                x = (column % images_per_tile) * level_size
                y = (row % images_per_tile) * level_size
                tile_image.paste(source_image, (x,y))
                tile_image.save(tile_path)

    def _create_descriptor(self, images, destination):
        """Creates a Deep Zoom collection descriptor from a list of images."""
        doc = xml.dom.minidom.Document()
        collection = doc.createElementNS(NS_DEEPZOOM, "Collection")
        collection.setAttribute("xmlns", NS_DEEPZOOM)
        collection.setAttribute("MaxLevel", str(self.max_level))
        collection.setAttribute("TileSize", str(self.tile_size))
        collection.setAttribute("Format", str(self.tile_format))
        collection.setAttribute("Quality", str(self.image_quality))

        items = doc.createElementNS(NS_DEEPZOOM, "Items")

        next_item_id = 0
        for path in images:
            descriptor = DeepZoomImageDescriptor()
            descriptor.open(path)
            id = next_item_id
            n = next_item_id
            source = path # relative path
            width = descriptor.width
            height = descriptor.height

            item = doc.createElementNS(NS_DEEPZOOM, "I")
            item.setAttribute("Id", str(id))
            item.setAttribute("N", str(n))
            item.setAttribute("Source", str(source))

            size = doc.createElementNS(NS_DEEPZOOM, "Size")
            size.setAttribute("Width", str(width))
            size.setAttribute("Height", str(height))
            item.appendChild(size)

            items.appendChild(item)
            next_item_id += 1

        collection.setAttribute("NextItemId", str(next_item_id))

        collection.appendChild(items)
        doc.appendChild(collection)

        descriptor = doc.toxml(encoding="UTF-8")
#        descriptor = doc.toprettyxml(indent="  ", encoding="UTF-8")
        file = open(destination, "w")
        file.write(descriptor)
        file.close()


################################################################################

def _expand(d):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(d)))

def _ensure(d):
    if not os.path.exists(d):
        os.mkdir(d)
    return d

def _clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    return val

################################################################################

def main():
    parser = optparse.OptionParser(usage="Usage: %prog [options] filename")

    parser.add_option("-d", "--destination", dest="destination",
                      help="Set the destination of the output.")

    parser.add_option("-s", "--tile_size", dest="tile_size", type="int",
                      default=254, help="Size of the tiles. Default: 254")
    parser.add_option("-f", "--tile_format", dest="tile_format",
                      default="jpg", help="Image format of the tiles \
                                          (jpg or png). Default: jpg")
    parser.add_option("-o", "--tile_overlap", dest="tile_overlap", type="int",
                      default=1, help="Overlap of the tiles in pixels (0-10). Default: 1")
    parser.add_option("-q", "--image_quality", dest="image_quality", type="float",
                      default=0.95, help="Quality of the image output (0-1). Default: 0.95")
    parser.add_option("-r", "--resize_filter", dest="resize_filter", default="antialias",
                      help="Type of filter for resizing (bicubic, nearest, \
                            bilinear, antialias (best). Default: antialias")

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(1)
    source = _expand(args[0])

    if not os.path.exists(source):
        print "Invalid File", source
        sys.exit(1)

    if not options.destination:
        options.destination = os.path.splitext(source)[0] + ".dzi"
    if options.resize_filter and options.resize_filter in resize_filter_map:
        options.resize_filter = resize_filter_map[options.resize_filter]

    creator = ImageCreator(tile_size=options.tile_size,
                           tile_format=options.tile_format,
                           image_quality=options.image_quality,
                           resize_filter=options.resize_filter)
    creator.create(source, options.destination)

if __name__ == "__main__":
    main()