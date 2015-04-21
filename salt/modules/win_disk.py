# -*- coding: utf-8 -*-
'''
Module for gathering disk information on Windows

:depends:   - win32api Python module
'''

# Import python libs
import ctypes
import string

# Import salt libs
import salt.utils

try:
    import win32api
except ImportError:
    pass

# Define the module's virtual name
__virtualname__ = 'disk'


def __virtual__():
    '''
    Only works on Windows systems
    '''
    if salt.utils.is_windows():
        return __virtualname__
    return False


def usage():
    '''
    Return usage information for volumes mounted on this minion

    CLI Example:

    .. code-block:: bash

        salt '*' disk.usage
    '''
    drives = []
    ret = {}
    drive_bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.uppercase:
        if drive_bitmask & 1:
            drives.append(letter)
        drive_bitmask >>= 1
    for drive in drives:
        try:
            (available_bytes,
             total_bytes,
             total_free_bytes) = win32api.GetDiskFreeSpaceEx(
                 '{0}:\\'.format(drive)
            )
            used = total_bytes - total_free_bytes
            capacity = used / float(total_bytes) * 100
            ret['{0}:\\'.format(drive)] = {
                'filesystem': '{0}:\\'.format(drive),
                '1K-blocks': total_bytes / 1024,
                'used': used / 1024,
                'available': total_free_bytes / 1024,
                'capacity': '{0:.0f}%'.format(capacity),
            }
        except Exception:
            ret['{0}:\\'.format(drive)] = {
                'filesystem': '{0}:\\'.format(drive),
                '1K-blocks': None,
                'used': None,
                'available': None,
                'capacity': None,
            }
    return ret
