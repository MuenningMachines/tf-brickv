# -*- coding: utf-8 -*-
"""
brickv (Brick Viewer)
Copyright (C) 2012-2015 Matthias Bolte <matthias@tinkerforge.com>

config_common.py: Common Config Handling

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this program; if not, write to the
Free Software Foundation, Inc., 59 Temple Place - Suite 330,
Boston, MA 02111-1307, USA.
"""

import sys
import logging

from brickv.utils import get_resources_path

LOGGING_LEVEL = logging.ERROR
LOGGING_FORMAT = '%(asctime)s <%(levelname)s> <%(filename)s:%(lineno)s> %(message)s'
LOGGING_DATEFMT = '%Y-%m-%d %H:%M:%S'

BRICKV_VERSION = '2.4.14'

HOST_INFO_COUNT = 10

DEFAULT_HOST = 'localhost'
DEFAULT_PORT = 4223

DEFAULT_USE_AUTHENTICATION = False
DEFAULT_SECRET = ''
DEFAULT_REMEMBER_SECRET = False

# host|port|use_authentication|remember_secret|secret
DEFAULT_HOST_INFO = 'localhost|4223|0|0|'

DEFAULT_USE_FUSION_GUI_STYLE = sys.platform == 'darwin'

DEFAULT_AUTO_SEARCH_FOR_UPDATES = True

def load_marker_file(name):
    try:
        # Don't warn if the file is missing, as it is expected when run from source.
        path = get_resources_path(name, warn_on_missing_file=False)

        if path is not None:
            with open(path, 'r') as f:
                return f.read().strip()
    except FileNotFoundError:
        pass

    return None

INTERNAL = load_marker_file('internal')

SNAPSHOT = load_marker_file('snapshot')

PACKAGE_TYPE = load_marker_file('package_type')

BRICKV_FULL_VERSION = BRICKV_VERSION

if INTERNAL != None:
    BRICKV_FULL_VERSION += '+internal~{}'.format(INTERNAL)
elif SNAPSHOT != None:
    BRICKV_FULL_VERSION += '+snapshot~{}'.format(SNAPSHOT)
