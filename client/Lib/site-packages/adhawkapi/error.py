'''This module defines common error types for all API modules'''


class Error(Exception):
    '''Base class for all errors in the Adhawk API'''
    pass


class CommunicationError(Error):
    '''Base class for all communication related errors in the API'''
    pass


class RecoverableCommunicationError(Error):
    '''Base class for all non-critical communication related errors in the API

    This class should be used for errors that shouldn't necessarily terminate
    the application, but it's nice to be noted rather than silently ignored
    '''
    pass


class InternalError(Error):
    '''Unrecoverable programmatic errors'''
    pass
