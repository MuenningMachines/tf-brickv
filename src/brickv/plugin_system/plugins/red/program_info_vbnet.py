# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015 Matthias Bolte <matthias@tinkerforge.com>

program_info_vbnet.py: Program Visual Basic .NET Info Widget

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

from brickv.plugin_system.plugins.red.program_info import ProgramInfo
from brickv.plugin_system.plugins.red.program_utils import Constants
from brickv.plugin_system.plugins.red.ui_program_info_vbnet import Ui_ProgramInfoVBNET

class ProgramInfoVBNET(ProgramInfo, Ui_ProgramInfoVBNET):
    def __init__(self, context):
        ProgramInfo.__init__(self, context)

        self.setupUi(self)

        self.check_show_advanced_options.stateChanged.connect(self.update_ui_state)

    # overrides ProgramInfo.update_ui_state
    def update_ui_state(self):
        show_advanced_options = self.check_show_advanced_options.isChecked()

        # version
        def cb_mono_versions(versions):
            for version in versions:
                if version.executable == self.program.executable:
                    self.label_version.setText(version.version)
                    return

            self.label_version.setText('<unknown>')

        self.get_executable_versions('mono', cb_mono_versions)

        # start mode
        start_mode_api_name   = self.program.cast_custom_option_value('vbnet.start_mode', str, '<unknown>')
        start_mode            = Constants.get_vbnet_start_mode(start_mode_api_name)
        start_mode_executable = start_mode == Constants.VBNET_START_MODE_EXECUTABLE

        self.label_start_mode.setText(Constants.vbnet_start_mode_display_names[start_mode])

        # executable
        self.label_executable_title.setVisible(start_mode_executable)
        self.label_executable.setVisible(start_mode_executable)
        self.label_executable.setText(self.program.cast_custom_option_value('vbnet.executable', str, '<unknown>'))

        # working directory
        self.label_working_directory_title.setVisible(show_advanced_options)
        self.label_working_directory.setVisible(show_advanced_options)
        self.label_working_directory.setText(self.program.working_directory)

        # options
        self.label_options_title.setVisible(show_advanced_options)
        self.label_options.setVisible(show_advanced_options)
        self.label_options.setText('\n'.join(self.program.cast_custom_option_value_list('vbnet.options', str, [])))
