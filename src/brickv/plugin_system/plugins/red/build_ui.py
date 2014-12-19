#!/usr/bin/env python

import os

os.system("pyuic4 -o ui_red.py ui/red.ui")
os.system("pyuic4 -o ui_red_tab_overview.py ui/red_tab_overview.ui")
os.system("pyuic4 -o ui_red_tab_settings.py ui/red_tab_settings.ui")
os.system("pyuic4 -o ui_red_tab_settings_brickd.py ui/red_tab_settings_brickd.ui")
os.system("pyuic4 -o ui_red_tab_settings_datetime.py ui/red_tab_settings_datetime.ui")
os.system("pyuic4 -o ui_red_tab_settings_file_system.py ui/red_tab_settings_file_system.ui")
os.system("pyuic4 -o ui_red_tab_program.py ui/red_tab_program.ui")
os.system("pyuic4 -o ui_red_tab_console.py ui/red_tab_console.ui")
os.system("pyuic4 -o ui_red_tab_versions.py ui/red_tab_versions.ui")
os.system("pyuic4 -o ui_red_tab_extension.py ui/red_tab_extension.ui")
os.system("pyuic4 -o ui_red_tab_extension_ethernet.py ui/red_tab_extension_ethernet.ui")

os.system("pyuic4 -o ui_program_info_main.py ui/program_info_main.ui")
os.system("pyuic4 -o ui_program_info_files.py ui/program_info_files.ui")
os.system("pyuic4 -o ui_program_info_logs.py ui/program_info_logs.ui")
os.system("pyuic4 -o ui_program_info_logs_view.py ui/program_info_logs_view.ui")
os.system("pyuic4 -o ui_program_info_c.py ui/program_info_c.ui")
os.system("pyuic4 -o ui_program_info_c_compile.py ui/program_info_c_compile.ui")
os.system("pyuic4 -o ui_program_info_csharp.py ui/program_info_csharp.ui")
os.system("pyuic4 -o ui_program_info_delphi.py ui/program_info_delphi.ui")
os.system("pyuic4 -o ui_program_info_delphi_compile.py ui/program_info_delphi_compile.ui")
os.system("pyuic4 -o ui_program_info_java.py ui/program_info_java.ui")
os.system("pyuic4 -o ui_program_info_javascript.py ui/program_info_javascript.ui")
os.system("pyuic4 -o ui_program_info_octave.py ui/program_info_octave.ui")
os.system("pyuic4 -o ui_program_info_perl.py ui/program_info_perl.ui")
os.system("pyuic4 -o ui_program_info_php.py ui/program_info_php.ui")
os.system("pyuic4 -o ui_program_info_python.py ui/program_info_python.ui")
os.system("pyuic4 -o ui_program_info_ruby.py ui/program_info_ruby.ui")
os.system("pyuic4 -o ui_program_info_shell.py ui/program_info_shell.ui")
os.system("pyuic4 -o ui_program_info_vbnet.py ui/program_info_vbnet.ui")

os.system("pyuic4 -o ui_program_page_general.py ui/program_page_general.ui")
os.system("pyuic4 -o ui_program_page_files.py ui/program_page_files.ui")
os.system("pyuic4 -o ui_program_page_c.py ui/program_page_c.ui")
os.system("pyuic4 -o ui_program_page_csharp.py ui/program_page_csharp.ui")
os.system("pyuic4 -o ui_program_page_delphi.py ui/program_page_delphi.ui")
os.system("pyuic4 -o ui_program_page_java.py ui/program_page_java.ui")
os.system("pyuic4 -o ui_program_page_javascript.py ui/program_page_javascript.ui")
os.system("pyuic4 -o ui_program_page_octave.py ui/program_page_octave.ui")
os.system("pyuic4 -o ui_program_page_perl.py ui/program_page_perl.ui")
os.system("pyuic4 -o ui_program_page_php.py ui/program_page_php.ui")
os.system("pyuic4 -o ui_program_page_python.py ui/program_page_python.ui")
os.system("pyuic4 -o ui_program_page_ruby.py ui/program_page_ruby.ui")
os.system("pyuic4 -o ui_program_page_shell.py ui/program_page_shell.ui")
os.system("pyuic4 -o ui_program_page_vbnet.py ui/program_page_vbnet.ui")
os.system("pyuic4 -o ui_program_page_arguments.py ui/program_page_arguments.ui")
os.system("pyuic4 -o ui_program_page_stdio.py ui/program_page_stdio.ui")
os.system("pyuic4 -o ui_program_page_schedule.py ui/program_page_schedule.ui")
os.system("pyuic4 -o ui_program_page_summary.py ui/program_page_summary.ui")
os.system("pyuic4 -o ui_program_page_upload.py ui/program_page_upload.ui")
os.system("pyuic4 -o ui_program_page_download.py ui/program_page_download.ui")

os.system("python build_scripts.py")
