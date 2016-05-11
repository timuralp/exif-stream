EXIF-Stream
=======
EXIF-Stream is a library to perform stream parsing of a JPEG/EXIF image.

The majority of this code was developed following an excellent write up of the
file format from
[here](http://www.media.mit.edu/pia/Research/deepview/exif.html).

The project is not quite complete and is lacking both in tests and
functionality. Consider it to be a very early version.

Example
-------

Here's a sample program using the stream parser to retrieve EXIF tags from a
photo in python:

```
from exifstream import stream
import sys

f = open(sys.argv[1], 'rb')

s = stream.StreamProcessor()
while True:
    chunk = f.read(100)
    if not chunk:
        break
    s.process(chunk)
for tag in s.tags:
    print tag
```
