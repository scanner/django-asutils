#
# File: $Id: sendfile.py 1824 2008-10-13 08:44:36Z scanner $
#
"""
The source code in this file originally came from:

    http://www.djangosnippets.org/snippets/365/
    
"""

import os
import os.path
import tempfile
import zipfile
import re

from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper

http_range_re = re.compile('^bytes=(?P<start>\d+)?-(?P<end>\d+)?')

####################################################################
#
def handle_uploaded_file(f, destination):
    """
    A convenience method that handles the work of writing an uploaded file
    to its destination.
    
    Arguments:
    - `f`: file like thing that lets us get an uploaded file in chunks.
    - `destination`: The name of the file we are going to write this data to.
    """
    print "Writing file to: '%s'" % destination
    d = open(destination, 'wb+')
    for chunk in f.chunks():
        d.write(chunk)
    d.close()
    return

#############################################################################
#
def send_file(request, filename, content_type='text/plain', blksize = 8192):
    """                                                                         
    Send a file through Django without loading the whole file into              
    memory at once. The FileWrapper will turn the file object into an           
    iterator for chunks of 8KB.                                                 
    """
    wrapper = FileWrapper(file(filename), blksize = blksize)
    response = HttpResponse(wrapper, content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename=%s' % \
                                      os.path.basename(filename)
    response['Content-Length'] = os.path.getsize(filename)
    return response

#############################################################################
#
def send_zipfile(request, filename):
    """                                                                         
    Create a ZIP file on disk and transmit it in chunks of 8KB,                 
    without loading the whole file into memory. A similar approach can          
    be used for large dynamic PDF files.                                        
    """
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    for index in range(10):
        archive.write(filename, 'file%d.txt' % index)
    archive.close()
    wrapper = FileWrapper(temp)
    response = HttpResponse(wrapper, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=%s.zip' % \
                                      os.path.basename(filename)
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response

#############################################################################
#
class StreamFileWrapper(FileWrapper):
    """
    our 'stream_file' function uses the StreamFileWrapper to enclose the file
    being streamed so that when django is sending the bits back to the client
    that is when the file is read from and sent out incrementally.

    Basically this enhances the FileWrapper to send the part of a file between
    'start' and 'end' passed in to __init__.
    """

    #########################################################################
    #
    def __init__(self, filelike, start, end, blksize = 131072):
        """
        Call our parent's initialize. Then set our start/end/curr pointers and
        seek the file to that position.
        """
        if start > end:
            raise NameError("request end must be greater or equal to start. Start: %d, end: %d" % (start, end))
        
        FileWrapper.__init__(self, filelike, blksize)
        self.start = start
        self.curr = start
        self.end = end
        self.filelike.seek(self.start, 0)

    #########################################################################
    #
    def __uread__(self):
        """
        __getitem__() and next() have the same underlying routine. The only
        differnce is that __getitem__() raises IndexError if there is nothing
        left to read while next() raises StopIteration. (also __getitem__() is
        handed a key, which we ignore.

        This function returns None when there is no more input. The calling
        routine figures out what exception to raise.

        NOTE: This will advance self.curr.
        """
        if self.curr >= self.end:
            return None

        data = self.filelike.read(min(self.blksize, (self.end - self.curr) + 1))

        if data:
            self.curr += len(data)
            
        return data
        
    #########################################################################
    #
    def __getitem__(self,key):
        data = self.__uread__()
        if data:
            return data
        raise IndexError

    #########################################################################
    #
    def next(self):
        data = self.__uread__()
        if data:
            return data
        raise StopIteration
    
#############################################################################
#
def stream_file(request, filename, content_type):
    """
    This method is used to stream media files and the like to a
    client. Basically this is used to honor partial and range fetches.

    NOTE: Since clients can stream really large files (HD movies, for instance,
    will well over 4gb for 1080p) it is extremely questionable to have this
    being passed through a django instance. Perhaps we should have a C program
    that does the actual streaming and have the media server redirect to it.
    """

    size = os.path.getsize(filename)
    
    # Pull out of the 'http_range' header the information for what bits and
    # bytes to send to the client. If no 'http_range' header exists, then
    # they want the entire range.
    #
    if request.META.has_key('HTTP_RANGE'):
        search = http_range_re.search(request.META['HTTP_RANGE'])
        if search.group('start'):
            fstart = int(search.group('start'))
        else:
            fstart = 0
            
        if search.group('end'):
            fend = int(search.group('end'))
        else:
            fend = size - 1
    else:
        fstart = 0
        fend = size - 1

    num_bytes = fend - fstart + 1;

    wrapper = StreamFileWrapper(file(filename), fstart, fend)

    # If the number of bytes we need to send equals the file size
    # then we can send back a complete response. Otherwise
    # we need to send babck a partial content response.
    #
    if num_bytes == size:
        response = HttpResponse(wrapper, content_type = str(content_type))
        response['Content-Length'] = str(size)
        response['Accept-Ranges'] = 'bytes'
    else:
        response = HttpResponse(wrapper, status = 206,
                                content_type = str(content_type))
        response['Content-Range'] = 'bytes %d-%d/%d' % (fstart, fend, size)
        response['Content-Length'] = str(num_bytes)
            
    return response
