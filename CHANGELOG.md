# Changelog

## Version 2.0.0a2 – January 16, 2020

- Format code using [Black].

## Version 2.0.0a1 – January 16, 2020

- Port to Python 3.

## Version 1.0.0 – October 6, 2011

- Add workaround for [IIP] bug that causes it to serve low-level tiles with
  wrong dimensions.
- Add `DeepZoomCollection.remove` and `DeepZoomImageDescriptor.remove` class
  methods for removing descriptors and their corresponding tiles folders.

## Version 0.9.4 – September 9, 2011

- Add sample image and made example script executable.
- Add instructions for installing PIL.

## Version 0.9 – November 14, 2010

- Fix issue #1: Bug in the tile saving in ImageCreator.create.
- Set `CollectionCreator` `max_level` default to `7`.
- Set `CollectionCreator` `tile_size` default to `256`.

## Version 0.1.2 – May 24, 2009

- Rename `DZIDescriptor` to `DeepZoomImageDescriptor` for consistency with the
  OpenZoom SDK descriptor framework.

## Version 0.1.1 – April 8, 2009

- Remove unnecessary `urllib2` import.
- Add description of dependencies.

## Version 0.1.0 – March 23, 2009

- First release. Nothing is new, or everything is new, depending on how you
  think about it. -- _Google_

[black]: https://black.readthedocs.io/en/stable/
[iip]: http://iipimage.sourceforge.net/
