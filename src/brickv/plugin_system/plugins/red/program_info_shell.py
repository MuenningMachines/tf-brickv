# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015 Matthias Bolte <matthias@tinkerforge.com>

program_info_shell.py: Program Shell Info Widget

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
from brickv.plugin_system.plugins.red.ui_program_info_shell import Ui_ProgramInfoShell

class ProgramInfoShell(ProgramInfo, Ui_ProgramInfoShell):
    def __init__(self, context):
        ProgramInfo.__init__(self, context)

        self.setupUi(self)

        self.check_show_advanced_options.stateChanged.connect(self.update_ui_state)

    # overrides ProgramInfo.update_ui_state
    def update_ui_state(self):
        show_advanced_options = self.check_show_advanced_options.isChecked()

        # version
        def cb_shell_versions(versions):
            for version in versions:
                if version.executable == self.program.executable:
                    self.label_version.setText(version.version)
                    return

            self.label_version.setText('<unknown>')

        self.get_executable_versions('shell', cb_shell_versions)

        # start mode
        start_mode_api_name    = self.program.cast_custom_option_value('shell.start_mode', str, '<unknown>')
        start_mode             = Constants.get_shell_start_mode(start_mode_api_name)
        start_mode_script_file = start_mode == Constants.SHELL_START_MODE_SCRIPT_FILE
        start_mode_command     = start_mode == Constants.SHELL_START_MODE_COMMAND

        self.label_start_mode.setText(Constants.shell_start_mode_display_names[start_mode])

        # script file
        self.label_script_file_title.setVisible(start_mode_script_file)
        self.label_script_file.setVisible(start_mode_script_file)
        self.label_script_file.setText(self.program.cast_custom_option_value('shell.script_file', str, '<unknown>'))

        # command
        self.label_command_title.setVisible(start_mode_command)
        self.label_command.setVisible(start_mode_command)
        self.label_command.setText(self.program.cast_custom_option_value('shell.command', str, '<unknown>'))

        # working directory
        self.label_working_directory_title.setVisible(show_advanced_options)
        self.label_working_directory.setVisible(show_advanced_options)
        self.label_working_directory.setText(self.program.working_directory)

        # options
        self.label_options_title.setVisible(show_advanced_options)
        self.label_options.setVisible(show_advanced_options)
        self.label_options.setText('\n'.join(self.program.cast_custom_option_value_list('shell.options', str, [])))
