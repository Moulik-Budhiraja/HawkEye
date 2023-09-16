''' This module contains a class to hold firmware info data,
 and a helper function to get eyes and trackers from ocular mode.'''

import typing

from . import defaults, registers
from .version import SemanticVersion


class KitInfo(typing.NamedTuple):
    '''Helper container to cache Firmware related information'''
    serial_num: str
    active_trackers: list
    active_eyes: list
    product_id: registers.SpecProductId
    camera_type: registers.SpecCamera
    safe_mode: bool
    api_version: SemanticVersion
    firmware_version: str


def get_active_eyes_and_trackers(ocular_mode):
    '''Helper function to get active eyes and active trackers from ocular mode'''
    active_eyes = []
    for eye in range(defaults.MAX_EYES):
        if ocular_mode & 1 << eye:
            active_eyes.append(eye)

    active_trackers = []
    for tracker_id in range(defaults.MAX_SCANNERS):
        # In the future, check the capability of each tracker to determine
        # which eye they belong to
        if ocular_mode & 1 << (tracker_id % defaults.MAX_EYES):
            active_trackers.append(tracker_id)
    return active_eyes, active_trackers
