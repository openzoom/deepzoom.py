# deepzoom.py: Python Deep Zoom Tools

## Installation

    git clone https://github.com/openzoom/deepzoom.py.git
    cd deepzoom.py
    python setup.py install
    
## Example

    cd deepzoom.py/examples/helloworld/
    ./helloworld.py

## Dependencies

- [Python Imaging Library (PIL)](http://www.pythonware.com/products/pil)

### Installation

  1. [Get `pip`](http://www.pip-installer.org/en/latest/installing.html)
  2. Run `sudo pip install pil`
  3. Run `python`
  4. Enter `import PIL` and make sure there’s no error
  5. Congratulations, you’re ready to use `deepzoom.py`
  
### Resources

  - [Google App Engine: Installing PIL](http://code.google.com/appengine/docs/python/images/installingPIL.html)
  - [Installing PIL on Mac OS X Lion](http://bencrowder.net/blog/2011/08/installing-pil-on-lion/)
  - [Building PIL on OS X: Snow Leopard](http://bradmontgomery.blogspot.com/2010/02/building-pil-on-os-x-snow-leopard.html)


## Acknowledgements
  
Initially developed by [Kapil Thangavelu](mailto:kapil.foss@gmail.com).
Powered by [OpenZoom](http://openzoom.org).

## License

Licensed under the [New BSD Licence](http://www.opensource.org/licenses/bsd-license.php).
  
## Changelog
  
### Version 0.9.4 – September 9, 2011
  
  - Added sample image and made example script executable.
  - Added instructions for installing PIL.
  
### Version 0.9 – November 14, 2010
  
  - Fixed issue #1: Bug in the tile saving in ImageCreator.create.
  - Set `CollectionCreator` `max_level` default to `7`.
  - Set `CollectionCreator` `tile_size` default to `256`.

### Version 0.1.2 – May 24, 2009

  - Renamed `DZIDescriptor` to `DeepZoomImageDescriptor` for
    consistency with the OpenZoom SDK descriptor framework.
  
###  Version 0.1.1 – April 8, 2009

  - Removed unnecessary `urllib2` import.
  - Added description of dependencies.
  
  
### Version 0.1.0 – March 23, 2009

  - First release. Nothing is new, or everything is new,
    depending on how you think about it. -- *Google*
