# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015 Matthias Bolte <matthias@tinkerforge.com>
Copyright (C) 2014 Olaf Lüke <olaf@tinkerforge.com>

program_page_shell.py: Program Wizard Shell Page

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

import html

from brickv.plugin_system.plugins.red.program_page import ProgramPage
from brickv.plugin_system.plugins.red.program_utils import *
from brickv.plugin_system.plugins.red.ui_program_page_shell import Ui_ProgramPageShell
from brickv.plugin_system.plugins.red.script_manager import check_script_result

def get_shell_versions(script_manager, callback):
    def cb_versions(result):
        okay, _ = check_script_result(result)

        if okay:
            try:
                version = (' '.join(result.stdout.split('\n')[0].split(' ')[:-1])).replace('version ', '')
                callback([ExecutableVersion('/bin/bash', version)])
                return
            except:
                pass

        # Could not get versions, we assume that some version of bash is installed
        callback([ExecutableVersion('/bin/bash', 'bash')])

    script_manager.execute_script('shell_versions', cb_versions)


class ProgramPageShell(ProgramPage, Ui_ProgramPageShell):
    def __init__(self, title_prefix=''):
        ProgramPage.__init__(self)

        self.setupUi(self)

        self.language = Constants.LANGUAGE_SHELL

        self.setTitle('{0}{1} Configuration'.format(title_prefix, Constants.language_display_names[self.language]))

        self.registerField('shell.version', self.combo_version)
        self.registerField('shell.start_mode', self.combo_start_mode)
        self.registerField('shell.script_file', self.combo_script_file, 'currentText')
        self.registerField('shell.command', self.edit_command)
        self.registerField('shell.working_directory', self.combo_working_directory, 'currentText')

        self.combo_start_mode.currentIndexChanged.connect(self.update_ui_state)
        self.combo_start_mode.currentIndexChanged.connect(self.completeChanged.emit)
        self.check_show_advanced_options.stateChanged.connect(self.update_ui_state)
        self.label_spacer.setText('')

        self.combo_script_file_selector       = MandatoryTypedFileSelector(self,
                                                                           self.label_script_file,
                                                                           self.combo_script_file,
                                                                           self.label_script_file_type,
                                                                           self.combo_script_file_type,
                                                                           self.label_script_file_help)
        self.edit_command_checker             = MandatoryLineEditChecker(self,
                                                                         self.label_command,
                                                                         self.edit_command)
        self.combo_working_directory_selector = MandatoryDirectorySelector(self,
                                                                           self.label_working_directory,
                                                                           self.combo_working_directory)
        self.option_list_editor               = ListWidgetEditor(self.label_options,
                                                                 self.list_options,
                                                                 self.label_options_help,
                                                                 self.button_add_option,
                                                                 self.button_remove_option,
                                                                 self.button_edit_option,
                                                                 self.button_up_option,
                                                                 self.button_down_option,
                                                                 '<new Shell option {0}>')

    # overrides QWizardPage.initializePage
    def initializePage(self):
        self.set_formatted_sub_title('Specify how the {language} program [{name}] should be executed.')

        self.update_combo_version('shell', self.combo_version)

        self.combo_start_mode.setCurrentIndex(Constants.DEFAULT_SHELL_START_MODE)
        self.combo_script_file_selector.reset()
        self.check_show_advanced_options.setChecked(False)
        self.combo_working_directory_selector.reset()
        self.option_list_editor.reset()

        # if a program exists then this page is used in an edit wizard
        program = self.wizard().program

        if program != None:
            # start mode
            start_mode_api_name = program.cast_custom_option_value('shell.start_mode', str, '<unknown>')
            start_mode          = Constants.get_shell_start_mode(start_mode_api_name)

            self.combo_start_mode.setCurrentIndex(start_mode)

            # script file
            self.combo_script_file_selector.set_current_text(program.cast_custom_option_value('shell.script_file', str, ''))

            # command
            self.edit_command.setText(program.cast_custom_option_value('shell.command', str, ''))

            # working directory
            self.combo_working_directory_selector.set_current_text(program.working_directory)

            # options
            self.option_list_editor.clear()

            for option in program.cast_custom_option_value_list('shell.options', str, []):
                self.option_list_editor.add_item(option)

        self.update_ui_state()

    # overrides QWizardPage.isComplete
    def isComplete(self):
        executable = self.get_executable()
        start_mode = self.get_field('shell.start_mode')

        if len(executable) == 0:
            return False

        if start_mode == Constants.SHELL_START_MODE_SCRIPT_FILE and \
           not self.combo_script_file_selector.complete:
            return False

        if start_mode == Constants.SHELL_START_MODE_COMMAND and \
           not self.edit_command_checker.complete:
            return False

        return self.combo_working_directory_selector.complete and ProgramPage.isComplete(self)

    # overrides ProgramPage.update_ui_state
    def update_ui_state(self):
        start_mode             = self.get_field('shell.start_mode')
        start_mode_script_file = start_mode == Constants.SHELL_START_MODE_SCRIPT_FILE
        start_mode_command     = start_mode == Constants.SHELL_START_MODE_COMMAND
        show_advanced_options  = self.check_show_advanced_options.isChecked()

        self.combo_script_file_selector.set_visible(start_mode_script_file)
        self.label_command.setVisible(start_mode_command)
        self.edit_command.setVisible(start_mode_command)
        self.label_command_help.setVisible(start_mode_command)
        self.combo_working_directory_selector.set_visible(show_advanced_options)
        self.option_list_editor.set_visible(show_advanced_options)
        self.label_spacer.setVisible(not show_advanced_options)

        self.option_list_editor.update_ui_state()

    def get_executable(self):
        return self.combo_version.itemData(self.get_field('shell.version'))

    def get_html_summary(self):
        version           = self.get_field('shell.version')
        start_mode        = self.get_field('shell.start_mode')
        script_file       = self.get_field('shell.script_file')
        command           = self.get_field('shell.command')
        working_directory = self.get_field('shell.working_directory')
        options           = ' '.join(self.option_list_editor.get_items())

        html_text  = 'Shell Version: {0}<br/>'.format(html.escape(self.combo_version.itemText(version)))
        html_text += 'Start Mode: {0}<br/>'.format(html.escape(Constants.shell_start_mode_display_names[start_mode]))

        if start_mode == Constants.SHELL_START_MODE_SCRIPT_FILE:
            html_text += 'Script File: {0}<br/>'.format(html.escape(script_file))
        elif start_mode == Constants.SHELL_START_MODE_COMMAND:
            html_text += 'Command: {0}<br/>'.format(html.escape(command))

        html_text += 'Working Directory: {0}<br/>'.format(html.escape(working_directory))
        html_text += 'Shell Options: {0}<br/>'.format(html.escape(options))

        return html_text

    def get_custom_options(self):
        return {
            'shell.start_mode':  Constants.shell_start_mode_api_names[self.get_field('shell.start_mode')],
            'shell.script_file': self.get_field('shell.script_file'),
            'shell.command':     self.get_field('shell.command'),
            'shell.options':     self.option_list_editor.get_items()
        }

    def get_command(self):
        executable  = self.get_executable()
        arguments   = self.option_list_editor.get_items()
        environment = []
        start_mode  = self.get_field('shell.start_mode')

        if start_mode == Constants.SHELL_START_MODE_SCRIPT_FILE:
            arguments.append(self.get_field('shell.script_file'))
        elif start_mode == Constants.SHELL_START_MODE_COMMAND:
            arguments.append('-c')
            arguments.append(self.get_field('shell.command'))

        working_directory = self.get_field('shell.working_directory')

        return executable, arguments, environment, working_directory

    def apply_program_changes(self):
        self.apply_program_custom_options_and_command_changes()
