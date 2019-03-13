# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015, 2017 Matthias Bolte <matthias@tinkerforge.com>

program_page.py: Program Wizard Page

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

import time
import html

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QWizardPage, QMessageBox

from brickv.plugin_system.plugins.red.api import *
from brickv.plugin_system.plugins.red.program_utils import *
from brickv.utils import get_main_window

class ProgramPage(QWizardPage):
    # makes QWizardPage.field virtual
    def get_field(self, name):
        return self.wizard().get_field(name)

    def update_ui_state(self):
        pass

    def set_formatted_sub_title(self, sub_title):
        language = Constants.language_display_names[self.get_field('language')]
        name     = html.escape(self.get_field('name'))

        self.setSubTitle(sub_title.format(**{'language': language, 'name': name}))

    # to be used on all edit pages
    def set_last_edit_timestamp(self):
        program = self.wizard().program

        if program == None:
            return

        try:
            program.set_custom_option_value('last_edit', int(time.time())) # FIXME: async_call
        except (Error, REDError) as e:
            QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                 'Could not update last edit timestamp of program [{0}]:\n\n{1}'
                                 .format(program.cast_custom_option_value('name', str, '<unknown>'), e))

    # to be used on language configuration pages
    def get_executable_versions(self, executable_name, callback):
        def cb_get():
            versions = self.wizard().executable_versions[executable_name]

            if versions == None:
                # if executable version is still not set, try again in 100 msec
                QTimer.singleShot(100, cb_get)
                return

            callback(versions)

        # if executable version is not set yet, try again in 100 msec
        if self.wizard().executable_versions[executable_name] == None:
            QTimer.singleShot(100, cb_get)
        else:
            cb_get()

    # to be used on language configuration pages
    def update_combo_version(self, executable_name, combo_version):
        def cb_update(versions):
            combo_version.clear()

            for version in versions:
                combo_version.addItem(version.version, version.executable)

            # if a program exists then this page is used in an edit wizard
            if self.wizard().program != None:
                executable = self.wizard().program.executable

                if len(executable) > 0:
                    set_current_combo_index_from_data(combo_version, executable)

            combo_version.setEnabled(True)
            self.completeChanged.emit()

        self.get_executable_versions(executable_name, cb_update)

    # to be used on language configuration pages
    def apply_program_custom_options_and_command_changes(self):
        program = self.wizard().program

        if program == None:
            return False

        # command
        command = self.get_command()

        if command != None:
            executable, arguments, environment, working_directory = command

            editable_arguments_offset   = max(program.cast_custom_option_value('editable_arguments_offset', int, 0), 0)
            editable_arguments          = program.arguments.items[editable_arguments_offset:]
            editable_environment_offset = max(program.cast_custom_option_value('editable_environment_offset', int, 0), 0)
            editable_environment        = program.environment.items[editable_environment_offset:]

            editable_arguments_offset   = len(arguments)
            editable_environment_offset = len(environment)

            arguments   += editable_arguments
            environment += editable_environment
        else:
            executable                  = '/bin/false'
            arguments                   = []
            environment                 = []
            working_directory           = '.'
            editable_arguments_offset   = 0
            editable_environment_offset = 0

        try:
            program.set_command(executable, arguments, environment, working_directory) # FIXME: async_call
        except (Error, REDError) as e:
            QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                 'Could not update command of program [{0}]:\n\n{1}'
                                 .format(program.cast_custom_option_value('name', str, '<unknown>'), e))
            return False

        # custom options
        custom_options = self.get_custom_options()

        custom_options['editable_arguments_offset']   = editable_arguments_offset
        custom_options['editable_environment_offset'] = editable_environment_offset

        for name, value in custom_options.items():
            try:
                program.set_custom_option_value(name, value) # FIXME: async_call
            except (Error, REDError) as e:
                QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                     'Could not update custom options of program [{0}]:\n\n{1}'
                                     .format(program.cast_custom_option_value('name', str, '<unknown>'), e))
                return False

        self.set_last_edit_timestamp()

        return True
