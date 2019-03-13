# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014 Olaf Lüke <olaf@tinkerforge.com>
Copyright (C) 2014-2015 Matthias Bolte <matthias@tinkerforge.com>

program_page_javascript.py: Program Wizard JavaScript Page

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
from PyQt5.QtWidgets import QMessageBox

from brickv.plugin_system.plugins.red.api import *
from brickv.plugin_system.plugins.red.program_page import ProgramPage
from brickv.plugin_system.plugins.red.program_utils import *
from brickv.plugin_system.plugins.red.ui_program_page_javascript import Ui_ProgramPageJavaScript
from brickv.plugin_system.plugins.red.script_manager import check_script_result
from brickv.utils import get_main_window

def get_nodejs_versions(script_manager, callback):
    def cb_versions(result):
        okay, _ = check_script_result(result)

        if okay:
            try:
                version = result.stdout.split('\n')[0].replace('v', '')
                callback([ExecutableVersion('/usr/local/bin/node', version)])
                return
            except:
                pass

        # Could not get versions, we assume that some version of nodejs is installed
        callback([ExecutableVersion('/usr/local/bin/node', None)])

    script_manager.execute_script('nodejs_versions', cb_versions)


class ProgramPageJavaScript(ProgramPage, Ui_ProgramPageJavaScript):
    def __init__(self, title_prefix=''):
        ProgramPage.__init__(self)

        self.setupUi(self)

        self.language = Constants.LANGUAGE_JAVASCRIPT

        self.setTitle('{0}{1} Configuration'.format(title_prefix, Constants.language_display_names[self.language]))

        self.registerField('javascript.flavor', self.combo_flavor)
        self.registerField('javascript.start_mode', self.combo_start_mode)
        self.registerField('javascript.script_file', self.combo_script_file, 'currentText')
        self.registerField('javascript.command', self.edit_command)
        self.registerField('javascript.working_directory', self.combo_working_directory, 'currentText')

        self.combo_flavor.currentIndexChanged.connect(self.update_ui_state)
        self.combo_flavor.currentIndexChanged.connect(self.completeChanged.emit)
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
                                                                 '<new Node.js option {0}>')

    # overrides QWizardPage.initializePage
    def initializePage(self):
        self.set_formatted_sub_title('Specify how the {language} program [{name}] should be executed.')

        def cb_nodejs_versions(versions):
            if versions[0].version != None:
                node_version_str = ' ' + versions[0].version
            else:
                node_version_str = ''

            self.combo_flavor.clear()
            self.combo_flavor.addItem('Client-Side (Browser)', '/bin/false')
            self.combo_flavor.addItem('Server-Side (Node.js{0})'.format(node_version_str), versions[0].executable)

            # if a program exists then this page is used in an edit wizard
            if self.wizard().program != None:
                program         = self.wizard().program
                flavor_api_name = program.cast_custom_option_value('javascript.flavor', str, '<unknown>')
                flavor          = Constants.get_javascript_flavor(flavor_api_name)

                if flavor == Constants.JAVASCRIPT_FLAVOR_BROWSER:
                    executable = '/bin/false'
                else:
                    executable = program.executable

                set_current_combo_index_from_data(self.combo_flavor, executable)

            self.combo_flavor.setEnabled(True)
            self.completeChanged.emit()

        self.get_executable_versions('nodejs', cb_nodejs_versions)

        self.combo_start_mode.setCurrentIndex(Constants.DEFAULT_JAVASCRIPT_START_MODE)
        self.combo_script_file_selector.reset()
        self.check_show_advanced_options.setChecked(False)
        self.combo_working_directory_selector.reset()
        self.option_list_editor.reset()

        # if a program exists then this page is used in an edit wizard
        program = self.wizard().program

        if program != None:
            # start mode
            start_mode_api_name = program.cast_custom_option_value('javascript.start_mode', str, '<unknown>')
            start_mode          = Constants.get_javascript_start_mode(start_mode_api_name)

            self.combo_start_mode.setCurrentIndex(start_mode)

            # script file
            self.combo_script_file_selector.set_current_text(program.cast_custom_option_value('javascript.script_file', str, ''))

            # command
            self.edit_command.setText(program.cast_custom_option_value('javascript.command', str, ''))

            # working directory
            self.combo_working_directory_selector.set_current_text(program.working_directory)

            # options
            self.option_list_editor.clear()

            for option in program.cast_custom_option_value_list('javascript.options', str, []):
                self.option_list_editor.add_item(option)

        self.update_ui_state()

    # overrides QWizardPage.isComplete
    def isComplete(self):
        flavor     = self.get_field('javascript.flavor')
        executable = self.get_executable()
        start_mode = self.get_field('javascript.start_mode')

        if flavor == Constants.JAVASCRIPT_FLAVOR_NODEJS:
            if len(executable) == 0:
                return False

            if start_mode == Constants.JAVASCRIPT_START_MODE_SCRIPT_FILE and \
               not self.combo_script_file_selector.complete:
                return False

            if start_mode == Constants.JAVASCRIPT_START_MODE_COMMAND and \
               not self.edit_command_checker.complete:
                return False

        return self.combo_working_directory_selector.complete and ProgramPage.isComplete(self)

    # overrides ProgramPage.update_ui_state
    def update_ui_state(self):
        flavor                 = self.get_field('javascript.flavor')
        flavor_browser         = flavor == Constants.JAVASCRIPT_FLAVOR_BROWSER
        flavor_nodejs          = flavor == Constants.JAVASCRIPT_FLAVOR_NODEJS
        start_mode             = self.get_field('javascript.start_mode')
        start_mode_script_file = start_mode == Constants.JAVASCRIPT_START_MODE_SCRIPT_FILE
        start_mode_command     = start_mode == Constants.JAVASCRIPT_START_MODE_COMMAND
        show_advanced_options  = self.check_show_advanced_options.isChecked()

        self.label_start_mode.setVisible(flavor_nodejs)
        self.combo_start_mode.setVisible(flavor_nodejs)
        self.combo_script_file_selector.set_visible(flavor_nodejs and start_mode_script_file)
        self.label_command.setVisible(flavor_nodejs and start_mode_command)
        self.edit_command.setVisible(flavor_nodejs and start_mode_command)
        self.label_command_help.setVisible(flavor_nodejs and start_mode_command)
        self.line.setVisible(flavor_nodejs)
        self.check_show_advanced_options.setVisible(flavor_nodejs)
        self.combo_working_directory_selector.set_visible(flavor_nodejs and show_advanced_options)
        self.option_list_editor.set_visible(flavor_nodejs and show_advanced_options)
        self.label_spacer.setVisible(flavor_browser or not show_advanced_options)

        self.option_list_editor.update_ui_state()

    def get_executable(self):
        return self.combo_flavor.itemData(self.get_field('javascript.flavor'))

    def get_html_summary(self):
        flavor            = self.get_field('javascript.flavor')
        start_mode        = self.get_field('javascript.start_mode')
        script_file       = self.get_field('javascript.script_file')
        command           = self.get_field('javascript.command')
        working_directory = self.get_field('javascript.working_directory')
        options           = ' '.join(self.option_list_editor.get_items())

        html_text = 'JavaScript Flavor: {0}<br/>'.format(html.escape(self.combo_flavor.itemText(flavor)))

        if flavor == Constants.JAVASCRIPT_FLAVOR_NODEJS:
            html_text += 'Start Mode: {0}<br/>'.format(html.escape(Constants.javascript_start_mode_display_names[start_mode]))

            if start_mode == Constants.JAVASCRIPT_START_MODE_SCRIPT_FILE:
                html_text += 'Script File: {0}<br/>'.format(html.escape(script_file))
            elif start_mode == Constants.JAVASCRIPT_START_MODE_COMMAND:
                html_text += 'Command: {0}<br/>'.format(html.escape(command))

            html_text += 'Working Directory: {0}<br/>'.format(html.escape(working_directory))
            html_text += 'Node.js Options: {0}<br/>'.format(html.escape(options))

        return html_text

    def get_custom_options(self):
        return {
            'javascript.flavor':      Constants.javascript_flavor_api_names[self.get_field('javascript.flavor')],
            'javascript.start_mode':  Constants.javascript_start_mode_api_names[self.get_field('javascript.start_mode')],
            'javascript.script_file': self.get_field('javascript.script_file'),
            'javascript.command':     self.get_field('javascript.command'),
            'javascript.options':     self.option_list_editor.get_items()
        }

    def get_command(self):
        flavor = self.get_field('javascript.flavor')

        if flavor == Constants.JAVASCRIPT_FLAVOR_BROWSER:
            return None

        executable  = self.get_executable()
        arguments   = self.option_list_editor.get_items()
        environment = ['NODE_PATH=/usr/local/lib/node_modules']
        start_mode  = self.get_field('javascript.start_mode')

        if start_mode == Constants.JAVASCRIPT_START_MODE_SCRIPT_FILE:
            arguments.append(self.get_field('javascript.script_file'))
        elif start_mode == Constants.JAVASCRIPT_START_MODE_COMMAND:
            arguments.append('-e')
            arguments.append(self.get_field('javascript.command'))

        working_directory = self.get_field('javascript.working_directory')

        return executable, arguments, environment, working_directory

    def apply_program_changes(self):
        if not self.apply_program_custom_options_and_command_changes():
            return

        # stop scheduler if switching to browser flavor
        program = self.wizard().program

        if program == None:
            return

        if self.get_field('javascript.flavor') == Constants.JAVASCRIPT_FLAVOR_BROWSER:
            try:
                program.set_schedule(REDProgram.START_MODE_NEVER, False, 0, '') # FIXME: async_call
            except (Error, REDError) as e:
                QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                     'Could not update schedule of program [{0}]:\n\n{1}'
                                     .format(program.cast_custom_option_value('name', str, '<unknown>'), e))
