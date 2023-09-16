'''This module defines a convenient API to access the hardware blobs'''

from . import blob_parsers, error, publicapi
from .capi.py import libah_api


def write_blob(blob_type, data, ctx=None):
    '''Write the content of the specified blob'''
    # We expect the data to match the latest blob version format
    # if it fails to create a blob v<latest> out of the data, we don't write it
    blob_version = publicapi.BlobVersion[blob_type.name].value
    try:
        blob_data = blob_parsers.create_blob(blob_type, blob_version, ctx, data)
    except ValueError as excp:
        raise error.Error(str(excp))
    libah_api.write_blob(blob_type, blob_data)


def read_blob(blob_type, ctx=None):
    '''Read the content of the specified blob'''
    blob_data = libah_api.read_blob(blob_type)
    try:
        return blob_parsers.parse_blob(blob_type, ctx, blob_data).data
    except ValueError as excp:
        raise error.Error(str(excp))
