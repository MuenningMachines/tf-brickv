# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014, 2017 Matthias Bolte <matthias@tinkerforge.com>

program_info.py: Program Info Widget

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

from collections import namedtuple

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWidget

ProgramInfoContext = namedtuple('ProgramInfoContext', 'session script_manager executable_versions program')

class ProgramInfo(QWidget):
    def __init__(self, context):
        super().__init__()

        self.session             = context.session
        self.script_manager      = context.script_manager
        self.executable_versions = context.executable_versions
        self.program             = context.program

    def update_ui_state(self):
        pass

    def close_all_dialogs(self):
        pass

    # to be used on language configuratiopn pages
    def get_executable_versions(self, executable_name, callback):
        def cb_get():
            versions = self.executable_versions[executable_name]

            if versions == None:
                QTimer.singleShot(100, cb_get)
                return

            callback(versions)

        if self.executable_versions[executable_name] == None:
            QTimer.singleShot(100, cb_get)
        else:
            cb_get()

    # to be overriden on language configuratiopn pages
    def get_language_action(self):
        return None, 'None'
