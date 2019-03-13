# -*- coding: utf-8 -*-
"""
RED Plugin
Copyright (C) 2014-2015, 2017 Matthias Bolte <matthias@tinkerforge.com>

program_page_general.py: Program Wizard General Page

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

import re

from PyQt5.QtCore import QRegExp
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QRegExpValidator

from brickv.plugin_system.plugins.red.api import *
from brickv.plugin_system.plugins.red.program_page import ProgramPage
from brickv.plugin_system.plugins.red.program_utils import *
from brickv.plugin_system.plugins.red.ui_program_page_general import Ui_ProgramPageGeneral
from brickv.utils import get_main_window

class ProgramPageGeneral(ProgramPage, Ui_ProgramPageGeneral):
    def __init__(self, title_prefix=''):
        ProgramPage.__init__(self)

        self.setupUi(self)

        self.edit_mode            = False
        self.identifier_is_unique = False

        self.setTitle(title_prefix + 'General Information')
        self.setSubTitle('Specify name, identifier, programming language and description for the program.')

        self.edit_identifier.setValidator(QRegExpValidator(QRegExp('^[a-zA-Z0-9_][a-zA-Z0-9._-]{2,}$'), self))
        self.combo_language.insertSeparator(Constants.LANGUAGE_SEPARATOR)

        self.registerField('name', self.edit_name)
        self.registerField('identifier', self.edit_identifier)
        self.registerField('language', self.combo_language)
        self.registerField('description', self.text_description, 'plainText', self.text_description.textChanged)

        self.edit_name.textChanged.connect(self.auto_generate_identifier)
        self.check_auto_generate.stateChanged.connect(self.update_ui_state)
        self.edit_identifier.textChanged.connect(self.check_identifier)
        self.combo_language.currentIndexChanged.connect(self.update_ui_state)
        self.combo_language.currentIndexChanged.connect(self.check_language)

        self.edit_name_checker       = MandatoryLineEditChecker(self, self.label_name, self.edit_name)
        self.edit_identifier_checker = MandatoryLineEditChecker(self, self.label_identifier, self.edit_identifier)

        self.check_language(self.combo_language.currentIndex())

    # overrides QWizardPage.initializePage
    def initializePage(self):
        self.edit_name.setText('unnamed')
        self.combo_language.setCurrentIndex(Constants.LANGUAGE_INVALID)

        # if a program exists then this page is used in an edit wizard
        if self.wizard().program != None:
            program        = self.wizard().program
            self.edit_mode = True

            self.setSubTitle('Specify name and description for the program.')

            self.edit_name.setText(program.cast_custom_option_value('name', str, '<unknown>'))
            self.edit_identifier.setText(program.identifier)
            self.text_description.setPlainText(program.cast_custom_option_value('description', str, ''))

            language_api_name = program.cast_custom_option_value('language', str, '<unknown>')

            try:
                language = Constants.get_language(language_api_name)
                self.combo_language.setCurrentIndex(language)
            except:
                pass

        self.update_ui_state()

    # overrides QWizardPage.isComplete
    def isComplete(self):
        return self.edit_name_checker.complete and \
               self.edit_identifier_checker.complete and \
               self.identifier_is_unique and \
               self.get_field('language') != Constants.LANGUAGE_INVALID and \
               ProgramPage.isComplete(self)

    # overrides ProgramPage.update_ui_state
    def update_ui_state(self):
        auto_generate = self.check_auto_generate.isChecked()

        self.auto_generate_identifier(self.edit_name.text())

        self.label_identifier.setVisible(not auto_generate)
        self.edit_identifier.setVisible(not auto_generate)
        self.label_identifier_help.setVisible(not auto_generate)

        self.check_auto_generate.setEnabled(not self.edit_mode)
        self.edit_identifier.setEnabled(not self.edit_mode)
        self.label_language.setEnabled(not self.edit_mode)
        self.combo_language.setEnabled(not self.edit_mode)
        self.label_language_help.setEnabled(not self.edit_mode)

        # FIXME: image versions 1.4 till 1.6 comes with Octave 3.8 which has
        # broken Java support. since image version 1.7 Octave is downgraded to
        # the working version 3.6
        if self.wizard().image_version.number >= (1, 4) and \
           self.wizard().image_version.number <= (1, 6):
            self.label_octave.setVisible(self.get_field('language') == Constants.LANGUAGE_OCTAVE)
        else:
            self.label_octave.setVisible(False)

    def auto_generate_identifier(self, name):
        if not self.check_auto_generate.isChecked() or self.edit_mode:
            return

        # ensure the identifier matches ^[a-zA-Z0-9_][a-zA-Z0-9._-]{2,}$
        identifier = re.sub('[^a-zA-Z0-9._-]', '_', name).lstrip('-.')

        unique_identifier = identifier
        counter = 1

        while len(unique_identifier) < 3:
            unique_identifier += '_'

        while unique_identifier in self.wizard().identifiers and counter < 10000:
            unique_identifier = identifier + str(counter)
            counter += 1

            while len(unique_identifier) < 3:
                unique_identifier += '_'

        self.edit_identifier.setText(unique_identifier)

        if unique_identifier in self.wizard().identifiers:
            QMessageBox.critical(get_main_window(), 'New Program Error',
                                 'Could not auto-generate unique identifier from program name [{0}] because all tested ones are already in use.'
                                 .format(name))

    def check_identifier(self, identifier):
        identifier_was_unique = self.identifier_is_unique

        if identifier in self.wizard().identifiers:
            self.identifier_is_unique = False
            self.edit_identifier.setStyleSheet('QLineEdit { color : red }')
        else:
            self.identifier_is_unique = True
            self.edit_identifier.setStyleSheet('')

        if identifier_was_unique != self.identifier_is_unique:
            self.completeChanged.emit()

    def check_language(self, language):
        if language == Constants.LANGUAGE_INVALID:
            self.label_language.setStyleSheet('QLabel { color : red }')
        else:
            self.label_language.setStyleSheet('')

        self.completeChanged.emit()

    def apply_program_changes(self):
        program = self.wizard().program

        if program == None:
            return

        name = self.get_field('name')

        try:
            program.set_custom_option_value('name', name) # FIXME: async_call
        except (Error, REDError) as e:
            QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                 'Could not update name of program [{0}]:\n\n{1}'
                                 .format(program.cast_custom_option_value('name', str, '<unknown>'), e))
            return

        description = self.get_field('description')

        try:
            program.set_custom_option_value('description', description) # FIXME: async_call
        except (Error, REDError) as e:
            QMessageBox.critical(get_main_window(), 'Edit Program Error',
                                 'Could not update description of program [{0}]:\n\n{1}'
                                 .format(program.cast_custom_option_value('name', str, '<unknown>'), e))
            return

        self.set_last_edit_timestamp()
