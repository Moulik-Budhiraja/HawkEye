'''This module contains set of helper routines used throughout the API layer'''

import struct

from .error import CommunicationError, RecoverableCommunicationError


class BadRequestError(CommunicationError):
    '''Bad request received'''


class BadResponseError(CommunicationError):
    '''Request received a bad response'''


class BadStreamData(RecoverableCommunicationError):
    '''When the stream data didn't match the expected format'''


def unpack_request(fmt, buffer):
    '''Wrapper for struct.unpack to convert its exceptions to our own'''
    try:
        return struct.unpack(fmt, buffer)
    except struct.error as excp:
        raise BadRequestError('Request didn\'t match expected format:\n'
                              f'{excp}\nformat: {fmt}\nbuffer: {buffer}')


def unpack_response(fmt, buffer):
    '''Wrapper for struct.unpack to convert its exceptions to our own'''
    try:
        return struct.unpack(fmt, buffer)
    except struct.error as excp:
        raise BadResponseError('Response didn\'t match expected format:\n'
                               f'{excp}\nformat: {fmt}\nbuffer: {buffer}')


def unpack_stream(fmt, buffer, offset=0):
    '''Wrapper for struct.unpack to convert its exceptions to our own'''
    try:
        return struct.unpack_from(fmt, buffer, offset)
    except struct.error as excp:
        raise BadStreamData('Invalid stream data:\n'
                            f'{excp}\nformat: {fmt}\nbuffer: {buffer}')


def unpack_iter_stream(fmt_const, fmt_iter, buffer, offset=0):
    '''Wrapper for struct.unpack and struct.iter_unpack to:
        - repack all iterations into a single flat tuple
        - convert its exceptions to our own
    '''
    try:
        const_data = struct.unpack_from(fmt_const, buffer, offset)
        stream_iter = struct.iter_unpack(fmt_iter, buffer[offset + struct.calcsize(fmt_const):])
        return const_data + tuple(data for stream in stream_iter for data in stream)
    except struct.error as excp:
        raise BadStreamData('Invalid iter stream data:\n'
                            f'{excp}\nformat const: {fmt_const}\nformat iter: '
                            f'{fmt_iter}\nbuffer: {buffer}')


def str2bool(val):
    '''Helper routine to convert a string ('true' or 'false') to bool.

    Note that both 'true' and 'false' strings evaluate to True. So we have to
    explicitly checked the value of the string.

    Also note that the conversion is case insensitive to accomodate windows+mac,
    since the different underlying storage may behave differently

    '''

    temp = str(val)
    return temp.lower() == 'true'
