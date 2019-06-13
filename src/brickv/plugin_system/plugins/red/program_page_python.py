# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015 Matthias Bolte <matthias@tinkerforge.com>

program_page_python.py: Program Wizard Python Page

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
from brickv.plugin_system.plugins.red.program_utils import ExecutableVersion, Constants, \
                                                           MandatoryTypedFileSelector, \
                                                           MandatoryLineEditChecker, \
                                                           MandatoryDirectorySelector, \
                                                           ListWidgetEditor
from brickv.plugin_system.plugins.red.ui_program_page_python import Ui_ProgramPagePython
from brickv.plugin_system.plugins.red.script_manager import check_script_result

def get_python_versions(script_manager, callback):
    def cb_versions(result):
        okay, _ = check_script_result(result, stderr_is_redirected=True)

        if okay:
            try:
                versions = result.stdout.split('\n')
                callback([ExecutableVersion('/usr/bin/python2', versions[0].split(' ')[1]),
                          ExecutableVersion('/usr/bin/python3', versions[1].split(' ')[1])])
                return
            except:
                pass

        # Could not get versions, we assume that some version
        # of python 2.7 and some version of python 3 is installed
        callback([ExecutableVersion('/usr/bin/python2', '2.7'),
                  ExecutableVersion('/usr/bin/python3', '3.x')])

    script_manager.execute_script('python_versions', cb_versions, redirect_stderr_to_stdout=True)


class ProgramPagePython(ProgramPage, Ui_ProgramPagePython):
    def __init__(self, title_prefix=''):
        ProgramPage.__init__(self)

        self.setupUi(self)

        self.language     = Constants.LANGUAGE_PYTHON
        self.url_template = self.label_url.text()

        self.setTitle('{0}{1} Configuration'.format(title_prefix, Constants.language_display_names[self.language]))

        self.registerField('python.version', self.combo_version)
        self.registerField('python.start_mode', self.combo_start_mode)
        self.registerField('python.script_file', self.combo_script_file, 'currentText')
        self.registerField('python.module_name', self.edit_module_name)
        self.registerField('python.command', self.edit_command)
        self.registerField('python.working_directory', self.combo_working_directory, 'currentText')

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
        self.edit_module_name_checker         = MandatoryLineEditChecker(self,
                                                                         self.label_module_name,
                                                                         self.edit_module_name)
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
                                                                 '<new Python option {0}>')

    # overrides QWizardPage.initializePage
    def initializePage(self):
        self.set_formatted_sub_title('Specify how the {language} program [{name}] should be executed.')

        self.update_combo_version('python', self.combo_version)

        self.combo_start_mode.setCurrentIndex(Constants.DEFAULT_PYTHON_START_MODE)
        self.combo_script_file_selector.reset()
        self.label_url.setText(self.url_template.replace('<SERVER>', 'red-brick').replace('<IDENTIFIER>', self.get_field('identifier')))
        self.check_show_advanced_options.setChecked(False)
        self.combo_working_directory_selector.reset()
        self.option_list_editor.reset()

        # if a program exists then this page is used in an edit wizard
        program = self.wizard().program

        if program != None:
            # start mode
            start_mode_api_name = program.cast_custom_option_value('python.start_mode', str, '<unknown>')
            start_mode          = Constants.get_python_start_mode(start_mode_api_name)

            self.combo_start_mode.setCurrentIndex(start_mode)

            # script file
            self.combo_script_file_selector.set_current_text(program.cast_custom_option_value('python.script_file', str, ''))

            # module name
            self.edit_module_name.setText(program.cast_custom_option_value('python.module_name', str, ''))

            # command
            self.edit_command.setText(program.cast_custom_option_value('python.command', str, ''))

            # working directory
            self.combo_working_directory_selector.set_current_text(program.working_directory)

            # options
            self.option_list_editor.clear()

            for option in program.cast_custom_option_value_list('python.options', str, []):
                self.option_list_editor.add_item(option)

        self.update_ui_state()

    # overrides QWizardPage.isComplete
    def isComplete(self):
        executable = self.get_executable()
        start_mode = self.get_field('python.start_mode')

        # In web interface mode there is nothing to configure at all
        if start_mode == Constants.PYTHON_START_MODE_WEB_INTERFACE:
            return ProgramPage.isComplete(self)

        if len(executable) == 0:
            return False

        if start_mode == Constants.PYTHON_START_MODE_SCRIPT_FILE and \
           not self.combo_script_file_selector.complete:
            return False

        if start_mode == Constants.PYTHON_START_MODE_MODULE_NAME and \
           not self.edit_module_name_checker.complete:
            return False

        if start_mode == Constants.PYTHON_START_MODE_COMMAND and \
           not self.edit_command_checker.complete:
            return False

        return self.combo_working_directory_selector.complete and ProgramPage.isComplete(self)

    # overrides ProgramPage.update_ui_state
    def update_ui_state(self):
        start_mode               = self.get_field('python.start_mode')
        start_mode_script_file   = start_mode == Constants.PYTHON_START_MODE_SCRIPT_FILE
        start_mode_module_name   = start_mode == Constants.PYTHON_START_MODE_MODULE_NAME
        start_mode_command       = start_mode == Constants.PYTHON_START_MODE_COMMAND
        start_mode_web_interface = start_mode == Constants.PYTHON_START_MODE_WEB_INTERFACE
        show_advanced_options    = self.check_show_advanced_options.isChecked()

        self.combo_version.setVisible(not start_mode_web_interface)
        self.label_version.setVisible(not start_mode_web_interface)
        self.combo_script_file_selector.set_visible(start_mode_script_file)
        self.label_module_name.setVisible(start_mode_module_name)
        self.edit_module_name.setVisible(start_mode_module_name)
        self.label_module_name_help.setVisible(start_mode_module_name)
        self.label_command.setVisible(start_mode_command)
        self.edit_command.setVisible(start_mode_command)
        self.label_command_help.setVisible(start_mode_command)
        self.label_web_interface_help.setVisible(start_mode_web_interface)
        self.label_url_title.setVisible(start_mode_web_interface)
        self.label_url.setVisible(start_mode_web_interface)
        self.line.setVisible(not start_mode_web_interface)
        self.check_show_advanced_options.setVisible(not start_mode_web_interface)
        self.combo_working_directory_selector.set_visible(not start_mode_web_interface and show_advanced_options)
        self.option_list_editor.set_visible(not start_mode_web_interface and show_advanced_options)
        self.label_spacer.setVisible(start_mode_web_interface or not show_advanced_options)

        self.option_list_editor.update_ui_state()

    def get_executable(self):
        return self.combo_version.itemData(self.get_field('python.version'))

    def get_html_summary(self):
        version           = self.get_field('python.version')
        start_mode        = self.get_field('python.start_mode')
        script_file       = self.get_field('python.script_file')
        module_name       = self.get_field('python.module_name')
        command           = self.get_field('python.command')
        working_directory = self.get_field('python.working_directory')
        options           = ' '.join(self.option_list_editor.get_items())

        if start_mode == Constants.PYTHON_START_MODE_WEB_INTERFACE:
            html_text = 'Start Mode: {0}<br/>'.format(html.escape(Constants.python_start_mode_display_names[start_mode]))
        else:
            html_text  = 'Python Version: {0}<br/>'.format(html.escape(self.combo_version.itemText(version)))
            html_text += 'Start Mode: {0}<br/>'.format(html.escape(Constants.python_start_mode_display_names[start_mode]))

            if start_mode == Constants.PYTHON_START_MODE_SCRIPT_FILE:
                html_text += 'Script File: {0}<br/>'.format(html.escape(script_file))
            elif start_mode == Constants.PYTHON_START_MODE_MODULE_NAME:
                html_text += 'Module Name: {0}<br/>'.format(html.escape(module_name))
            elif start_mode == Constants.PYTHON_START_MODE_COMMAND:
                html_text += 'Command: {0}<br/>'.format(html.escape(command))

            html_text += 'Working Directory: {0}<br/>'.format(html.escape(working_directory))
            html_text += 'Python Options: {0}<br/>'.format(html.escape(options))

        return html_text

    def get_custom_options(self):
        return {
            'python.start_mode':  Constants.python_start_mode_api_names[self.get_field('python.start_mode')],
            'python.script_file': self.get_field('python.script_file'),
            'python.module_name': self.get_field('python.module_name'),
            'python.command':     self.get_field('python.command'),
            'python.options':     self.option_list_editor.get_items()
        }

    def get_command(self):
        start_mode = self.get_field('python.start_mode')

        if start_mode == Constants.PYTHON_START_MODE_WEB_INTERFACE:
            return None

        executable  = self.get_executable()
        arguments   = self.option_list_editor.get_items()
        environment = []

        if start_mode == Constants.PYTHON_START_MODE_SCRIPT_FILE:
            arguments.append(self.get_field('python.script_file'))
        elif start_mode == Constants.PYTHON_START_MODE_MODULE_NAME:
            arguments.append('-m')
            arguments.append(self.get_field('python.module_name'))
        elif start_mode == Constants.PYTHON_START_MODE_COMMAND:
            arguments.append('-c')
            arguments.append(self.get_field('python.command'))

        working_directory = self.get_field('python.working_directory')

        return executable, arguments, environment, working_directory

    def apply_program_changes(self):
        self.apply_program_custom_options_and_command_changes()
