# deepzoom.py: Python Deep Zoom Tools

## Installation

```bash
git clone https://github.com/openzoom/deepzoom.py.git
cd deepzoom.py
python setup.py install
```

## Development

Install for local development:

```
python3 -m pip install -e .
```

Run tests:

```
python3 -m pip install -e '.[test]'
python3 -m pytest
```

## Example

```bash
cd examples/helloworld/

# Single image (DZI)
./helloworld-dzi.py

# Collection (DZC)
./helloworld-dzc.py
```

The command line interface (`python deepzoom/__init__.py image.tif`) lifts
Pillow’s [decompression bomb][bomb] limit so it can convert very large images.
The library keeps the limit; to process large trusted images, set
`PIL.Image.MAX_IMAGE_PIXELS = None` yourself.

## Acknowledgements

Initially developed by [Kapil Thangavelu](mailto:kapil.foss@gmail.com).
Powered by [OpenZoom][].

## License

Licensed under the [New BSD Licence][bsd].

[bomb]: https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.open
[bsd]: http://www.opensource.org/licenses/bsd-license.php
[openzoom]: http://openzoom.org
[pil]: http://www.pythonware.com/products/pil
[pillow]: https://pillow.readthedocs.io/en/stable/installation.html#basic-installation
