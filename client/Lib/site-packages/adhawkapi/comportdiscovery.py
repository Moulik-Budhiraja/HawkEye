'''This module provides the ability to discover and connect to AdHawk devices'''

import os
import re
import platform
import subprocess
import serial.tools.list_ports

from adhawkapi.supported_devices import SUPPORTED_DEVICES


def compatible_ports(supported_devices=None):
    '''Returns list of AdHawk's devices currently available on this system'''
    if supported_devices is None:
        supported_devices = SUPPORTED_DEVICES

    devices = {port.device: get_device_info(port)
               for port in serial.tools.list_ports.comports()}

    port_list = [f'{device}'
                 for device, info in devices.items()
                 for vendid, devid, suffix in supported_devices
                 if info[0] == vendid and info[1] == devid]

    try:
        spi_device_name = '/dev/spidev0.0'
        os.stat(spi_device_name)
        port_list.append(spi_device_name)
    except OSError:
        pass

    return port_list


def compatible_ports_info(supported_devices=None):
    '''Returns a detailed list of AdHawk's devices currently available on this system'''
    if supported_devices is None:
        supported_devices = SUPPORTED_DEVICES

    devices = {port.device: get_device_info(port)
               for port in serial.tools.list_ports.comports()}

    return [(info[0], info[1], device, suffix)
            for device, info in devices.items()
            for vendid, devid, suffix in supported_devices
            if info[0] == vendid and info[1] == devid]


def get_device_info(port):
    '''Retrieve vid and pid. Linux support only'''

    # pylint: disable=too-many-return-statements

    # linux function only
    if 'linux' not in platform.system().lower():
        return (port.vid, port.pid)

    device = port.device
    args = ['ls', '-l', device]
    try:
        proc = subprocess.run(args, capture_output=True, check=True,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.CalledProcessError:
        # instead of raising an exception, assume failed search and return invalid device
        return (0, 0)

    info = re.search('([0-9]+), ([0-9]+)', proc.stdout.decode())
    if not info:
        # instead of raising an exception, assume failed search and return invalid device
        return (0, 0)

    major = info.group(1)
    minor = info.group(2)

    devpath = f'/sys/dev/char/{major}:{minor}'
    args = ['ls', '-l', devpath]
    try:
        proc = subprocess.run(args, capture_output=True, check=True,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.CalledProcessError:
        # instead of raising an exception, assume failed search and return invalid device
        return (0, 0)

    truepath = re.search(r'(\-\> )(.*)', proc.stdout.decode())
    if not truepath:
        # instead of raising an exception, assume failed search and return invalid device
        return (0, 0)

    # dict to populate with device info
    dev = {}
    devpath = "/sys/" + truepath.group(2).split("../")[-1]

    while devpath:
        vidfile = devpath + "/idVendor"
        pidfile = devpath + "/idProduct"
        if os.path.isfile(pidfile) and os.path.isfile(vidfile):
            with open(vidfile, 'r') as vidpath:
                dev["vid"] = int(vidpath.readline(), 16)
            with open(pidfile, 'r') as pidpath:
                dev["pid"] = int(pidpath.readline(), 16)
            break
        devpath = devpath.rsplit("/", 1)[0]

    if not dev:
        # instead of raising an exception, assume failed search and return invalid device
        return (0, 0)

    return (dev["vid"], dev["pid"])
