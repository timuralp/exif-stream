EXIF-Stream
=======
EXIF-Stream is a library to perform stream parsing of a JPEG/EXIF image.

The majority of this code was developed following an excellent write up of the
file format from
[here](http://www.media.mit.edu/pia/Research/deepview/exif.html).

The project is not quite complete and is lacking both in tests and
functionality. Notably, it is currently missing parsing of the sub-IFD tags for
the camera information. I also have not tested it with any photos that include
thumbnails.
