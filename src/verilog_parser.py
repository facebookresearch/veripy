####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################
################################################################################
#                                                                              #
#     Author: Baheerathan Anandharengan                                        #
#     E-Mail: baheerathan@meta.com                                               #
#                                                                              #
#     Key Contributor: Dheepak Jayaraman                                       #
#     E-Mail: dheepak@meta.com                                                   #
#                                                                              #
################################################################################

import argparse
import csv
import datetime
import io
import itertools
import json
import logging
import math
import os
import os.path
import re
import string
import subprocess
import sys
from os.path import getmtime
from src.spec_flow import *
from src.utils import *
from src.regex import *
from collections import OrderedDict
from csv import reader
from math import ceil, log
from typing import Dict, Set

import yaml as yaml


class verilog_parser:
    def __init__(
        self,
        module_name,
        lines,
        incl_dirs,
        files,
        package_files,
        hash_defines,
        parsing_format,
        debug_en,
        debug_file,
        ifdef_dis,
        verilog_define_files,
        functions_list,
        profiling,
        profiling_file,
        cmdline,
    ):
        self.module_name = module_name
        self.parse_lines = lines
        self.incl_dirs = incl_dirs
        self.files = files
        self.package_files = package_files
        self.hash_defines = hash_defines
        self.parsing_format = parsing_format
        self.debug = debug_en
        self.debug_file = debug_file + ".parser"
        self.verilog_define_files = verilog_define_files
        self.parser_on = cmdline.parser_on
        self.debug_print = 0
        self.generate_stub = cmdline.generate_stub
        self.parse_generate = cmdline.parse_generate
        self.gen_dependencies = cmdline.generate_dependancies
        self.interface_spec_files = cmdline.intf_specs
        self.interface_def_files = cmdline.intf_defs
        self.module_def_files = cmdline.mod_defs
        self.auto_package_load = cmdline.auto_package_load

        self.clock = "clk"
        self.async_reset = "arst_n"
        self.sync_reset = "rst_n"
        self.reset_type = "ASYNC"

        self.tick_defines = {}
        self.tick_ifdef_dis = ifdef_dis
        self.tick_ifdef_en = 1
        self.tick_decisions = []
        self.tick_types = []
        self.tick_served = []
        self.tick_curr_decision = 1
        self.tick_curr_type = ""
        self.tick_curr_served = 0
        self.last_tick_loc = 0

        self.packages = []
        self.packages.append("default")

        self.classes = []
        self.classes.append("default")

        self.params = {}
        self.typedef_enums = {}
        self.typedef_logics = {}
        self.typedef_structs = {}
        self.typedef_unions = {}
        self.typedef_bindings = {}
        self.manual_ports = 0

        # Initializing default package to avoid errors
        self.typedef_enums["default"] = {}
        self.typedef_logics["default"] = {}
        self.typedef_structs["default"] = {}
        self.typedef_unions["default"] = {}

        # Initializing default class to avoid errors
        self.typedef_enums["default"]["default"] = {}
        self.typedef_logics["default"]["default"] = {}
        self.typedef_structs["default"]["default"] = {}
        self.typedef_unions["default"]["default"] = {}

        self.functions_list = functions_list

        self.sub_tick_defines = {}
        self.sub_tick_ifdef_en = 1
        self.sub_tick_ifdef_arr = []
        self.sub_tick_decisions = []
        self.sub_tick_types = []
        self.sub_tick_served = []
        self.sub_tick_curr_decision = 1
        self.sub_tick_curr_type = ""
        self.sub_tick_curr_served = 0
        self.sub_last_tick_loc = 0

        self.sub_packages = []
        self.sub_packages.append("default")

        self.sub_classes = []
        self.sub_classes.append("default")

        self.sub_params = {}
        self.sub_typedef_enums = {}
        self.sub_typedef_logics = {}
        self.sub_typedef_structs = {}
        self.sub_typedef_unions = {}
        self.sub_typedef_bindings = {}

        # Initializing default package to avoid errors
        self.sub_typedef_enums["default"] = {}
        self.sub_typedef_logics["default"] = {}
        self.sub_typedef_structs["default"] = {}
        self.sub_typedef_unions["default"] = {}

        # Initializing default class to avoid errors
        self.sub_typedef_enums["default"]["default"] = {}
        self.sub_typedef_logics["default"]["default"] = {}
        self.sub_typedef_structs["default"]["default"] = {}
        self.sub_typedef_unions["default"]["default"] = {}

        self.ports = {}
        self.regs = {}
        self.wires = {}
        self.signals = {}
        self.always_constructs = []
        self.force_widths = []
        self.force_internals = []
        self.genvars = []
        self.integers = []
        self.generate_for_loops = {}
        self.generate_for_loop_count = 0

        self.always_for_loops = {}
        self.always_for_loop_count = 0

        self.pkg2assign_index = 0
        self.pkg2assign_info = {}
        self.assign2pkg_index = 0
        self.assign2pkg_info = {}

        self.sub_include_files_list = []
        self.sub_ports = {}
        self.sub_inst_ports = {}
        self.sub_inst_files = {}
        self.sub_inst_params = {}

        self.auto_reset_data = {}
        self.auto_reset_val = ""
        self.auto_reset_index = 0
        self.auto_reset_en = 0
        self.module_found = 0
        self.module_param_line = ""

        self.original_line = ""
        self.line_no = ""
        self.line = ""

        # Output variables
        self.lines = []
        self.debug_info = []
        self.found_error = 0
        self.header_files = []
        self.filelist = []

        self.package_name = ""
        self.class_name = ""

        self.dependencies = {}
        self.dependencies["include_files"] = []
        self.dependencies["header_files"] = []
        self.dependencies["verilog_subs"] = []
        self.dependencies["veripy_subs"] = {}
        self.dependencies["spec_files"] = []
        self.dependencies["interface_files"] = []
        self.dependencies["module_files"] = []
        self.dependencies["depends"] = []
        self.dependencies["build_cmd"] = []

        if self.debug:
            self.dbg_file = open(self.debug_file, "w")

        # TODO: Need to assign this variable
        self.temporary_file = "TEMPFILE"

        ################################################################################
        # Loading SV packages
        ################################################################################
        if self.package_files is not None:
            for package in self.package_files:
                self.load_import_or_include_file("TOP", "IMPORT_COMMANDLINE", package)

        ################################################################################
        # Performance profiling variables
        ################################################################################

        self.profiling = profiling
        self.profiling_file = profiling_file

        # Dictionaries to store performance data
        self.time_dict = {}
        self.all_time_dict = {
            "total_hits": 0,
            "total_time": 0,
        }
        self.all_time_callers = {
            "total_hits": 0,
            "total_time": 0,
        }
        self.all_time_caller_regex = {
            "total_hits": 0,
            "total_time": 0,
        }

        self.real_re_search = re.search

    def time_re_search(self, reg, inp):
        import time

        name = str(reg)
        t = time.process_time()
        result = self.real_re_search(reg, inp)
        elapsed_time = time.process_time() - t
        if name in self.all_time_dict:
            self.all_time_dict[name]["hits"] += 1
            self.all_time_dict[name]["total_time"] += elapsed_time
            self.all_time_dict[name]["max_time"] = max(
                elapsed_time, self.all_time_dict[name]["max_time"]
            )
        else:
            self.all_time_dict[name] = {
                "hits": 1,
                "total_time": elapsed_time,
                "max_time": elapsed_time,
            }
        caller = sys._getframe().f_back.f_code.co_name
        if caller in self.all_time_callers:
            self.all_time_callers[caller]["hits"] += 1
            self.all_time_callers[caller]["total_time"] += elapsed_time
            self.all_time_callers[caller]["max_time"] = max(
                elapsed_time, self.all_time_callers[caller]["max_time"]
            )
        else:
            self.all_time_callers[caller] = {
                "hits": 1,
                "total_time": elapsed_time,
                "max_time": elapsed_time,
            }
        caller_regex = caller + " -> " + name
        if caller_regex in self.all_time_caller_regex:
            self.all_time_caller_regex[caller_regex]["hits"] += 1
            self.all_time_caller_regex[caller_regex]["total_time"] += elapsed_time
            self.all_time_caller_regex[caller_regex]["max_time"] = max(
                elapsed_time, self.all_time_caller_regex[caller_regex]["max_time"]
            )
        else:
            self.all_time_caller_regex[caller_regex] = {
                "hits": 1,
                "total_time": elapsed_time,
                "max_time": elapsed_time,
            }

        self.all_time_caller_regex["total_hits"] += 1
        self.all_time_caller_regex["total_time"] += elapsed_time
        self.all_time_callers["total_hits"] += 1
        self.all_time_callers["total_time"] += elapsed_time
        self.all_time_dict["total_hits"] += 1
        self.all_time_dict["total_time"] += elapsed_time
        return result

    def nice_stats(self, result_dict, pfile):
        pfile.write("Module: " + self.module_name + "\n")
        pfile.write(f"TOTAL HITS={result_dict['total_hits']}\n")
        pfile.write(f"TOTAL TIME={result_dict['total_time']}\n")
        del result_dict["total_time"]
        del result_dict["total_hits"]

        pfile.write("Max hits\n")
        for key, value in sorted(
            result_dict.items(), key=lambda item: item[1]["hits"], reverse=True
        )[:10]:
            pfile.write("%s: %s\n" % (key, value))
        pfile.write("Max total_time\n")
        for key, value in sorted(
            result_dict.items(), key=lambda item: item[1]["total_time"], reverse=True
        )[:10]:
            pfile.write("%s: %s\n" % (key, value))
        pfile.write("Max max_time\n")
        for key, value in sorted(
            result_dict.items(), key=lambda item: item[1]["max_time"], reverse=True
        )[:10]:
            pfile.write("%s: %s\n" % (key, value))

    def dbg_store(self, dbg_info):
        """
        Function to print a debug string in a debug dump file
        """

        first = 1
        if self.debug:
            if type(dbg_info) is list:
                for curr_str in dbg_info:
                    if first:
                        first = 0
                        self.debug_info.append(str(curr_str))
                    else:
                        self.debug_info.append(", " + str(curr_str))
            else:
                self.debug_info.append(str(dbg_info))

            self.debug_info.append("\n")

        return

    def dbg(self, dbg_info):
        """
        Function to print a debug string in a debug dump file
        """

        first = 1
        if self.debug:
            if type(dbg_info) is list:
                for curr_str in dbg_info:
                    if first:
                        first = 0
                        self.dbg_file.write(str(curr_str))

                        if self.debug_print:
                            print(str(curr_str))
                    else:
                        self.dbg_file.write(", " + str(curr_str))

                        if self.debug_print:
                            print(", " + str(curr_str))

                if self.debug_print:
                    print()
            else:
                self.dbg_file.write(str(dbg_info))

                if self.debug_print:
                    print(str(dbg_info))

            self.dbg_file.write("\n")

        return

    def get_ports(self, submod_name, file_name):
        """
        Function to gather ports from a module
        """

        self.dbg("### Instantiating sub-module " + submod_name + "; FILE: " + file_name)
        if not os.path.exists(file_name):
            print(f"File not found {file_name}")
            sys.exit(1)

        with open(file_name, "r") as mod_data:

            if self.package_files is not None:
                for package in self.package_files:
                    self.dbg(
                        "\n\n################################################################################"
                    )
                    self.dbg(
                        "# Loading package " + package + " submodule " + submod_name
                    )
                    self.dbg(
                        "################################################################################"
                    )
                    self.load_import_or_include_file(
                        "SUB", "IMPORT_COMMANDLINE", package
                    )

            # Loading command line verilog include files
            if self.verilog_define_files is not None:
                for c_verilog_define_file in self.verilog_define_files:
                    self.load_import_or_include_file(
                        "SUB", "INCLUDE", c_verilog_define_file
                    )

            # Loading include files listed part of &BeginInstance
            if self.sub_include_files_list is not None:
                for c_verilog_define_file in self.sub_include_files_list:
                    self.load_import_or_include_file(
                        "SUB", "INCLUDE", c_verilog_define_file
                    )

            m_line_no = 0
            m_prev_line_no = 0
            m_function_skip = 0
            m_task_skip = 0
            m_commented_skip = 0
            m_translate_skip = 0
            m_block_comment = 0
            m_tick_ifdef_en = 1
            m_gather_till_semicolon = 0
            m_append_next_line = 0
            m_prev_line = ""
            m_skip_semicolon_check = 0
            m_package_name = "default"
            m_class_name = "default"
            m_module_found = 0
            m_skip_till_endmodule = 0
            m_file_ext = os.path.splitext(os.path.basename(file_name))[1]

            for m_line in mod_data:
                m_line_no = m_line_no + 1

                # Remove space in the end
                m_line = m_line.rstrip()
                # This is to handle encrypted modules
                if m_file_ext != ".vp" and "pragma protect begin_protected" in m_line:
                    break

                m_commented_begin_skip_regex = RE_COMMENTED_SKIP_BEGIN.search(m_line)
                m_commented_end_skip_regex = RE_COMMENTED_SKIP_END.search(m_line)

                if m_commented_begin_skip_regex:
                    m_commented_skip = 1
                    continue

                if m_commented_end_skip_regex:
                    m_commented_skip = 0
                    continue

                if m_commented_skip:
                    continue

                # Skip parsing code between pragma translate_off and translate_on
                m_translate_off_regex = RE_TRANSLATE_OFF.search(m_line)
                m_translate_on_regex = RE_TRANSLATE_ON.search(m_line)

                if m_translate_off_regex:
                    m_translate_skip = 1
                    continue

                if m_translate_on_regex:
                    m_translate_skip = 0
                    continue

                if m_translate_skip:
                    continue

                # if the whole line is commented from the beginning
                m_single_comment_begin_start_regex = (
                    RE_SINGLE_COMMENT_BEGIN_START.search(m_line)
                )
                if m_single_comment_begin_start_regex:
                    continue

                # Removing single line comment at the end of a line
                m_line = re.sub(r"\s*\/\/.*", "", m_line)

                # Removing single line block comment
                m_line = re.sub(r"\/\*.*\*\/", "", m_line)

                # Removing block comment in a single line
                m_line = remove_single_line_comment(m_line)

                # Removing multiple space to single and no space at the end
                m_line = re.sub(r"\s+", " ", m_line)
                m_line = re.sub(r"\s*$", "", m_line)

                m_block_comment_begin_start_regex = RE_BLOCK_COMMENT_BEGIN_START.search(
                    m_line
                )
                m_block_comment_begin_regex = RE_BLOCK_COMMENT_BEGIN.search(m_line)
                m_block_comment_end_regex = RE_BLOCK_COMMENT_END.search(m_line)

                if m_block_comment_end_regex:
                    m_block_comment = 0
                    # If something after the */, we need to parse
                    if m_block_comment_end_regex.group(1) == "":
                        continue
                    else:
                        m_line = m_block_comment_end_regex.group(1)

                if m_block_comment:
                    continue

                if m_block_comment_begin_start_regex:
                    m_block_comment = 1
                    continue
                elif m_block_comment_begin_regex:
                    m_block_comment = 1

                ################################################################################
                # `ifdef/ifndef/elif/else/endif processing
                ################################################################################
                m_tick_ifdef_regex = RE_TICK_IFDEF.search(m_line)
                m_tick_ifndef_regex = RE_TICK_IFNDEF.search(m_line)
                m_tick_elif_regex = RE_TICK_ELSIF.search(m_line)
                m_tick_else_regex = RE_TICK_ELSE.search(m_line)
                m_tick_endif_regex = RE_TICK_ENDIF.search(m_line)

                if m_tick_ifdef_regex:
                    m_tick_ifdef_en = self.sub_tick_ifdef_proc(
                        "ifdef", m_tick_ifdef_regex.group(1)
                    )
                    continue
                elif m_tick_ifndef_regex:
                    m_tick_ifdef_en = self.sub_tick_ifdef_proc(
                        "ifndef", m_tick_ifndef_regex.group(1)
                    )
                    continue
                elif m_tick_elif_regex:
                    m_tick_ifdef_en = self.sub_tick_ifdef_proc(
                        "elif", m_tick_elif_regex.group(1)
                    )
                    continue
                elif m_tick_else_regex:
                    m_tick_ifdef_en = self.sub_tick_ifdef_proc("else", "")
                    continue
                elif m_tick_endif_regex:
                    m_tick_ifdef_en = self.sub_tick_ifdef_proc("endif", "")
                    continue

                if not m_tick_ifdef_en:  # If tick disables the code
                    continue
                else:  # if m_tick_ifdef_en:
                    if m_append_next_line:
                        m_line = m_prev_line + " " + m_line
                        m_append_next_line = 0

                    if m_gather_till_semicolon:
                        if (
                            not m_append_next_line
                            and not m_skip_semicolon_check
                            and ANY_MONSTER_REGEX.search(m_line)
                        ):
                            print(
                                "\nError: Missing semicolon in line "
                                + str(m_prev_line_no)
                                + " in "
                                + file_name
                            )
                            print(m_prev_line + "\n")
                            self.found_error = 1

                        m_line = m_prev_line + " " + m_line

                        m_semicolon_regex = RE_SEMICOLON.search(m_line)
                        if m_semicolon_regex:
                            m_gather_till_semicolon = 0
                        else:
                            self.dbg(
                                "### "
                                + str(m_tick_ifdef_en)
                                + " :: "
                                + str(m_line_no)
                                + " :::"
                                + m_line
                                + ":::"
                            )
                            m_prev_line = m_line
                            continue

                    self.dbg(
                        "### "
                        + str(m_tick_ifdef_en)
                        + " :: "
                        + str(m_line_no)
                        + " :::"
                        + m_line
                        + ":::"
                    )

                    # Skipping empty lines
                    m_empty_line_regex = RE_EMPTY_LINE.search(m_line)
                    if m_empty_line_regex:
                        continue

                    self.dbg("\n" + str(m_line_no) + " :::" + m_line + ":::")

                    if m_skip_till_endmodule:
                        m_endmodule_regex = RE_END_MODULE_DECLARATION.search(m_line)

                        if m_endmodule_regex:
                            m_skip_till_endmodule = 0
                            continue

                    m_endmodule_regex = RE_END_MODULE_DECLARATION.search(m_line)

                    if m_endmodule_regex:
                        m_module_found = 0

                    m_semicolon_regex = RE_SEMICOLON.search(m_line)

                    ################################################################################
                    # Looking for IO declarations as part of module declaration
                    ################################################################################
                    m_module_regex = RE_MODULE_DECLARATION.search(m_line)

                    if m_module_regex:
                        # Perf improvement - check if ' import ' is there before even starting costly regex
                        if " import " in m_line:
                            m_module_import_semicolon_regex = (
                                RE_IMPORT_INMOD_SEMICOLON.search(m_line)
                            )
                            m_module_import_comma_regex = RE_IMPORT_INMOD_COMMA.search(
                                m_line
                            )

                            # If import present inside module declaration, then remove it and load packages
                            if m_module_import_comma_regex:
                                m_line = (
                                    m_module_import_comma_regex.group(1)
                                    + " import "
                                    + m_module_import_comma_regex.group(3)
                                )
                                import_file_name = (
                                    m_module_import_comma_regex.group(2) + ".sv"
                                )
                                import_package = m_module_import_comma_regex.group(2)

                                if import_package not in self.sub_packages:
                                    self.load_import_or_include_file(
                                        "SUB", "IMPORT_EMBEDDED", import_file_name
                                    )
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )
                            elif m_module_import_semicolon_regex:
                                m_line = (
                                    m_module_import_semicolon_regex.group(1)
                                    + " "
                                    + m_module_import_semicolon_regex.group(3)
                                )
                                import_file_name = (
                                    m_module_import_semicolon_regex.group(2) + ".sv"
                                )
                                import_package = (
                                    m_module_import_semicolon_regex.group(2) + ".sv"
                                )

                                if import_package not in self.sub_packages:
                                    self.load_import_or_include_file(
                                        "SUB", "IMPORT_EMBEDDED", import_file_name
                                    )
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )

                            m_module_regex = RE_MODULE_DECLARATION.search(m_line)

                    if m_module_regex:
                        m_semicolon_regex = RE_SEMICOLON.search(m_line)

                        if m_semicolon_regex:  # Complete param ended with ;
                            m_gather_till_semicolon = 0

                            m_module_param = RE_MODULE_PARAM.search(m_line)
                            m_module_noparam = RE_MODULE_NOPARAM.search(m_line)

                            if m_module_param:
                                m_module_io_declaration = m_module_param.group(2)
                                ################################################################################
                                # Parameter parsing
                                ################################################################################
                                self.param_proc("SUB", m_module_param.group(1), "", "")
                            elif m_module_noparam:
                                m_module_io_declaration = m_module_noparam.group(2)
                                ################################################################################
                                # Parameter parsing
                                ################################################################################
                                self.param_proc(
                                    "SUB", m_module_noparam.group(1), "", ""
                                )
                            else:
                                m_module_io_declaration = m_module_regex.group(2)

                            m_module_name = m_module_regex.group(1)

                            if m_module_name == submod_name:
                                m_skip_till_endmodule = 0
                                m_module_found = 1
                            else:
                                m_skip_till_endmodule = 1
                                continue

                            m_module_io_declaration = re.sub(
                                r";+", "", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"^\s*\(\s*", "", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"\s*\)\s*$", "", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"\s*,\s*", ",", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"\s+", " ", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"\s*$", "", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r"^\s*", "", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r",i", ";i", m_module_io_declaration
                            )
                            m_module_io_declaration = re.sub(
                                r",o", ";o", m_module_io_declaration
                            )

                            m_manual_io_array = m_module_io_declaration.split(";")

                            for m_manual_io in m_manual_io_array:
                                m_manual_input_regex = RE_DECLARE_INPUT.search(
                                    m_manual_io
                                )
                                m_manual_output_regex = RE_DECLARE_OUTPUT.search(
                                    m_manual_io
                                )
                                m_manual_inout_regex = RE_DECLARE_INOUT.search(
                                    m_manual_io
                                )

                                if m_manual_input_regex:  # all other input
                                    self.parse_ios(
                                        "SUB",
                                        "MANUAL",
                                        "input",
                                        m_manual_input_regex.group(1),
                                    )
                                elif m_manual_output_regex:  # all other input
                                    self.parse_ios(
                                        "SUB",
                                        "MANUAL",
                                        "output",
                                        m_manual_output_regex.group(1),
                                    )
                                elif m_manual_inout_regex:  # all other inout
                                    self.parse_ios(
                                        "SUB",
                                        "MANUAL",
                                        "inout",
                                        m_manual_inout_regex.group(1),
                                    )

                        else:  # Multi line param
                            m_gather_till_semicolon = 1
                            m_prev_line = m_line
                            m_prev_line_no = m_line_no
                            continue

                    ################################################################################
                    # `include processing
                    ################################################################################
                    m_tick_include_regex = RE_TICK_INCLUDE.search(m_line)

                    if m_tick_include_regex:
                        self.load_import_or_include_file(
                            "SUB", "INCLUDE", m_tick_include_regex.group(1)
                        )
                        continue

                    ################################################################################
                    # Skip parsing the code if the nodule is not found
                    ################################################################################
                    if m_module_found == 0:
                        continue

                    ################################################################################
                    # Function Skip
                    ################################################################################
                    m_function_regex = RE_FUNCTION.search(m_line)
                    m_endfunction_regex = RE_ENDFUNCTION.search(m_line)

                    if m_function_regex:
                        m_function_skip = 1
                        self.dbg("\n### Skipping function at " + str(m_line_no))
                        continue
                    elif m_endfunction_regex:
                        m_function_skip = 0
                        continue

                    if m_function_skip:
                        continue

                    ################################################################################
                    # Task Skip
                    ################################################################################
                    m_task_regex = RE_TASK.search(m_line)
                    m_endtask_regex = RE_ENDTASK.search(m_line)

                    if m_task_regex:
                        m_task_skip = 1
                        self.dbg("\n### Skipping task at " + str(m_line_no))
                        continue
                    elif m_endtask_regex:
                        m_task_skip = 0
                        continue

                    if m_task_skip:
                        continue

                    ################################################################################
                    # `define processing
                    ################################################################################
                    m_tick_define_regex = RE_TICK_DEFINE.search(m_line)

                    if m_tick_define_regex:
                        m_tick_def_exp = m_tick_define_regex.group(1)
                        m_tick_def_exp = re.sub(r"\s*\(", " (", m_tick_def_exp, 1)
                        m_line = re.sub(r"\s*\(", " (", m_line, 1)

                        self.tick_def_proc("SUB", m_tick_def_exp)
                        continue

                    ################################################################################
                    # `undef processing
                    ################################################################################
                    m_tick_undef_regex = RE_TICK_UNDEF.search(m_line)
                    if m_tick_undef_regex:
                        self.dbg(m_line)
                        if m_tick_undef_regex.group(1) not in self.sub_tick_defines:
                            print(
                                "\nWarning: Unabed to find #define to undef\n"
                                + m_tick_undef_regex.group(0)
                                + "\n"
                            )
                        else:
                            del self.sub_tick_defines[m_tick_undef_regex.group(1)]
                            self.dbg(
                                "  # Removed #define "
                                + m_tick_undef_regex.group(1)
                                + " for undef"
                            )

                        continue

                    ################################################################################
                    # package parsing
                    ################################################################################
                    package_regex = RE_PACKAGE.search(m_line)

                    if package_regex:
                        m_package_name = package_regex.group(1)
                        self.dbg("### Parsing Package: " + m_package_name)
                        self.packages.append(m_package_name)

                        m_package_name = "default"

                        if m_package_name not in self.sub_typedef_enums:
                            self.sub_typedef_enums[m_package_name] = {}
                            self.sub_typedef_enums[m_package_name]["default"] = {}

                        if m_package_name not in self.sub_typedef_logics:
                            self.sub_typedef_logics[m_package_name] = {}
                            self.sub_typedef_logics[m_package_name]["default"] = {}

                        if m_package_name not in self.sub_typedef_structs:
                            self.sub_typedef_structs[m_package_name] = {}
                            self.sub_typedef_structs[m_package_name]["default"] = {}

                        if m_package_name not in self.sub_typedef_unions:
                            self.sub_typedef_unions[m_package_name] = {}
                            self.sub_typedef_unions[m_package_name]["default"] = {}

                    ################################################################################
                    # class and endclass
                    ################################################################################
                    virtual_class_regex = RE_VIRTUAL_CLASS.search(m_line)
                    class_regex = RE_CLASS.search(m_line)
                    endclass_regex = RE_ENDCLASS.search(m_line)

                    if virtual_class_regex:
                        m_class_name = virtual_class_regex.group(1)
                        self.sub_classes.append(m_class_name)
                    elif class_regex:
                        m_class_name = class_regex.group(1)
                        self.sub_classes.append(m_class_name)
                    elif endclass_regex:
                        m_class_name = "default"

                    if virtual_class_regex or class_regex:
                        if m_class_name not in self.sub_typedef_enums[m_package_name]:
                            self.sub_typedef_enums[m_package_name][m_class_name] = {}

                        if m_class_name not in self.sub_typedef_logics[m_package_name]:
                            self.sub_typedef_logics[m_package_name][m_class_name] = {}

                        if m_class_name not in self.sub_typedef_structs[m_package_name]:
                            self.sub_typedef_structs[m_package_name][m_class_name] = {}

                        if m_class_name not in self.sub_typedef_unions[m_package_name]:
                            self.sub_typedef_unions[m_package_name][m_class_name] = {}

                    ################################################################################
                    # typedef enum logic extraction
                    ################################################################################
                    m_enum_regex = RE_TYPEDEF_ENUM.search(m_line)

                    if m_enum_regex:
                        if m_semicolon_regex:  # Complete param ended with ;
                            m_line = re.sub(r"\s+", " ", m_line)
                            m_enum_more_regex = RE_TYPEDEF_ENUM_EXTRACT.search(m_line)

                            if m_enum_more_regex:
                                m_gather_till_semicolon = 0
                                self.enums_proc(
                                    "SUB",
                                    m_enum_more_regex.group(2) + ";",
                                    m_package_name,
                                    m_class_name,
                                )

                                m_line = (
                                    m_enum_more_regex.group(1)
                                    + " "
                                    + m_enum_more_regex.group(3)
                                )

                                m_line = re.sub(r"\s*logic\s+", "", m_line)
                                self.parse_reg_wire_logic(
                                    "SUB",
                                    "TYPEDEF",
                                    "logic",
                                    m_line,
                                    m_package_name,
                                    m_class_name,
                                )
                            else:
                                self.dbg(
                                    "\nError: Unable to extract enums from the following"
                                )
                                self.dbg(m_line)
                                print(
                                    "\nError: Unable to extract enums from the following"
                                )
                                print(m_line)
                                self.found_error = 1

                            m_prev_line = ""
                            continue
                        else:  # Multi line param
                            m_gather_till_semicolon = 1

                    ################################################################################
                    # typedef logic extraction
                    ################################################################################
                    m_typedef_logic_regex = RE_TYPEDEF_LOGIC.search(m_line)

                    if m_typedef_logic_regex:
                        if m_semicolon_regex:  # Complete param ended with ;
                            m_gather_till_semicolon = 0
                            m_line = re.sub(r"\s+", " ", m_line)
                            self.dbg("\n::: " + m_line + " :::")
                            m_line = m_typedef_logic_regex.group(1)

                            self.parse_reg_wire_logic(
                                "SUB",
                                "TYPEDEF",
                                "logic",
                                m_line,
                                m_package_name,
                                m_class_name,
                            )
                        else:  # Multi line param
                            m_gather_till_semicolon = 1

                    ################################################################################
                    # typedef struct extraction
                    ################################################################################
                    m_typedef_struct_check_regex = RE_TYPEDEF_STRUCT_CHECK.search(
                        m_line
                    )
                    m_typedef_struct_nospace_regex = RE_TYPEDEF_STRUCT_NOSPACE.search(
                        m_line
                    )
                    m_typedef_closing_brace_regex = RE_CLOSING_BRACE.search(m_line)

                    if m_typedef_struct_check_regex or m_typedef_struct_nospace_regex:
                        if m_typedef_closing_brace_regex:  # Complete param ended with ;
                            m_skip_semicolon_check = 0
                            m_gather_till_semicolon = 0
                            m_line = re.sub(r"\s+", " ", m_line)
                            self.parse_struct_union(
                                "STRUCT", "SUB", m_line, m_package_name, m_class_name
                            )
                            continue
                        else:  # Multi line param
                            m_skip_semicolon_check = 1
                            m_gather_till_semicolon = 1

                    ################################################################################
                    # typedef union extraction
                    ################################################################################
                    m_typedef_union_check_regex = RE_TYPEDEF_UNION_CHECK.search(m_line)
                    m_typedef_union_nospace_regex = RE_TYPEDEF_UNION_NOSPACE.search(
                        m_line
                    )
                    m_typedef_closing_brace_regex = RE_CLOSING_BRACE.search(m_line)

                    if m_typedef_union_check_regex or m_typedef_union_nospace_regex:
                        if m_typedef_closing_brace_regex:  # Complete param ended with ;
                            m_gather_till_semicolon = 0
                            m_skip_semicolon_check = 0
                            m_line = re.sub(r"\s+", " ", m_line)
                            self.parse_struct_union(
                                "UNION", "SUB", m_line, m_package_name, m_class_name
                            )
                            continue
                        else:  # Multi line param
                            m_gather_till_semicolon = 1
                            m_skip_semicolon_check = 1

                    ################################################################################
                    # Detect typedef usages
                    ################################################################################
                    if self.parsing_format != "verilog":
                        m_temp_line = re.sub(r"\s+", " ", m_line)
                        m_temp_line = re.sub(r"^\s*", "", m_temp_line)

                        m_temp_line_split_list = m_temp_line.split(" ", 1)

                        m_typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                            m_temp_line_split_list[0]
                        )
                        m_typedef_ref_double_regex = (
                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                m_temp_line_split_list[0]
                            )
                        )

                        m_found_in_typedef = ""

                        if m_typedef_ref_double_regex:
                            m_typedef_package = m_typedef_ref_double_regex.group(1)
                            m_typedef_class = m_typedef_ref_double_regex.group(2)
                            m_typedef_name = m_typedef_ref_double_regex.group(3)
                        elif m_typedef_ref_regex:  # If a package or class is associated
                            if m_typedef_ref_regex.group(1) in list(self.sub_classes):
                                m_typedef_package = "default"
                                m_typedef_class = m_typedef_ref_regex.group(1)
                                m_typedef_name = m_typedef_ref_regex.group(2)
                            else:
                                m_typedef_package = m_typedef_ref_regex.group(1)
                                m_typedef_class = "default"
                                m_typedef_name = m_typedef_ref_regex.group(2)
                        else:  # No package referred
                            m_typedef_package = "default"
                            m_typedef_class = "default"
                            m_typedef_name = m_temp_line_split_list[0]

                        if m_typedef_package not in self.sub_packages:
                            self.load_import_or_include_file(
                                "SUB", "IMPORT_COMMANDLINE", m_typedef_package + ".sv"
                            )

                        if (
                            m_typedef_name
                            in self.sub_typedef_logics[m_typedef_package][
                                m_typedef_class
                            ]
                        ):
                            m_found_in_typedef = "LOGICS"
                        elif (
                            m_typedef_name
                            in self.sub_typedef_structs[m_typedef_package][
                                m_typedef_class
                            ]
                        ):
                            m_found_in_typedef = "STRUCTS"
                        elif (
                            m_typedef_name
                            in self.sub_typedef_unions[m_typedef_package][
                                m_typedef_class
                            ]
                        ):
                            m_found_in_typedef = "UNIONS"

                        if m_found_in_typedef != "":
                            if m_semicolon_regex:  # Complete typedef ended with ;
                                m_gather_till_semicolon = 0
                                m_typedef_equal_regex = RE_EQUAL_EXTRACT_SPACE.search(
                                    m_temp_line
                                )

                                if m_typedef_equal_regex:
                                    m_temp_line = m_typedef_equal_regex.group(1)
                                    m_temp_line = re.sub(r"\s+$", "", m_temp_line)

                                self.binding_typedef("SUB", "MANUAL", m_temp_line)

                                continue
                            else:
                                m_gather_till_semicolon = 1

                    ################################################################################
                    # Parameter parsing
                    ################################################################################
                    m_param_regex = RE_PARAM.search(m_line)
                    m_localparam_regex = RE_LOCALPARAM.search(m_line)

                    if m_param_regex or m_localparam_regex:
                        if m_semicolon_regex:  # Complete param ended with ;
                            self.param_proc("SUB", m_line, m_package_name, m_class_name)
                            m_gather_till_semicolon = 0
                        else:  # Multi line param
                            m_gather_till_semicolon = 1

                    ################################################################################
                    # imported package processing
                    ################################################################################
                    m_import_regex = RE_IMPORT.search(m_line)
                    m_import_with_colons_regex = RE_IMPORT_COLONS.search(m_line)

                    if m_import_regex:
                        m_import_file_name = m_import_regex.group(1) + ".sv"
                        m_import_package = m_import_regex.group(1)
                    elif m_import_with_colons_regex:
                        m_import_file_name = m_import_with_colons_regex.group(1) + ".sv"
                        m_import_package = m_import_with_colons_regex.group(1)

                    if m_import_regex or m_import_with_colons_regex:
                        if m_import_package not in self.sub_packages:
                            self.load_import_or_include_file(
                                "SUB", "IMPORT_EMBEDDED", m_import_file_name
                            )
                        else:
                            self.dbg(
                                "### Skip importing previously imported package "
                                + m_import_package
                            )

                        continue

                    ################################################################################
                    # Manual declarations
                    ################################################################################
                    m_manual_input_regex = RE_DECLARE_INPUT.search(m_line)
                    m_manual_output_regex = RE_DECLARE_OUTPUT.search(m_line)
                    m_manual_inout_regex = RE_DECLARE_INOUT.search(m_line)

                    if (
                        m_manual_input_regex
                        or m_manual_output_regex
                        or m_manual_inout_regex
                    ):
                        if m_semicolon_regex:  # Complete param ended with ;
                            m_gather_till_semicolon = 0

                            if m_manual_input_regex:  # all other input
                                self.parse_ios(
                                    "SUB",
                                    "MANUAL",
                                    "input",
                                    m_manual_input_regex.group(1),
                                )
                            elif m_manual_output_regex:  # all other input
                                self.parse_ios(
                                    "SUB",
                                    "MANUAL",
                                    "output",
                                    m_manual_output_regex.group(1),
                                )
                            elif m_manual_inout_regex:  # all other input
                                self.parse_ios(
                                    "SUB",
                                    "MANUAL",
                                    "inout",
                                    m_manual_inout_regex.group(1),
                                )

                            continue
                        else:  # Multi line param
                            m_gather_till_semicolon = 1

                m_prev_line = m_line
                m_prev_line_no = m_line_no

        return

    def clog2(self, x):
        """
        Function to calculate clog2. Returns the ceiling log base two of an integer
        """

        if x < 0:
            raise ValueError("expected depth >= 0")

        addrSize, shifter = 0, 1
        while x > shifter:
            shifter <<= 1
            addrSize += 1

        return addrSize

    def find_manual_submod(self, gen_dependencies, submod_name):
        """
        Function to check if keyword is a verilog or system verilog file
        """

        found_submod_file = 0

        if self.gen_dependencies:
            # Look for systemverilog module
            file_name_with_ext = submod_name + ".psv"
            submod_file_with_path = file_name_with_ext

            if os.path.isfile(file_name_with_ext):  # In file doesn't exist
                found_submod_file = 1
                submod_file_with_path = file_name_with_ext
            else:
                if not found_submod_file:
                    for dir in self.incl_dirs:
                        if not found_submod_file:
                            sub_mode_file_path = (
                                str(dir) + "/" + str(file_name_with_ext)
                            )
                            if os.path.isfile(sub_mode_file_path):
                                found_submod_file = 1
                                submod_file_with_path = sub_mode_file_path

        if not found_submod_file:
            # Look for systemverilog module
            file_name_with_ext = submod_name + ".sv"
            submod_file_with_path = file_name_with_ext

            if os.path.isfile(file_name_with_ext):  # In file doesn't exist
                found_submod_file = 1
                submod_file_with_path = file_name_with_ext
            else:
                if not found_submod_file:
                    for dir in self.incl_dirs:
                        if not found_submod_file:
                            sub_mode_file_path = (
                                str(dir) + "/" + str(file_name_with_ext)
                            )
                            if os.path.isfile(sub_mode_file_path):
                                found_submod_file = 1
                                submod_file_with_path = sub_mode_file_path

        if not found_submod_file:
            submod_file_with_path = self.find_in_files(file_name_with_ext)

            if submod_file_with_path is not None:
                found_submod_file = 1

        if not found_submod_file:
            # Look for verilog module
            file_name_with_ext = submod_name + ".v"

            if os.path.isfile(file_name_with_ext):  # In file doesn't exist
                found_submod_file = 1
                submod_file_with_path = file_name_with_ext
            else:
                if not found_submod_file:
                    for dir in self.incl_dirs:
                        if not found_submod_file:
                            sub_mode_file_path = (
                                str(dir) + "/" + str(file_name_with_ext)
                            )
                            if os.path.isfile(sub_mode_file_path):
                                found_submod_file = 1
                                submod_file_with_path = sub_mode_file_path

        if not found_submod_file:
            submod_file_with_path = self.find_in_files(file_name_with_ext)

            if submod_file_with_path is not None:
                found_submod_file = 1

        if found_submod_file:
            return submod_file_with_path
        else:
            return 0

    def check_for_bracket(self, check_str):
        """
        Function to check for () and split the string between (*) and rest
        """
        bracket_count = 0
        first_open_bracket_found = 0
        check_str_array = list(check_str)
        found_closing_bracket = 0
        return_str_list = []

        if "(" not in check_str or ")" not in check_str:
            return [found_closing_bracket, "", ""]

        for idx, char in enumerate(check_str_array):
            if char == "(":
                first_open_bracket_found = 1
                bracket_count += 1
            elif char == ")":
                bracket_count -= 1
                if bracket_count == 0 and first_open_bracket_found:
                    found_closing_bracket = 1
                    break

        return_str_list.append(found_closing_bracket)
        return_str_list.append(check_str[: idx + 1])
        return_str_list.append(check_str[idx + 1 :])

        return return_str_list

    def binding_typedef(self, module_type, bind_type, bind_str):
        """
        Function to bind a typedef to a variable
        """

        bind_class = "default"
        bind_package = "default"
        bind_depth = ""
        bind_bitdef = ""
        packed_depth = 0

        bind_str = re.sub(r"\s*,\s*", ",", bind_str)
        bind_str = re.sub(r"\s*;\s*", "", bind_str)
        bind_str = re.sub(r"^\s*", "", bind_str)
        bind_str = re.sub(r"\s*$", "", bind_str)

        typedef_no_bitdef_no_depth_regex = RE_TYPEDEF_NO_BITDEF_NO_DEPTH.search(
            bind_str
        )
        typedef_bitdef_no_depth_regex = RE_TYPEDEF_BITDEF_NO_DEPTH.search(bind_str)
        typedef_no_bitdef_depth_regex = RE_TYPEDEF_NO_BITDEF_DEPTH.search(bind_str)
        typedef_bitdef_depth_regex = RE_TYPEDEF_BITDEF_DEPTH.search(bind_str)

        if typedef_bitdef_no_depth_regex:
            bind_bitdef = (
                typedef_bitdef_no_depth_regex.group(1)
                + " ["
                + typedef_bitdef_no_depth_regex.group(2)
            )
            bind_depth = ""
            bind_str = (
                typedef_bitdef_no_depth_regex.group(1)
                + " "
                + typedef_bitdef_no_depth_regex.group(3)
            )
        elif typedef_no_bitdef_depth_regex:
            bind_bitdef = ""
            bind_depth = typedef_no_bitdef_depth_regex.group(3)
            bind_str = (
                typedef_no_bitdef_depth_regex.group(1)
                + " "
                + typedef_no_bitdef_depth_regex.group(2)
            )
        elif typedef_bitdef_depth_regex:
            bind_bitdef = typedef_bitdef_depth_regex.group(2)
            bind_depth = typedef_bitdef_depth_regex.group(4)
            bind_str = (
                typedef_bitdef_depth_regex.group(1)
                + " "
                + typedef_bitdef_depth_regex.group(3)
            )

        bind_str = re.sub(r"\s+", " ", bind_str)
        bind_str_split_list = bind_str.split(" ")

        double_colon_regex = RE_TYPEDEF_DOUBLE_COLON.search(bind_str_split_list[0])
        double_double_colon_regex = RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
            bind_str_split_list[0]
        )

        if double_double_colon_regex:
            bind_package = double_double_colon_regex.group(1)
            bind_class = double_double_colon_regex.group(2)
            bind_typedef = double_double_colon_regex.group(3)
        elif double_colon_regex:
            bind_package = double_colon_regex.group(1)
            bind_typedef = double_colon_regex.group(2)
        else:
            bind_typedef = bind_str_split_list[0]

        if module_type == "TOP":
            if bind_package not in self.packages:
                self.load_import_or_include_file(
                    "TOP", "IMPORT_COMMANDLINE", bind_package + ".sv"
                )
        else:
            if bind_package not in self.sub_packages:
                self.load_import_or_include_file(
                    "SUB", "IMPORT_COMMANDLINE", bind_package + ".sv"
                )

        bind_var = bind_str_split_list[1]
        bind_var_split_list = bind_var.split(",")

        self.dbg(
            "### TYPEDEF BIND: "
            + bind_type
            + " : "
            + bind_package
            + " : "
            + bind_class
            + " : "
            + bind_typedef
            + " : "
            + bind_var
            + " : "
            + bind_depth
        )

        if module_type == "TOP":
            found_in_typedef = ""

            if bind_typedef in self.typedef_logics[bind_package][bind_class]:
                found_in_typedef = "LOGICS"
            elif bind_typedef in self.typedef_structs[bind_package][bind_class]:
                found_in_typedef = "STRUCTS"
            elif bind_typedef in self.typedef_unions[bind_package][bind_class]:
                found_in_typedef = "UNIONS"

            if found_in_typedef != "":
                for c_bind_var in bind_var_split_list:
                    self.typedef_bindings[c_bind_var] = {}
                    self.typedef_bindings[c_bind_var]["name"] = c_bind_var
                    self.typedef_bindings[c_bind_var]["typedef"] = bind_typedef
                    self.typedef_bindings[c_bind_var]["type"] = found_in_typedef
                    self.typedef_bindings[c_bind_var]["package"] = bind_package
                    self.typedef_bindings[c_bind_var]["class"] = bind_class
                    self.typedef_bindings[c_bind_var]["mode"] = bind_type
                    self.typedef_bindings[c_bind_var]["packed"] = bind_bitdef
                    self.typedef_bindings[c_bind_var]["depth"] = bind_depth
            else:
                self.dbg("\nError: Unable to find the typedef for the following")
                self.dbg(
                    "### TYPEDEF BIND: "
                    + found_in_typedef
                    + " : "
                    + bind_str_split_list[0]
                    + " : "
                    + bind_str_split_list[1]
                )
                print("\nError: Unable to find the typedef for the following")
                print(
                    "### TYPEDEF BIND: "
                    + found_in_typedef
                    + " : "
                    + bind_str_split_list[0]
                    + " : "
                    + bind_str_split_list[1]
                )
                self.found_error = 1
        else:
            found_in_typedef = ""

            if bind_typedef in self.sub_typedef_logics[bind_package][bind_class]:
                found_in_typedef = "LOGICS"
            elif bind_typedef in self.sub_typedef_structs[bind_package][bind_class]:
                found_in_typedef = "STRUCTS"
            elif bind_typedef in self.sub_typedef_unions[bind_package][bind_class]:
                found_in_typedef = "UNIONS"

            if found_in_typedef != "":
                for c_bind_var in bind_var_split_list:
                    self.sub_typedef_bindings[c_bind_var] = {}
                    self.sub_typedef_bindings[c_bind_var]["name"] = c_bind_var
                    self.sub_typedef_bindings[c_bind_var]["typedef"] = bind_typedef
                    self.sub_typedef_bindings[c_bind_var]["type"] = found_in_typedef
                    self.sub_typedef_bindings[c_bind_var]["package"] = bind_package
                    self.sub_typedef_bindings[c_bind_var]["class"] = bind_class
                    self.sub_typedef_bindings[c_bind_var]["mode"] = bind_type
                    self.sub_typedef_bindings[c_bind_var]["packed"] = bind_bitdef
                    self.sub_typedef_bindings[c_bind_var]["depth"] = bind_depth
            else:
                self.dbg("\nError: Unable to find the typedef for the following")
                self.dbg(
                    "### TYPEDEF BIND: "
                    + found_in_typedef
                    + " : "
                    + bind_str_split_list[0]
                    + " : "
                    + bind_str_split_list[1]
                )
                print("\nError: Unable to find the typedef for the following")
                print(
                    "### TYPEDEF BIND: "
                    + found_in_typedef
                    + " : "
                    + bind_str_split_list[0]
                    + " : "
                    + bind_str_split_list[1]
                )
                self.found_error = 1
                sys.exit(1)

        return

    def check_if_parsing_needed(self, curr_line):
        """
        Function to check if the remaining line is to be parsed along with next line
        """

        parsing_needed = 0

        curr_line_unique_case_regex = RE_UNIQUE_CASE.search(curr_line)
        curr_line_case_regex = RE_CASE.search(curr_line)
        curr_line_casez_regex = RE_CASEZ.search(curr_line)
        curr_line_if_regex = RE_IF.search(curr_line)
        curr_line_else_if_regex = RE_ELSEIF.search(curr_line)
        curr_line_else_regex = RE_ELSE.search(curr_line)
        curr_line_semicolon_regex = RE_SEMICOLON.search(curr_line)
        curr_line_end_regex = RE_END.search(curr_line)
        curr_line_begin_regex = RE_BEGIN_NO_GROUP.search(curr_line)
        curr_line_endcase_regex = RE_ENDCASE.search(curr_line)

        if (
            curr_line_case_regex
            or curr_line_casez_regex
            or curr_line_if_regex
            or curr_line_else_if_regex
            or curr_line_else_regex
            or curr_line_semicolon_regex
            or curr_line_end_regex
            or curr_line_endcase_regex
            or curr_line_begin_regex
            or curr_line_unique_case_regex
        ):
            parsing_needed = 1

        return parsing_needed

    def parse_assignments(self, assignment_type, assign_str):
        """
        Function to parse a single assignment
        """

        self.dbg("\n### " + assignment_type + " :: " + assign_str)

        if RE_SYS_TASK.match(assign_str):
            self.dbg("\n# Ignore system task")
            return

        # Replace the inside operator with another operator (*) so that the 'inside' keyword does not get appended to
        # other strings after whitespace removal
        # TODO by icanma: check/verify below implementation for handling inside operator
        # assign_str = re.sub(r"\binside\b", "*", assign_str)

        # Replace the first = with ###, so that we dont have to worry about the
        # presence of = in comparison
        assign_str = re.sub(r"\s*", "", assign_str)

        if assignment_type == "ALWAYS_SEQ":
            assign_str_reset_val_regex = RE_RESET_VAL.search(assign_str)

            self.auto_reset_val = ""

            if assign_str_reset_val_regex:
                self.auto_reset_val = assign_str_reset_val_regex.group(2)
                assign_str = assign_str_reset_val_regex.group(
                    1
                ) + assign_str_reset_val_regex.group(3)

            assign_str = assign_str.replace("<=", "###", 1)
        else:
            assign_str = assign_str.replace("=", "###", 1)

        # Spliting the assign statment with lhs and rhs
        assignment_triple_hash_regex = RE_TRIPLE_HASH.search(assign_str)

        if assignment_triple_hash_regex:
            lhs_assign_str = assignment_triple_hash_regex.group(1)
            rhs_assign_str = assignment_triple_hash_regex.group(2)
        else:
            if assignment_type == "ALWAYS_SEQ":
                print(
                    '\nError: Unable to find non-blocking assignment "<=" inside sequential always block at line '
                    + str(self.line_no)
                )
                print(self.line)
                assign_str = assign_str.replace("=", "###", 1)
            else:
                print(
                    '\nError: Unable to find blocking assignment "=" inside combinational always block at line '
                    + str(self.line_no)
                )
                print(self.line)
                assign_str = assign_str.replace("<=", "###", 1)

            print(self.original_line + "\n")
            self.found_error = 1

            assignment_triple_hash_regex = RE_TRIPLE_HASH.search(assign_str)

            if assignment_triple_hash_regex:
                lhs_assign_str = assignment_triple_hash_regex.group(1)
                rhs_assign_str = assignment_triple_hash_regex.group(2)
            else:
                return

        # Skip LHS parsing for wired assignments
        if assignment_type != "wiredassign":
            # LHS Parsing
            # LHS can be concat of two or more self.signals
            lhs_assign_comma_regex = RE_COMMA.search(lhs_assign_str)

            lhs_assign_str_array = []
            # If multiple declarations on the same line, then break it
            if lhs_assign_comma_regex:
                # removing space, { and }
                lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                lhs_assign_str_array = lhs_assign_str.split(",")
            else:  # Single declaration, then append to the array
                lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                lhs_assign_str_array.append(lhs_assign_str)

            self.dbg("  # LHS:" + lhs_assign_str)
            for curr_lhs in lhs_assign_str_array:
                if assignment_type == "assign":
                    if self.parsing_format == "verilog":
                        self.parse_signal("wire", curr_lhs, 0)
                    else:
                        self.parse_signal("reg", curr_lhs, 0)
                else:
                    if self.auto_reset_val != "" and self.auto_reset_en:
                        self.parse_signal("reg", curr_lhs, 1)
                    else:
                        self.parse_signal("reg", curr_lhs, 0)

        # RHS Parsing
        # Remove : only outside [], inside [] are for bitwidth definition
        self.dbg("  # RHS:" + rhs_assign_str)

        # Replace $bits(signal) with a constant to skip parsing
        rhs_assign_str = re.sub(r"\$bits\([\w:]*\)", "", rhs_assign_str)

        # Replace $signed and signed'
        rhs_assign_str = re.sub(r"\$signed", "", rhs_assign_str)
        rhs_assign_str = re.sub(r"\bsigned\'", "", rhs_assign_str)

        rhs_assign_str = re.sub(r"::", "#", rhs_assign_str)
        rhs_assign_str = re.sub(r"\'\(", " ", rhs_assign_str)

        rhs_assign_str = self.remove_outside_sqbrackets("assign", rhs_assign_str)

        # Break it into individual
        rhs_assign_str_array = rhs_assign_str.split()

        for rhs_signal in rhs_assign_str_array:
            self.parse_signal("signal", rhs_signal, 0)

        return

    def parse_case_expression(self, exp_str):
        """
        Function to parse a case expression
        """

        exp_str = re.sub(r"::", "#", exp_str)
        exp_str_clean = self.remove_outside_sqbrackets("assign", exp_str)

        # Break it into individual
        exp_str_clean_list = exp_str_clean.split()

        for cond_signal in exp_str_clean_list:
            self.parse_signal("signal", cond_signal, 0)

        return

    def parse_conditions(self, cond_str):
        """
        Function to parse input conditions
        """

        dollar_bits_width = 0

        if "$bits(" in cond_str:
            dollar_bits_regex = RE_DOLLAR_BITS_CHECK.search(cond_str)

            if dollar_bits_regex:
                dollar_bits_width = self.get_dollar_bits_val(
                    "TOP", dollar_bits_regex.group(3), "default", "default"
                )
                cond_str = (
                    dollar_bits_regex.group(1)
                    + str(dollar_bits_width)
                    + dollar_bits_regex.group(5)
                )

        # Replace $signed and signed'
        cond_str = re.sub(r"\$signed", "", cond_str)
        cond_str = re.sub(r"\bsigned\'", "", cond_str)

        # Remove space before [ for HLS generated code
        cond_str = re.sub(r"\s*\[", "[", cond_str)
        cond_str = re.sub(r"\[\s*", "[", cond_str)

        # Remove : only outside [], inside [] are for bitwidth definition
        self.dbg("  # CONDITION:" + cond_str)
        # avoid removing package references
        cond_str = re.sub(r"::", "#", cond_str)

        cond_str = self.remove_outside_sqbrackets("assign", cond_str)

        # Break it into individual
        cond_str_list = cond_str.split()

        for cond_signal in cond_str_list:
            self.parse_signal("signal", cond_signal, 0)

        self.dbg("\n")

        return

    def update_typedef_regs(self, reg_type, reg_mode, reg):
        """
        Function to update regs/logics with manual or force typedefs
        """

        # Removing depth definition if any
        reg = re.sub(r"\s*\[[\w`:-]+\]\s*", "", reg)
        reg = re.sub(r"\s+", "", reg)
        reg_list = reg.split(",")

        for reg_name in reg_list:
            int_class = self.typedef_bindings[reg_name]["class"]
            int_package = self.typedef_bindings[reg_name]["package"]
            typedef = self.typedef_bindings[reg_name]["typedef"]
            signal_bitdef = ""
            signal_uwidth = ""
            signal_lwidth = ""
            signal_depth = ""

            if self.typedef_bindings[reg_name]["type"] == "LOGICS":
                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[reg_name]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )

                signal_uwidth = self.typedef_logics[int_package][int_class][typedef][
                    "uwidth"
                ]
                signal_lwidth = self.typedef_logics[int_package][int_class][typedef][
                    "lwidth"
                ]
                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""
            elif self.typedef_bindings[reg_name]["type"] == "STRUCTS":
                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[reg_name]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )

                signal_lwidth = 0

                if self.typedef_structs[int_package][int_class][typedef]["width"] != 0:
                    signal_uwidth = (
                        self.typedef_structs[int_package][int_class][typedef]["width"]
                        - 1
                    )
                else:
                    signal_uwidth = 0
                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""
            elif self.typedef_bindings[reg_name]["type"] == "UNIONS":
                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[reg_name]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[reg_name]["package"]
                            + "::"
                            + self.typedef_bindings[reg_name]["class"]
                            + "::"
                            + self.typedef_bindings[reg_name]["typedef"]
                        )

                signal_lwidth = 0

                if self.typedef_unions[int_package][int_class][typedef]["width"] != 0:
                    signal_uwidth = (
                        self.typedef_unions[int_package][int_class][typedef]["width"]
                        - 1
                    )
                else:
                    signal_uwidth = 0

                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""

            self.update_wire_reg_signal_lists(
                reg_type,
                reg_mode,
                reg_name,
                signal_bitdef,
                signal_uwidth,
                signal_lwidth,
                signal_depth,
                "",
            )

        return

    def parse_signal(self, signal_type, signal_str, reset_store):
        """
        Function to parse a signal/param/define/constant
        """

        signal_uwidth = ""
        signal_lwidth = ""
        signal_depth = ""
        signal_bitdef = ""

        # TODO: Need to parse system verilog struct
        signal_str_sqbrct_regex = RE_OPEN_SQBRCT.search(signal_str)
        signal_str_tick_regex = RE_NUM_TICK.search(signal_str)
        signal_str_constant_regex = RE_CONSTANT.search(signal_str)
        signal_str_define_tick_begin_regex = RE_DEFINE_TICK_BEGIN.search(signal_str)
        signal_hash_regex = RE_HASH.search(signal_str)
        signal_double_hash_regex = RE_DOUBLE_HASH.search(signal_str)
        signal_dot_regex = RE_DOT.search(signal_str)
        signal_dollar_bits_regex = None

        if "$bits(" in signal_str:
            signal_dollar_bits_regex = RE_DOLLAR_BITS_CHECK.search(signal_str)

        # Remove .next, .prev as part of self.signals
        signal_str = re.sub(r"\.next$", "", signal_str)
        signal_str = re.sub(r"\.prev$", "", signal_str)
        signal_str = re.sub(r"\$clog2$", "", signal_str)
        signal_str = re.sub(r"\[\s+", "[", signal_str)
        # signal_str = re.sub(r"\$bits", "", signal_str)
        int_package = "default"
        int_class = "default"
        module_type = "TOP"

        # Skip if this is a constnat
        if signal_str == "":
            self.dbg("    # Skipping empty signal" + signal_str)
            return
        if signal_str_tick_regex:
            self.dbg("    # Skipping constant " + signal_str)
            return
        elif signal_str_constant_regex:
            self.dbg("    # Skipping constant " + signal_str)
            return
        elif signal_str_define_tick_begin_regex:
            self.dbg("    # Skipping define " + signal_str)
            return
        elif signal_str in self.params:
            self.dbg("    # Skipping parameter " + signal_str)
            return
        elif signal_str in self.genvars:
            self.dbg("    # Skipping genvar " + signal_str)
            return
        elif signal_str in self.integers:
            self.dbg("    # Skipping integer " + signal_str)
            return
        elif signal_str == "default":
            self.dbg("    # Skipping default case expression")
            return
        elif signal_str in self.functions_list:
            self.dbg("    # Skipping a function call " + signal_str)
            return
        elif (
            (signal_hash_regex and "[" not in signal_hash_regex.group(1))
            or signal_double_hash_regex
        ) and not signal_dollar_bits_regex:  # If this is an imported enum
            # elif (signal_hash_regex or signal_double_hash_regex) and not signal_dollar_bits_regex:  # If this is an imported enum
            if signal_double_hash_regex:  # If a package name and class is associated
                int_package = signal_double_hash_regex.group(1)
                int_class = signal_double_hash_regex.group(2)
                member_name = signal_double_hash_regex.group(3)
            else:
                if module_type == "TOP":
                    if signal_hash_regex.group(1) in list(self.classes):
                        # int_package = 'default'
                        int_class = signal_hash_regex.group(1)
                        member_name = signal_hash_regex.group(2)
                    else:
                        int_package = signal_hash_regex.group(1)
                        int_class = "default"
                        member_name = signal_hash_regex.group(2)
                else:
                    if signal_hash_regex.group(1) in list(self.sub_classes):
                        int_class = signal_hash_regex.group(1)
                        member_name = signal_hash_regex.group(2)
                    else:
                        int_package = signal_hash_regex.group(1)
                        int_class = "default"
                        member_name = signal_hash_regex.group(2)

            if int_package not in self.packages:  # Look for the package
                self.load_import_or_include_file(
                    "TOP", "IMPORT_COMMANDLINE", int_package + ".sv"
                )

            if member_name in self.typedef_logics[int_package][int_class]:
                signal_str = signal_str.replace("#", "::")
                self.dbg("    # Skipping imported enum " + signal_str)

            elif member_name in self.typedef_structs[int_package][int_class]:
                signal_str = signal_str.replace("#", "::")
                self.dbg("    # Skipping imported struct " + signal_str)

            elif member_name in self.typedef_unions[int_package][int_class]:
                signal_str = signal_str.replace("#", "::")
                self.dbg("    # Skipping imported union " + signal_str)

            elif member_name in self.typedef_enums[int_package][int_class]:
                signal_str = signal_str.replace("#", "::")
                self.dbg("    # Skipping imported enum " + signal_str)

            elif member_name in self.functions_list:
                self.dbg("    # Skipping a function call " + signal_str)

            else:
                signal_str = signal_str.replace("#", "::")

                if signal_str in self.functions_list:
                    self.dbg("    # Skipping a function call " + signal_str)

                else:
                    print("\nError: Unable to parse a signal :: " + signal_str)
                    self.dbg("\nError: Unable to parse a signal :: " + signal_str)
                    self.found_error = 1

            return

        elif signal_str in self.typedef_bindings or (
            signal_dot_regex and signal_dot_regex.group(1) in self.typedef_bindings
        ):  # If this is a imported enum
            # TODO: Need to parse nested .
            if signal_dot_regex:
                signal_str = signal_dot_regex.group(1)

            int_class = self.typedef_bindings[signal_str]["class"]
            int_package = self.typedef_bindings[signal_str]["package"]
            typedef = self.typedef_bindings[signal_str]["typedef"]

            if self.typedef_bindings[signal_str]["type"] == "LOGICS":
                signal_name = signal_str

                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[signal_str]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )

                signal_uwidth = self.typedef_logics[int_package][int_class][typedef][
                    "uwidth"
                ]
                signal_lwidth = self.typedef_logics[int_package][int_class][typedef][
                    "lwidth"
                ]
                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""

            elif self.typedef_bindings[signal_str]["type"] == "STRUCTS":
                signal_name = signal_str

                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[signal_str]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )

                signal_lwidth = 0

                if self.typedef_structs[int_package][int_class][typedef]["width"] != 0:
                    signal_uwidth = (
                        self.typedef_structs[int_package][int_class][typedef]["width"]
                        - 1
                    )
                else:
                    signal_uwidth = 0
                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""

            elif self.typedef_bindings[signal_str]["type"] == "UNIONS":
                signal_name = signal_str

                if int_package == "default" or int_package == "":
                    if int_class == "default" or int_class == "":
                        signal_bitdef = self.typedef_bindings[signal_str]["typedef"]
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                else:
                    if int_class == "default" or int_class == "":
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )
                    else:
                        signal_bitdef = (
                            self.typedef_bindings[signal_str]["package"]
                            + "::"
                            + self.typedef_bindings[signal_str]["class"]
                            + "::"
                            + self.typedef_bindings[signal_str]["typedef"]
                        )

                signal_lwidth = 0

                if self.typedef_unions[int_package][int_class][typedef]["width"] != 0:
                    signal_uwidth = (
                        self.typedef_unions[int_package][int_class][typedef]["width"]
                        - 1
                    )
                else:
                    signal_uwidth = 0

                # TODO: Need to derive depth for mutli dimentional array
                signal_depth = ""

            self.update_wire_reg_signal_lists(
                signal_type,
                "AUTO",
                signal_name,
                signal_bitdef,
                signal_uwidth,
                signal_lwidth,
                signal_depth,
                "",
            )

        else:
            if signal_str_sqbrct_regex:
                signal_str = signal_str.replace("#", "::")
                signal_str = signal_str.replace("[", " ", 1)
                signal_str_array = signal_str.split()
                # removing the closing ]
                signal_name = signal_str_array[0]
                signal_bitdef = re.sub(r"\]$", "", signal_str_array[1])

                signal_bitdef_sqbrct_regex = RE_OPEN_SQBRCT.search(signal_bitdef)
                signal_bitdef_packed_regex = RE_PACKED_ARRAY.search(signal_bitdef)

                if (
                    signal_bitdef_sqbrct_regex and not signal_bitdef_packed_regex
                ):  # The bitselect is another signal with bitdef, then we need to udpate it
                    close_sqbrct_with_dot_regex = RE_CLOSE_SQBRCT_WITH_DOT.search(
                        signal_bitdef
                    )

                    # Covering signal_name].field
                    if close_sqbrct_with_dot_regex:
                        signal_bitdef = close_sqbrct_with_dot_regex.group(1)

                    # Remove : only outside [], inside [] are for bitwidth definition
                    signal_bitdef = self.remove_outside_sqbrackets(
                        "assign", signal_bitdef
                    )

                    # Break it into individual
                    signal_bitdef_array = signal_bitdef.split()

                    for bitsel_signal in signal_bitdef_array:
                        # print "        # BITSEL:", bitsel_signal
                        self.parse_signal(signal_type, bitsel_signal, 0)

                    signal_bitdef = ""

                    if signal_name not in self.typedef_bindings:
                        self.update_wire_reg_signal_lists(
                            signal_type,
                            "AUTO",
                            signal_name,
                            signal_bitdef,
                            signal_uwidth,
                            signal_lwidth,
                            signal_depth,
                            "",
                        )
                else:  # Bit def does not contain another variable with bitdef
                    # Calculate the bitdef
                    # if unable to calculate bitdef, then see if another signal is used for bit select
                    signal_bitdef_colon_regex = RE_COLON.search(str(signal_bitdef))

                    # Checking if : present in the bit def, then we need to break it into upper and lower bitdef
                    if signal_bitdef_colon_regex:
                        signal_bitdef_array = signal_bitdef.split(":")

                        # Upper bitdef calculation
                        # TODO: Need to pass package
                        signal_upper_bitdef_val = self.tickdef_param_getval(
                            "TOP", signal_bitdef_array[0], "", ""
                        )
                        # dbg("          # Upper :: " + signal_bitdef_array[0] + " :: " + signal_upper_bitdef_val[0] + " # " + str(signal_upper_bitdef_val[1]))

                        # Lower bitdef calculation
                        # TODO: Need to pass package
                        signal_lower_bitdef_val = self.tickdef_param_getval(
                            "TOP", signal_bitdef_array[1], "", ""
                        )
                        # dbg("          # Lower :: " + signal_bitdef_array[1] + " :: " + signal_lower_bitdef_val[0] + " # " + str(signal_lower_bitdef_val[1]))

                        if (
                            signal_upper_bitdef_val[0] == "STRING"
                            or signal_lower_bitdef_val[0] == "STRING"
                        ):
                            signal_uwidth = ""
                            signal_lwidth = ""
                        else:
                            signal_uwidth = signal_upper_bitdef_val[1]
                            signal_lwidth = signal_lower_bitdef_val[1]

                    else:  # Single bitdef
                        # TODO: Need to pass package
                        signal_bitdef_val = self.tickdef_param_getval(
                            "TOP", signal_bitdef, "", ""
                        )
                        # print "          #", signal_bitdef, " :: ", signal_bitdef_val[0], " # ", signal_bitdef_val[1]

                        # If the signal_bitdef_val[0] is STRING, then we need to check for signal
                        if signal_bitdef_val[0] == "STRING":
                            # print "        # BITSEL:", signal_bitdef
                            signal_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                signal_bitdef
                            )

                            # skip if this is packed array select
                            if not signal_bitdef_packed_regex:
                                close_sqbrct_with_dot_regex = (
                                    RE_CLOSE_SQBRCT_WITH_DOT.search(signal_bitdef)
                                )

                                # Covering signal_name].field
                                if close_sqbrct_with_dot_regex:
                                    signal_bitdef = close_sqbrct_with_dot_regex.group(1)

                                signal_bitdef = self.remove_outside_sqbrackets(
                                    "assign", signal_bitdef
                                )

                                # Break it into individual
                                signal_bitdef_array = signal_bitdef.split()

                                for curr_signal_bitdef in signal_bitdef_array:
                                    self.parse_signal(
                                        signal_type, curr_signal_bitdef, 0
                                    )

                            # Bitdef numerical value can't be calculated
                            signal_bitdef = ""
                        else:
                            signal_uwidth = signal_bitdef_val[1]
                            signal_lwidth = signal_bitdef_val[1]

                    if signal_name not in self.typedef_bindings:
                        self.update_wire_reg_signal_lists(
                            signal_type,
                            "AUTO",
                            signal_name,
                            signal_bitdef,
                            signal_uwidth,
                            signal_lwidth,
                            signal_depth,
                            "",
                        )

                ################################################################################
                # For multidimentional typedef_logic/struct/union, we have to detect after
                # remvoing depth index after the signal name
                ################################################################################
                if signal_name in self.typedef_bindings:
                    int_class = self.typedef_bindings[signal_name]["class"]
                    int_package = self.typedef_bindings[signal_name]["package"]
                    typedef = self.typedef_bindings[signal_name]["typedef"]

                    if self.typedef_bindings[signal_name]["type"] == "LOGICS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_uwidth = self.typedef_logics[int_package][int_class][
                            typedef
                        ]["uwidth"]
                        signal_lwidth = self.typedef_logics[int_package][int_class][
                            typedef
                        ]["lwidth"]
                        signal_depth = ""
                    elif self.typedef_bindings[signal_name]["type"] == "STRUCTS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_lwidth = 0

                        if (
                            self.typedef_structs[int_package][int_class][typedef][
                                "width"
                            ]
                            != 0
                        ):
                            signal_uwidth = (
                                self.typedef_structs[int_package][int_class][typedef][
                                    "width"
                                ]
                                - 1
                            )
                        else:
                            signal_uwidth = 0

                        signal_depth = ""
                    elif self.typedef_bindings[signal_name]["type"] == "UNIONS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_lwidth = 0

                        if (
                            self.typedef_unions[int_package][int_class][typedef][
                                "width"
                            ]
                            != 0
                        ):
                            signal_uwidth = (
                                self.typedef_unions[int_package][int_class][typedef][
                                    "width"
                                ]
                                - 1
                            )
                        else:
                            signal_uwidth = 0

                        signal_depth = ""

                    self.update_wire_reg_signal_lists(
                        signal_type,
                        "AUTO",
                        signal_name,
                        signal_bitdef,
                        signal_uwidth,
                        signal_lwidth,
                        signal_depth,
                        "",
                    )
            else:  # No bit definition for this signal
                signal_name = signal_str

                if signal_name not in self.typedef_bindings:
                    close_sqbrct_with_dot_regex = RE_CLOSE_SQBRCT_WITH_DOT.search(
                        signal_name
                    )

                    # Covering signal_name].field
                    if close_sqbrct_with_dot_regex:
                        signal_name = close_sqbrct_with_dot_regex.group(1)

                    self.update_wire_reg_signal_lists(
                        signal_type,
                        "AUTO",
                        signal_name,
                        signal_bitdef,
                        signal_uwidth,
                        signal_lwidth,
                        signal_depth,
                        "",
                    )
                else:
                    int_class = self.typedef_bindings[signal_name]["class"]
                    int_package = self.typedef_bindings[signal_name]["package"]
                    typedef = self.typedef_bindings[signal_name]["typedef"]

                    if self.typedef_bindings[signal_name]["type"] == "LOGICS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_uwidth = self.typedef_logics[int_package][int_class][
                            typedef
                        ]["uwidth"]
                        signal_lwidth = self.typedef_logics[int_package][int_class][
                            typedef
                        ]["lwidth"]
                        signal_depth = ""
                    elif self.typedef_bindings[signal_name]["type"] == "STRUCTS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_lwidth = 0

                        if (
                            self.typedef_structs[int_package][int_class][typedef][
                                "width"
                            ]
                            != 0
                        ):
                            signal_uwidth = (
                                self.typedef_structs[int_package][int_class][typedef][
                                    "width"
                                ]
                                - 1
                            )
                        else:
                            signal_uwidth = 0

                        signal_depth = ""
                    elif self.typedef_bindings[signal_name]["type"] == "UNIONS":
                        if int_package == "default" or int_package == "":
                            if int_class == "default" or int_class == "":
                                signal_bitdef = self.typedef_bindings[signal_name][
                                    "typedef"
                                ]
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                        else:
                            if int_class == "default" or int_class == "":
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )
                            else:
                                signal_bitdef = (
                                    self.typedef_bindings[signal_name]["package"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["class"]
                                    + "::"
                                    + self.typedef_bindings[signal_name]["typedef"]
                                )

                        signal_lwidth = 0

                        if (
                            self.typedef_unions[int_package][int_class][typedef][
                                "width"
                            ]
                            != 0
                        ):
                            signal_uwidth = (
                                self.typedef_unions[int_package][int_class][typedef][
                                    "width"
                                ]
                                - 1
                            )
                        else:
                            signal_uwidth = 0

                        signal_depth = ""

                    self.update_wire_reg_signal_lists(
                        signal_type,
                        "AUTO",
                        signal_name,
                        signal_bitdef,
                        signal_uwidth,
                        signal_lwidth,
                        signal_depth,
                        "",
                    )

        if reset_store:
            if signal_name in self.auto_reset_data[self.auto_reset_index]:
                self.auto_reset_data[self.auto_reset_index][signal_name][
                    "resetval"
                ] = self.auto_reset_val
            else:
                self.auto_reset_data[self.auto_reset_index][signal_name] = {}
                self.auto_reset_data[self.auto_reset_index][signal_name][
                    "name"
                ] = signal_name
                self.auto_reset_data[self.auto_reset_index][signal_name][
                    "resetval"
                ] = self.auto_reset_val
        return

    def update_wire_reg_signal_lists(
        self,
        signal_type,
        parse_type,
        signal_name,
        bitdef,
        uwidth,
        lwidth,
        depth,
        signed,
    ):
        """
        Function to update wire/reg/signal lists.
        It compares the exiting bit definition accumulated and update it based on current widths.
        """

        # Removing space
        signal_name = re.sub(r"\s*", "", signal_name)

        # dbg("  # UPDATE: ", signal_type, parse_type, signal_name, bitdef, uwidth, lwidth, depth, signed)

        if uwidth == "":
            uwidth = 0

        if lwidth == "":
            lwidth = 0

        if uwidth == "" and lwidth == "":
            updated_bitdef = "0:0"
        else:
            updated_bitdef = bitdef

        if signal_name in sv_keywords:
            print(
                "\nWarning: Detecting Verilog/SystemVerilog keywords as a signal "
                + signal_name
            )
            print(self.original_line + "\n")
            return

        if signal_type == "wire":
            # Updating self.wires array
            if (
                signal_name not in self.wires
            ):  # port is present in the self.wires database
                self.wires[signal_name] = {}
                self.wires[signal_name]["name"] = signal_name
                self.wires[signal_name]["bitdef"] = updated_bitdef
                self.wires[signal_name]["uwidth"] = uwidth
                self.wires[signal_name]["lwidth"] = lwidth
                self.wires[signal_name]["mode"] = parse_type
                self.wires[signal_name]["depth"] = depth
                self.wires[signal_name]["signed"] = ""
                self.wires[signal_name]["type"] = ""

                if signed != "":
                    self.wires[signal_name]["signed"] = signed

                self.dbg(
                    "    # NEW WIRE :: "
                    + self.wires[signal_name]["name"]
                    + " # "
                    + self.wires[signal_name]["mode"]
                    + " # "
                    + self.wires[signal_name]["bitdef"]
                    + " # "
                    + str(self.wires[signal_name]["uwidth"])
                    + " # "
                    + str(self.wires[signal_name]["lwidth"])
                    + " # "
                    + str(self.wires[signal_name]["depth"])
                    + " # "
                    + self.wires[signal_name]["signed"]
                    + " #"
                )

            else:
                # Update only if the wire/reg is not FORCED or MANUAL
                if (
                    self.wires[signal_name]["mode"] != "FORCE"
                    and self.wires[signal_name]["mode"] != "MANUAL"
                ):

                    # Update upper width if the new width is bigger
                    if uwidth != "" and int(uwidth) > int(
                        self.wires[signal_name]["uwidth"]
                    ):
                        self.wires[signal_name]["uwidth"] = uwidth
                        self.wires[signal_name]["bitdef"] = self.update_bitdef(
                            1,
                            updated_bitdef,
                            self.wires[signal_name]["bitdef"],
                            self.wires[signal_name]["uwidth"],
                            self.wires[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    # Update lower width if the new width is smaller
                    if lwidth != "" and int(lwidth) < int(
                        self.wires[signal_name]["lwidth"]
                    ):
                        self.wires[signal_name]["lwidth"] = lwidth
                        self.wires[signal_name]["bitdef"] = self.update_bitdef(
                            0,
                            updated_bitdef,
                            self.wires[signal_name]["bitdef"],
                            self.wires[signal_name]["uwidth"],
                            self.wires[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    self.wires[signal_name]["mode"] = parse_type

                    if lwidth == 0 and uwidth == 0:
                        if updated_bitdef != "":
                            self.wires[signal_name]["bitdef"] = updated_bitdef

                    if depth != "":
                        self.wires[signal_name]["depth"] = depth

                    self.dbg(
                        "    # UPDATED WIRE :: "
                        + self.wires[signal_name]["name"]
                        + " # "
                        + self.wires[signal_name]["mode"]
                        + " # "
                        + self.wires[signal_name]["bitdef"]
                        + " # "
                        + str(self.wires[signal_name]["uwidth"])
                        + " # "
                        + str(self.wires[signal_name]["lwidth"])
                        + " # "
                        + str(self.wires[signal_name]["depth"])
                    )
                else:
                    self.dbg(
                        "    # SKIPPED WIRE :: "
                        + self.wires[signal_name]["name"]
                        + " # "
                        + self.wires[signal_name]["mode"]
                        + " # "
                        + self.wires[signal_name]["bitdef"]
                        + " # "
                        + str(self.wires[signal_name]["uwidth"])
                        + " # "
                        + str(self.wires[signal_name]["lwidth"])
                        + " # "
                        + str(self.wires[signal_name]["depth"])
                    )

        elif signal_type == "reg" or signal_type == "logic":
            # Updating self.regs array

            if (
                signal_name not in self.regs
            ):  # port is present in the self.wires database
                self.regs[signal_name] = {}
                self.regs[signal_name]["name"] = signal_name
                self.regs[signal_name]["bitdef"] = updated_bitdef
                self.regs[signal_name]["uwidth"] = uwidth
                self.regs[signal_name]["lwidth"] = lwidth
                self.regs[signal_name]["mode"] = parse_type
                self.regs[signal_name]["depth"] = depth
                self.regs[signal_name]["signed"] = signed
                self.regs[signal_name]["type"] = ""

                self.dbg(
                    "    # NEW REG :: "
                    + self.regs[signal_name]["name"]
                    + " # "
                    + self.regs[signal_name]["mode"]
                    + " # "
                    + self.regs[signal_name]["bitdef"]
                    + " # "
                    + str(self.regs[signal_name]["uwidth"])
                    + " # "
                    + str(self.regs[signal_name]["lwidth"])
                    + " # "
                    + str(self.regs[signal_name]["depth"])
                )
            else:
                # Update only if the wire/reg is not FORCED or MANUAL
                if (
                    self.regs[signal_name]["mode"] != "FORCE"
                    and self.regs[signal_name]["mode"] != "MANUAL"
                ):

                    # Update upper width if the new width is bigger
                    if uwidth != "" and int(uwidth) > int(
                        self.regs[signal_name]["uwidth"]
                    ):
                        self.regs[signal_name]["uwidth"] = uwidth
                        self.regs[signal_name]["bitdef"] = self.update_bitdef(
                            1,
                            updated_bitdef,
                            self.regs[signal_name]["bitdef"],
                            self.regs[signal_name]["uwidth"],
                            self.regs[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    # Update lower width if the new width is smaller
                    if lwidth != "" and int(lwidth) < int(
                        self.regs[signal_name]["lwidth"]
                    ):
                        self.regs[signal_name]["lwidth"] = lwidth
                        self.regs[signal_name]["bitdef"] = self.update_bitdef(
                            0,
                            updated_bitdef,
                            self.regs[signal_name]["bitdef"],
                            self.regs[signal_name]["uwidth"],
                            self.regs[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    self.regs[signal_name]["mode"] = parse_type

                    # if lwidth == 0 and uwidth == 0:
                    # if updated_bitdef != '':
                    # self.regs[signal_name]['bitdef'] = updated_bitdef

                    if depth != "":
                        self.regs[signal_name]["depth"] = depth

                    self.dbg(
                        "    # UPDATED REG :: "
                        + self.regs[signal_name]["name"]
                        + " # "
                        + self.regs[signal_name]["mode"]
                        + " # "
                        + self.regs[signal_name]["bitdef"]
                        + " # "
                        + str(self.regs[signal_name]["uwidth"])
                        + " # "
                        + str(self.regs[signal_name]["lwidth"])
                        + " # "
                        + str(self.regs[signal_name]["depth"])
                    )
                else:
                    self.dbg(
                        "    # SKIPPED REG :: "
                        + self.regs[signal_name]["name"]
                        + " # "
                        + self.regs[signal_name]["mode"]
                        + " # "
                        + self.regs[signal_name]["bitdef"]
                        + " # "
                        + str(self.regs[signal_name]["uwidth"])
                        + " # "
                        + str(self.regs[signal_name]["lwidth"])
                        + " # "
                        + str(self.regs[signal_name]["depth"])
                    )

        elif signal_type == "signal":
            # Updating self.signals array
            if (
                signal_name not in self.signals
            ):  # port is present in the self.wires database
                self.signals[signal_name] = {}
                self.signals[signal_name]["name"] = signal_name
                self.signals[signal_name]["bitdef"] = updated_bitdef
                self.signals[signal_name]["uwidth"] = uwidth
                self.signals[signal_name]["lwidth"] = lwidth
                self.signals[signal_name]["mode"] = parse_type
                self.signals[signal_name]["depth"] = depth
                self.signals[signal_name]["signed"] = ""

                self.dbg(
                    "    # NEW SIGNAL :: "
                    + self.signals[signal_name]["name"]
                    + " # "
                    + self.signals[signal_name]["mode"]
                    + " # "
                    + self.signals[signal_name]["bitdef"]
                    + " # "
                    + str(self.signals[signal_name]["uwidth"])
                    + " # "
                    + str(self.signals[signal_name]["lwidth"])
                    + " # "
                    + str(self.signals[signal_name]["depth"])
                )
            else:
                # Update only if the wire/reg is not FORCED or MANUAL
                if (
                    self.signals[signal_name]["mode"] != "FORCE"
                    and self.signals[signal_name]["mode"] != "MANUAL"
                ):

                    # Update upper width if the new width is bigger
                    if uwidth != "" and int(uwidth) > int(
                        self.signals[signal_name]["uwidth"]
                    ):
                        self.signals[signal_name]["uwidth"] = uwidth
                        self.signals[signal_name]["bitdef"] = self.update_bitdef(
                            1,
                            updated_bitdef,
                            self.signals[signal_name]["bitdef"],
                            self.signals[signal_name]["uwidth"],
                            self.signals[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    # Update lower width if the new width is smaller
                    if lwidth != "" and int(lwidth) < int(
                        self.signals[signal_name]["lwidth"]
                    ):
                        self.signals[signal_name]["lwidth"] = lwidth
                        self.signals[signal_name]["bitdef"] = self.update_bitdef(
                            0,
                            updated_bitdef,
                            self.signals[signal_name]["bitdef"],
                            self.signals[signal_name]["uwidth"],
                            self.signals[signal_name]["lwidth"],
                            uwidth,
                            lwidth,
                        )

                    self.signals[signal_name]["mode"] = parse_type

                    if depth != "":
                        self.signals[signal_name]["depth"] = depth

                    self.dbg(
                        "    # UPDATED SIGNAL :: "
                        + self.signals[signal_name]["name"]
                        + " # "
                        + self.signals[signal_name]["mode"]
                        + " # "
                        + self.signals[signal_name]["bitdef"]
                        + " # "
                        + str(self.signals[signal_name]["uwidth"])
                        + " # "
                        + str(self.signals[signal_name]["lwidth"])
                        + " # "
                        + str(self.signals[signal_name]["depth"])
                    )
                else:
                    self.dbg(
                        "    # SKIPPED SIGNAL :: "
                        + self.signals[signal_name]["name"]
                        + " # "
                        + self.signals[signal_name]["mode"]
                        + " # "
                        + self.signals[signal_name]["bitdef"]
                        + " # "
                        + str(self.signals[signal_name]["uwidth"])
                        + " # "
                        + str(self.signals[signal_name]["lwidth"])
                        + " # "
                        + str(self.signals[signal_name]["depth"])
                    )

        return

    def update_bitdef(
        self,
        bitdef_sel,
        new_bitdef,
        old_bitdef,
        old_uwidth,
        old_lwidth,
        new_uwidth,
        new_lwidth,
    ):
        """
        Function to update the bit definition
        """

        updated_bitdef = ""

        new_bitdef_colon_regex = RE_COLON.search(str(new_bitdef))
        old_bitdef_colon_regex = RE_COLON.search(str(old_bitdef))

        if new_bitdef_colon_regex:
            new_bitdef_list = new_bitdef.split(":")
        else:
            new_bitdef_list = []
            new_bitdef_list.append(new_uwidth)
            new_bitdef_list.append(new_lwidth)

        if old_bitdef_colon_regex:
            old_bitdef_list = old_bitdef.split(":")
        else:
            old_bitdef_list = []
            old_bitdef_list.append(old_uwidth)
            old_bitdef_list.append(old_lwidth)

        if bitdef_sel:  # Update upper bitdef
            # Both bitdef has :
            if new_bitdef_colon_regex and old_bitdef_colon_regex:
                updated_bitdef = str(new_bitdef_list[0]) + ":" + str(old_bitdef_list[1])
            elif new_bitdef_colon_regex:
                updated_bitdef = str(new_bitdef_list[0]) + ":" + str(old_lwidth)
            elif old_bitdef_colon_regex:
                updated_bitdef = str(new_uwidth) + ":" + str(old_bitdef_list[1])
            else:
                updated_bitdef = str(new_uwidth) + ":" + str(old_lwidth)
        else:  # Update lower bitdef
            # Both bitdef has :
            if new_bitdef_colon_regex and old_bitdef_colon_regex:
                updated_bitdef = str(old_bitdef_list[0]) + ":" + str(new_bitdef_list[1])
            elif new_bitdef_colon_regex:
                updated_bitdef = str(old_bitdef_list[0]) + ":" + str(new_lwidth)
            elif old_bitdef_colon_regex:
                updated_bitdef = str(old_uwidth) + ":" + str(new_bitdef_list[1])
            else:
                updated_bitdef = str(old_uwidth) + ":" + str(new_lwidth)

        return updated_bitdef

    def remove_outside_sqbrackets(self, signal_type, signal_str):
        """
        Function to remove , { } + / * = < > ? : & | ~ ^ () outside []
        """

        # print "  #", signal_str
        bracket_count = 0
        ret_signal_str = ""
        signal_str_array = []
        signal_str_array = list(signal_str)

        for char in signal_str_array:
            if char == "[":
                bracket_count = bracket_count + 1
                ret_signal_str = ret_signal_str + char
                continue
            elif char == "]":
                bracket_count = bracket_count - 1
                ret_signal_str = ret_signal_str + char
                continue
            else:
                if bracket_count != 0:
                    ret_signal_str = ret_signal_str + char
                    continue
                else:
                    if (
                        char == ","
                        or char == "{"
                        or char == "}"
                        or char == "^"
                        or char == "+"
                        or char == "-"
                        or char == "/"
                        or char == "*"
                        or char == "="
                        or char == "<"
                        or char == ">"
                        or char == "–"
                        or char == ":"
                        or char == "?"
                        or char == ";"
                        or char == "%"
                        or char == "&"
                        or char == "|"
                        or char == "~"
                        or char == "!"
                        or char == "("
                        or char == ")"
                    ):
                        ret_signal_str = ret_signal_str + " "
                        continue
                    else:
                        ret_signal_str = ret_signal_str + char
                        continue

        ret_signal_str = re.sub(r"\s+", " ", ret_signal_str)
        # self.dbg("      #" + ret_signal_str)

        return ret_signal_str

    def parse_reg_wire_logic(
        self,
        module_type,
        declare_parse_type,
        declare_type,
        declare_str,
        package,
        class_name,
    ):
        """
        Function to parse a single reg/wire/logic declaration line
        """

        self.dbg(declare_type + " :: " + declare_str)

        declare_str_orig = declare_str
        declare_signed = ""  # signed
        declare_bitdef = ""
        declare_uwidth = ""
        declare_lwidth = ""
        declare_depth = ""
        declare_name = ""

        if package == "default" or package == "":
            int_package = "default"
        else:
            int_package = package

        if class_name == "default" or class_name == "":
            int_class = "default"
        else:
            int_class = class_name

        # Removing ; and adding space before [] if not there
        declare_str = re.sub(r"\s*;\s*", ";", declare_str)
        declare_str = re.sub(r"\s*\[", " [", declare_str)
        declare_str = re.sub(r"\]\s*", "] ", declare_str)
        declare_str = re.sub(r"\]\s*\[", "][", declare_str)

        # looking for signed and removing the keyword
        declare_signed_regex = RE_DECLARE_SIGNED.search(declare_str)
        if declare_signed_regex:
            declare_str = re.sub(r"\s*\bsigned\b\s*", " ", declare_str)
            declare_signed = "signed"

        # Extracting bit definition if present
        declare_bitdef_regex = RE_DECLARE_BITDEF.search(declare_str)
        if declare_bitdef_regex:
            declare_bitdef = declare_bitdef_regex.group(1)
            declare_str = declare_bitdef_regex.group(2)

        # Extracting depth definition if present
        declare_depth_regex = RE_DECLARE_DEPTH.search(declare_str)
        if declare_depth_regex:
            declare_str = declare_depth_regex.group(1)
            declare_depth = declare_depth_regex.group(2)

        # Remaining is the name of IO
        declare_str = re.sub(r"\s*;\s*", "", declare_str)

        declare_comma_regex = RE_COMMA.search(declare_str)

        # If multiple declarations on the same line, then break it
        declare_str_array = []
        if declare_comma_regex:
            declare_str = re.sub(r"\s*", "", declare_str)
            declare_str_array = declare_str.split(",")
        else:  # Single declaration, then append to the array
            declare_str_array.append(declare_str)

        if declare_bitdef != "":
            declare_bitdef_val = []
            declare_bitdef_val = self.tickdef_param_getval(
                "TOP", declare_bitdef, int_package, int_class
            )

            if declare_bitdef_val[0] == "STRING":
                declare_bitdef_packed_regex = RE_PACKED_ARRAY.search(declare_bitdef)

                if declare_bitdef_packed_regex:
                    # print("      Skip parsing packed array :: " + declare_type + ' ' + declare_str_orig)
                    pass
                else:
                    self.dbg(
                        "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                    )
                    self.dbg("  # " + declare_str_orig)
                    self.dbg("  # " + declare_bitdef)
                    print(
                        "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                    )
                    print("  # " + declare_str_orig)
                    print("  # " + declare_bitdef)
            else:
                declare_bitdef_regex = RE_COLON.search(str(declare_bitdef_val[1]))

                # Multi bit definition
                if declare_bitdef_regex:
                    declare_uwidth = declare_bitdef_regex.group(1)
                    declare_lwidth = declare_bitdef_regex.group(2)
                else:  # Single bit definition
                    declare_lwidth = declare_bitdef_val[1]

        if declare_parse_type != "TYPEDEF":
            for declare_name in declare_str_array:
                self.update_wire_reg_signal_lists(
                    declare_type,
                    declare_parse_type,
                    declare_name,
                    declare_bitdef,
                    declare_uwidth,
                    declare_lwidth,
                    declare_depth,
                    declare_signed,
                )
        else:
            # Updating self.typedef_logics
            for declare_name in declare_str_array:
                declare_name = declare_name
                if module_type == "TOP":
                    if (
                        declare_name not in self.typedef_logics[int_package][int_class]
                    ):  # port is present in the self.wires database
                        self.typedef_logics[int_package][int_class][declare_name] = {}
                        self.typedef_logics[int_package][int_class][declare_name][
                            "name"
                        ] = declare_name
                        self.typedef_logics[int_package][int_class][declare_name][
                            "bitdef"
                        ] = declare_bitdef
                        self.typedef_logics[int_package][int_class][declare_name][
                            "uwidth"
                        ] = declare_uwidth
                        self.typedef_logics[int_package][int_class][declare_name][
                            "lwidth"
                        ] = declare_lwidth

                        if declare_uwidth == "":
                            declare_uwidth = 0

                        if declare_lwidth == "":
                            declare_lwidth = 0

                        if declare_uwidth != "" and declare_lwidth != "":
                            if declare_uwidth == 0 and declare_lwidth == 0:
                                self.typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"] = 0
                            else:
                                self.typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"] = (
                                    int(declare_uwidth) - int(declare_lwidth) + 1
                                )
                        else:
                            self.typedef_logics[int_package][int_class][declare_name][
                                "width"
                            ] = 0

                        self.dbg(
                            "  # TOP :: TYPEDEF LOGIC :: "
                            + int_package
                            + " # "
                            + int_class
                            + " # "
                            + self.typedef_logics[int_package][int_class][declare_name][
                                "name"
                            ]
                            + " # "
                            + self.typedef_logics[int_package][int_class][declare_name][
                                "bitdef"
                            ]
                            + " # "
                            + str(
                                self.typedef_logics[int_package][int_class][
                                    declare_name
                                ]["uwidth"]
                            )
                            + " # "
                            + str(
                                self.typedef_logics[int_package][int_class][
                                    declare_name
                                ]["lwidth"]
                            )
                            + " # "
                            + str(
                                self.typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"]
                            )
                        )
                    else:
                        self.dbg("\nError: The following typedef is already declared")
                        self.dbg("  #" + declare_str)
                        print("\nError: The following typedef is already declared")
                        print("  #" + declare_str)
                        self.found_error = 1
                else:  # if module_type == 'TOP':
                    if (
                        declare_name
                        not in self.sub_typedef_logics[int_package][int_class]
                    ):  # port is present in the self.wires database
                        self.sub_typedef_logics[int_package][int_class][
                            declare_name
                        ] = {}
                        self.sub_typedef_logics[int_package][int_class][declare_name][
                            "name"
                        ] = declare_name
                        self.sub_typedef_logics[int_package][int_class][declare_name][
                            "bitdef"
                        ] = declare_bitdef
                        self.sub_typedef_logics[int_package][int_class][declare_name][
                            "uwidth"
                        ] = declare_uwidth
                        self.sub_typedef_logics[int_package][int_class][declare_name][
                            "lwidth"
                        ] = declare_lwidth

                        if declare_uwidth == "":
                            declare_uwidth = 0

                        if declare_lwidth == "":
                            declare_lwidth = 0

                        if declare_uwidth != "" and declare_lwidth != "":
                            if declare_uwidth == 0 and declare_lwidth == 0:
                                self.sub_typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"] = 0
                            else:
                                self.sub_typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"] = (
                                    int(declare_uwidth) - int(declare_lwidth) + 1
                                )
                        else:
                            self.sub_typedef_logics[int_package][int_class][
                                declare_name
                            ]["width"] = 0

                        self.dbg(
                            "  # SUB :: TYPEDEF LOGIC :: "
                            + int_package
                            + " # "
                            + int_class
                            + " # "
                            + self.sub_typedef_logics[int_package][int_class][
                                declare_name
                            ]["name"]
                            + " # "
                            + self.sub_typedef_logics[int_package][int_class][
                                declare_name
                            ]["bitdef"]
                            + " # "
                            + str(
                                self.sub_typedef_logics[int_package][int_class][
                                    declare_name
                                ]["uwidth"]
                            )
                            + " # "
                            + str(
                                self.sub_typedef_logics[int_package][int_class][
                                    declare_name
                                ]["lwidth"]
                            )
                            + " # "
                            + str(
                                self.sub_typedef_logics[int_package][int_class][
                                    declare_name
                                ]["width"]
                            )
                        )

                    else:
                        self.dbg("\nError: The following typedef is already declared")
                        self.dbg("  #" + declare_str)
                        print("\nError: The following typedef is already declared")
                        print("  #" + declare_str)
                        self.found_error = 1

        return

    def parse_ios(self, module_type, io_parse_type, io_dir, io_str):
        """
        Function to parse a single input/output declaration line
        """

        self.dbg(module_type + ":: " + io_parse_type + " : " + io_dir + " : " + io_str)
        io_str_orig = io_str

        io_signed = ""  # signed
        io_bitdef = ""
        io_uwidth = ""
        io_lwidth = ""
        io_depth = ""
        io_name = ""
        io_bitdef_type = ""
        io_typedef_ref = ""

        # Removing ; and adding space before [] if not there
        io_str = re.sub(r"\s*;\s*", ";", io_str)
        io_str = re.sub(r"\s*\[", " [", io_str)
        io_str = re.sub(r"\]\s*", "] ", io_str)
        io_str = re.sub(r"\]\s*\[", "][", io_str)

        # Removing wire/reg type
        io_wire_regex = RE_DECLARE_WIRE.search(io_str)
        io_reg_regex = RE_DECLARE_REG.search(io_str)
        io_logic_regex = RE_DECLARE_LOGIC.search(io_str)

        if io_dir == "output":
            if io_wire_regex:
                io_str = re.sub(r"\s*\bwire\b\s*", "", io_str)
                io_bitdef_type = "WIRE"
            elif io_reg_regex:
                io_str = re.sub(r"\s*\breg\b\s*", "", io_str)
                io_bitdef_type = "REG"
            elif io_logic_regex:
                io_str = re.sub(r"\s*\blogic\b\s*", "", io_str)
                io_bitdef_type = "LOGIC"
        elif io_dir == "input":
            if io_wire_regex:
                io_str = re.sub(r"\s*\bwire\b\s*", "", io_str)
                io_bitdef_type = "WIRE"
            elif io_logic_regex:
                io_str = re.sub(r"\s*\blogic\b\s*", "", io_str)
                io_bitdef_type = "LOGIC"
        elif io_dir == "inout":
            if io_wire_regex:
                io_str = re.sub(r"\s*\bwire\b\s*", "", io_str)
                io_bitdef_type = "WIRE"
            elif io_logic_regex:
                io_str = re.sub(r"\s*\blogic\b\s*", "", io_str)
                io_bitdef_type = "LOGIC"

        # looking for signed and removing the keyword
        io_signed_regex = RE_DECLARE_SIGNED.search(io_str)

        if io_signed_regex:
            io_str = re.sub(r"\s*\bsigned\b\s*", " ", io_str)
            io_signed = "signed"

        io_bitdef_regex = RE_DECLARE_BITDEF.search(io_str)
        io_packed_bitdef_regex = RE_DECLARE_PACKED_BITDEF.search(io_str)

        if io_packed_bitdef_regex:
            io_bitdef = (
                io_packed_bitdef_regex.group(1) + "[" + io_packed_bitdef_regex.group(2)
            )
            io_bitdef = re.sub(r"\s+", "", io_bitdef)
            io_str = io_packed_bitdef_regex.group(3)
        elif io_bitdef_regex:
            io_bitdef = io_bitdef_regex.group(1)
            io_bitdef = re.sub(r"\s+", "", io_bitdef)
            io_str = io_bitdef_regex.group(2)

        io_depth_regex = RE_DECLARE_DEPTH.search(io_str)

        if io_depth_regex:
            io_str = io_depth_regex.group(1)
            io_depth = io_depth_regex.group(2)

        # Remaining is the name of IO
        io_str = re.sub(r"\s*;\s*", "", io_str)
        io_str = re.sub(r"\s*$", "", io_str)

        io_comma_regex = RE_COMMA.search(io_str)

        # If multiple declarations on the same line, then break it
        io_str_array = []

        if io_comma_regex:
            io_str = re.sub(r"\s*,\s*", ",", io_str)
            io_str = re.sub(r"\s*$", "", io_str)
            io_str = re.sub(r"^\s*", "", io_str)
            io_str_array = io_str.split(",")
            io_str_first_element = io_str_array[0]
        else:  # Single declaration, then append to the array
            io_str_array.append(io_str)
            io_str_first_element = io_str

        int_package = "default"
        int_class = "default"

        # for the manual module 2001 style, we pass single IO declaration at a time
        bindings_found = 0

        if (
            io_bitdef_regex
        ):  # If there is no bit definition, then look for typedef for SV
            pass
        else:  # If there is no bit definition, then look for typedef for SV
            space_bw_regex = RE_SPACE_BW.search(io_str_first_element)

            if space_bw_regex:
                # Removed the typedef bitdef
                if io_comma_regex:
                    io_str_array[0] = space_bw_regex.group(2)
                else:
                    io_str_array = []
                    io_str_array.append(space_bw_regex.group(2))

                double_colon_regex = RE_DOUBLE_COLON.search(space_bw_regex.group(1))

                # TODO: Need to add double_double_colon_regex
                if double_colon_regex:  # package name part of a struct
                    bindings_found = 1
                    int_package = double_colon_regex.group(1)
                    io_lwidth = 0
                    io_uwidth = 0

                    if module_type == "TOP":
                        if int_package not in self.packages:  # Look for the package
                            self.load_import_or_include_file(
                                "TOP", "IMPORT_COMMANDLINE", int_package + ".sv"
                            )

                        if (
                            double_colon_regex.group(2)
                            in self.typedef_logics[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_LOGIC"

                            if (
                                self.typedef_logics[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_logics[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            double_colon_regex.group(2)
                            in self.typedef_structs[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_STRUCT"

                            if (
                                self.typedef_structs[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_structs[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            double_colon_regex.group(2)
                            in self.typedef_unions[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_UNION"

                            if (
                                self.typedef_unions[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_unions[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        else:
                            print(
                                "\n#Error: Unable to find the typedef logic/struct/union"
                            )
                            print("  " + io_str_orig)
                            print(
                                "  PACKAGE: "
                                + int_package
                                + ", CLASS: "
                                + int_class
                                + ", TYPEDEF: "
                                + double_colon_regex.group(2)
                            )
                            self.dbg(
                                "\nError: Unable to find the typedef logic/struct/union"
                            )
                            self.dbg("  " + io_str_orig)
                            self.dbg(
                                "  PACKAGE: "
                                + int_package
                                + ", CLASS: "
                                + int_class
                                + ", TYPEDEF: "
                                + double_colon_regex.group(2)
                            )
                            self.found_error = 1
                            sys.exit(1)
                    else:  # Sub module level
                        if int_package not in self.sub_packages:  # Look for the package
                            self.load_import_or_include_file(
                                "SUB", "IMPORT_COMMANDLINE", int_package + ".sv"
                            )

                        if (
                            double_colon_regex.group(2)
                            in self.sub_typedef_logics[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_LOGIC"

                            if (
                                self.sub_typedef_logics[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_logics[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            double_colon_regex.group(2)
                            in self.sub_typedef_structs[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_STRUCT"

                            if (
                                self.sub_typedef_structs[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_structs[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            double_colon_regex.group(2)
                            in self.sub_typedef_unions[int_package][int_class]
                        ):
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_UNION"

                            if (
                                self.sub_typedef_unions[int_package][int_class][
                                    double_colon_regex.group(2)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_unions[int_package][int_class][
                                        double_colon_regex.group(2)
                                    ]["width"]
                                    - 1
                                )
                        else:
                            print(
                                "\nError: Unable to find the typedef logic/struct/union"
                            )
                            print("  " + io_str_orig)
                            print(
                                "  PACKAGE: "
                                + int_package
                                + ", CLASS: "
                                + int_class
                                + ", TYPEDEF: "
                                + double_colon_regex.group(2)
                            )
                            self.dbg(
                                "\nError: Unable to find the typedef logic/struct/union"
                            )
                            self.dbg("  " + io_str_orig)
                            self.dbg(
                                "  PACKAGE: "
                                + int_package
                                + ", CLASS: "
                                + int_class
                                + ", TYPEDEF: "
                                + double_colon_regex.group(2)
                            )
                            self.found_error = 1
                else:
                    int_package = "default"
                    int_class = "default"
                    io_lwidth = 0
                    io_uwidth = 0

                    if module_type == "TOP":
                        if (
                            space_bw_regex.group(1)
                            in self.typedef_logics[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_LOGIC"

                            if (
                                self.typedef_logics[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_logics[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            space_bw_regex.group(1)
                            in self.typedef_structs[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_STRUCT"

                            if (
                                self.typedef_structs[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_structs[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            space_bw_regex.group(1)
                            in self.typedef_unions[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_UNION"

                            if (
                                self.typedef_unions[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.typedef_unions[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )
                    else:
                        if (
                            space_bw_regex.group(1)
                            in self.sub_typedef_logics[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_LOGIC"

                            if (
                                self.sub_typedef_logics[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_logics[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            space_bw_regex.group(1)
                            in self.sub_typedef_structs[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_STRUCT"

                            if (
                                self.sub_typedef_structs[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_structs[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )
                        elif (
                            space_bw_regex.group(1)
                            in self.sub_typedef_unions[int_package][int_class]
                        ):
                            bindings_found = 1
                            io_typedef_ref = space_bw_regex.group(1)
                            io_bitdef_type = "TYPEDEF_UNION"

                            if (
                                self.sub_typedef_unions[int_package][int_class][
                                    space_bw_regex.group(1)
                                ]["width"]
                                != 0
                            ):
                                io_uwidth = (
                                    self.sub_typedef_unions[int_package][int_class][
                                        space_bw_regex.group(1)
                                    ]["width"]
                                    - 1
                                )

                io_bitdef = io_typedef_ref

        if io_bitdef != "" and io_typedef_ref == "":
            io_bitdef_val = []
            io_bitdef_val = self.tickdef_param_getval(
                module_type, io_bitdef, int_package, ""
            )

            if io_bitdef_val[0] == "STRING":
                io_bitdef_packed_regex = RE_PACKED_ARRAY.search(io_bitdef)

                if io_bitdef_packed_regex:
                    # print('      Skip parsing packed array for now ' + io_str)
                    pass
                else:
                    self.dbg(
                        "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                    )
                    self.dbg("  # " + io_str_orig)
                    print(
                        "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                    )
                    print("  # " + io_str_orig)
            else:
                io_bitdef_regex = RE_COLON.search(str(io_bitdef_val[1]))

                # Multi bit definition
                if io_bitdef_regex:
                    io_uwidth = io_bitdef_regex.group(1)
                    io_lwidth = io_bitdef_regex.group(2)
                else:  # Single bit definition
                    io_lwidth = io_bitdef_val[1]

        for io_name in io_str_array:
            # Binding all the typedefs
            if bindings_found:
                self.binding_typedef(
                    module_type, io_parse_type, io_typedef_ref + " " + io_name + ";"
                )

            if io_parse_type == "FORCE":
                # Updating ports array
                if (
                    io_name not in self.ports
                ):  # port is present in the self.ports database
                    self.ports[io_name] = {}

                self.ports[io_name]["name"] = io_name
                self.ports[io_name]["dir"] = io_dir
                self.ports[io_name]["bitdef"] = io_bitdef
                self.ports[io_name]["uwidth"] = io_uwidth
                self.ports[io_name]["lwidth"] = io_lwidth
                self.ports[io_name]["mode"] = io_parse_type
                self.ports[io_name]["depth"] = io_depth
                self.ports[io_name]["signed"] = io_signed
                self.ports[io_name]["typedef"] = io_bitdef_type
            elif io_parse_type == "MANUAL":
                # Updating self.ports array
                if (
                    io_name not in self.ports
                ):  # port is present in the self.ports database
                    if module_type == "TOP":
                        self.ports[io_name] = {}
                    else:
                        self.sub_ports[io_name] = {}

                if module_type == "TOP":
                    self.ports[io_name]["name"] = io_name
                    self.ports[io_name]["dir"] = io_dir
                    self.ports[io_name]["bitdef"] = io_bitdef
                    self.ports[io_name]["uwidth"] = io_uwidth
                    self.ports[io_name]["lwidth"] = io_lwidth
                    self.ports[io_name]["mode"] = io_parse_type
                    self.ports[io_name]["depth"] = io_depth
                    self.ports[io_name]["signed"] = io_signed
                    self.ports[io_name]["typedef"] = io_bitdef_type
                else:
                    self.sub_ports[io_name] = {}
                    self.sub_ports[io_name]["name"] = io_name
                    self.sub_ports[io_name]["dir"] = io_dir
                    self.sub_ports[io_name]["bitdef"] = io_bitdef
                    self.sub_ports[io_name]["uwidth"] = io_uwidth
                    self.sub_ports[io_name]["lwidth"] = io_lwidth
                    self.sub_ports[io_name]["mode"] = io_parse_type
                    self.sub_ports[io_name]["depth"] = io_depth
                    self.sub_ports[io_name]["signed"] = io_signed
                    self.sub_ports[io_name]["typedef"] = io_bitdef_type
            else:  # Auto
                # Updating self.ports array
                if (
                    io_name not in self.ports
                ):  # port is present in the self.ports database
                    self.ports[io_name] = {}

                self.ports[io_name]["name"] = io_name
                self.ports[io_name]["dir"] = io_dir
                self.ports[io_name]["bitdef"] = io_bitdef
                self.ports[io_name]["uwidth"] = io_uwidth
                self.ports[io_name]["lwidth"] = io_lwidth
                self.ports[io_name]["mode"] = io_parse_type
                self.ports[io_name]["depth"] = io_depth
                self.ports[io_name]["signed"] = io_signed
                self.ports[io_name]["typedef"] = io_bitdef_type

            self.dbg(
                "  # PARSE_IOS :: "
                + io_parse_type
                + " : "
                + module_type
                + ":: "
                + io_dir
                + " : "
                + io_name
                + " : "
                + io_bitdef_type
                + " : "
                + io_bitdef
                + " : "
                + str(io_uwidth)
                + " : "
                + str(io_lwidth)
                + " : "
                + io_depth
                + " #"
            )

        return

    def load_import_or_include_file(self, module_type, inc_type, inc_file):
        """
        Function to load a 'include file and parse 'define and parameter declarations
        """
        self.dbg("\n\n###: load_import_or_include_file inc_file : " + inc_file)
        self.dbg("\n\n###: " + module_type + " :: " + inc_type + " :: " + inc_file)
        inc_file_path = inc_file
        found_tick_inc_file = 0
        package_function_skip = 0
        package_name = "default"
        class_name = ""
        class_name = "default"
        incl_tick_ifdef_en = 1

        if os.path.isfile(inc_file):  # In file doesn't exist
            found_tick_inc_file = 1
        else:
            for dir in self.incl_dirs:
                if not found_tick_inc_file:
                    inc_file_path = str(dir) + "/" + str(inc_file)

                    if os.path.isfile(inc_file_path):
                        found_tick_inc_file = 1
                        inc_file = inc_file_path

        if not found_tick_inc_file:
            inc_file_path_int = self.find_in_files(inc_file)

            if inc_file_path_int is not None:
                found_tick_inc_file = 1
                inc_file_path = inc_file_path_int

        if found_tick_inc_file:
            self.dbg(
                "\n################################################################################"
            )

            inc_file_path = re.sub(r"\/\/", "/", inc_file_path)

            if inc_type == "IMPORT_COMMANDLINE" or inc_type == "IMPORT_EMBEDDED":
                self.dbg(
                    "###load_import_or_include_file Loading Package file"
                    + inc_file_path
                    + " ###"
                )
                if module_type == "TOP":
                    print("    - Importing package " + inc_file_path)
                else:
                    print("      + Importing package " + inc_file_path)
            else:
                self.dbg(
                    "###load_import_or_include_file Loading `include file "
                    + inc_file_path
                    + " ###"
                )
                if module_type == "TOP":
                    print("    - Loading `include file " + inc_file_path)
                else:
                    print("      + Loading `include file " + inc_file_path)

            self.dbg(
                "################################################################################"
            )

            with open(inc_file_path, "r") as tick_incl_data:
                tick_incl_block_comment = 0

                if self.gen_dependencies and module_type == "TOP":
                    self.dependencies["include_files"].append(
                        {inc_file_path: {"mtime": getmtime(inc_file_path)}}
                    )

                if module_type == "TOP":
                    self.filelist.append(inc_file_path)

                incl_line_no = 0
                prev_tick_incl_line = ""
                tick_incl_gather_till_semicolon = 0

                for tick_incl_line in tick_incl_data:
                    incl_line_no = incl_line_no + 1

                    # Remove space in the end
                    tick_incl_line = tick_incl_line.rstrip()

                    # Removing newline and spaces at the end
                    tick_incl_line = tick_incl_line.rstrip()

                    # Removing single line comment
                    tick_incl_line = re.sub(r"\s*\/\/.*", "", tick_incl_line)

                    # Removing block comment in a single line
                    tick_incl_line = remove_single_line_comment(tick_incl_line)

                    # Removing multiple space to single and no space at the end
                    tick_incl_line = re.sub(r"\s+", " ", tick_incl_line)
                    tick_incl_line = re.sub(r"\s*$", "", tick_incl_line)

                    # if the whole line is commented from the beginning
                    tick_incl_single_comment_begin_start_regex = (
                        RE_SINGLE_COMMENT_BEGIN_START.search(tick_incl_line)
                    )
                    if tick_incl_single_comment_begin_start_regex:
                        continue

                    tick_incl_block_comment_begin_start_regex = (
                        RE_BLOCK_COMMENT_BEGIN_START.search(tick_incl_line)
                    )
                    tick_incl_block_comment_begin_regex = RE_BLOCK_COMMENT_BEGIN.search(
                        tick_incl_line
                    )
                    tick_incl_block_comment_end_regex = RE_BLOCK_COMMENT_END.search(
                        tick_incl_line
                    )

                    if tick_incl_block_comment_end_regex:
                        tick_incl_block_comment = 0
                        # If something after the */, we need to parse
                        if tick_incl_block_comment_end_regex.group(1) == "":
                            continue
                        else:
                            tick_incl_line = tick_incl_block_comment_end_regex.group(1)

                    if tick_incl_block_comment:
                        continue

                    if tick_incl_block_comment_begin_start_regex:
                        tick_incl_block_comment = 1
                        continue
                    elif tick_incl_block_comment_begin_regex:
                        tick_incl_block_comment = 1

                    # Gather multiple lines until ;
                    if tick_incl_gather_till_semicolon:
                        tick_incl_line = prev_tick_incl_line + " " + tick_incl_line

                        tick_incl_semicolon_regex = RE_SEMICOLON.search(tick_incl_line)

                        if tick_incl_semicolon_regex:
                            tick_incl_gather_till_semicolon = 0

                    # When block comment begin is detected, we have to strip the block comment beginning and still
                    # parse the content
                    if tick_incl_block_comment_begin_regex:
                        tick_incl_block_comment = 1

                        # Removing single line block comment
                        tick_incl_line = re.sub(r"\s*\/\*.*", "", tick_incl_line)

                    if tick_incl_line == "":
                        continue

                    ################################################################################
                    # `ifdef/ifndef/elif/else/endif processing
                    ################################################################################
                    incl_tick_ifdef_regex = RE_TICK_IFDEF.search(tick_incl_line)
                    incl_tick_ifndef_regex = RE_TICK_IFNDEF.search(tick_incl_line)
                    incl_tick_elif_regex = RE_TICK_ELSIF.search(tick_incl_line)
                    incl_tick_else_regex = RE_TICK_ELSE.search(tick_incl_line)
                    incl_tick_endif_regex = RE_TICK_ENDIF.search(tick_incl_line)

                    if incl_tick_ifdef_regex:
                        if module_type == "TOP":
                            incl_tick_ifdef_en = self.tick_ifdef_proc(
                                "ifdef", incl_tick_ifdef_regex.group(1)
                            )
                        else:
                            incl_tick_ifdef_en = self.sub_tick_ifdef_proc(
                                "ifdef", incl_tick_ifdef_regex.group(1)
                            )

                        continue
                    elif incl_tick_ifndef_regex:
                        if module_type == "TOP":
                            incl_tick_ifdef_en = self.tick_ifdef_proc(
                                "ifndef", incl_tick_ifndef_regex.group(1)
                            )
                        else:
                            incl_tick_ifdef_en = self.sub_tick_ifdef_proc(
                                "ifndef", incl_tick_ifndef_regex.group(1)
                            )

                        continue
                    elif incl_tick_elif_regex:
                        if module_type == "TOP":
                            incl_tick_ifdef_en = self.tick_ifdef_proc(
                                "elif", incl_tick_elif_regex.group(1)
                            )
                        else:
                            incl_tick_ifdef_en = self.sub_tick_ifdef_proc(
                                "elif", incl_tick_elif_regex.group(1)
                            )

                        continue
                    elif incl_tick_else_regex:
                        if module_type == "TOP":
                            incl_tick_ifdef_en = self.tick_ifdef_proc("else", "")
                        else:
                            incl_tick_ifdef_en = self.sub_tick_ifdef_proc("else", "")

                        continue
                    elif incl_tick_endif_regex:
                        if module_type == "TOP":
                            incl_tick_ifdef_en = self.tick_ifdef_proc("endif", "")
                        else:
                            incl_tick_ifdef_en = self.sub_tick_ifdef_proc("endif", "")

                        continue

                    if not incl_tick_ifdef_en:  # If tick disables the code
                        continue
                    else:  # if incl_tick_ifdef_en:
                        ################################################################################
                        # Function Skip
                        ################################################################################
                        function_regex = RE_FUNCTION.search(tick_incl_line)
                        endfunction_regex = RE_ENDFUNCTION.search(tick_incl_line)

                        if function_regex:
                            function_name1_regex = RE_FUNCTION_NAME1.search(
                                tick_incl_line
                            )
                            function_name2_regex = RE_FUNCTION_NAME2.search(
                                tick_incl_line
                            )
                            if function_name1_regex:
                                # TODO: Calculate the function return width
                                package_function_skip = 0
                                if package_name == "" or package_name == "default":
                                    if class_name == "" or class_name == "default":
                                        function_name = function_name1_regex.group(1)
                                    else:
                                        function_name = (
                                            class_name
                                            + "::"
                                            + function_name1_regex.group(1)
                                        )
                                else:
                                    if class_name == "" or class_name == "default":
                                        function_name = (
                                            package_name
                                            + "::"
                                            + function_name1_regex.group(1)
                                        )
                                    else:
                                        function_name = (
                                            package_name
                                            + "::"
                                            + class_name
                                            + "::"
                                            + function_name1_regex.group(1)
                                        )

                                self.dbg(
                                    "\n### Skipping function "
                                    + function_name
                                    + " at "
                                    + str(incl_line_no)
                                    + " in "
                                    + inc_file_path
                                )
                                self.functions_list[function_name] = {}
                                self.functions_list[function_name][
                                    "name"
                                ] = function_name

                                continue
                            elif function_name2_regex:
                                # TODO: Calculate the function return width
                                package_function_skip = 0
                                if package_name == "" or package_name == "default":
                                    if class_name == "" or class_name == "default":
                                        function_name = function_name2_regex.group(1)
                                    else:
                                        function_name = (
                                            class_name
                                            + "::"
                                            + function_name2_regex.group(1)
                                        )
                                else:
                                    if class_name == "" or class_name == "default":
                                        function_name = (
                                            package_name
                                            + "::"
                                            + function_name2_regex.group(1)
                                        )
                                    else:
                                        function_name = (
                                            package_name
                                            + "::"
                                            + class_name
                                            + "::"
                                            + function_name2_regex.group(1)
                                        )

                                self.dbg(
                                    "\n### Skipping function "
                                    + function_name
                                    + " at "
                                    + str(incl_line_no)
                                    + " in "
                                    + inc_file_path
                                )
                                self.functions_list[function_name] = {}
                                self.functions_list[function_name][
                                    "name"
                                ] = function_name

                                continue
                            else:
                                self.dbg(
                                    "\nError: Unable to find function name. Might me due to missing ;"
                                )
                                self.dbg(tick_incl_line + "\n")
                                print(
                                    "\nError: Unable to find function name. Might me due to missing ;"
                                )
                                print(tick_incl_line + "\n")
                                self.found_error = 1
                        elif endfunction_regex:
                            package_function_skip = 0
                            continue

                        if package_function_skip:
                            continue

                        ################################################################################
                        # `include processing
                        ################################################################################
                        tick_include_regex = RE_TICK_INCLUDE.search(tick_incl_line)
                        if tick_include_regex:
                            self.load_import_or_include_file(
                                module_type, "INCLUDE", tick_include_regex.group(1)
                            )
                            continue

                        ################################################################################
                        # imported package processing
                        ################################################################################
                        import_regex = RE_IMPORT.search(tick_incl_line)
                        import_with_colons_regex = RE_IMPORT_COLONS.search(
                            tick_incl_line
                        )

                        if import_regex:
                            import_package = import_regex.group(1)
                            import_file_name = import_regex.group(1) + ".sv"
                        elif import_with_colons_regex:
                            import_file_name = import_with_colons_regex.group(1) + ".sv"
                            import_package = import_with_colons_regex.group(1)

                        if import_regex or import_with_colons_regex:
                            if module_type == "TOP":
                                if import_package not in self.packages:
                                    self.load_import_or_include_file(
                                        module_type, "IMPORT_EMBEDDED", import_file_name
                                    )
                                    continue
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )

                                continue
                            else:
                                if import_package not in self.sub_packages:
                                    self.load_import_or_include_file(
                                        module_type, "IMPORT_EMBEDDED", import_file_name
                                    )
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )

                                continue

                        ################################################################################
                        # class and endclass
                        ################################################################################
                        virtual_class_regex = RE_VIRTUAL_CLASS.search(tick_incl_line)
                        class_regex = RE_CLASS.search(tick_incl_line)
                        endclass_regex = RE_ENDCLASS.search(tick_incl_line)

                        if virtual_class_regex:
                            class_name = virtual_class_regex.group(1)
                            if module_type == "TOP":
                                self.classes.append(class_name)
                            else:
                                self.sub_classes.append(class_name)
                        elif class_regex:
                            class_name = class_regex.group(1)
                            if module_type == "TOP":
                                self.classes.append(class_name)
                            else:
                                self.sub_classes.append(class_name)
                        elif endclass_regex:
                            class_name = ""

                        if virtual_class_regex or class_regex:
                            if module_type == "TOP":
                                if class_name not in self.typedef_enums[package_name]:
                                    self.typedef_enums[package_name][class_name] = {}

                                if class_name not in self.typedef_logics[package_name]:
                                    self.typedef_logics[package_name][class_name] = {}

                                if class_name not in self.typedef_structs[package_name]:
                                    self.typedef_structs[package_name][class_name] = {}

                                if class_name not in self.typedef_unions[package_name]:
                                    self.typedef_unions[package_name][class_name] = {}
                            else:
                                if (
                                    class_name
                                    not in self.sub_typedef_enums[package_name]
                                ):
                                    self.sub_typedef_enums[package_name][
                                        class_name
                                    ] = {}

                                if (
                                    class_name
                                    not in self.sub_typedef_logics[package_name]
                                ):
                                    self.sub_typedef_logics[package_name][
                                        class_name
                                    ] = {}

                                if (
                                    class_name
                                    not in self.sub_typedef_structs[package_name]
                                ):
                                    self.sub_typedef_structs[package_name][
                                        class_name
                                    ] = {}

                                if (
                                    class_name
                                    not in self.sub_typedef_unions[package_name]
                                ):
                                    self.sub_typedef_unions[package_name][
                                        class_name
                                    ] = {}

                        ################################################################################
                        # `define parsing
                        ################################################################################
                        tick_define_regex = RE_TICK_DEFINE.search(tick_incl_line)

                        if tick_define_regex:
                            self.dbg("\n::: " + tick_incl_line + " :::")
                            tick_define_info = tick_define_regex.group(1)
                            tick_define_info = re.sub(r"\s+", " ", tick_define_info)
                            tick_define_info = re.sub(
                                r"\s*\(", " (", tick_define_info, 1
                            )
                            tick_incl_line = re.sub(r"\s*\(", " (", tick_incl_line, 1)

                            self.tick_def_proc(module_type, tick_define_info)

                        ################################################################################
                        # Parameter parsing
                        ################################################################################
                        tick_incl_param_regex = RE_PARAM.search(tick_incl_line)
                        tick_incl_localparam_regex = RE_LOCALPARAM.search(
                            tick_incl_line
                        )
                        tick_incl_semicolon_regex = RE_SEMICOLON.search(tick_incl_line)

                        if tick_incl_param_regex or tick_incl_localparam_regex:
                            if tick_incl_semicolon_regex:  # Complete param ended with ;
                                self.dbg("\n::: " + tick_incl_line + " :::")
                                self.param_proc(
                                    module_type,
                                    tick_incl_line,
                                    package_name,
                                    class_name,
                                )
                                tick_incl_gather_till_semicolon = 0
                            else:  # Multi line param
                                tick_incl_gather_till_semicolon = 1

                        ################################################################################
                        # package parsing
                        ################################################################################
                        package_regex = RE_PACKAGE.search(tick_incl_line)

                        if package_regex:
                            package_name = package_regex.group(1)
                            self.dbg("### Parsing Package: " + package_name)
                            if module_type == "TOP":
                                self.packages.append(package_name)
                            else:
                                self.sub_packages.append(package_name)

                            if inc_type == "IMPORT_COMMANDLINE":
                                package_name = package_regex.group(1)
                            else:
                                package_name = "default"

                            if module_type == "TOP":
                                if package_name not in self.typedef_enums:
                                    self.typedef_enums[package_name] = {}
                                    self.typedef_enums[package_name]["default"] = {}

                                if package_name not in self.typedef_logics:
                                    self.typedef_logics[package_name] = {}
                                    self.typedef_logics[package_name]["default"] = {}

                                if package_name not in self.typedef_structs:
                                    self.typedef_structs[package_name] = {}
                                    self.typedef_structs[package_name]["default"] = {}

                                if package_name not in self.typedef_unions:
                                    self.typedef_unions[package_name] = {}
                                    self.typedef_unions[package_name]["default"] = {}
                            else:
                                if package_name not in self.sub_typedef_enums:
                                    self.sub_typedef_enums[package_name] = {}
                                    self.sub_typedef_enums[package_name]["default"] = {}

                                if package_name not in self.sub_typedef_logics:
                                    self.sub_typedef_logics[package_name] = {}
                                    self.sub_typedef_logics[package_name][
                                        "default"
                                    ] = {}

                                if package_name not in self.sub_typedef_structs:
                                    self.sub_typedef_structs[package_name] = {}
                                    self.sub_typedef_structs[package_name][
                                        "default"
                                    ] = {}

                                if package_name not in self.sub_typedef_unions:
                                    self.sub_typedef_unions[package_name] = {}
                                    self.sub_typedef_unions[package_name][
                                        "default"
                                    ] = {}

                        ################################################################################
                        # typedef enum logic extraction
                        ################################################################################
                        enum_regex = RE_TYPEDEF_ENUM.search(tick_incl_line)

                        if enum_regex:
                            if tick_incl_semicolon_regex:  # Complete param ended with ;
                                tick_incl_line = re.sub(r"\s+", " ", tick_incl_line)
                                self.dbg("\n### ::: " + tick_incl_line + " :::")
                                enum_more_regex = RE_TYPEDEF_ENUM_EXTRACT.search(
                                    tick_incl_line
                                )

                                if enum_more_regex:
                                    tick_incl_gather_till_semicolon = 0
                                    self.enums_proc(
                                        module_type,
                                        enum_more_regex.group(2) + ";",
                                        package_name,
                                        class_name,
                                    )

                                    tick_incl_line = (
                                        enum_more_regex.group(1)
                                        + " "
                                        + enum_more_regex.group(3)
                                    )

                                    tick_incl_line = re.sub(
                                        r"\s*logic\s+", "", tick_incl_line
                                    )
                                    self.parse_reg_wire_logic(
                                        module_type,
                                        "TYPEDEF",
                                        "logic",
                                        tick_incl_line,
                                        package_name,
                                        class_name,
                                    )
                                else:
                                    self.dbg(
                                        "\nError: Unable to extract enums from the following"
                                    )
                                    self.dbg(tick_incl_line)
                                    print(
                                        "\nError: Unable to extract enums from the following"
                                    )
                                    print(tick_incl_line)
                                    self.found_error = 1
                            else:  # Multi line param
                                tick_incl_gather_till_semicolon = 1

                        ################################################################################
                        # typedef logic extraction
                        ################################################################################
                        typedef_logic_regex = RE_TYPEDEF_LOGIC.search(tick_incl_line)

                        if typedef_logic_regex:
                            if tick_incl_semicolon_regex:  # Complete param ended with ;
                                tick_incl_gather_till_semicolon = 0
                                tick_incl_line = re.sub(r"\s+", " ", tick_incl_line)
                                self.dbg("\n::: " + tick_incl_line + " :::")
                                tick_incl_line = typedef_logic_regex.group(1)

                                self.parse_reg_wire_logic(
                                    module_type,
                                    "TYPEDEF",
                                    "logic",
                                    tick_incl_line,
                                    package_name,
                                    class_name,
                                )
                            else:  # Multi line param
                                tick_incl_gather_till_semicolon = 1

                        ################################################################################
                        # typedef struct extraction
                        ################################################################################
                        typedef_struct_check_regex = RE_TYPEDEF_STRUCT_CHECK.search(
                            tick_incl_line
                        )
                        typedef_struct_nospace_regex = RE_TYPEDEF_STRUCT_NOSPACE.search(
                            tick_incl_line
                        )
                        typedef_closing_brace_regex = RE_CLOSING_BRACE.search(
                            tick_incl_line
                        )

                        if typedef_struct_check_regex or typedef_struct_nospace_regex:
                            if (
                                typedef_closing_brace_regex
                            ):  # Complete param ended with ;
                                tick_incl_gather_till_semicolon = 0
                                tick_incl_line = re.sub(r"\s+", " ", tick_incl_line)
                                self.parse_struct_union(
                                    "STRUCT",
                                    module_type,
                                    tick_incl_line,
                                    package_name,
                                    class_name,
                                )
                                continue
                            else:  # Multi line param
                                tick_incl_gather_till_semicolon = 1

                        ################################################################################
                        # typedef union extraction
                        ################################################################################
                        typedef_union_check_regex = RE_TYPEDEF_UNION_CHECK.search(
                            tick_incl_line
                        )
                        typedef_union_nospace_regex = RE_TYPEDEF_UNION_NOSPACE.search(
                            tick_incl_line
                        )
                        typedef_closing_brace_regex = RE_CLOSING_BRACE.search(
                            tick_incl_line
                        )

                        if typedef_union_check_regex or typedef_union_nospace_regex:
                            if (
                                typedef_closing_brace_regex
                            ):  # Complete param ended with ;
                                tick_incl_gather_till_semicolon = 0
                                tick_incl_line = re.sub(r"\s+", " ", tick_incl_line)
                                self.parse_struct_union(
                                    "UNION",
                                    module_type,
                                    tick_incl_line,
                                    package_name,
                                    class_name,
                                )
                                continue
                            else:  # Multi line param
                                tick_incl_gather_till_semicolon = 1

                        prev_tick_incl_line = tick_incl_line

        else:
            if inc_type == "IMPORT_COMMANDLINE" or inc_type == "IMPORT_EMBEDDED":
                self.dbg("\nError: Unable to find the package file " + inc_file)
                self.dbg("  List of search directories")
                print("\nError: Unable to find the package file " + inc_file)
                print("  List of search directories")
            else:
                self.dbg("\nError: Unable to find the `include file " + inc_file)
                self.dbg("  List of search directories")
                print("\nError: Unable to find the `include file " + inc_file)
                print("  List of search directories")

            for dir in self.incl_dirs:
                self.dbg("    " + str(dir))
                print("    " + str(dir))
            sys.exit(1)

        return

    def parse_struct_union(
        self, parse_type, module_type, struct_str, package, class_name
    ):
        """
        Function to parse a struct or union
        """
        self.dbg(
            "\n::: "
            + module_type
            + " PACKAGE: "
            + package
            + " # "
            + parse_type
            + " # "
            + struct_str
            + " :::"
        )

        if class_name == "default" or class_name == "":
            int_class = "default"
        else:
            int_class = class_name

        if package == "":  # assign a default package if no package is metioned
            int_package = "default"
        else:
            int_package = package

        struct_width = ""
        typedef_struct_packed_extract_regex = RE_TYPEDEF_STRUCT_PACKED_EXTRACT.search(
            struct_str
        )
        typedef_union_packed_extract_regex = RE_TYPEDEF_UNION_PACKED_EXTRACT.search(
            struct_str
        )
        typedef_struct_extract_regex = RE_TYPEDEF_STRUCT_EXTRACT.search(struct_str)
        typedef_union_extract_regex = RE_TYPEDEF_UNION_EXTRACT.search(struct_str)

        if (
            typedef_struct_packed_extract_regex
            or typedef_union_packed_extract_regex
            or typedef_struct_extract_regex
            or typedef_union_extract_regex
        ):
            if typedef_struct_packed_extract_regex:
                struct_members = typedef_struct_packed_extract_regex.group(2)
                struct_name = typedef_struct_packed_extract_regex.group(3)
            elif typedef_struct_extract_regex:
                struct_members = typedef_struct_extract_regex.group(1)
                struct_name = typedef_struct_extract_regex.group(2)
            elif typedef_union_packed_extract_regex:
                struct_members = typedef_union_packed_extract_regex.group(2)
                struct_name = typedef_union_packed_extract_regex.group(3)
            elif typedef_union_extract_regex:
                struct_members = typedef_union_extract_regex.group(1)
                struct_name = typedef_union_extract_regex.group(2)

            if module_type == "TOP":
                if parse_type == "STRUCT":
                    if (
                        int_package not in self.typedef_structs
                    ):  # Init a package for the first time
                        self.typedef_structs[int_package] = {}
                        self.typedef_structs[int_package][int_class] = {}
                        self.typedef_structs[int_package][int_class][struct_name] = {}
                    else:
                        self.typedef_structs[int_package][int_class][struct_name] = {}
                        self.typedef_structs[int_package][int_class][struct_name][
                            "struct"
                        ] = struct_members
                else:
                    if (
                        int_package not in self.typedef_unions
                    ):  # Init a package for the first time
                        self.typedef_unions[int_package] = {}
                        self.typedef_unions[int_package][int_class] = {}
                        self.typedef_unions[int_package][int_class][struct_name] = {}
                    else:
                        self.typedef_unions[int_package][int_class][struct_name] = {}
                        self.typedef_unions[int_package][int_class][struct_name][
                            "struct"
                        ] = struct_members
            else:
                if parse_type == "STRUCT":
                    if (
                        int_package not in self.sub_typedef_structs
                    ):  # Init a package for the first time
                        self.sub_typedef_structs[int_package] = {}
                        self.sub_typedef_structs[int_package][int_class] = {}
                        self.sub_typedef_structs[int_package][int_class][
                            struct_name
                        ] = {}
                    else:
                        self.sub_typedef_structs[int_package][int_class][
                            struct_name
                        ] = {}
                        self.sub_typedef_structs[int_package][int_class][struct_name][
                            "struct"
                        ] = struct_members
                else:
                    if (
                        int_package not in self.sub_typedef_unions
                    ):  # Init a package for the first time
                        self.sub_typedef_unions[int_package] = {}
                        self.sub_typedef_unions[int_package][int_class][
                            struct_name
                        ] = {}
                        self.sub_typedef_unions[int_package][int_class][
                            struct_name
                        ] = {}
                    else:
                        self.sub_typedef_unions[int_package][int_class][
                            struct_name
                        ] = {}
                        self.sub_typedef_unions[int_package][int_class][struct_name][
                            "struct"
                        ] = struct_members

            struct_members_semicolon_regex = RE_SEMICOLON.search(struct_members)

            struct_members_list = []
            struct_members_list_pre = []
            # If multiple declarations on the same line, then break it
            if struct_members_semicolon_regex:
                # removing space, { and }
                struct_members = re.sub(r"\]", "] ", struct_members)
                struct_members = re.sub(r"\[", " [", struct_members)
                struct_members = re.sub(r"[{}]", "", struct_members)
                struct_members = re.sub(r"\s+", " ", struct_members)
                struct_members = re.sub(r"^\s*", "", struct_members)
                struct_members = re.sub(r"\s*,\s*", ",", struct_members)
                struct_members = re.sub(r"\s*;\s*", ";", struct_members)
                struct_members = re.sub(r"\s*$", "", struct_members)
                struct_members = re.sub(r"\s*;\s*$", "", struct_members)
                struct_members_list_pre = struct_members.split(";")
            else:  # Single declaration, then append to the array
                struct_members_list_pre.append(struct_members)

            # Breaking command separated struct/union members into separate declarations
            for curr_struct_member in struct_members_list_pre:
                struct_memebers_comma_regex = RE_COMMA.search(curr_struct_member)

                if struct_memebers_comma_regex:
                    curr_struct_member = re.sub(r"\s+", "#", curr_struct_member)
                    struct_hash_regex = RE_HASH.search(curr_struct_member)

                    if struct_hash_regex:
                        struct_ref = struct_hash_regex.group(1)
                        struct_members_comma_separated = struct_hash_regex.group(2)
                        struct_members_comma_separated_list = (
                            struct_members_comma_separated.split(",")
                        )

                        for c_struct_member in struct_members_comma_separated_list:
                            struct_members_list.append(
                                struct_ref + " " + c_struct_member
                            )
                else:
                    struct_members_list.append(curr_struct_member)

            if parse_type == "STRUCT":
                self.dbg("  # STRUCT MEMBERS: " + struct_members)
            else:
                self.dbg("  # UNION MEMBERS: " + struct_members)

            for curr_struct_member in struct_members_list:
                struct_logic_regex = RE_DECLARE_LOGIC.search(curr_struct_member)

                if struct_logic_regex:
                    self.dbg("    # LOGIC :: " + curr_struct_member)

                    logic_signed = ""  # signed
                    logic_bitdef = ""
                    logic_uwidth = ""
                    logic_lwidth = ""
                    logic_depth = ""
                    logic_name = ""

                    # Removing ;
                    logic_str = re.sub(r"\s*;\s*", ";", curr_struct_member)

                    # Removing logic
                    logic_str = re.sub(r"^\s*logic\s+", "", logic_str)

                    # looking for signed and removing the keyword
                    logic_signed_regex = RE_DECLARE_SIGNED.search(logic_str)

                    if logic_signed_regex:
                        logic_str = re.sub(r"\s*\bsigned\b\s*", " ", logic_str)
                        logic_signed = "signed"

                    # Extracting bit definition if present
                    logic_bitdef_regex = RE_DECLARE_BITDEF.search(logic_str)
                    logic_packed_bitdef_regex = RE_DECLARE_PACKED_BITDEF.search(
                        logic_str
                    )

                    if logic_packed_bitdef_regex:
                        logic_bitdef = (
                            logic_packed_bitdef_regex.group(1)
                            + "["
                            + logic_packed_bitdef_regex.group(2)
                        )
                        logic_str = logic_packed_bitdef_regex.group(3)
                    elif logic_bitdef_regex:
                        logic_bitdef = logic_bitdef_regex.group(1)
                        logic_str = logic_bitdef_regex.group(2)
                    else:  # Remove logic keyword
                        logic_str = re.sub(r"^\s*logic\s*", "", logic_str)

                    # Extracting depth definition if present
                    logic_depth_regex = RE_DECLARE_DEPTH.search(logic_str)

                    if logic_depth_regex:
                        logic_str = logic_depth_regex.group(1)
                        logic_depth = logic_depth_regex.group(2)

                    # Remaining is the name of IO
                    logic_str = re.sub(r"\s*;\s*", "", logic_str)

                    logic_comma_regex = RE_COMMA.search(logic_str)

                    # If multiple declarations on the same line, then break it
                    logic_str_array = []
                    if logic_comma_regex:
                        logic_str = re.sub(r"\s*", "", logic_str)
                        logic_str_array = logic_str.split(",")
                    else:  # Single declaration, then append to the array
                        logic_str_array.append(logic_str)

                    logic_name = logic_str
                    if logic_bitdef != "":
                        logic_bitdef_val = []
                        # TODO: need to add class as input to this function and pass it in the next line
                        logic_bitdef_val = self.tickdef_param_getval(
                            module_type, logic_bitdef, int_package, ""
                        )

                        if logic_bitdef_val[0] == "STRING":
                            logic_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                logic_bitdef
                            )

                            if logic_bitdef_packed_regex:
                                self.dbg(
                                    (
                                        "    # Skip parsing packed array :: "
                                        + curr_struct_member
                                    )
                                )
                            else:
                                self.dbg(
                                    "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                                )
                                self.dbg(
                                    "  # "
                                    + module_type
                                    + ":: name: "
                                    + logic_name
                                    + ", signed: "
                                    + logic_signed
                                    + ", bitdef: "
                                    + logic_bitdef
                                    + ", depth: "
                                    + logic_depth
                                )
                                print(
                                    "\nWarning: Unable to calculate the numerical value for bitdef of the following"
                                )
                                print(
                                    "  # "
                                    + module_type
                                    + ":: name: "
                                    + logic_name
                                    + ", signed: "
                                    + logic_signed
                                    + ", bitdef: "
                                    + logic_bitdef
                                    + ", depth: "
                                    + logic_depth
                                )
                        else:
                            logic_bitdef_regex = RE_COLON.search(
                                str(logic_bitdef_val[1])
                            )

                            # Multi bit definition
                            if logic_bitdef_regex:
                                logic_uwidth = logic_bitdef_regex.group(1)
                                logic_lwidth = logic_bitdef_regex.group(2)
                            else:  # Single bit definition
                                logic_lwidth = logic_bitdef_val[1]

                    if logic_uwidth == "":
                        logic_uwidth = 0

                    if logic_lwidth == "":
                        logic_lwidth = 0

                    if logic_uwidth != "" and logic_lwidth != "":
                        if logic_uwidth == 0 and logic_lwidth == 0:
                            logic_width = 1
                        else:
                            logic_width = int(logic_uwidth) - int(logic_lwidth) + 1
                    else:
                        logic_width = 1

                    if parse_type == "STRUCT":
                        if struct_width == "":
                            struct_width = logic_width
                        else:
                            struct_width = struct_width + logic_width
                    else:
                        # Check if all the widths are same inside union
                        if struct_width != "":
                            if struct_width != logic_width:
                                struct_width = logic_width
                                self.dbg(
                                    "\nWarning:  ### The width of the members inside the following union is not same"
                                )
                                self.dbg("  # " + struct_name)
                                self.dbg("  ::: " + struct_str + " :::")
                                print(
                                    "\nWarning:  ### The width of the members inside the following union is not same"
                                )
                                print("  # " + struct_name)
                                print("  ::: " + struct_str + " :::")
                                # self.found_error = 1
                            else:
                                struct_width = logic_width
                        else:
                            struct_width = logic_width

                    if module_type == "TOP":
                        if parse_type == "STRUCT":
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ] = {}
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["name"] = logic_name
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["type"] = "LOGIC"
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["bitdef"] = logic_bitdef
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["width"] = logic_width
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["uwidth"] = logic_uwidth
                            self.typedef_structs[int_package][int_class][struct_name][
                                logic_name
                            ]["lwidth"] = logic_lwidth
                            self.typedef_structs[int_package][int_class][struct_name][
                                "width"
                            ] = struct_width
                        else:
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ] = {}
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["name"] = logic_name
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["type"] = "LOGIC"
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["bitdef"] = logic_bitdef
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["width"] = logic_width
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["uwidth"] = logic_uwidth
                            self.typedef_unions[int_package][int_class][struct_name][
                                logic_name
                            ]["lwidth"] = logic_lwidth
                            self.typedef_unions[int_package][int_class][struct_name][
                                "width"
                            ] = struct_width
                    else:
                        if parse_type == "STRUCT":
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name] = {}
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["name"] = logic_name
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["type"] = "LOGIC"
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["bitdef"] = logic_bitdef
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["width"] = logic_width
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["uwidth"] = logic_uwidth
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ][logic_name]["lwidth"] = logic_lwidth
                            self.sub_typedef_structs[int_package][int_class][
                                struct_name
                            ]["width"] = struct_width
                        else:
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name] = {}
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["name"] = logic_name
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["type"] = "LOGIC"
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["bitdef"] = logic_bitdef
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["width"] = logic_width
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["uwidth"] = logic_uwidth
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ][logic_name]["lwidth"] = logic_lwidth
                            self.sub_typedef_unions[int_package][int_class][
                                struct_name
                            ]["width"] = struct_width

                    self.dbg(
                        "      #"
                        + module_type
                        + ":: name: "
                        + logic_name
                        + ", bitdef: "
                        + logic_bitdef
                        + ", uwidth: "
                        + str(logic_uwidth)
                        + ", lwidth: "
                        + str(logic_lwidth)
                        + ", width: "
                        + str(logic_width)
                    )
                else:  # check if this is a struct
                    curr_struct_list = curr_struct_member.split(" ")
                    curr_struct_member_ref = curr_struct_list[0]
                    curr_struct_member = curr_struct_list[1]

                    curr_struct_member_ref_package = int_package
                    curr_struct_member_ref_class = int_class
                    curr_struct_member_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                        curr_struct_member_ref
                    )
                    curr_struct_member_ref_regex_double = (
                        RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(curr_struct_member_ref)
                    )

                    if (
                        curr_struct_member_ref_regex_double
                    ):  # If a package name and class is associated
                        curr_struct_member_ref_package = (
                            curr_struct_member_ref_regex_double.group(1)
                        )
                        curr_struct_member_ref_class = (
                            curr_struct_member_ref_regex_double.group(2)
                        )
                        curr_struct_member_ref = (
                            curr_struct_member_ref_regex_double.group(3)
                        )
                    elif (
                        curr_struct_member_ref_regex
                    ):  # If a package name is associated
                        if module_type == "TOP":
                            if curr_struct_member_ref_regex.group(1) in list(
                                self.classes
                            ):
                                # curr_struct_member_ref_package = 'default'
                                curr_struct_member_ref_class = (
                                    curr_struct_member_ref_regex.group(1)
                                )
                                curr_struct_member_ref = (
                                    curr_struct_member_ref_regex.group(2)
                                )
                            else:
                                curr_struct_member_ref_package = (
                                    curr_struct_member_ref_regex.group(1)
                                )
                                curr_struct_member_ref_class = "default"
                                curr_struct_member_ref = (
                                    curr_struct_member_ref_regex.group(2)
                                )
                        else:
                            if curr_struct_member_ref_regex.group(1) in list(
                                self.sub_classes
                            ):
                                # curr_struct_member_ref_package = 'default'
                                curr_struct_member_ref_class = (
                                    curr_struct_member_ref_regex.group(1)
                                )
                                curr_struct_member_ref = (
                                    curr_struct_member_ref_regex.group(2)
                                )
                            else:
                                curr_struct_member_ref_package = (
                                    curr_struct_member_ref_regex.group(1)
                                )
                                curr_struct_member_ref_class = "default"
                                curr_struct_member_ref = (
                                    curr_struct_member_ref_regex.group(2)
                                )

                    if module_type == "TOP":
                        if curr_struct_member_ref_package not in self.packages:
                            self.load_import_or_include_file(
                                "TOP",
                                "IMPORT_COMMANDLINE",
                                curr_struct_member_ref_package + ".sv",
                            )

                        if (
                            curr_struct_member_ref
                            in self.typedef_structs[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the struct hash
                            self.dbg("    # STRUCT :: " + curr_struct_member)
                            if parse_type == "STRUCT":
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "STRUCT"
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_structs[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width

                                self.dbg(
                                    "      # STRUCT - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.typedef_structs[int_package][int_class][
                                            struct_name
                                        ][curr_struct_member]["width"]
                                    )
                                )
                            else:
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "STRUCT"
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_structs[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      # UNION - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )

                        elif (
                            curr_struct_member_ref
                            in self.typedef_unions[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the union hash
                            self.dbg("    # UNION :: " + curr_struct_member)
                            if parse_type == "STRUCT":
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "UNION"
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_unions[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width

                                self.dbg(
                                    "      # STRUCT - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.typedef_structs[int_package][int_class][
                                            struct_name
                                        ][curr_struct_member]["width"]
                                    )
                                )
                            else:
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "UNION"
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_unions[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      # UNION - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )

                        elif (
                            curr_struct_member_ref
                            in self.typedef_logics[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the struct hash
                            self.dbg("    # LOGIC :: " + curr_struct_member)

                            if parse_type == "STRUCT":
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["logic"] = curr_struct_member_ref
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "LOGIC"
                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_logics[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #TOP STRUCT - LOGIC: "
                                    + curr_struct_member
                                    + ", logic: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    )
                                )
                            else:
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["logic"] = curr_struct_member_ref
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "LOGIC"
                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["width"] = self.typedef_logics[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ', struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ', struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #TOP UNION - LOGIC: "
                                    + curr_struct_member
                                    + ", logic: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    )
                                )
                        else:
                            self.dbg(
                                "\nError: Unable to find the following struct/union/logic in the packages"
                                + " :: "
                                + module_type
                            )
                            self.dbg("    # PACKAGE: " + int_package)
                            self.dbg("    # MEMBER: " + curr_struct_member)
                            self.dbg("    # REF: " + curr_struct_member_ref)
                            self.dbg("    # STRUCT: " + struct_name)
                            self.dbg("    # " + struct_str)
                            print(
                                "\nError: Unable to find the following struct/union/logic in the packages"
                                + " :: "
                                + module_type
                            )
                            print("    # PACKAGE: " + int_package)
                            print("    # MEMBER: " + curr_struct_member)
                            print("    # REF: " + curr_struct_member_ref)
                            print("    # STRUCT: " + struct_name)
                            print("    # " + struct_str)
                            self.found_error = 1
                    else:
                        if curr_struct_member_ref_package not in self.sub_packages:
                            self.load_import_or_include_file(
                                "SUB",
                                "IMPORT_COMMANDLINE",
                                curr_struct_member_ref_package + ".sv",
                            )

                        if (
                            curr_struct_member_ref
                            in self.sub_typedef_structs[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the struct hash
                            self.dbg("    # STRUCT :: " + curr_struct_member)
                            if parse_type == "STRUCT":
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "STRUCT"
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_structs[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #SUB STRUCT - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )
                            else:
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "STRUCT"
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_structs[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_structs[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_structs[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #SUB UNION - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )
                        elif (
                            curr_struct_member_ref
                            in self.sub_typedef_unions[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the struct hash
                            self.dbg("    # UNION :: " + curr_struct_member)
                            if parse_type == "STRUCT":
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "UNION"
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_unions[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #SUB STRUCT - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )
                            else:
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["struct"] = curr_struct_member_ref
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "UNION"
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_unions[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_unions[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_unions[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #SUB UNION - STRUCT: "
                                    + curr_struct_member
                                    + ", struct: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(struct_width)
                                )
                        elif (
                            curr_struct_member_ref
                            in self.sub_typedef_logics[curr_struct_member_ref_package][
                                curr_struct_member_ref_class
                            ]
                        ):  # struct is present in the struct hash
                            self.dbg("    # LOGIC :: " + curr_struct_member)
                            if parse_type == "STRUCT":
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["logic"] = curr_struct_member_ref
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "LOGIC"
                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_logics[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_structs[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #TOP STRUCT - LOGIC: "
                                    + curr_struct_member
                                    + ", logic: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    )
                                )
                            else:
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member] = {}
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["name"] = curr_struct_member
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["package"] = package
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["logic"] = curr_struct_member_ref
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member]["type"] = "LOGIC"
                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ][curr_struct_member][
                                    "width"
                                ] = self.sub_typedef_logics[
                                    curr_struct_member_ref_package
                                ][
                                    curr_struct_member_ref_class
                                ][
                                    curr_struct_member_ref
                                ][
                                    "width"
                                ]

                                # Adding the struct width to top struct width
                                if parse_type == "STRUCT":
                                    if struct_width == "":
                                        struct_width = self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    else:
                                        struct_width = (
                                            struct_width
                                            + self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        )
                                else:
                                    # Check if all the widths are same inside union
                                    if struct_width != "":
                                        if (
                                            struct_width
                                            != self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                        ):
                                            struct_width = self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                            # self.dbg('\nWarning: The width of the members inside the following union is not same')
                                            # self.dbg('  # ' + struct_name)
                                            # self.dbg('  ::: ' + struct_str + ' :::')
                                            # print('\nWarning: The width of the members inside the following union is not same')
                                            # print('  # ' + struct_name)
                                            # print('  ::: ' + struct_str + ' :::')
                                        else:
                                            struct_width = self.sub_typedef_logics[
                                                curr_struct_member_ref_package
                                            ][curr_struct_member_ref_class][
                                                curr_struct_member_ref
                                            ][
                                                "width"
                                            ]
                                    else:
                                        struct_width = self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]

                                self.sub_typedef_unions[int_package][int_class][
                                    struct_name
                                ]["width"] = struct_width
                                self.dbg(
                                    "      #TOP UNION - LOGIC: "
                                    + curr_struct_member
                                    + ", logic: "
                                    + curr_struct_member_ref
                                    + ", width: "
                                    + str(
                                        self.sub_typedef_logics[
                                            curr_struct_member_ref_package
                                        ][curr_struct_member_ref_class][
                                            curr_struct_member_ref
                                        ][
                                            "width"
                                        ]
                                    )
                                )
                        else:
                            self.dbg(
                                "\nError: Unable to find the following struct/union/logic in the packages"
                                + " :: "
                                + module_type
                            )
                            self.dbg("    # PACKAGE: " + int_package)
                            self.dbg("    # CLASS: " + int_class)
                            self.dbg("    # MEMBER: " + curr_struct_member)
                            self.dbg("    # REF: " + curr_struct_member_ref)
                            self.dbg("    # STRUCT: " + struct_name)
                            self.dbg("    # " + struct_str)
                            print(
                                "\nError: Unable to find the following struct/union/logic in the packages"
                                + " :: "
                                + module_type
                            )
                            print("    # PACKAGE: " + int_package)
                            print("    # CLASS: " + int_class)
                            print("    # MEMBER: " + curr_struct_member)
                            print("    # REF: " + curr_struct_member_ref)
                            print("    # STRUCT: " + struct_name)
                            print("    # " + struct_str)
                            sys.exit(1)
                            self.found_error = 1

            if parse_type == "STRUCT":
                self.dbg("  # STRUCT: " + struct_name + ", WIDTH: " + str(struct_width))
            else:
                self.dbg("  # UNION: " + struct_name + ", WIDTH: " + str(struct_width))
        else:
            self.dbg("\nError: Unable to detect struct or union")
            self.dbg("    # " + struct_str)
            print("\nError: Unable to detect struct or union")
            print("    # " + struct_str)
            self.found_error = 1

        return

    def param_proc(self, module_type, param_str, package, class_name):
        """
        Function to parse parameter or localparam
        """

        param_str = re.sub(r"\s+", " ", param_str)
        self.dbg(module_type + ":: " + param_str)

        # Removing parameter keywords and bitwidth and spaces
        param_str = re.sub(r"^\s*parameter\s+", "", param_str)
        param_str = re.sub(r",\s*parameter\s+", ",", param_str)
        param_str = re.sub(r"^\s*localparam\s+", "", param_str)
        param_str = re.sub(r"^signed\s+", "", param_str)
        param_str = re.sub(r"^\s*\[.*\]\s*", "", param_str)
        param_str = re.sub(r"\s*\[[\w:]+\]\s*", "", param_str)
        param_str = re.sub(r";", "", param_str)
        param_str = re.sub(r"\s*", "", param_str)
        param_str_array = param_str.split(",")

        if class_name == "default" or class_name == "":
            int_class = "default"
        else:
            int_class = class_name

        if package == "":
            int_package = "default"
        else:
            int_package = package

        for param in param_str_array:
            param = re.sub(r"\s*=\s*", "#", param, 1)
            param_split_regex = RE_HASH_SPLIT.search(param)

            if param_split_regex:
                param_name = param_split_regex.group(1)
                # TODO: Need to pass package
                param_val_ret = self.tickdef_param_getval(
                    module_type, param_split_regex.group(2), int_package, int_class
                )

                if param_val_ret[0] == "STRING":
                    self.dbg(
                        "  PARAM:: "
                        + param_name
                        + " : "
                        + param_val_ret[0]
                        + " : "
                        + param_split_regex.group(2)
                    )

                    # TODO: Need to check if the param is already there, then issue warning
                    if module_type == "TOP":
                        self.params[param_name] = {}
                        self.params[param_name]["type"] = param_val_ret[0]
                        self.params[param_name]["val"] = param_split_regex.group(2)
                        self.params[param_name]["exp"] = param_split_regex.group(2)
                    else:
                        self.sub_params[param_name] = {}
                        self.sub_params[param_name]["type"] = param_val_ret[0]
                        self.sub_params[param_name]["val"] = param_split_regex.group(2)
                        self.sub_params[param_name]["exp"] = param_split_regex.group(2)
                else:
                    self.dbg(
                        "  PARAM:: "
                        + param_name
                        + " : "
                        + param_val_ret[0]
                        + " : "
                        + str(param_val_ret[1])
                    )

                    # TODO: Need to check if the param is already there, then issue warning
                    if module_type == "TOP":
                        self.params[param_name] = {}
                        self.params[param_name]["type"] = param_val_ret[0]
                        self.params[param_name]["val"] = param_val_ret[1]
                        self.params[param_name]["exp"] = param_str
                    else:
                        self.sub_params[param_name] = {}
                        self.sub_params[param_name]["type"] = param_val_ret[0]
                        self.sub_params[param_name]["val"] = param_val_ret[1]
                        self.sub_params[param_name]["exp"] = param_str

        return

    def enums_proc(self, module_type, enum_str, package, class_name):
        """
        Function to parse enums in a package
        """

        enum_str = re.sub(r"\s+", " ", enum_str)
        self.dbg(module_type + ":: " + enum_str)

        int_class = "default"

        if package == "":
            int_package = "default"
        else:
            int_package = package

        # Implicit enums (range in [8:12] or [4]
        # Explicit enums
        # Combination of implicit and explicit enums

        # Removing parameter keywords and bitwidth and spaces
        enum_str = re.sub(r";", "", enum_str)
        enum_str = re.sub(r"\s*", "", enum_str)
        enum_str_array = enum_str.split(",")

        enum_val = 0

        for enum in enum_str_array:
            enum_split_regex = RE_PARAM_SPLIT.search(enum)

            if enum_split_regex:  # Explicit enum
                enum_name = enum_split_regex.group(1)
                enum_val = enum_split_regex.group(2)

                self.dbg("  # ENUM: " + enum_name + " :: " + str(enum_val))

                if module_type == "TOP":
                    self.typedef_enums[int_package][int_class][enum_name] = enum_val
                else:
                    self.sub_typedef_enums[int_package][int_class][enum_name] = enum_val

                enum_number_regex = RE_NUMBERS_ONLY.search(enum_val)

                if module_type == "TOP":
                    self.params[enum_name] = {}
                    if enum_number_regex:
                        self.params[enum_name]["type"] = "STRING"
                    else:
                        self.params[enum_name]["type"] = "NUMBER"

                    self.params[enum_name]["val"] = enum_val
                    self.params[enum_name]["exp"] = enum_val
                else:
                    self.sub_params[enum_name] = {}
                    if enum_number_regex:
                        self.sub_params[enum_name]["type"] = "STRING"
                    else:
                        self.sub_params[enum_name]["type"] = "NUMBER"

                    self.sub_params[enum_name]["val"] = enum_val
                    self.sub_params[enum_name]["exp"] = enum_val

                if enum_number_regex:
                    enum_val = int(enum_val) + 1
            else:  # Implicit enum
                enum_implicit_range_regex = RE_ENUM_IMPLICIT_RANGE.search(enum)
                enum_implicit_count_regex = RE_ENUM_IMPLICIT_COUNT.search(enum)

                enum_start = enum_val
                enum_end = enum_val
                enum_name_append = 0

                if enum_implicit_range_regex:
                    enum_name = enum_implicit_range_regex.group(1)
                    enum_start = enum_implicit_range_regex.group(2)
                    enum_end = int(enum_implicit_range_regex.group(3)) + 1
                    enum_name_append = 1
                elif enum_implicit_count_regex:
                    enum_name = enum_implicit_count_regex.group(1)
                    enum_start = 0
                    enum_end = enum_implicit_count_regex.group(2)
                    enum_name_append = 1
                else:
                    enum_name = enum
                    enum_start = 0
                    enum_end = 1

                for enum_idx in range(int(enum_start), int(enum_end)):
                    if enum_name_append:
                        c_enum_name = enum_name + str(enum_idx)
                    else:
                        c_enum_name = enum_name

                    self.dbg("  ## ENUM: " + c_enum_name + " :: " + str(enum_val))

                    if module_type == "TOP":
                        self.typedef_enums[int_package][int_class][
                            c_enum_name
                        ] = enum_val
                    else:
                        self.sub_typedef_enums[int_package][int_class][
                            c_enum_name
                        ] = enum_val

                    if module_type == "TOP":
                        self.params[c_enum_name] = {}
                        self.params[c_enum_name]["type"] = "NUMBER"
                        self.params[c_enum_name]["val"] = enum_val
                        self.params[c_enum_name]["exp"] = enum_val
                    else:
                        self.sub_params[c_enum_name] = {}
                        self.sub_params[c_enum_name]["type"] = "NUMBER"
                        self.sub_params[c_enum_name]["val"] = enum_val
                        self.sub_params[c_enum_name]["exp"] = enum_val

                    enum_val = int(enum_val) + 1

        return

    def tick_ifdef_proc(self, tick_ifdef_type, tick_ifdef_str):
        """
        Function to process 'ifdef and it returns current ifdef status to skip
        the code or parse it
        """

        last_tick_decision = 0
        popped_tick_decision = 0
        popped_tick_type = ""
        popped_tick_served = 0

        if tick_ifdef_type == "ifdef":
            tick_level = len(self.tick_decisions)
            self.dbg(
                "\n### self.tick_decisions : " + (" ").join(str(self.tick_decisions))
            )
            self.dbg(
                "\n### TOP: "
                + ":: TICK LEVEL: "
                + str(tick_level)
                + ", "
                + tick_ifdef_type
                + ", "
                + tick_ifdef_str
            )
        else:
            tick_level = len(self.tick_decisions) - 1
            self.dbg(
                "\n### TOP: "
                + ":: TICK LEVEL: "
                + str(tick_level)
                + ", "
                + tick_ifdef_type
                + ", "
                + tick_ifdef_str
            )

        tick_ifdef_str_regex = RE_TICK_IFDEF_STR.search(tick_ifdef_str)

        if tick_ifdef_type == "else":
            # Pop the last ifdef/elif of the same level
            if len(self.tick_decisions) > 0:
                self.dbg(
                    "# TICK: Popping previous construct "
                    + popped_tick_type
                    + " for else"
                )
                popped_tick_decision = self.tick_decisions.pop()
                popped_tick_type = self.tick_types.pop()
                popped_tick_served = self.tick_served.pop()
                self.dbg(
                    "  Type: "
                    + popped_tick_type
                    + ",  Decision: "
                    + str(popped_tick_decision)
                    + ",  Served: "
                    + str(popped_tick_served)
                )

            if len(self.tick_decisions) > 0:
                self.last_tick_loc = len(self.tick_decisions) - 1
                last_tick_decision = self.tick_decisions[self.last_tick_loc]
            else:
                last_tick_decision = 1

            # if the current tick ifdef/elif already served, then else will be disabled
            if self.tick_curr_served:
                self.tick_curr_decision = 0
                self.tick_decisions.append(0)
                self.tick_types.append("else")
                self.tick_served.append(1)
            else:
                if last_tick_decision:
                    self.tick_curr_decision = 1
                    self.tick_decisions.append(1)
                    self.tick_types.append("else")
                    self.tick_served.append(1)
                else:
                    self.tick_curr_decision = 0
                    self.tick_decisions.append(0)
                    self.tick_types.append("else")
                    self.tick_served.append(1)

            self.dbg("# TICK: Pushing current construct else")
            if len(self.tick_decisions) > 0:
                self.dbg(self.tick_types)
                self.dbg(self.tick_decisions)
                self.dbg(self.tick_served)
        elif tick_ifdef_type == "endif":
            if len(self.tick_decisions) > 0:
                self.dbg(
                    "# TICK: Popping previous construct "
                    + popped_tick_type
                    + " for endif"
                )
                popped_tick_decision = self.tick_decisions.pop()
                popped_tick_type = self.tick_types.pop()
                popped_tick_served = self.tick_served.pop()
                self.dbg(
                    "  Type: "
                    + popped_tick_type
                    + ",  Decision: "
                    + str(popped_tick_decision)
                    + ",  Served: "
                    + str(popped_tick_served)
                )

                if len(self.tick_decisions) > 0:
                    self.last_tick_loc = len(self.tick_decisions) - 1
                    self.tick_curr_decision = self.tick_decisions[self.last_tick_loc]
                    self.tick_curr_type = self.tick_types[self.last_tick_loc]
                    self.tick_curr_served = self.tick_served[self.last_tick_loc]
                else:
                    # Out of all the ifdef and hence its enabled
                    self.tick_curr_decision = 1
                    self.tick_curr_type = ""
                    self.tick_curr_served = 0

            else:
                self.dbg(
                    "\nError: There is no pending ifdef/elif in the buffer, but reaching #endif at line "
                    + str(line_no)
                )
                print(
                    "\nError: There is no pending ifdef/elif in the buffer, but reaching #endif at line "
                    + str(line_no)
                )
                sys.exit(1)
        else:  # ifdef / ifndef / elif
            # for all other ifdef, ifndef, elif to process tick_ifdef_str evaluation
            if len(self.tick_decisions) > 0:
                self.last_tick_loc = len(self.tick_decisions) - 1
                last_tick_decision = self.tick_decisions[self.last_tick_loc]
            else:
                last_tick_decision = 1

            if (
                (tick_ifdef_type == "elif" and self.tick_curr_served == 0)
                or tick_ifdef_type == "ifdef"
                or tick_ifdef_type == "ifndef"
            ):
                # Need to pop previous elif or ifdef or ifndef for elif case
                if tick_ifdef_type == "elif":
                    self.dbg(
                        "# TICK: Popping previous construct "
                        + popped_tick_type
                        + " for elif"
                    )
                    popped_tick_decision = self.tick_decisions.pop()
                    popped_tick_type = self.tick_types.pop()
                    popped_tick_served = self.tick_served.pop()
                    self.dbg(
                        "  Type: "
                        + popped_tick_type
                        + ",  Decision: "
                        + str(popped_tick_decision)
                        + ",  Served: "
                        + str(popped_tick_served)
                    )

                if tick_ifdef_str_regex:  # Check if this is without expression
                    if (
                        tick_ifdef_str in self.tick_defines
                    ):  # define is present in the tick database
                        if tick_ifdef_type == "ifndef":
                            self.tick_curr_decision = 0
                            self.tick_curr_type = tick_ifdef_type
                            self.tick_curr_served = 0
                        else:
                            # Current decision is set only if previous decision is 1
                            if last_tick_decision:
                                self.tick_curr_decision = 1
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1
                            else:
                                self.tick_curr_decision = 0
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1

                        self.tick_decisions.append(self.tick_curr_decision)
                        self.tick_types.append(self.tick_curr_type)
                        self.tick_served.append(self.tick_curr_served)
                    else:
                        if tick_ifdef_type == "ifndef":
                            if last_tick_decision:
                                self.tick_curr_decision = 1
                                self.tick_curr_served = 1
                                self.tick_curr_type = tick_ifdef_type
                            else:
                                self.tick_curr_decision = 0
                                self.tick_curr_served = 1
                                self.tick_curr_type = tick_ifdef_type
                        else:
                            self.tick_curr_decision = 0
                            self.tick_curr_served = 0
                            self.tick_curr_type = tick_ifdef_type

                        self.tick_decisions.append(self.tick_curr_decision)
                        self.tick_types.append(self.tick_curr_type)
                        self.tick_served.append(self.tick_curr_served)

                    self.dbg("# TICK: Pushing current construct " + self.tick_curr_type)
                    if len(self.tick_decisions) > 0:
                        self.dbg(self.tick_types)
                        self.dbg(self.tick_decisions)
                        self.dbg(self.tick_served)
                else:
                    # If ifdef has an expression, then we need to get the result of expression
                    # TODO: Need to pass package
                    ifdef_exp_val = self.tickdef_param_getval(
                        "TOP", tick_ifdef_str, "", ""
                    )

                    if tick_ifdef_type == "ifndef":
                        if ifdef_exp_val[1]:
                            self.tick_curr_decision = 0
                            self.tick_curr_type = tick_ifdef_type
                            self.tick_curr_served = 0
                        else:
                            if last_tick_decision:
                                self.tick_curr_decision = 1
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1
                            else:
                                self.tick_curr_decision = 0
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1

                        self.tick_decisions.append(self.tick_curr_decision)
                        self.tick_types.append(self.tick_curr_type)
                        self.tick_served.append(self.tick_curr_served)
                    else:
                        if ifdef_exp_val[1]:
                            if last_tick_decision:
                                self.tick_curr_decision = 1
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1
                            else:
                                self.tick_curr_decision = 0
                                self.tick_curr_type = tick_ifdef_type
                                self.tick_curr_served = 1
                        else:
                            self.tick_curr_decision = 0
                            self.tick_curr_type = tick_ifdef_type
                            self.tick_curr_served = 0

                        self.tick_decisions.append(self.tick_curr_decision)
                        self.tick_types.append(self.tick_curr_type)
                        self.tick_served.append(self.tick_curr_served)

                    self.dbg("# TICK: Pushing current construct " + self.tick_curr_type)
                    if len(self.tick_decisions) > 0:
                        self.dbg(self.tick_types)
                        self.dbg(self.tick_decisions)
                        self.dbg(self.tick_served)
            else:
                self.tick_curr_decision = 0

        self.dbg("# TICK: DECISION: " + str(self.tick_curr_decision))

        return self.tick_curr_decision

    def sub_tick_ifdef_proc(self, sub_tick_ifdef_type, sub_tick_ifdef_str):
        """
        Function to process 'ifdef and it returns current ifdef status to skip
        the code or parse it
        """
        sub_last_tick_decision = 0
        sub_popped_tick_decision = 0
        sub_popped_tick_type = ""
        sub_popped_tick_served = 0

        if sub_tick_ifdef_type == "ifdef":
            sub_tick_level = len(self.sub_tick_decisions)
            self.dbg(
                "\n### TICK LEVEL: "
                + str(sub_tick_level)
                + ", "
                + sub_tick_ifdef_type
                + ", "
                + sub_tick_ifdef_str
                + ", "
                + str(self.sub_tick_ifdef_en)
            )
        else:
            sub_tick_level = len(self.sub_tick_decisions) - 1
            self.dbg(
                "\n### TICK LEVEL: "
                + str(sub_tick_level)
                + ", "
                + sub_tick_ifdef_type
                + ", "
                + sub_tick_ifdef_str
                + ", "
                + str(self.sub_tick_ifdef_en)
            )

        sub_tick_ifdef_str_regex = RE_TICK_IFDEF_STR.search(sub_tick_ifdef_str)

        if sub_tick_ifdef_type == "else":
            # Pop the last ifdef/elif of the same level
            if len(self.sub_tick_decisions) > 0:
                self.dbg(
                    "# TICK: Popping previous construct "
                    + sub_popped_tick_type
                    + " for else"
                )
                sub_popped_tick_decision = self.sub_tick_decisions.pop()
                sub_popped_tick_type = self.sub_tick_types.pop()
                sub_popped_tick_served = self.sub_tick_served.pop()
                self.dbg(
                    "  Type: "
                    + sub_popped_tick_type
                    + ",  Decision: "
                    + str(sub_popped_tick_decision)
                    + ",  Served: "
                    + str(sub_popped_tick_served)
                )

            if len(self.sub_tick_decisions) > 0:
                self.sub_last_tick_loc = len(self.sub_tick_decisions) - 1
                sub_last_tick_decision = self.sub_tick_decisions[self.sub_last_tick_loc]
            else:
                sub_last_tick_decision = 1

            # if the current tick ifdef/elif already served, then else will be disabled
            if self.sub_tick_curr_served == 1:
                self.sub_tick_curr_decision = 0
                self.sub_tick_decisions.append(0)
                self.sub_tick_types.append("else")
                self.sub_tick_served.append(1)
            else:
                if sub_last_tick_decision:
                    self.sub_tick_curr_decision = 1
                    self.sub_tick_decisions.append(1)
                    self.sub_tick_types.append("else")
                    self.sub_tick_served.append(1)
                else:
                    self.sub_tick_curr_decision = 0
                    self.sub_tick_decisions.append(0)
                    self.sub_tick_types.append("else")
                    self.sub_tick_served.append(1)

            self.dbg("# TICK: Pushing current construct else")
            if len(self.sub_tick_decisions) > 0:
                self.dbg(self.sub_tick_types)
                self.dbg(self.sub_tick_decisions)
                self.dbg(self.sub_tick_served)
        elif sub_tick_ifdef_type == "endif":
            if len(self.sub_tick_decisions) > 0:
                self.dbg(
                    "# TICK: Popping previous construct "
                    + sub_popped_tick_type
                    + " for endif"
                )
                sub_popped_tick_decision = self.sub_tick_decisions.pop()
                sub_popped_tick_type = self.sub_tick_types.pop()
                sub_popped_tick_served = self.sub_tick_served.pop()
                self.dbg(
                    "  Type: "
                    + sub_popped_tick_type
                    + ",  Decision: "
                    + str(sub_popped_tick_decision)
                    + ",  Served: "
                    + str(sub_popped_tick_served)
                )

                if len(self.sub_tick_decisions) > 0:
                    self.sub_last_tick_loc = len(self.sub_tick_decisions) - 1
                    self.sub_tick_curr_decision = self.sub_tick_decisions[
                        self.sub_last_tick_loc
                    ]
                    self.sub_tick_curr_type = self.sub_tick_types[
                        self.sub_last_tick_loc
                    ]
                    self.sub_tick_curr_served = self.sub_tick_served[
                        self.sub_last_tick_loc
                    ]
                else:
                    # Out of all the ifdef and hence its enabled
                    self.sub_tick_curr_decision = 1
                    self.sub_tick_curr_type = ""
                    self.sub_tick_curr_served = 0

            else:
                self.dbg(
                    "\nError: There is no pending `ifdef/`elif in the buffer, but reaching `endif at line "
                    + str(self.line_no)
                )
                print(
                    "\nError: There is no pending `ifdef/`elif in the buffer, but reaching `endif at line "
                    + str(self.line_no)
                )
                sys.exit(1)
        else:  # ifdef / ifndef / elif
            # for all other ifdef, ifndef, elif to process sub_tick_ifdef_str evaluation
            if len(self.sub_tick_decisions) > 0:
                self.sub_last_tick_loc = len(self.sub_tick_decisions) - 1
                sub_last_tick_decision = self.sub_tick_decisions[self.sub_last_tick_loc]
            else:
                sub_last_tick_decision = 1

            if (
                (sub_tick_ifdef_type == "elif" and self.sub_tick_curr_served == 0)
                or sub_tick_ifdef_type == "ifdef"
                or sub_tick_ifdef_type == "ifndef"
            ):
                # Need to pop previous elif or ifdef or ifndef for elif case
                if sub_tick_ifdef_type == "elif":
                    self.dbg(
                        "# TICK: Popping previous construct "
                        + sub_popped_tick_type
                        + " for elif"
                    )
                    sub_popped_tick_decision = self.sub_tick_decisions.pop()
                    sub_popped_tick_type = self.sub_tick_types.pop()
                    sub_popped_tick_served = self.sub_tick_served.pop()
                    self.dbg(
                        "  Type: "
                        + sub_popped_tick_type
                        + ",  Decision: "
                        + str(sub_popped_tick_decision)
                        + ",  Served: "
                        + str(sub_popped_tick_served)
                    )

                if sub_tick_ifdef_str_regex:  # Check if this is without expression
                    if (
                        sub_tick_ifdef_str in self.sub_tick_defines
                    ):  # define is present in the tick database
                        if sub_tick_ifdef_type == "ifndef":
                            self.sub_tick_curr_decision = 0
                            self.sub_tick_curr_type = sub_tick_ifdef_type
                            self.sub_tick_curr_served = 0
                        else:
                            # Current decision is set only if previous decision is 1
                            if sub_last_tick_decision:
                                self.sub_tick_curr_decision = 1
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1
                            else:
                                self.sub_tick_curr_decision = 0
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1

                        self.sub_tick_decisions.append(self.sub_tick_curr_decision)
                        self.sub_tick_types.append(self.sub_tick_curr_type)
                        self.sub_tick_served.append(self.sub_tick_curr_served)
                    else:
                        if sub_tick_ifdef_type == "ifndef":
                            if sub_last_tick_decision:
                                self.sub_tick_curr_decision = 1
                                self.sub_tick_curr_served = 1
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                            else:
                                self.sub_tick_curr_decision = 0
                                self.sub_tick_curr_served = 1
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                        else:
                            self.sub_tick_curr_decision = 0
                            self.sub_tick_curr_served = 0
                            self.sub_tick_curr_type = sub_tick_ifdef_type

                        self.sub_tick_decisions.append(self.sub_tick_curr_decision)
                        self.sub_tick_types.append(self.sub_tick_curr_type)
                        self.sub_tick_served.append(self.sub_tick_curr_served)

                    self.dbg(
                        "# TICK: Pushing current construct " + self.sub_tick_curr_type
                    )
                    if len(self.sub_tick_decisions) > 0:
                        self.dbg(self.sub_tick_types)
                        self.dbg(self.sub_tick_decisions)
                        self.dbg(self.sub_tick_served)
                else:
                    # If ifdef has an expression, then we need to get the result of expression
                    # TODO: Need to pass package
                    sub_ifdef_exp_val = self.tickdef_param_getval(
                        "SUB", sub_tick_ifdef_str, "", ""
                    )

                    if sub_tick_ifdef_type == "ifndef":
                        if sub_ifdef_exp_val:
                            self.sub_tick_curr_decision = 0
                            self.sub_tick_curr_type = sub_tick_ifdef_type
                            self.sub_tick_curr_served = 0
                        else:
                            if sub_last_tick_decision:
                                self.sub_tick_curr_decision = 1
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1
                            else:
                                self.sub_tick_curr_decision = 0
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1

                        self.sub_tick_decisions.append(self.sub_tick_curr_decision)
                        self.sub_tick_types.append(self.sub_tick_curr_type)
                        self.sub_tick_served.append(self.sub_tick_curr_served)
                    else:
                        if sub_ifdef_exp_val:
                            if sub_last_tick_decision:
                                self.sub_tick_curr_decision = 1
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1
                            else:
                                self.sub_tick_curr_decision = 0
                                self.sub_tick_curr_type = sub_tick_ifdef_type
                                self.sub_tick_curr_served = 1
                        else:
                            self.sub_tick_curr_decision = 0
                            self.sub_tick_curr_type = sub_tick_ifdef_type
                            self.sub_tick_curr_served = 0

                        self.sub_tick_decisions.append(self.sub_tick_curr_decision)
                        self.sub_tick_types.append(self.sub_tick_curr_type)
                        self.sub_tick_served.append(self.sub_tick_curr_served)

                    self.dbg(
                        "# TICK: Pushing current construct " + self.sub_tick_curr_type
                    )
                    if len(self.sub_tick_decisions) > 0:
                        self.dbg(self.sub_tick_types)
                        self.dbg(self.sub_tick_decisions)
                        self.dbg(self.sub_tick_served)
            else:
                self.sub_tick_curr_decision = 0

        self.dbg("# TICK: DECISION: " + str(self.sub_tick_curr_decision))

        return self.sub_tick_curr_decision

    def tick_def_proc(self, module_type, tick_def_in):
        """
        The following function parses the `define and updates the tick table with value and type.
        Type can be NUMBER, STRING, BITDEF
        """

        # Removing single line comment at the end of #define
        tick_def_in = re.sub(r"\s*\/\/.*", "", tick_def_in)

        # Removing multiple space to single and no space at the end
        tick_def_in = re.sub(r"\s+", " ", tick_def_in)
        tick_def_in = re.sub(r"\s*$", "", tick_def_in)

        tick_def_val_ret = []

        tick_def_regex = RE_TICK_DEF.search(tick_def_in)

        tick_def_wo_val_regex = RE_TICK_DEF_WO_VAL.search(tick_def_in)

        # If there is no values or expression for a define, it's value will be assigned as 1
        if tick_def_wo_val_regex:
            if module_type == "TOP":
                if tick_def_wo_val_regex.group(1) in self.tick_defines:
                    print(
                        "\nWarning: The following #define already defined\n"
                        + tick_def_wo_val_regex.group(0)
                    )
                else:
                    self.tick_defines[tick_def_wo_val_regex.group(1)] = {}

                self.tick_defines[tick_def_wo_val_regex.group(1)]["type"] = "NUMBER"
                self.tick_defines[tick_def_wo_val_regex.group(1)]["val"] = 1
                self.tick_defines[tick_def_wo_val_regex.group(1)]["exp"] = 1
                self.dbg(module_type + ":: `define " + tick_def_in)
                self.dbg(
                    "   TYPE: "
                    + self.tick_defines[tick_def_wo_val_regex.group(1)]["type"]
                    + " :: VALUE: "
                    + str(self.tick_defines[tick_def_wo_val_regex.group(1)]["val"])
                )
            else:
                if tick_def_wo_val_regex.group(1) in self.sub_tick_defines:
                    print(
                        "\nWarning: The following #define already defined\n"
                        + tick_def_wo_val_regex.group(0)
                    )
                else:
                    self.sub_tick_defines[tick_def_wo_val_regex.group(1)] = {}

                self.sub_tick_defines[tick_def_wo_val_regex.group(1)]["type"] = "NUMBER"
                self.sub_tick_defines[tick_def_wo_val_regex.group(1)]["val"] = 1
                self.sub_tick_defines[tick_def_wo_val_regex.group(1)]["exp"] = 1
                self.dbg(module_type + ":: `define " + tick_def_in)
                self.dbg(
                    "   TYPE: "
                    + self.sub_tick_defines[tick_def_wo_val_regex.group(1)]["type"]
                    + " :: VALUE: "
                    + str(self.sub_tick_defines[tick_def_wo_val_regex.group(1)]["val"])
                )
        else:
            if tick_def_regex:
                if module_type == "TOP":  # Top level defines
                    if tick_def_regex.group(1) in self.tick_defines:
                        print(
                            "\nWarning: The following #define already defined\n"
                            + tick_def_regex.group(0)
                        )
                    else:
                        self.tick_defines[tick_def_regex.group(1)] = {}

                    # TODO: Need to pass package
                    tick_def_val_ret = self.tickdef_param_getval(
                        module_type, tick_def_regex.group(2), "", ""
                    )
                    self.tick_defines[tick_def_regex.group(1)][
                        "type"
                    ] = tick_def_val_ret[0]

                    if tick_def_val_ret[0] == "STRING":
                        self.tick_defines[tick_def_regex.group(1)][
                            "val"
                        ] = tick_def_regex.group(2)
                    else:
                        self.tick_defines[tick_def_regex.group(1)][
                            "val"
                        ] = tick_def_val_ret[1]

                    self.tick_defines[tick_def_regex.group(1)][
                        "exp"
                    ] = tick_def_regex.group(2)

                    self.dbg(module_type + ":: `define " + tick_def_in)
                    self.dbg(
                        "   TYPE: "
                        + self.tick_defines[tick_def_regex.group(1)]["type"]
                        + " :: VALUE: "
                        + str(self.tick_defines[tick_def_regex.group(1)]["val"])
                    )
                else:  # Submodule level defines
                    if tick_def_regex.group(1) in self.sub_tick_defines:
                        print(
                            "\nWarning: The following #define already defined\n"
                            + tick_def_regex.group(0)
                        )
                    else:
                        self.sub_tick_defines[tick_def_regex.group(1)] = {}

                    # TODO: Need to pass package
                    tick_def_val_ret = self.tickdef_param_getval(
                        module_type, tick_def_regex.group(2), "", ""
                    )
                    self.sub_tick_defines[tick_def_regex.group(1)][
                        "type"
                    ] = tick_def_val_ret[0]

                    if tick_def_val_ret[0] == "STRING":
                        self.sub_tick_defines[tick_def_regex.group(1)][
                            "val"
                        ] = tick_def_regex.group(2)
                    else:
                        self.sub_tick_defines[tick_def_regex.group(1)][
                            "val"
                        ] = tick_def_val_ret[1]

                    self.sub_tick_defines[tick_def_regex.group(1)][
                        "exp"
                    ] = tick_def_regex.group(2)

                    self.dbg(module_type + ":: `define " + tick_def_in)
                    self.dbg(
                        "   TYPE: "
                        + self.sub_tick_defines[tick_def_regex.group(1)]["type"]
                        + " :: VALUE: "
                        + str(self.sub_tick_defines[tick_def_regex.group(1)]["val"])
                    )
            else:
                self.dbg("\nError: Unable to get value for `define\n")
                self.dbg(tick_def_in)
                print("\nError: Unable to get value for `define\n")
                print(tick_def_in)
                self.found_error = 1

        return

    def get_tick_defval(self, tick_def):
        """
        Function to get the value of a `define. This can be called in a embedded python script.
        """

        if tick_def in self.tick_defines:
            tick_defval = self.tick_defines[tick_def]["val"]
        else:
            self.dbg(
                "        Error: Unable to find the `define "
                + tick_def
                + " in line "
                + str(self.line_no)
                + "\n"
            )
            self.dbg(self.line)
            print(
                "        Error: Unable to find the `define "
                + tick_def
                + " in line "
                + str(self.line_no)
                + "\n"
            )
            print(self.line)
            sys.exit(1)

        return tick_defval

    def get_param(self, param):
        """
        Function to get the value of a verilog parameter. This can be called in a
        embedded python script.
        """

        if param in self.params:
            param_val = self.params[param]["val"]
        else:
            self.dbg(
                "        Error: Unable to find the parameter "
                + param
                + " in line "
                + str(self.line_no)
                + "\n"
            )
            self.dbg(self.line)
            print(
                "        Error: Unable to find the parameter "
                + param
                + " in line "
                + str(self.line_no)
                + "\n"
            )
            print(self.line)
            sys.exit(1)

        return param_val

    def replace_clog2(self, module_type, string_in):
        """
        Replaces $clog2(*) with result
        """

        # Relace $clog2(with # for detection
        string_in = re.sub(r"\$clog2\s*\(", "#", string_in)
        string_in = re.sub(r"clog2\s*\(", "#", string_in)

        bracket_count = 0
        gather_clog2_str = 0
        clog2_str = ""
        ret_string = ""
        string_in_array = []
        string_in_array = list(string_in)
        update_clog2_val = 0

        for char in string_in_array:
            if char == "#":
                clog2_str = ""
                bracket_count = 1
                gather_clog2_str = 1
                continue
            elif char == "(":
                if (
                    bracket_count != 0
                ):  # Wait for # for first increment of bracket_count
                    bracket_count = bracket_count + 1
            elif char == ")":
                if bracket_count == 1:  # End of clog2(*)
                    update_clog2_val = 1
                    clog2_val_array = self.tickdef_param_getval(
                        module_type, clog2_str, "", ""
                    )

                    if clog2_val_array[0] == "STRING":
                        print("\nWarning: Unable to calculate $clog2 value")
                        print("  " + string_in + "\n")
                        self.dbg("\nWarning: Unable to calculate $clog2 value")
                        self.dbg("  " + string_in + "\n")
                        clog2_val = ""
                    else:
                        clog2_val = self.clog2(clog2_val_array[1])

                    clog2_str = ""

                if (
                    bracket_count != 0
                ):  # Wait for # for first increment of bracket_count
                    bracket_count = bracket_count - 1

            # self.dbg('  # ' + char + ' :: ' + str(bracket_count) + ' :: ' + str(update_clog2_val) + ' :: ' + str(gather_clog2_str))

            if update_clog2_val:
                update_clog2_val = 0
                ret_string = ret_string + str(clog2_val)
                continue
            elif bracket_count != 0:
                if gather_clog2_str == 1:
                    clog2_str = clog2_str + char
                else:
                    ret_string = ret_string + char
                continue
            else:
                ret_string = ret_string + char

        ret_string = re.sub(r"\s+", " ", ret_string)
        # self.dbg("      #" + str(ret_string))

        return ret_string

    def get_dollar_bits_val(self, module_type, dollar_string, int_package, int_class):
        """
        Returns $bits value
        """

        dollar_bits_width = 0

        dollar_member_regex = RE_TYPEDEF_DOUBLE_COLON.search(dollar_string)
        dollar_member_regex_double = RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
            dollar_string
        )

        if dollar_member_regex_double:  # If a package name and class is associated
            int_package = dollar_member_regex_double.group(1)
            int_class = dollar_member_regex_double.group(2)
            dollar_member = dollar_member_regex_double.group(3)
        elif dollar_member_regex:  # If a package name is associated
            if module_type == "TOP":
                if dollar_member_regex.group(1) in list(self.classes):
                    # int_package = 'default'
                    int_class = dollar_member_regex.group(1)
                    dollar_member = dollar_member_regex.group(2)
                else:
                    int_package = dollar_member_regex.group(1)
                    int_class = "default"
                    dollar_member = dollar_member_regex.group(2)
            else:
                if dollar_member_regex.group(1) in list(self.sub_classes):
                    # int_package = 'default'
                    int_class = dollar_member_regex.group(1)
                    dollar_member = dollar_member_regex.group(2)
                else:
                    int_package = dollar_member_regex.group(1)
                    int_class = "default"
                    dollar_member = dollar_member_regex.group(2)
        else:
            dollar_member = dollar_string

        if module_type == "TOP":
            if int_package not in self.packages:
                self.load_import_or_include_file(
                    "TOP", "IMPORT_COMMANDLINE", int_package + ".sv"
                )

            if (
                dollar_member in self.typedef_structs[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.typedef_structs[int_package][int_class][
                    dollar_member
                ]["width"]
            elif (
                dollar_member in self.typedef_unions[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.typedef_unions[int_package][int_class][
                    dollar_member
                ]["width"]
            elif (
                dollar_member in self.typedef_logics[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.typedef_logics[int_package][int_class][
                    dollar_member
                ]["width"]
            elif dollar_member in self.regs:  # struct is present in the struct hash
                dollar_bits_width = self.regs[dollar_member]["uwidth"] + 1
            elif dollar_member in self.wires:  # struct is present in the struct hash
                dollar_bits_width = self.wires[dollar_member]["uwidth"] + 1
            elif dollar_member in self.signals:  # struct is present in the struct hash
                dollar_bits_width = self.signals[dollar_member]["uwidth"] + 1
            elif (
                dollar_member in self.typedef_bindings
            ):  # struct is present in the struct hash
                dollar_member_package = self.typedef_bindings[dollar_member]["package"]
                dollar_member_class = self.typedef_bindings[dollar_member]["class"]
                dollar_member_typedef = self.typedef_bindings[dollar_member]["typedef"]
                dollar_member_type = self.typedef_bindings[dollar_member]["type"]

                dollar_bits_width = 0

                if dollar_member_type == "STRUCTS":
                    dollar_bits_width = self.typedef_structs[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
                elif dollar_member_type == "UNIONS":
                    dollar_bits_width = self.typedef_unions[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
                elif dollar_member_type == "LOGICS":
                    dollar_bits_width = self.typedef_logics[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
            else:
                dollar_dot_regex = RE_DOT.search(dollar_member)

                if dollar_dot_regex:
                    dollar_dot_array = dollar_string.split(".")
                    dollar_dot_array_len = len(dollar_dot_array)

                    dollar_bits_width = ""
                    if dollar_dot_array[0] in self.typedef_bindings:
                        dot_package = self.typedef_bindings[dollar_dot_array[0]][
                            "package"
                        ]
                        dot_class = self.typedef_bindings[dollar_dot_array[0]]["class"]
                        dot_typedef = self.typedef_bindings[dollar_dot_array[0]][
                            "typedef"
                        ]
                        dot_type = self.typedef_bindings[dollar_dot_array[0]]["type"]
                        dollar_bits_width = 0

                        for jj in range(1, dollar_dot_array_len):
                            if dot_type == "STRUCTS" or dot_type == "STRUCT":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.typedef_structs[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.typedef_structs[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.typedef_structs[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]
                            elif dot_type == "UNIONS" or dot_type == "UNION":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.typedef_unions[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.typedef_unions[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.typedef_unions[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]
                            elif dot_type == "LOGICS" or dot_type == "LOGIC":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.typedef_logics[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.typedef_logics[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.typedef_logics[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]

                    # Checking if the dollar_bits_width is a valid number
                    dot_width_number_regex = RE_NUMBERS_ONLY.search(
                        str(dollar_bits_width)
                    )

                    if not dot_width_number_regex:
                        dollar_bits_width = 1
                        self.dbg(
                            "\nError: Unable to calculate $bits for the following\n"
                        )
                        self.dbg("  # " + dollar_string)
                        print("\nError: Unable to calculate $bits for the following\n")
                        print("  # " + dollar_string)
                        self.found_error = 1
                else:
                    dollar_bits_width = 1
                    self.dbg("\nError: Unable to calculate $bits for the following\n")
                    self.dbg("  # " + dollar_string)
                    print("\nError: Unable to calculate $bits for the following\n")
                    print("  # " + dollar_string)
                    self.found_error = 1
        else:
            if int_package not in self.sub_packages:
                self.load_import_or_include_file(
                    "SUB", "IMPORT_COMMANDLINE", int_package + ".sv"
                )

            if (
                dollar_member in self.sub_typedef_structs[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.sub_typedef_structs[int_package][int_class][
                    dollar_member
                ]["width"]
            elif (
                dollar_member in self.sub_typedef_unions[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.sub_typedef_unions[int_package][int_class][
                    dollar_member
                ]["width"]
            elif (
                dollar_member in self.sub_typedef_logics[int_package][int_class]
            ):  # struct is present in the struct hash
                dollar_bits_width = self.sub_typedef_logics[int_package][int_class][
                    dollar_member
                ]["width"]
            elif (
                dollar_member in self.sub_typedef_bindings
            ):  # struct is present in the struct hash
                dollar_member_package = self.sub_typedef_bindings[dollar_member][
                    "package"
                ]
                dollar_member_class = self.sub_typedef_bindings[dollar_member]["class"]
                dollar_member_typedef = self.sub_typedef_bindings[dollar_member][
                    "typedef"
                ]
                dollar_member_type = self.sub_typedef_bindings[dollar_member]["type"]

                dollar_bits_width = 0

                if dollar_member_type == "STRUCTS":
                    dollar_bits_width = self.sub_typedef_structs[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
                elif dollar_member_type == "UNIONS":
                    dollar_bits_width = self.sub_typedef_unions[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
                elif dollar_member_type == "LOGICS":
                    dollar_bits_width = self.sub_typedef_logics[dollar_member_package][
                        dollar_member_class
                    ][dollar_member_typedef]["width"]
            else:
                dollar_dot_regex = RE_DOT.search(dollar_member)

                if dollar_dot_regex:
                    dollar_dot_array = dollar_string.split(".")
                    dollar_dot_array_len = len(dollar_dot_array)

                    dollar_bits_width = ""
                    if dollar_dot_array[0] in self.sub_typedef_bindings:
                        dot_package = self.sub_typedef_bindings[dollar_dot_array[0]][
                            "package"
                        ]
                        dot_class = self.sub_typedef_bindings[dollar_dot_array[0]][
                            "class"
                        ]
                        dot_typedef = self.sub_typedef_bindings[dollar_dot_array[0]][
                            "typedef"
                        ]
                        dot_type = self.sub_typedef_bindings[dollar_dot_array[0]][
                            "type"
                        ]
                        dollar_bits_width = 0

                        for jj in range(1, dollar_dot_array_len):
                            if dot_type == "STRUCTS" or dot_type == "STRUCT":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.sub_typedef_structs[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.sub_typedef_structs[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.sub_typedef_structs[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]
                            elif dot_type == "UNIONS" or dot_type == "UNION":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.sub_typedef_unions[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.sub_typedef_unions[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.sub_typedef_unions[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]
                            elif dot_type == "LOGICS" or dot_type == "LOGIC":
                                if jj == (dollar_dot_array_len - 1):
                                    dollar_bits_width = self.sub_typedef_logics[
                                        dot_package
                                    ][dot_class][dot_typedef][dollar_dot_array[jj]][
                                        "width"
                                    ]
                                else:
                                    dot_type = self.sub_typedef_logics[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["type"]
                                    dot_typedef = self.sub_typedef_logics[dot_package][
                                        dot_class
                                    ][dot_typedef][dollar_dot_array[jj]]["struct"]

                    # Checking if the dollar_bits_width is a valid number
                    dot_width_number_regex = RE_NUMBERS_ONLY.search(
                        str(dollar_bits_width)
                    )

                    if not dot_width_number_regex:
                        dollar_bits_width = 1
                        self.dbg(
                            "\nError: Unable to calculate $bits for the following\n"
                        )
                        self.dbg("  # " + dollar_string)
                        print("\nError: Unable to calculate $bits for the following\n")
                        print("  # " + dollar_string)
                        self.found_error = 1
                else:
                    dollar_bits_width = 1
                    self.dbg("\nError: Unable to calculate $bits for the following\n")
                    self.dbg("  # " + dollar_string)
                    print("\nError: Unable to calculate $bits for the following\n")
                    print("  # " + dollar_string)
                    self.found_error = 1

        return dollar_bits_width

    def tickdef_param_getval(self, module_type, tick_def_exp, package, class_name):
        """
        Function to calculate value for a `define and return its type. Type can be numerical, string
        """

        tick_def_exp = re.sub(r"#", "::", tick_def_exp)
        # TODO: Need to handle multiple $bits
        # Looing for $bits usage to get the width of a logic or struct
        # 1 - anything before $bits
        # 2 - $bits(
        # 3 - Inside $bits(.*)
        # 4 -)
        # 5 -

        dollar_clog2_regex = RE_DOLLAR_CLOG2.search(tick_def_exp)
        clog2_regex = RE_CLOG2.search(tick_def_exp)
        dollar_bits_regex = None
        if "$bits(" in tick_def_exp:
            dollar_bits_regex = RE_DOLLAR_BITS_CHECK.search(tick_def_exp)

        if dollar_clog2_regex:
            tick_def_exp = self.replace_clog2(module_type, tick_def_exp)
        elif clog2_regex:
            tick_def_exp = self.replace_clog2(module_type, tick_def_exp)

        if class_name == "default" or class_name == "":
            int_class = "default"
        else:
            int_class = class_name

        if package == "":
            int_package = "default"
        else:
            int_package = package

        if dollar_bits_regex and module_type == "TOP":
            dollar_bits_width = self.get_dollar_bits_val(
                module_type, dollar_bits_regex.group(3), int_package, int_class
            )
            tick_def_exp = (
                dollar_bits_regex.group(1)
                + str(dollar_bits_width)
                + dollar_bits_regex.group(5)
            )

        tick_def_info = []
        tick_def_exp_split = self.split_on_word_boundary(tick_def_exp)
        next_is_tick_define = 0
        next_is_package_content = 0

        tick_eval_string = ""
        for tick_split in tick_def_exp_split:
            if tick_split.endswith("`"):
                tick_eval_string = tick_eval_string + tick_split[:-1]
                next_is_tick_define = 1
                continue
            elif tick_split in self.packages:
                next_is_package_content = 1
                continue
            else:
                if tick_split == "::":
                    continue
                elif next_is_package_content:
                    next_is_package_content = 0

                    if (
                        module_type == "TOP"
                    ):  # Checking for current module tick defines hash
                        if tick_split in self.params:
                            tick_eval_string = tick_eval_string + str(
                                self.params[tick_split]["val"]
                            )
                    else:
                        if tick_split in self.sub_params:
                            tick_eval_string = tick_eval_string + str(
                                self.sub_params[tick_split]["val"]
                            )
                elif next_is_tick_define:
                    if (
                        module_type == "TOP"
                    ):  # Checking for current module tick defines hash
                        if tick_split in self.tick_defines:
                            tick_eval_string = tick_eval_string + str(
                                self.tick_defines[tick_split]["val"]
                            )
                        else:
                            self.dbg(
                                "        Warning: Unable to find the `define "
                                + tick_split
                                + " in line "
                                + str(self.line_no)
                            )
                            print(
                                "        Warning: Unable to find the `define "
                                + tick_split
                                + " in line "
                                + str(self.line_no)
                            )
                            tick_eval_string = tick_eval_string + tick_split
                    else:  # Checking for submodule tick defines hash
                        if tick_split in self.sub_tick_defines:
                            tick_eval_string = tick_eval_string + str(
                                self.sub_tick_defines[tick_split]["val"]
                            )
                        else:
                            print(self.sub_tick_defines.keys())
                            self.dbg(
                                "        Warning: Unable to find the `define "
                                + tick_split
                                + " in line "
                                + str(self.line_no)
                            )
                            print(
                                "        Warning: Unable to find the `define "
                                + tick_split
                                + " in line "
                                + str(self.line_no)
                            )
                            tick_eval_string = tick_eval_string + tick_split

                    next_is_tick_define = 0
                else:
                    # Checkefor self.params used in the `define
                    if (
                        module_type == "TOP"
                    ):  # Checking for current module tick defines hash
                        if tick_split in self.params:
                            tick_eval_string = tick_eval_string + str(
                                self.params[tick_split]["val"]
                            )
                        elif tick_split in self.hash_defines:
                            tick_eval_string = tick_eval_string + str(
                                self.hash_defines[tick_split]["val"]
                            )
                        else:
                            tick_eval_string = tick_eval_string + tick_split
                    else:  # Checking for submodule tick defines hash
                        if tick_split in self.sub_params:
                            tick_eval_string = tick_eval_string + str(
                                self.sub_params[tick_split]["val"]
                            )
                        else:
                            tick_eval_string = tick_eval_string + tick_split

        tick_def_is_bitdef = RE_TICK_DEF_CHECK_BITDEF.search(tick_eval_string)

        # TODO: Need to support ternary param calcuations
        # localparam [31:0] MDW = (AW >= BW) ? AW+1 : BW+1 ;

        if tick_def_is_bitdef:
            bit_def_type = "BITDEF"
            bit_def_val = ""
            curr_bit_def_val = ""

            # Upper bit def eval
            try:
                curr_bit_def_val = int(eval(tick_def_is_bitdef.group(1)))
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                curr_bit_def_val = tick_def_is_bitdef.group(1)

            bit_def_val = curr_bit_def_val

            check_val = isinstance(curr_bit_def_val, int)

            if not check_val:
                bit_def_type = "STRING"

            # Lower bit def eval
            curr_bit_def_val = ""
            try:
                curr_bit_def_val = int(eval(tick_def_is_bitdef.group(2)))
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                curr_bit_def_val = tick_def_is_bitdef.group(2)

            bit_def_val = str(bit_def_val) + ":" + str(curr_bit_def_val)

            check_val = isinstance(curr_bit_def_val, int)

            if not check_val:
                bit_def_type = "STRING"

            tick_def_info.append(bit_def_type)

            if bit_def_type == "STRING":
                tick_def_info.append(tick_eval_string)
            else:
                tick_def_info.append(bit_def_val)
        else:
            try:
                tick_eval_string_val = eval(tick_eval_string)
            except (SyntaxError, NameError, TypeError, ZeroDivisionError):
                tick_eval_string_val = ""

            check_val = isinstance(tick_eval_string_val, int)

            if check_val:
                tick_def_info.append("NUMBER")
            else:
                check_val = isinstance(tick_eval_string_val, float)
                if check_val:
                    tick_def_info.append("NUMBER")
                    tick_eval_string_val = int(tick_eval_string_val)
                else:
                    tick_def_info.append("STRING")

            tick_def_info.append(tick_eval_string_val)

        return tick_def_info

    def split_on_word_boundary(self, string_in):
        """
        Function to split a string on a word boundary and return as an array
        """

        split_on_word_boundary = [
            item
            for item in map(str.strip, re.split(r"(\W+)", string_in))
            if len(item) > 0
        ]
        return split_on_word_boundary

    def find_in_files(self, filename):
        """
        Function to print a debug string in a debug dump file
        """

        for c_file in self.files:
            file_search_regex = filename + "$"
            RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
            search_file_regex = RE_SEARCH_FILE_REGEX.search(c_file)

            if search_file_regex:
                return c_file
        return

    def parse_verilog(self):
        """
        Function to parse verilog
        =======
        Step: 2
        =======
        Parse verilog or system verilog code
        Gather wire/reg/input/output information
        Gather registers list and width for each &Posedge
        """

        # Override the search regex
        re.search = self.time_re_search

        gather_till_semicolon = 0
        prev_line = ""
        prev_original_line = ""
        prev_line_no = ""
        inside_always_combo_block = 0
        inside_always_seq_block = 0
        always_sequential = 0
        look_for_always_begin = 0
        look_for_if_begin = 0
        append_next_line = 0
        block_comment = 0
        function_skip = 0
        translate_skip = 0
        task_skip = 0
        parsing_skip = 0
        skip_ifdef_parsing = 0
        generate_skip = 0
        generate_endmodule = 0
        look_for_instance_cmds = 0
        inside_generate = 0
        gather_manual_instance = 0
        manual_instance_line = ""
        parse_manual_instance = 0
        skip_semicolon_check = 0
        curr_construct = ""
        curr_for_construct = ""

        if self.verilog_define_files is not None:
            for c_verilog_define_file in self.verilog_define_files:
                self.load_import_or_include_file(
                    "TOP", "INCLUDE", c_verilog_define_file
                )

        if self.parser_on:
            line_no = 0
            original_line = ""
            self.tick_ifdef_en = 1

            if self.parsing_format == "verilog":
                print("  # Analysing expanded verilog file")
            else:
                print("  # Analysing expanded system verilog file")

            self.dbg(
                "\n################################################################################"
            )
            self.dbg("### Started parsing the expanded verilog/systemverilog file")
            self.dbg(
                "################################################################################"
            )
            for line in self.parse_lines:
                line_no = line_no + 1
                original_line = line
                self.line = line
                self.line_no = line_no
                self.original_line = original_line

                # Remove space in the end
                line = line.rstrip()

                # Stop verilog parsing when stub mode end finds GenDrive*
                if self.generate_stub:
                    gendrivez_verilog_regex = RE_GENDRIVEZ_VERILOG.search(line)
                    gendrive0_verilog_regex = RE_GENDRIVE0_VERILOG.search(line)
                    gendrive0andz_verilog_regex = RE_GENDRIVE0ANDZ_VERILOG.search(line)

                    if (
                        gendrivez_verilog_regex
                        or gendrive0_verilog_regex
                        or gendrive0andz_verilog_regex
                    ):
                        break

                # Skip parsing code between pragma translate_off and translate_on
                translate_off_regex = RE_TRANSLATE_OFF.search(line)
                translate_on_regex = RE_TRANSLATE_ON.search(line)

                if translate_off_regex:
                    translate_skip = 1
                    continue

                if translate_on_regex:
                    translate_skip = 0
                    continue

                if translate_skip:
                    continue

                # if the whole line is commented from the beginning
                single_comment_begin_start_regex = RE_SINGLE_COMMENT_BEGIN_START.search(
                    line
                )

                if single_comment_begin_start_regex:
                    continue

                connect_regex = RE_CONNECT.search(line)

                # Removing single line comment at the end of a line if current line is not &Connect
                if not connect_regex:
                    line = re.sub(r"\s*\/\/.*", "", line)

                # Removing block comment in a single line
                line = remove_single_line_comment(line)

                gen_line = line

                # Removing multiple space to single and no space at the end
                line = re.sub(r"\s+", " ", line)
                line = re.sub(r"\s*$", "", line)

                block_comment_begin_start_regex = RE_BLOCK_COMMENT_BEGIN_START.search(
                    line
                )
                block_comment_begin_regex = RE_BLOCK_COMMENT_BEGIN.search(line)
                block_comment_end_regex = RE_BLOCK_COMMENT_END.search(line)

                if block_comment_end_regex:
                    block_comment = 0
                    # If something after the */, we need to parse
                    if block_comment_end_regex.group(1) == "":
                        continue
                    else:
                        line = block_comment_end_regex.group(1)

                if block_comment:
                    continue

                if block_comment_begin_start_regex:
                    block_comment = 1
                    continue
                elif block_comment_begin_regex:
                    block_comment = 1

                ################################################################################
                # &ParserOff and &SkipEnd for parsing skip
                ################################################################################
                parser_off_regex = RE_PARSER_OFF.search(line)
                parser_on_regex = RE_PARSER_ON.search(line)
                begin_skip_regex = RE_SKIP_BEGIN.search(line)
                end_skip_regex = RE_SKIP_END.search(line)

                if parser_off_regex or begin_skip_regex:
                    parsing_skip = 1
                    print("    - Turning Off verilog parser at line " + str(line_no))
                    continue
                elif parser_on_regex or end_skip_regex:
                    parsing_skip = 0
                    print("    - Turning On verilog parser at line " + str(line_no))
                    continue

                if parsing_skip:
                    continue

                ################################################################################
                # &SkipIfdefBegin and &SkipIfdefEnd for parsing skip
                ################################################################################
                skipifdefbegin_regex = RE_SKIP_IFDEF_BEGIN.search(line)
                skipifdefend_regex = RE_SKIP_IFDEF_END.search(line)

                if skipifdefbegin_regex:
                    skip_ifdef_parsing = 1
                    print("    - Skip parsing at line " + str(line_no))
                    continue
                elif skipifdefend_regex:
                    skip_ifdef_parsing = 0
                    print("    - End Skipping at line " + str(line_no))
                    continue

                ################################################################################
                # `ifdef/ifndef/elif/else/endif processing
                ################################################################################
                tick_ifdef_regex = RE_TICK_IFDEF.search(line)
                tick_ifndef_regex = RE_TICK_IFNDEF.search(line)
                tick_elif_regex = RE_TICK_ELSIF.search(line)
                tick_else_regex = RE_TICK_ELSE.search(line)
                tick_endif_regex = RE_TICK_ENDIF.search(line)

                if tick_ifdef_regex:
                    self.tick_ifdef_en = self.tick_ifdef_proc(
                        "ifdef", tick_ifdef_regex.group(1)
                    )
                    continue
                elif tick_ifndef_regex:
                    self.tick_ifdef_en = self.tick_ifdef_proc(
                        "ifndef", tick_ifndef_regex.group(1)
                    )
                    continue
                elif tick_elif_regex:
                    self.tick_ifdef_en = self.tick_ifdef_proc(
                        "elif", tick_elif_regex.group(1)
                    )
                    continue
                elif tick_else_regex:
                    self.tick_ifdef_en = self.tick_ifdef_proc("else", "")
                    continue
                elif tick_endif_regex:
                    self.tick_ifdef_en = self.tick_ifdef_proc("endif", "")
                    continue

                if self.tick_ifdef_dis or skip_ifdef_parsing:
                    self.tick_ifdef_en = 1

                if not self.tick_ifdef_en:  # If tick disables the code
                    continue
                else:  # if tick_ifdef_en:
                    # Replace always @* to always (@*)
                    line = re.sub(r"^\s*always\s*@\s*\*", "always (@*)", line)

                    # convert "always_comb begin" to "always_comb (*) begin"
                    line = re.sub(r"always_comb\s+begin", "always_comb (*) begin", line)

                    # Gathering till it finds ;
                    if gather_till_semicolon or append_next_line:
                        if (
                            not append_next_line
                            and not skip_semicolon_check
                            and ANY_MONSTER_REGEX.search(line)
                        ):
                            print(
                                "\nError: Missing semicolon in line "
                                + str(prev_line_no)
                                + " in "
                                + self.temporary_file
                            )
                            print(prev_line + "\n")
                            self.found_error = 1

                        if gather_till_semicolon:
                            semicolon_regex = RE_SEMICOLON.search(line)

                            line = prev_line + " " + line

                            if not semicolon_regex:
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                continue
                            else:
                                gather_till_semicolon = 0
                        else:
                            line = prev_line + " " + line
                            append_next_line = 0

                    # Skipping empty lines
                    empty_line_regex = RE_EMPTY_LINE.search(line)

                    if empty_line_regex:
                        continue

                    self.dbg("\n" + str(line_no) + " :::" + line + ":::")

                    ################################################################################
                    # Assertions Skip
                    ################################################################################
                    assert_property_regex = RE_ASSERT_PROPERTY.search(line)

                    if assert_property_regex:
                        continue

                    ################################################################################
                    # Function Skip
                    ################################################################################
                    function_regex = RE_FUNCTION.search(line)
                    endfunction_regex = RE_ENDFUNCTION.search(line)

                    if function_regex:
                        function_skip = 1
                        self.dbg("\n### Skipping function at " + str(line_no))
                        continue
                    elif endfunction_regex:
                        function_skip = 0
                        continue

                    if function_skip:
                        continue

                    ################################################################################
                    # Task Skip
                    ################################################################################
                    task_regex = RE_TASK.search(line)
                    endtask_regex = RE_ENDTASK.search(line)

                    if task_skip:
                        if endtask_regex:
                            task_skip = 0

                        continue
                    else:
                        if task_regex:
                            task_skip = 1
                            self.dbg("\n### Skipping task at " + str(line_no))
                            continue

                    ################################################################################
                    # Pkg2Assign Code Generation
                    ################################################################################
                    pkg2assign_regex = RE_PKG2ASSIGN.search(line)
                    assign2pkg_regex = RE_ASSIGN2PKG.search(line)

                    if pkg2assign_regex or assign2pkg_regex:
                        if pkg2assign_regex:
                            p2a_prefix = pkg2assign_regex.group(2)
                            p2a_pkgmember = pkg2assign_regex.group(3)
                            p2a_bus = pkg2assign_regex.group(4)
                            self.dbg(
                                "### PKG2ASSIGN2PKG :: "
                                + p2a_prefix
                                + " # "
                                + p2a_pkgmember
                                + " # "
                                + p2a_bus
                                + " #"
                            )
                        else:
                            p2a_prefix = assign2pkg_regex.group(2)
                            p2a_pkgmember = assign2pkg_regex.group(3)
                            p2a_bus = assign2pkg_regex.group(4)
                            self.dbg(
                                "### ASSIGN2PKG :: "
                                + p2a_prefix
                                + " # "
                                + p2a_pkgmember
                                + " # "
                                + p2a_bus
                                + " #"
                            )

                        typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                            p2a_pkgmember
                        )
                        typedef_ref_regex_double = (
                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(p2a_pkgmember)
                        )

                        found_in_typedef = ""

                        if typedef_ref_regex_double:  # If a package name is associated
                            typedef_package = typedef_ref_regex_double.group(1)
                            typedef_class = typedef_ref_regex_double.group(2)
                            typedef_name = typedef_ref_regex_double.group(3)
                        elif typedef_ref_regex:  # If a package name is associated
                            if typedef_ref_regex.group(1) in list(self.classes):
                                typedef_package = "default"
                                typedef_class = typedef_ref_regex.group(1)
                                typedef_name = typedef_ref_regex.group(2)
                            else:
                                typedef_package = typedef_ref_regex.group(1)
                                typedef_class = "default"
                                typedef_name = typedef_ref_regex.group(2)
                        else:  # No package referred
                            typedef_package = "default"
                            typedef_class = "default"
                            typedef_name = temp_line_split_list[0]

                        # Loading the package if its not loaded already
                        if typedef_package not in self.packages:
                            self.load_import_or_include_file(
                                "TOP", "IMPORT_COMMANDLINE", typedef_package + ".sv"
                            )

                        if (
                            typedef_name
                            in self.typedef_logics[typedef_package][typedef_class]
                        ):
                            found_in_typedef = "LOGICS"
                            # print('### LOGICS ###',self.typedef_logics[typedef_package][typedef_class][typedef_name])
                            pass
                        elif (
                            typedef_name
                            in self.typedef_structs[typedef_package][typedef_class]
                        ):
                            found_in_typedef = "STRUCTS"
                            gen_lines = []

                            for c_member in self.typedef_structs[typedef_package][
                                typedef_class
                            ][typedef_name].keys():
                                reserved_regex = RE_RESERVED.search(c_member)

                                if (
                                    c_member != "struct"
                                    and c_member != "width"
                                    and not reserved_regex
                                ):
                                    if (
                                        self.typedef_structs[typedef_package][
                                            typedef_class
                                        ][typedef_name][c_member]["uwidth"]
                                        == 0
                                    ):
                                        if pkg2assign_regex:
                                            assign_statment = (
                                                "assign "
                                                + p2a_prefix
                                                + c_member
                                                + " = "
                                                + p2a_bus
                                                + "."
                                                + c_member
                                                + ";"
                                            )
                                        else:
                                            assign_statment = (
                                                "assign "
                                                + p2a_bus
                                                + "."
                                                + c_member
                                                + " = "
                                                + p2a_prefix
                                                + c_member
                                                + ";"
                                            )
                                    else:
                                        member_uwidth = (
                                            int(
                                                self.typedef_structs[typedef_package][
                                                    typedef_class
                                                ][typedef_name][c_member]["width"]
                                            )
                                            - 1
                                        )

                                        if pkg2assign_regex:
                                            assign_statment = (
                                                "assign "
                                                + p2a_prefix
                                                + c_member
                                                + "["
                                                + str(member_uwidth)
                                                + ":0] = "
                                                + p2a_bus
                                                + "."
                                                + c_member
                                                + ";"
                                            )
                                        else:
                                            assign_statment = (
                                                "assign "
                                                + p2a_bus
                                                + "."
                                                + c_member
                                                + " = "
                                                + p2a_prefix
                                                + c_member
                                                + "["
                                                + str(member_uwidth)
                                                + ":0];"
                                            )

                                    gen_lines.append(assign_statment)

                            self.parse_lines[line_no:line_no] = gen_lines
                            if pkg2assign_regex:
                                self.pkg2assign_info[self.pkg2assign_index] = []
                                self.pkg2assign_info[self.pkg2assign_index] = gen_lines
                                self.pkg2assign_index = self.pkg2assign_index + 1
                            else:
                                self.assign2pkg_info[self.assign2pkg_index] = []
                                self.assign2pkg_info[self.assign2pkg_index] = gen_lines
                                self.assign2pkg_index = self.assign2pkg_index + 1
                        elif (
                            typedef_name
                            in self.typedef_unions[typedef_package][typedef_class]
                        ):
                            # print('### UNIONS ###',self.typedef_unions[typedef_package][typedef_class][typedef_name])
                            found_in_typedef = "UNIONS"

                    ################################################################################
                    # Generate Skip & Parsing
                    ################################################################################
                    generate_regex = RE_GENERATE.search(line)
                    endgenerate_regex = RE_ENDGENERATE.search(line)
                    for_regex = RE_GENERATE_FOR.search(line)
                    for_extract_regex = RE_GENERATE_FOR_EXTRACT.search(line)

                    if self.parse_generate:
                        ################################################################################
                        # Generate Parsing
                        ################################################################################
                        if generate_regex:
                            gen_lines = []
                            generate_begin_space = generate_regex.group(1)
                            for_loop_space = ""
                            gen_code_block = ""
                            for_line = ""
                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []

                            inside_generate = 1
                            c_genvars = []
                            self.generate_for_loops = {}
                            self.generate_for_loop_count = 0
                            generate_begin_count = 0
                            print(
                                "    - Expanding Generate Block at line " + str(line_no)
                            )
                            self.dbg(
                                "\n\n################################################################################"
                            )
                            self.dbg(
                                "### EXPANDING GENERATE BLOCK AT LINE " + str(line_no)
                            )
                            self.dbg(
                                "################################################################################"
                            )
                            self.dbg(line)
                            continue
                        elif endgenerate_regex:
                            # Resetting always block data since its hard to track without begin
                            self.dbg(
                                "### Getting out of generate block at line "
                                + str(line_no)
                            )
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []
                            inside_generate = 0
                            continue
                        elif inside_generate:
                            original_line = original_line.rstrip()
                            self.dbg(original_line)
                            begin_regex = RE_BEGIN_ONLY.search(line)
                            end_regex = RE_END_ONLY.search(line)

                            if begin_regex:
                                generate_begin_count = generate_begin_count + 1

                            if end_regex:
                                if (
                                    self.generate_for_loop_count
                                    in self.generate_for_loops
                                ):
                                    if (
                                        generate_begin_count
                                        == self.generate_for_loops[
                                            self.generate_for_loop_count
                                        ]["begincount"]
                                    ):
                                        del self.generate_for_loops[
                                            self.generate_for_loop_count
                                        ]
                                        self.generate_for_loop_count = (
                                            self.generate_for_loop_count - 1
                                        )
                                        for_loop_space = re.sub(
                                            r"  $", "", for_loop_space
                                        )
                                        generate_begin_count = generate_begin_count - 1
                                        continue

                                generate_begin_count = generate_begin_count - 1

                            ################################################################################
                            # for loop processing
                            ################################################################################
                            if for_regex:
                                if for_extract_regex:
                                    self.generate_for_loop_count = (
                                        self.generate_for_loop_count + 1
                                    )
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ] = {}

                                    start_exp = for_extract_regex.group(1)
                                    end_exp = for_extract_regex.group(2)
                                    step_exp = for_extract_regex.group(3)

                                    start_exp = re.sub(r"\s+", "", start_exp)
                                    end_exp = re.sub(r"\s+", "", end_exp)
                                    step_exp = re.sub(r"\s+", "", step_exp)

                                    # Start Expression parsing
                                    start_exp_equal_regex = RE_EQUAL_EXTRACT.search(
                                        start_exp
                                    )

                                    if start_exp_equal_regex:
                                        c_genvar = start_exp_equal_regex.group(1)
                                        start_val_ret = self.tickdef_param_getval(
                                            "TOP",
                                            start_exp_equal_regex.group(2),
                                            "",
                                            "",
                                        )
                                        if start_val_ret[0] == "STRING":
                                            print(
                                                "\nError: Unable to calculate the start value for the for loop in generate"
                                            )
                                            print("  # " + line)
                                            self.found_error = 1
                                        else:
                                            c_start_val = start_val_ret[1]

                                    # End Expression parsing
                                    end_exp_less_than_equal_regex = (
                                        RE_LESS_THAN_EQUAL.search(end_exp)
                                    )
                                    end_exp_less_than_regex = RE_LESS_THAN.search(
                                        end_exp
                                    )
                                    end_exp_greater_than_equal_regex = (
                                        RE_GREATER_THAN_EQUAL.search(end_exp)
                                    )
                                    end_exp_greater_than_regex = RE_GREATER_THAN.search(
                                        end_exp
                                    )

                                    # Step Expression parsing
                                    step_minus_minus_regex = RE_MINUS_MINUS.search(
                                        step_exp
                                    )
                                    step_plus_plus_regex = RE_PLUS_PLUS.search(step_exp)
                                    step_minus_number_regex = RE_MINUS_NUMBER.search(
                                        step_exp
                                    )
                                    step_plus_number_regex = RE_PLUS_NUMBER.search(
                                        step_exp
                                    )

                                    c_step_val = 1

                                    if step_minus_minus_regex:
                                        c_step_val = "1"
                                    elif step_plus_plus_regex:
                                        c_step_val = "1"
                                    elif step_minus_number_regex:
                                        c_step_val = step_minus_number_regex.group(3)
                                    elif step_plus_number_regex:
                                        c_step_val = step_plus_number_regex.group(3)

                                    if end_exp_less_than_equal_regex:
                                        c_end_val = end_exp_less_than_equal_regex.group(
                                            2
                                        )
                                        # end_val_ret = self.tickdef_param_getval('TOP', end_exp_less_than_equal_regex.group(2), '', '')

                                        # if end_val_ret[0] == 'STRING':
                                        # print('\nError: Unable to calculate the end value for the for loop in generate')
                                        # print('  # ' + line)
                                        # self.found_error = 1
                                        # else:
                                        # c_end_val = end_val_ret[1] + int(c_step_val)
                                    elif end_exp_less_than_regex:
                                        c_end_val = (
                                            end_exp_less_than_regex.group(2)
                                            + "-"
                                            + str(c_step_val)
                                        )
                                        # end_val_ret = self.tickdef_param_getval('TOP', end_exp_less_than_regex.group(2), '', '')

                                        # if end_val_ret[0] == 'STRING':
                                        # print('\n#Error: Unable to calculate the end value for the for loop in generate')
                                        # print('  # ' + line)
                                        # self.found_error = 1
                                        # else:
                                        # c_end_val = end_val_ret[1]
                                    elif end_exp_greater_than_equal_regex:
                                        c_end_val = (
                                            end_exp_greater_than_equal_regex.group(2)
                                        )
                                        # end_val_ret = self.tickdef_param_getval('TOP', end_exp_greater_than_equal_regex.group(2), '', '')

                                        # if end_val_ret[0] == 'STRING':
                                        # print('\nError: Unable to calculate the end value for the for loop in generate')
                                        # print('  # ' + line)
                                        # self.found_error = 1
                                        # else:
                                        # c_end_val = end_val_ret[1] + int(c_step_val)
                                    elif end_exp_greater_than_regex:
                                        c_end_val = (
                                            end_exp_greater_than_regex.group(2)
                                            + "+"
                                            + str(c_step_val)
                                        )
                                        # end_val_ret = self.tickdef_param_getval('TOP', end_exp_greater_than_regex.group(2), '', '')

                                        # if end_val_ret[0] == 'STRING':
                                        # print('\nError: Unable to calculate the end value for the for loop in generate')
                                        # print('  # ' + line)
                                        # self.found_error = 1
                                        # else:
                                        # c_end_val = end_val_ret[1]

                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["orig"] = line
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["genvar"] = c_genvar
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["start_val"] = c_start_val
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["end_val"] = c_end_val
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["step_val"] = c_step_val
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["count"] = self.generate_for_loop_count
                                    self.generate_for_loops[
                                        self.generate_for_loop_count
                                    ]["begincount"] = generate_begin_count

                                    gen_code_block += (
                                        for_loop_space
                                        + "for "
                                        + c_genvar
                                        + " in range("
                                        + str(c_start_val)
                                        + ","
                                        + str(c_end_val)
                                        + ","
                                        + str(c_step_val)
                                        + "):\n"
                                    )
                                    for_loop_space = for_loop_space + "  "
                                    continue
                            else:
                                pass

                            if self.generate_for_loop_count > 0:
                                for c_for_idx in self.generate_for_loops.keys():
                                    search_var = (
                                        "\\b"
                                        + self.generate_for_loops[c_for_idx]["genvar"]
                                        + "\\b"
                                    )
                                    replace_var = (
                                        str(
                                            self.generate_for_loops[c_for_idx][
                                                "end_val"
                                            ]
                                        )
                                        + ":"
                                        + str(
                                            self.generate_for_loops[c_for_idx][
                                                "start_val"
                                            ]
                                        )
                                    )
                                    line = re.sub(search_var, replace_var, line)

                                self.dbg(
                                    "### GENERATE UPDATED :: "
                                    + str(line_no)
                                    + " ::: "
                                    + line
                                    + ":::"
                                )

                    else:  # if parse_generate:
                        ################################################################################
                        # Generate Skip
                        ################################################################################
                        generate_regex = RE_GENERATE.search(line)
                        endgenerate_regex = RE_ENDGENERATE.search(line)

                        if generate_regex:
                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []

                            generate_skip = 1
                            self.dbg(
                                "\n### Skipping generate block at "
                                + str(line_no)
                                + "\n"
                            )
                            continue
                        elif endgenerate_regex:
                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []

                            generate_skip = 0
                            continue

                        if generate_skip:
                            continue

                    semicolon_regex = RE_SEMICOLON.search(line)

                    ################################################################################
                    # genvar processing
                    ################################################################################
                    genvar_regex = RE_GENVAR.search(line)
                    genvar_extract_regex = RE_GENVAR_EXTRACT.search(line)

                    if genvar_regex:
                        if semicolon_regex:
                            gather_till_semicolon = 0

                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []

                            if genvar_extract_regex:
                                genvar_line = genvar_extract_regex.group(1)
                                genvar_line = re.sub(r"\s+", "", genvar_line)
                                genvar_list = genvar_line.split(",")
                                for genvar in genvar_list:
                                    self.genvars.append(genvar)
                                    self.dbg("# Storing genvar " + genvar)

                            continue
                        else:
                            gather_till_semicolon = 1
                            continue

                    ################################################################################
                    # integer processing
                    ################################################################################
                    int_regex = RE_INT.search(line)
                    int_extract_regex = RE_INT_EXTRACT.search(line)
                    integer_regex = RE_INTEGER.search(line)
                    integer_extract_regex = RE_INTEGER_EXTRACT.search(line)

                    if integer_regex or int_regex:
                        if semicolon_regex:
                            gather_till_semicolon = 0

                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []

                            if int_extract_regex:
                                integer_line = int_extract_regex.group(1)

                            if integer_extract_regex:
                                integer_line = integer_extract_regex.group(1)

                            if int_extract_regex or integer_extract_regex:
                                integer_line = re.sub(r"\s+", "", integer_line)
                                integer_list = integer_line.split(",")
                                for integer in integer_list:
                                    self.integers.append(integer)
                                    self.dbg("# Storing integer variable " + integer)

                            continue
                        else:
                            gather_till_semicolon = 1
                            continue

                    ################################################################################
                    # `define processing
                    ################################################################################
                    tick_define_regex = RE_TICK_DEFINE.search(line)

                    if tick_define_regex:
                        tick_def_exp = tick_define_regex.group(1)
                        tick_def_exp = re.sub(r"\s*\(", " (", tick_def_exp, 1)
                        line = re.sub(r"\s*\(", " (", line, 1)
                        original_line = re.sub(r"\s*\(", " (", original_line, 1)

                        self.tick_def_proc("TOP", tick_def_exp)
                        continue

                    ################################################################################
                    # `undef processing
                    ################################################################################
                    tick_undef_regex = RE_TICK_UNDEF.search(line)

                    if tick_undef_regex:
                        self.dbg(line)
                        if tick_undef_regex.group(1) not in self.tick_defines:
                            print(
                                "\nWarning: Unable to find #define to undef\n"
                                + tick_undef_regex.group(0)
                                + "\n"
                            )
                        else:
                            del self.tick_defines[tick_undef_regex.group(1)]
                            self.dbg(
                                "  # Removed #define "
                                + tick_undef_regex.group(1)
                                + " for undef"
                            )

                        continue

                    ################################################################################
                    # typedef enum logic extraction
                    ################################################################################
                    enum_regex = RE_TYPEDEF_ENUM.search(line)

                    if enum_regex:
                        if semicolon_regex:  # Complete param ended with ;
                            line = re.sub(r"\s+", " ", line)
                            enum_more_regex = RE_TYPEDEF_ENUM_EXTRACT.search(line)

                            if enum_more_regex:
                                gather_till_semicolon = 0
                                self.enums_proc(
                                    "TOP", enum_more_regex.group(2) + ";", "default", ""
                                )

                                line = (
                                    enum_more_regex.group(1)
                                    + " "
                                    + enum_more_regex.group(3)
                                )

                                line = re.sub(r"\s*logic\s+", "", line)
                                self.parse_reg_wire_logic(
                                    "TOP",
                                    "TYPEDEF",
                                    "logic",
                                    line,
                                    self.package_name,
                                    self.class_name,
                                )
                            else:
                                self.dbg(
                                    "\nError: Unable to extract enums from the following"
                                )
                                self.dbg(line)
                                print(
                                    "\nError: Unable to extract enums from the following"
                                )
                                print(line)
                                self.found_error = 1

                            prev_line = ""
                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1

                    ################################################################################
                    # typedef logic extraction
                    ################################################################################
                    typedef_logic_regex = RE_TYPEDEF_LOGIC.search(line)

                    if typedef_logic_regex:
                        if semicolon_regex:  # Complete param ended with ;
                            gather_till_semicolon = 0
                            line = re.sub(r"\s+", " ", line)
                            self.dbg("\n::: " + line + " :::")
                            line = typedef_logic_regex.group(1)

                            self.parse_reg_wire_logic(
                                "TOP", "TYPEDEF", "logic", line, "default", ""
                            )
                        else:  # Multi line param
                            gather_till_semicolon = 1

                    ################################################################################
                    # typedef struct extraction
                    ################################################################################
                    typedef_struct_check_regex = RE_TYPEDEF_STRUCT_CHECK.search(line)
                    typedef_struct_nospace_regex = RE_TYPEDEF_STRUCT_NOSPACE.search(
                        line
                    )
                    typedef_closing_brace_regex = RE_CLOSING_BRACE.search(line)

                    if typedef_struct_check_regex or typedef_struct_nospace_regex:
                        if typedef_closing_brace_regex:  # Complete param ended with ;
                            skip_semicolon_check = 0
                            gather_till_semicolon = 0
                            line = re.sub(r"\s+", " ", line)
                            self.parse_struct_union(
                                "STRUCT", "TOP", line, "default", "default"
                            )
                            continue
                        else:  # Multi line param
                            skip_semicolon_check = 1
                            gather_till_semicolon = 1

                    ################################################################################
                    # typedef union extraction
                    ################################################################################
                    typedef_union_check_regex = RE_TYPEDEF_UNION_CHECK.search(line)
                    typedef_union_nospace_regex = RE_TYPEDEF_UNION_NOSPACE.search(line)
                    typedef_closing_brace_regex = RE_CLOSING_BRACE.search(line)

                    if typedef_union_check_regex or typedef_union_nospace_regex:
                        if typedef_closing_brace_regex:  # Complete param ended with ;
                            gather_till_semicolon = 0
                            skip_semicolon_check = 0
                            line = re.sub(r"\s+", " ", line)
                            self.parse_struct_union(
                                "UNION", "TOP", line, "default", "default"
                            )
                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1
                            skip_semicolon_check = 1

                    ################################################################################
                    # package parsing
                    ################################################################################
                    package_regex = RE_PACKAGE.search(line)

                    if package_regex:
                        self.package_name = package_regex.group(1)
                        self.dbg("### Parsing Package: " + self.package_name)
                        print("### Parsing Package: " + self.package_name)
                        self.packages.append(self.package_name)

                        self.package_name = "default"

                        if self.package_name not in self.typedef_enums:
                            self.typedef_enums[self.package_name] = {}
                            self.typedef_enums[self.package_name]["default"] = {}

                        if self.package_name not in self.typedef_logics:
                            self.typedef_logics[self.package_name] = {}
                            self.typedef_logics[self.package_name]["default"] = {}

                        if self.package_name not in self.typedef_structs:
                            self.typedef_structs[self.package_name] = {}
                            self.typedef_structs[self.package_name]["default"] = {}

                        if self.package_name not in self.typedef_unions:
                            self.typedef_unions[self.package_name] = {}
                            self.typedef_unions[self.package_name]["default"] = {}

                    ################################################################################
                    # class and endclass
                    ################################################################################
                    virtual_class_regex = RE_VIRTUAL_CLASS.search(line)
                    class_regex = RE_CLASS.search(line)
                    endclass_regex = RE_ENDCLASS.search(line)

                    if virtual_class_regex:
                        self.class_name = virtual_class_regex.group(1)
                        self.classes.append(self.class_name)
                    elif class_regex:
                        self.class_name = class_regex.group(1)
                        self.classes.append(self.class_name)
                    elif endclass_regex:
                        self.class_name = ""

                    if virtual_class_regex or class_regex:
                        if self.class_name not in self.typedef_enums[self.package_name]:
                            self.typedef_enums[self.package_name][self.class_name] = {}

                        if (
                            self.class_name
                            not in self.typedef_logics[self.package_name]
                        ):
                            self.typedef_logics[self.package_name][self.class_name] = {}

                        if (
                            self.class_name
                            not in self.typedef_structs[self.package_name]
                        ):
                            self.typedef_structs[self.package_name][
                                self.class_name
                            ] = {}

                        if (
                            self.class_name
                            not in self.typedef_unions[self.package_name]
                        ):
                            self.typedef_unions[self.package_name][self.class_name] = {}

                    ################################################################################
                    # Detect typedef usages
                    ################################################################################
                    if (
                        self.parsing_format != "verilog"
                        and not inside_always_combo_block
                        and not inside_always_seq_block
                    ):
                        temp_line = re.sub(r"\s+", " ", line)
                        temp_line = re.sub(r"^\s*", "", temp_line)
                        temp_line = re.sub(r"\s*;\s*$", "", temp_line)

                        temp_line_split_list = temp_line.split(" ", 1)

                        typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                            temp_line_split_list[0]
                        )
                        typedef_ref_regex_double = (
                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                temp_line_split_list[0]
                            )
                        )

                        found_in_typedef = ""

                        if typedef_ref_regex_double:  # If a package name is associated
                            typedef_package = typedef_ref_regex_double.group(1)
                            typedef_class = typedef_ref_regex_double.group(2)
                            typedef_name = typedef_ref_regex_double.group(3)
                        elif typedef_ref_regex:  # If a package name is associated
                            if typedef_ref_regex.group(1) in list(self.classes):
                                typedef_package = "default"
                                typedef_class = typedef_ref_regex.group(1)
                                typedef_name = typedef_ref_regex.group(2)
                            else:
                                typedef_package = typedef_ref_regex.group(1)
                                typedef_class = "default"
                                typedef_name = typedef_ref_regex.group(2)
                        else:  # No package referred
                            typedef_package = "default"
                            typedef_class = "default"
                            typedef_name = temp_line_split_list[0]

                        if typedef_package not in self.packages:
                            self.load_import_or_include_file(
                                "TOP", "IMPORT_COMMANDLINE", typedef_package + ".sv"
                            )

                        if (
                            typedef_name
                            in self.typedef_logics[typedef_package][typedef_class]
                        ):
                            found_in_typedef = "LOGICS"
                        elif (
                            typedef_name
                            in self.typedef_structs[typedef_package][typedef_class]
                        ):
                            found_in_typedef = "STRUCTS"
                        elif (
                            typedef_name
                            in self.typedef_unions[typedef_package][typedef_class]
                        ):
                            found_in_typedef = "UNIONS"

                        if found_in_typedef != "":
                            if semicolon_regex:  # Complete param ended with ;
                                gather_till_semicolon = 0
                                typedef_equal_regex = RE_EQUAL_EXTRACT_SPACE.search(
                                    temp_line
                                )

                                if typedef_equal_regex:
                                    temp_line = typedef_equal_regex.group(1)
                                    temp_line = re.sub(r"\s+$", "", temp_line)
                                    temp_line_split_list = temp_line.split(" ", 1)

                                self.binding_typedef("TOP", "MANUAL", temp_line)

                                bitdef_begin_regex = RE_SQBRCT_BEGIN.search(
                                    temp_line_split_list[1]
                                )

                                # Remove packed bitdef after typedef
                                if bitdef_begin_regex:
                                    self.update_typedef_regs(
                                        "logic", "MANUAL", bitdef_begin_regex.group(2)
                                    )
                                else:
                                    self.update_typedef_regs(
                                        "logic", "MANUAL", temp_line_split_list[1]
                                    )

                                if typedef_equal_regex:
                                    self.parse_assignments(
                                        "wiredassign",
                                        temp_line_split_list[1]
                                        + " = "
                                        + typedef_equal_regex.group(2),
                                    )

                                continue
                            else:
                                gather_till_semicolon = 1

                    ################################################################################
                    # Load any parameters with &Module
                    ################################################################################
                    module_space_regex = RE_MODULE_SPACE.search(line)
                    module_def_space_regex = RE_MODULE_DEF_SPACE.search(line)
                    module_params_regex = RE_MODULE_PARAMS.search(line)
                    semicolon_regex = RE_SEMICOLON.search(line)

                    if module_space_regex:
                        begin_space = ""

                        if semicolon_regex:
                            if module_params_regex:
                                self.module_param_line = module_params_regex.group(2)

                                # TODO: May have to pass package name
                                self.param_proc("TOP", self.module_param_line, "", "")
                                gather_till_semicolon = 0
                        else:
                            gather_till_semicolon = 1
                            prev_line = line
                            prev_original_line = original_line
                            prev_line_no = line_no
                            continue

                    ################################################################################
                    # Load parameters and IOs from module spec
                    ################################################################################
                    if module_def_space_regex:
                        i_spec_flow = spec_flow(
                            self.interface_spec_files,
                            self.interface_def_files,
                            self.module_def_files,
                            self.module_name,
                            self.incl_dirs,
                            self.files,
                            self.debug,
                        )

                        i_spec_flow.get_module_definition()

                        self.module_info = i_spec_flow.module_info

                        # Check if any errors when running spec flow
                        if i_spec_flow.found_error:
                            self.found_error = 1

                        self.dbg(i_spec_flow.debug_info)

                        self.dbg(json.dumps(i_spec_flow.module_info, indent=2))

                        for c_param in i_spec_flow.module_info["params"]:
                            c_param = re.sub(r"\s+", " ", c_param)
                            self.param_proc("TOP", c_param, "", "")

                        for c_port in i_spec_flow.module_info["inputs"]:
                            c_port = re.sub(r"\s+", " ", c_port)
                            self.parse_ios("TOP", "SPEC", "input", c_port + ";")

                        for c_port in i_spec_flow.module_info["outputs"]:
                            c_port = re.sub(r"\s+", " ", c_port)
                            self.parse_ios("TOP", "SPEC", "output", c_port + ";")

                        for c_port in i_spec_flow.module_info["inouts"]:
                            c_port = re.sub(r"\s+", " ", c_port)
                            self.parse_ios("TOP", "SPEC", "inout", c_port + ";")

                        ################################################################################
                        # Loading the module dependencies with spec files list
                        ################################################################################
                        if self.gen_dependencies:
                            if self.interface_spec_files is not None:
                                for c_file in self.interface_spec_files:
                                    self.dependencies["spec_files"].append(
                                        {c_file: {"mtime": getmtime(c_file)}}
                                    )

                            if self.interface_def_files is not None:
                                for c_file in self.interface_def_files:
                                    self.dependencies["interface_files"].append(
                                        {c_file: {"mtime": getmtime(c_file)}}
                                    )

                            if self.module_def_files is not None:
                                for c_file in self.module_def_files:
                                    self.dependencies["module_files"].append(
                                        {c_file: {"mtime": getmtime(c_file)}}
                                    )

                    ################################################################################
                    # Manual module declaration parsing for incremental port updates
                    ################################################################################
                    module_regex = RE_MODULE_DECLARATION.search(line)

                    if module_regex:
                        # Removing &ports; from the manual module declaration if there is any
                        line = re.sub(r"&\s*[Pp][Oo][Rr][Tt][Ss]\s*[;]{0,1}", "", line)

                        # Perf improvement - check if ' import ' is there before even starting costly regex
                        if " import " in line:
                            module_import_semicolon_regex = (
                                RE_IMPORT_INMOD_SEMICOLON.search(line)
                            )
                            module_import_comma_regex = RE_IMPORT_INMOD_COMMA.search(
                                line
                            )

                            # If import present inside module declaration, then remove it and load packages
                            if module_import_comma_regex:
                                line = (
                                    module_import_comma_regex.group(1)
                                    + " import "
                                    + module_import_comma_regex.group(3)
                                )
                                import_file_name = (
                                    module_import_comma_regex.group(2) + ".sv"
                                )
                                import_package = module_import_comma_regex.group(2)

                                if import_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP", "IMPORT_EMBEDDED", import_file_name
                                    )
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )
                            elif module_import_semicolon_regex:
                                line = (
                                    module_import_semicolon_regex.group(1)
                                    + " "
                                    + module_import_semicolon_regex.group(3)
                                )
                                import_file_name = (
                                    module_import_semicolon_regex.group(2) + ".sv"
                                )
                                import_package = module_import_semicolon_regex.group(2)

                                if import_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP", "IMPORT_EMBEDDED", import_file_name
                                    )
                                else:
                                    self.dbg(
                                        "### Skip importing previously imported package "
                                        + import_package
                                    )

                        semicolon_regex = RE_SEMICOLON.search(line)

                        if semicolon_regex:  # Complete param ended with ;
                            self.module_found = 1
                            generate_endmodule = 1
                            gather_till_semicolon = 0

                            module_param = RE_MODULE_PARAM.search(line)
                            module_noparam = RE_MODULE_NOPARAM.search(line)

                            if module_param:
                                module_io_declaration = module_param.group(2)
                                ################################################################################
                                # Parameter parsing
                                ################################################################################
                                self.param_proc("TOP", module_param.group(1), "", "")
                            elif module_noparam:
                                module_io_declaration = module_noparam.group(2)
                                ################################################################################
                                # Parameter parsing
                                ################################################################################
                                self.param_proc("TOP", module_noparam.group(1), "", "")
                            else:
                                module_io_declaration = module_regex.group(2)

                            self.module_name = module_regex.group(1)
                            module_io_declaration = re.sub(
                                r";+", "", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"^\s*\(\s*", "", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"\s*\)\s*$", "", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"\s*,\s*", ",", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"\s+", " ", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"\s*$", "", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r"^\s*", "", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r",i", ";i", module_io_declaration
                            )
                            module_io_declaration = re.sub(
                                r",o", ";o", module_io_declaration
                            )

                            if module_io_declaration == "":
                                self.manual_ports = 0
                            else:
                                manual_io_array = module_io_declaration.split(";")

                                for manual_io in manual_io_array:
                                    self.manual_ports = 1
                                    manual_input_regex = RE_DECLARE_INPUT.search(
                                        manual_io
                                    )
                                    manual_output_regex = RE_DECLARE_OUTPUT.search(
                                        manual_io
                                    )

                                    if manual_input_regex:  # all other input
                                        self.parse_ios(
                                            "TOP",
                                            "MANUAL",
                                            "input",
                                            manual_input_regex.group(1),
                                        )
                                    elif manual_output_regex:  # all other input
                                        self.parse_ios(
                                            "TOP",
                                            "MANUAL",
                                            "output",
                                            manual_output_regex.group(1),
                                        )

                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1

                    ################################################################################
                    # Parameter parsing
                    ################################################################################
                    param_regex = RE_PARAM.search(line)
                    localparam_regex = RE_LOCALPARAM.search(line)

                    if param_regex or localparam_regex:
                        if semicolon_regex:  # Complete param ended with ;
                            # TODO: May have to pass package name
                            self.param_proc("TOP", line, "", "")
                            gather_till_semicolon = 0

                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []
                            prev_line = ""
                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1
                            prev_line = line
                            prev_original_line = original_line
                            prev_line_no = line_no
                            continue

                    ################################################################################
                    # `include processing
                    ################################################################################
                    tick_include_regex = RE_TICK_INCLUDE.search(line)

                    if tick_include_regex:
                        self.load_import_or_include_file(
                            "TOP", "INCLUDE", tick_include_regex.group(1)
                        )

                        # Resetting always block data since its hard to track without begin
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []
                        continue

                    ################################################################################
                    # imported package processing
                    ################################################################################
                    import_regex = RE_IMPORT.search(line)
                    import_with_colons_regex = RE_IMPORT_COLONS.search(line)

                    if import_regex:
                        import_file_name = import_regex.group(1) + ".sv"
                        import_package = import_regex.group(1)
                    elif import_with_colons_regex:
                        import_file_name = import_with_colons_regex.group(1) + ".sv"
                        import_package = import_with_colons_regex.group(1)

                    if import_regex or import_with_colons_regex:
                        if import_package not in self.packages:
                            self.load_import_or_include_file(
                                "TOP", "IMPORT_EMBEDDED", import_file_name
                            )
                        else:
                            self.dbg(
                                "### Skip importing previously imported package "
                                + import_package
                            )

                        # Resetting always block data since its hard to track without begin
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []
                        continue

                    ################################################################################
                    # &Posedge, &Negedge, &Clock, &SyncReset and &Asyncreset
                    ################################################################################
                    posedge_regex = RE_R_POSEDGE.search(line)
                    negedge_regex = RE_R_NEGEDGE.search(line)
                    endnegedge_regex = RE_R_ENDNEGEDGE.search(line)
                    endposgedge_regex = RE_R_ENDPOSEDGE.search(line)

                    if posedge_regex:
                        self.auto_reset_en = 1
                        self.auto_reset_data[self.auto_reset_index] = {}
                        continue

                    if negedge_regex:
                        self.auto_reset_en = 1
                        self.auto_reset_data[self.auto_reset_index] = {}
                        continue

                    if endnegedge_regex:
                        self.auto_reset_en = 0
                        self.auto_reset_index = self.auto_reset_index + 1
                        continue

                    if endposgedge_regex:
                        self.auto_reset_en = 0
                        self.auto_reset_index = self.auto_reset_index + 1
                        continue

                    ################################################################################
                    # &force commands
                    ################################################################################
                    force_regex = RE_FORCE.search(line)

                    if force_regex:
                        line = force_regex.group(1)

                        force_bind_regex = RE_FORCE_BIND.search(line)
                        force_width_regex = RE_FORCE_WIDTH.search(line)
                        force_internal_regex = RE_FORCE_INTERNAL.search(line)
                        force_input_regex = RE_DECLARE_INPUT.search(line)
                        force_output_regex = RE_DECLARE_OUTPUT.search(line)
                        force_others_regex = RE_FORCE_OTHERS.search(line)

                        if force_bind_regex:
                            self.binding_typedef(
                                "TOP", "FORCE", force_bind_regex.group(1)
                            )
                            temp_line = re.sub(r"\s+", " ", line)
                            temp_line = re.sub(r"^\s*", "", temp_line)
                            temp_line = re.sub(r"\s*;\s*$", "", temp_line)
                            temp_line = re.sub(r"\s*\[.*\]\s*", " ", temp_line)
                            temp_line_split_list = temp_line.split(" ")

                            self.update_typedef_regs(
                                "logic", "FORCE", "".join(temp_line_split_list[2:])
                            )
                        elif (
                            force_width_regex
                        ):  # Store all the width commands and apply that after parsing
                            self.force_widths.append(force_width_regex.group(1))
                        elif (
                            force_internal_regex
                        ):  # Store all the width commands and apply that after parsing
                            self.force_internals.append(force_internal_regex.group(1))
                        elif force_input_regex:  # all other input
                            temp_line = re.sub(r"\s+", " ", force_input_regex.group(1))
                            temp_line = re.sub(r"^\s*logic\s+", "", temp_line)
                            temp_line = re.sub(r"^\s*reg\s+", "", temp_line)
                            temp_line = re.sub(r"^\s*wire\s+", "", temp_line)
                            temp_line = re.sub(r";", "", temp_line)
                            temp_line_split_list = temp_line.split(" ")
                            io_double_colon_regex = (
                                RE_PORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                                    force_input_regex.group(1)
                                )
                            )
                            io_double_double_colon_regex = (
                                RE_PORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                    force_input_regex.group(1)
                                )
                            )

                            bind_package = "default"
                            bind_class = "default"

                            if io_double_double_colon_regex:
                                bind_package = io_double_double_colon_regex.group(1)
                                bind_class = io_double_double_colon_regex.group(2)
                                bind_typedef = io_double_double_colon_regex.group(3)

                                if bind_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP",
                                        "IMPORT_COMMANDLINE",
                                        bind_package + ".sv",
                                    )

                                self.binding_typedef(
                                    "TOP", "FORCE", force_input_regex.group(1)
                                )
                            elif io_double_colon_regex:
                                bind_package = io_double_colon_regex.group(1)
                                bind_typedef = io_double_colon_regex.group(2)

                                if bind_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP",
                                        "IMPORT_COMMANDLINE",
                                        bind_package + ".sv",
                                    )

                                self.binding_typedef(
                                    "TOP", "FORCE", force_input_regex.group(1)
                                )
                            else:
                                bind_typedef = temp_line_split_list[0]

                            self.parse_ios(
                                "TOP", "FORCE", "input", force_input_regex.group(1)
                            )
                        elif force_output_regex:  # all other output
                            temp_line = re.sub(r"\s+", " ", force_output_regex.group(1))
                            temp_line = re.sub(r"^\s*logic\s+", "", temp_line)
                            temp_line = re.sub(r"^\s*reg\s+", "", temp_line)
                            temp_line = re.sub(r"^\s*wire\s+", "", temp_line)
                            temp_line = re.sub(r";", "", temp_line)
                            temp_line_split_list = temp_line.split(" ")
                            io_double_colon_regex = (
                                RE_PORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                                    force_output_regex.group(1)
                                )
                            )
                            io_double_double_colon_regex = (
                                RE_PORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                    force_output_regex.group(1)
                                )
                            )

                            bind_package = "default"
                            bind_class = "default"

                            if io_double_double_colon_regex:
                                bind_package = io_double_double_colon_regex.group(1)
                                bind_class = io_double_double_colon_regex.group(2)
                                bind_typedef = io_double_double_colon_regex.group(3)

                                if bind_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP",
                                        "IMPORT_COMMANDLINE",
                                        bind_package + ".sv",
                                    )

                                self.binding_typedef(
                                    "TOP", "FORCE", force_output_regex.group(1)
                                )
                            elif io_double_colon_regex:
                                bind_package = io_double_colon_regex.group(1)
                                bind_typedef = io_double_colon_regex.group(2)

                                if bind_package not in self.packages:
                                    self.load_import_or_include_file(
                                        "TOP",
                                        "IMPORT_COMMANDLINE",
                                        bind_package + ".sv",
                                    )

                                self.binding_typedef(
                                    "TOP", "FORCE", force_output_regex.group(1)
                                )
                            else:
                                bind_typedef = temp_line_split_list[0]

                            self.parse_ios(
                                "TOP", "FORCE", "output", force_output_regex.group(1)
                            )
                        else:
                            self.parse_reg_wire_logic(
                                "TOP",
                                "FORCE",
                                force_others_regex.group(1),
                                force_others_regex.group(2),
                                "",
                                "",
                            )

                        # Resetting always block data since its hard to track without begin
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []

                        continue

                    ################################################################################
                    # Manual declarations
                    ################################################################################
                    manual_input_regex = RE_DECLARE_INPUT.search(line)
                    manual_output_regex = RE_DECLARE_OUTPUT.search(line)
                    manual_wire_regex = RE_DECLARE_WIRE.search(line)
                    manual_reg_regex = RE_DECLARE_REG.search(line)
                    manual_logic_regex = RE_DECLARE_LOGIC.search(line)
                    wired_assign_bitdef_regex = RE_WIRE_ASSIGNMENT_BITDEF.search(line)
                    wired_assign_regex = RE_WIRE_ASSIGNMENT.search(line)

                    if (
                        manual_input_regex
                        or manual_output_regex
                        or manual_wire_regex
                        or manual_reg_regex
                        or manual_logic_regex
                    ):
                        if semicolon_regex:  # Complete param ended with ;
                            gather_till_semicolon = 0

                            if manual_input_regex:  # all other input
                                self.parse_ios(
                                    "TOP",
                                    "MANUAL",
                                    "input",
                                    manual_input_regex.group(1),
                                )
                            elif manual_output_regex:  # all other input
                                self.parse_ios(
                                    "TOP",
                                    "MANUAL",
                                    "output",
                                    manual_output_regex.group(1),
                                )
                            elif manual_wire_regex:  # all other wire/reg/input/output
                                wire_line = re.sub(r"^\s*wire\s+", "", line)
                                line_split_list = wire_line.split("=", 1)
                                if (
                                    wired_assign_bitdef_regex
                                ):  # If its a wired assignment with bitdef
                                    wire_line = line_split_list[0]
                                    wire_line_split_list = wire_line.split(" ", 1)

                                    if self.parsing_format == "verilog":
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "wire",
                                            line_split_list[0],
                                            "",
                                            "",
                                        )
                                    else:
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "logic",
                                            line_split_list[0],
                                            "",
                                            "",
                                        )

                                    self.parse_assignments(
                                        "wiredassign",
                                        wire_line_split_list[1]
                                        + wire_line_split_list[0]
                                        + " = "
                                        + line_split_list[1],
                                    )
                                elif (
                                    wired_assign_regex
                                ):  # wired assignment without bitdef
                                    if self.parsing_format == "verilog":
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "wire",
                                            line_split_list[0],
                                            "",
                                            "",
                                        )
                                    else:
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "reg",
                                            line_split_list[0],
                                            "",
                                            "",
                                        )

                                    self.parse_assignments(
                                        "wiredassign",
                                        line_split_list[0] + " = " + line_split_list[1],
                                    )
                                else:  # Regular wire declaration
                                    if self.parsing_format == "verilog":
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "wire",
                                            manual_wire_regex.group(1),
                                            "",
                                            "",
                                        )
                                    else:
                                        self.parse_reg_wire_logic(
                                            "TOP",
                                            "MANUAL",
                                            "reg",
                                            manual_wire_regex.group(1),
                                            "",
                                            "",
                                        )
                            elif manual_reg_regex:  # all other wire/reg/input/output
                                self.parse_reg_wire_logic(
                                    "TOP",
                                    "MANUAL",
                                    "reg",
                                    manual_reg_regex.group(1),
                                    "",
                                    "",
                                )
                            elif manual_logic_regex:  # all other wire/reg/input/output
                                self.parse_reg_wire_logic(
                                    "TOP",
                                    "MANUAL",
                                    "logic",
                                    manual_logic_regex.group(1),
                                    "",
                                    "",
                                )

                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []
                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1

                    ################################################################################
                    # assign statements
                    ################################################################################
                    assign_regex = RE_ASSIGN.search(line)

                    if assign_regex:
                        if semicolon_regex:  # Complete param ended with ;
                            gather_till_semicolon = 0
                            self.parse_assignments("assign", assign_regex.group(1))

                            # Resetting always block data since its hard to track without begin
                            inside_always_seq_block = 0
                            inside_always_combo_block = 0
                            self.always_constructs = []
                            prev_line = ""
                            continue
                        else:  # Multi line param
                            gather_till_semicolon = 1

                    ################################################################################
                    # always block parsing
                    ################################################################################
                    always_regex = RE_ALWAYS.search(line)
                    always_ff_regex = RE_ALWAYS_FF.search(line)
                    always_comb_regex = RE_ALWAYS_COMB.search(line)
                    begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                    bracket_check_ret = []

                    if look_for_always_begin:
                        look_for_always_begin = 0

                        if curr_construct == "ALWAYS_FF":
                            inside_always_seq_block = 1
                        else:
                            inside_always_combo_block = 1

                        if begin_begin_regex:
                            curr_construct = curr_construct + "_WITH_BEGIN"
                            self.always_constructs.append(curr_construct)
                            self.dbg("# Pushing construct " + curr_construct)
                            self.dbg(self.always_constructs)
                            # Pasing rest to line variable
                            line = begin_begin_regex.group(1)

                            # check for label
                            label_end_regex = RE_LABEL_END.search(line)
                            label_regex = RE_LABEL.search(line)

                            # Removing the label if present
                            if label_end_regex:
                                line = ""
                            elif label_regex:
                                line = label_regex.group(1)

                            line = re.sub(r"\s*$", "", line)

                        else:
                            # Push always construct without begin
                            self.always_constructs.append(curr_construct)
                            self.dbg("## Pushing construct " + curr_construct)
                            self.dbg(self.always_constructs)

                    if always_regex or always_ff_regex:
                        # Resetting always block data
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []

                        if always_regex:
                            bracket_check_ret = self.check_for_bracket(
                                always_regex.group(1)
                            )
                        elif always_ff_regex:
                            bracket_check_ret = self.check_for_bracket(
                                always_ff_regex.group(1)
                            )

                        # If the () are matching
                        if bracket_check_ret[0]:
                            self.dbg(
                                "\n################################################################################"
                            )
                            self.dbg(
                                "### Parsing an always block at line " + str(line_no)
                            )
                            self.dbg(
                                "################################################################################"
                            )
                            condition = bracket_check_ret[1]

                            posedge_regex = RE_POSEDGE.search(condition)
                            negedge_regex = RE_NEGEDGE.search(condition)

                            if posedge_regex or negedge_regex:
                                curr_construct = "ALWAYS_FF"

                                # Removing keywords in a seq always
                                condition = re.sub(r"posedge", "", condition)
                                condition = re.sub(r"negedge", "", condition)
                                condition = re.sub(r"[@\(\)]", "", condition)
                                condition = re.sub(r"\s+or\s+", " ", condition)

                                # Parse the clock and reset signals
                                self.parse_conditions(condition)
                            else:
                                # For sequential block, we dont need to parse the sensitivity list
                                curr_construct = "ALWAYS_COMBO"

                            # copy the rest after) to line and look for begin
                            line = bracket_check_ret[2]
                            line = re.sub(r"\s*$", "", line)

                            begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                            if begin_begin_regex:
                                if curr_construct == "ALWAYS_FF":
                                    inside_always_seq_block = 1
                                else:
                                    inside_always_combo_block = 1

                                curr_construct = curr_construct + "_WITH_BEGIN"
                                look_for_always_begin = 0
                                self.always_constructs.append(curr_construct)
                                self.dbg("## Pushing construct " + curr_construct)
                                self.dbg(self.always_constructs)
                                # Pasing rest to line variable
                                line = begin_begin_regex.group(1)

                                # check for label
                                label_end_regex = RE_LABEL_END.search(line)
                                label_regex = RE_LABEL.search(line)

                                # Removing the label if present
                                if label_end_regex:
                                    line = ""
                                elif label_regex:
                                    line = label_regex.group(1)

                                line = re.sub(r"\s*$", "", line)

                            else:
                                look_for_always_begin = 1

                            append_next_line = 0
                        else:
                            append_next_line = 1

                    elif always_comb_regex:
                        # Resetting always block data
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []

                        condition = always_comb_regex.group(1)
                        bracket_check_ret = self.check_for_bracket(
                            always_comb_regex.group(1)
                        )

                        RE_OPEN_CURLY_BRACKET = re.compile(r"^\s*{")
                        RE_OPEN_WORD_CHAR = re.compile(r"^\s*\w")
                        always_combo_open_curly_regex = RE_OPEN_CURLY_BRACKET.search(
                            always_comb_regex.group(1)
                        )
                        always_combo_open_word_regex = RE_OPEN_WORD_CHAR.search(
                            always_comb_regex.group(1)
                        )

                        if (
                            always_combo_open_curly_regex
                            or always_combo_open_word_regex
                        ):
                            line = always_comb_regex.group(1)
                            inside_always_combo_block = 1
                            look_for_always_begin = 0
                            curr_construct = "ALWAYS_COMBO"
                            self.always_constructs.append(curr_construct)
                            self.dbg("# Pushing construct " + curr_construct)
                            self.dbg(self.always_constructs)
                        else:
                            # If the () are matching
                            if bracket_check_ret[0]:
                                self.dbg(
                                    "\n################################################################################"
                                )
                                self.dbg(
                                    "### Parsing an always block at line "
                                    + str(line_no)
                                )
                                self.dbg(
                                    "################################################################################"
                                )
                                condition = bracket_check_ret[1]
                                curr_construct = "ALWAYS_COMBO"

                                # copy the rest after) to line and look for begin
                                line = bracket_check_ret[2]
                                line = re.sub(r"\s*$", "", line)

                                begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                                if begin_begin_regex:
                                    if curr_construct == "ALWAYS_FF":
                                        inside_always_seq_block = 1
                                    else:
                                        inside_always_combo_block = 1

                                    curr_construct = curr_construct + "_WITH_BEGIN"
                                    look_for_always_begin = 0
                                    self.always_constructs.append(curr_construct)
                                    self.dbg("# Pushing construct " + curr_construct)
                                    self.dbg(self.always_constructs)
                                    # Pasing rest to line variable
                                    line = begin_begin_regex.group(1)
                                else:
                                    look_for_always_begin = 1

                                append_next_line = 0
                            else:
                                begin_regex = RE_BEGIN_NO_GROUP.search(line)

                                # for always_comb begin cases
                                if begin_regex:
                                    line = always_comb_regex.group(1)
                                    begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                                    self.dbg(
                                        "\n################################################################################"
                                    )
                                    self.dbg(
                                        "### Parsing an always block at line "
                                        + str(line_no)
                                    )
                                    self.dbg(
                                        "################################################################################"
                                    )

                                    if begin_begin_regex:  # if begin there without ()
                                        inside_always_combo_block = 1
                                        curr_construct = "ALWAYS_COMBO_WITH_BEGIN"
                                        look_for_always_begin = 0
                                        self.always_constructs.append(curr_construct)
                                        self.dbg(
                                            "# Pushing construct " + curr_construct
                                        )
                                        self.dbg(self.always_constructs)

                                        # Pasing rest to line variable
                                        line = begin_begin_regex.group(1)
                                        line = re.sub(r"\s*$", "", line)

                                        # check for label
                                        label_end_regex = RE_LABEL_END.search(line)
                                        label_regex = RE_LABEL.search(line)

                                        # Removing the label if present
                                        if label_end_regex:
                                            line = ""
                                        elif label_regex:
                                            line = label_regex.group(1)

                                        line = re.sub(r"\s*$", "", line)
                                    else:
                                        append_next_line = 1

                                else:
                                    append_next_line = 1

                    if inside_always_seq_block or inside_always_combo_block:
                        if look_for_if_begin:
                            look_for_if_begin = 0
                            begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                            if begin_begin_regex:
                                if curr_for_construct == "FOR":
                                    curr_for_construct == "FOR_WITH_BEGIN"
                                    self.always_constructs.append(curr_for_construct)
                                    self.dbg(
                                        "# Pushing construct " + curr_for_construct
                                    )
                                else:
                                    curr_construct = curr_construct + "_WITH_BEGIN"
                                    self.always_constructs.append(curr_construct)
                                    self.dbg("# Pushing construct " + curr_construct)
                                    curr_for_construct == "FOR_WITH_BEGIN"

                                self.dbg(self.always_constructs)

                                # Pasing rest to line variable
                                line = begin_begin_regex.group(1)
                                line = re.sub(r"\s*$", "", line)

                                # Removing Label
                                begin_label_regex = RE_WITH_LABEL.search(line)

                                if begin_label_regex:
                                    line = begin_label_regex.group(2)
                            else:
                                # Push construct without begin
                                if curr_for_construct == "FOR":
                                    self.always_constructs.append("FOR")
                                    self.dbg("# Pushing construct " + "FOR")
                                else:
                                    self.always_constructs.append(curr_construct)
                                    self.dbg("# Pushing construct " + curr_construct)

                                self.dbg(self.always_constructs)

                        for_regex = RE_FOR.search(line)

                        if for_regex:
                            bracket_check_ret = self.check_for_bracket(
                                for_regex.group(1)
                            )

                            # If the () are matching
                            if bracket_check_ret[0]:
                                condition = bracket_check_ret[1]

                                # curr_construct = 'FOR'
                                curr_for_construct = "FOR"

                                for_extract_regex = RE_FOR_EXTRACT.search(condition)

                                start_exp = for_extract_regex.group(1)
                                end_exp = for_extract_regex.group(2)
                                step_exp = for_extract_regex.group(3)

                                # Handling int declaration part of for loop
                                start_exp_int_regex = RE_FORLOOP_INT_EXTRACT.search(
                                    start_exp
                                )

                                if start_exp_int_regex:
                                    start_exp = (
                                        start_exp_int_regex.group(1)
                                        + "="
                                        + start_exp_int_regex.group(2)
                                    )
                                    self.integers.append(start_exp_int_regex.group(1))
                                    self.dbg(
                                        "# Storing integer variable "
                                        + start_exp_int_regex.group(1)
                                    )

                                # Handling integer declaration part of for loop
                                start_exp_integer_regex = (
                                    RE_FORLOOP_INTEGER_EXTRACT.search(start_exp)
                                )

                                if start_exp_integer_regex:
                                    start_exp = (
                                        start_exp_integer_regex.group(1)
                                        + "="
                                        + start_exp_integer_regex.group(2)
                                    )
                                    self.integers.append(
                                        start_exp_integer_regex.group(1)
                                    )
                                    self.dbg(
                                        "# Storing integer variable "
                                        + start_exp_integer_regex.group(1)
                                    )

                                start_exp = re.sub(r"\s+", "", start_exp)
                                end_exp = re.sub(r"\s+", "", end_exp)
                                step_exp = re.sub(r"\s+", "", step_exp)

                                # Start Expression parsing
                                start_exp_equal_regex = RE_EQUAL_EXTRACT.search(
                                    start_exp
                                )

                                if start_exp_equal_regex:
                                    for_var = start_exp_equal_regex.group(1)
                                    start_val_ret = self.tickdef_param_getval(
                                        "TOP", start_exp_equal_regex.group(2), "", ""
                                    )
                                    if start_val_ret[0] == "STRING":
                                        print(
                                            "\nError: Unable to calculate the start value for the for loop in generate"
                                        )
                                        print("  # " + line)
                                        self.found_error = 1
                                    else:
                                        c_start_val = start_val_ret[1]

                                # End Expression parsing
                                end_exp_less_than_equal_regex = (
                                    RE_LESS_THAN_EQUAL.search(end_exp)
                                )
                                end_exp_less_than_regex = RE_LESS_THAN.search(end_exp)
                                end_exp_greater_than_equal_regex = (
                                    RE_GREATER_THAN_EQUAL.search(end_exp)
                                )
                                end_exp_greater_than_regex = RE_GREATER_THAN.search(
                                    end_exp
                                )

                                # Step Expression parsing
                                step_minus_minus_regex = RE_MINUS_MINUS.search(step_exp)
                                step_plus_plus_regex = RE_PLUS_PLUS.search(step_exp)
                                step_minus_number_regex = RE_MINUS_NUMBER.search(
                                    step_exp
                                )
                                step_plus_number_regex = RE_PLUS_NUMBER.search(step_exp)

                                c_step_val = 1

                                if step_minus_minus_regex:
                                    c_step_val = "1"
                                elif step_plus_plus_regex:
                                    c_step_val = "1"
                                elif step_minus_number_regex:
                                    c_step_val = step_minus_number_regex.group(3)
                                elif step_plus_number_regex:
                                    c_step_val = step_plus_number_regex.group(3)

                                if end_exp_less_than_equal_regex:
                                    c_end_val = end_exp_less_than_equal_regex.group(2)
                                    # end_val_ret = self.tickdef_param_getval('TOP', end_exp_less_than_equal_regex.group(2), '', '')

                                    # if end_val_ret[0] == 'STRING':
                                    # print('\nWarning: Unable to calculate the end value for the for loop in generate')
                                    # print('  # ' + line)
                                elif end_exp_less_than_regex:
                                    c_end_val = (
                                        end_exp_less_than_regex.group(2)
                                        + "-"
                                        + str(c_step_val)
                                    )
                                    # end_val_ret = self.tickdef_param_getval('TOP', end_exp_less_than_regex.group(2), '', '')

                                    # if end_val_ret[0] == 'STRING':
                                    # print('\nWarning: Unable to calculate the end value for the for loop in generate')
                                    # print('  # ' + line)
                                elif end_exp_greater_than_equal_regex:
                                    c_end_val = end_exp_greater_than_equal_regex.group(
                                        2
                                    )
                                    # end_val_ret = self.tickdef_param_getval('TOP', end_exp_greater_than_equal_regex.group(2), '', '')

                                    # if end_val_ret[0] == 'STRING':
                                    # print('\Warning: Unable to calculate the end value for the for loop in generate')
                                    # print('  # ' + line)
                                elif end_exp_greater_than_regex:
                                    c_end_val = (
                                        end_exp_greater_than_regex.group(2)
                                        + "+"
                                        + str(c_step_val)
                                    )
                                    # end_val_ret = self.tickdef_param_getval('TOP', end_exp_greater_than_regex.group(2), '', '')

                                    # if end_val_ret[0] == 'STRING':
                                    # print('\Warning: Unable to calculate the end value for the for loop in generate')
                                    # print('  # ' + line)

                                self.always_for_loops[self.always_for_loop_count] = {}
                                self.always_for_loops[self.always_for_loop_count][
                                    "orig"
                                ] = line
                                self.always_for_loops[self.always_for_loop_count][
                                    "for_var"
                                ] = for_var
                                self.always_for_loops[self.always_for_loop_count][
                                    "start_val"
                                ] = c_start_val
                                self.always_for_loops[self.always_for_loop_count][
                                    "end_val"
                                ] = c_end_val
                                self.always_for_loops[self.always_for_loop_count][
                                    "step_val"
                                ] = c_step_val
                                self.always_for_loops[self.always_for_loop_count][
                                    "count"
                                ] = self.always_for_loop_count

                                self.dbg(
                                    "# FOR_LOOP: Var = "
                                    + for_var
                                    + "    BitDef: "
                                    + str(c_end_val)
                                    + ":"
                                    + str(c_start_val)
                                )

                                self.always_for_loop_count = (
                                    self.always_for_loop_count + 1
                                )

                                # copy the rest after) to line and look for begin
                                line = bracket_check_ret[2]

                                begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                                if begin_begin_regex:
                                    line = begin_begin_regex.group(1)
                                    line = re.sub(r"\s*$", "", line)
                                    curr_for_construct = "FOR_WITH_BEGIN"
                                    look_for_if_begin = 0
                                    self.always_constructs.append(curr_for_construct)
                                    self.dbg(
                                        "# Pushing construct " + curr_for_construct
                                    )
                                    self.dbg(self.always_constructs)

                                    begin_label_regex = RE_WITH_LABEL.search(line)

                                    if begin_label_regex:
                                        # Removing Label
                                        line = begin_label_regex.group(2)

                                    append_next_line = 0
                                else:
                                    look_for_if_begin = 1
                                    append_next_line = 1
                                    prev_line = line
                                    prev_original_line = original_line
                                    prev_line_no = line_no
                                    continue
                            else:
                                append_next_line = 1
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                continue

                        if self.always_for_loop_count > 0:
                            for c_for_idx in self.always_for_loops.keys():
                                search_var = (
                                    "\\b"
                                    + self.always_for_loops[c_for_idx]["for_var"]
                                    + "\\b"
                                )
                                replace_var = (
                                    str(self.always_for_loops[c_for_idx]["end_val"])
                                    + ":"
                                    + str(self.always_for_loops[c_for_idx]["start_val"])
                                )
                                line = re.sub(search_var, replace_var, line)

                            self.dbg(
                                "### "
                                + curr_construct
                                + " :: "
                                + str(line_no)
                                + " ::: "
                                + line
                                + ":::"
                            )

                        unique_case_regex = RE_UNIQUE_CASE.search(line)
                        case_regex = RE_CASE.search(line)
                        casez_regex = RE_CASEZ.search(line)
                        casex_regex = RE_CASEX.search(line)
                        endcase_regex = RE_ENDCASE.search(line)

                        ################################################################################
                        # Parsing endcase construct and removing case_condition construct
                        ################################################################################
                        if endcase_regex:
                            line = endcase_regex.group(1)
                            append_next_line = 1

                            if curr_construct != "CASE_CONDITION":
                                self.dbg(
                                    "\nError: Found endcase when current construct is "
                                    + curr_construct
                                    + " at line "
                                    + str(line_no)
                                    + " in "
                                    + self.temporary_file
                                )
                                self.dbg(original_line)
                                print(
                                    "\nError: Found endcase when current construct is "
                                    + curr_construct
                                    + " at line "
                                    + str(line_no)
                                    + " in "
                                    + self.temporary_file
                                )
                                print(original_line)
                                self.found_error = 1

                                if (
                                    curr_construct == "IF_WITH_BEGIN"
                                    or curr_construct == "ELSE_IF_WITH_BEGIN"
                                    or curr_construct == "ELSE_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                    or curr_construct == "CASE_EXPRESSION_WITH_BEGIN"
                                ):
                                    print(
                                        "INFO: end construct is expected for "
                                        + curr_construct
                                    )

                            else:
                                curr_construct = self.always_constructs.pop()
                                self.dbg(
                                    "# Popping construct "
                                    + curr_construct
                                    + " for endcase\n"
                                )

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                self.dbg(self.always_constructs)

                        ################################################################################
                        # Error out if RTL uses casex that is not allowed
                        ################################################################################
                        if casex_regex:
                            self.dbg(
                                "\nError: casex is not allowed in RTL at line "
                                + str(line_no)
                                + " in "
                                + self.temporary_file
                            )
                            self.dbg("       " + original_line)
                            print(
                                "\nError: casex is not allowed in RTL at line "
                                + str(line_no)
                                + " in "
                                + self.temporary_file
                            )
                            print(original_line)
                            sys.exit(1)

                        ################################################################################
                        # Parsing case and casez conditions
                        ################################################################################
                        if unique_case_regex or case_regex or casez_regex:
                            if unique_case_regex:
                                bracket_check_ret = self.check_for_bracket(
                                    unique_case_regex.group(1)
                                )
                            elif case_regex:
                                bracket_check_ret = self.check_for_bracket(
                                    case_regex.group(1)
                                )
                            elif casez_regex:
                                bracket_check_ret = self.check_for_bracket(
                                    casez_regex.group(1)
                                )

                            # If the () are matching
                            if bracket_check_ret[0]:
                                condition = bracket_check_ret[1]
                                line = bracket_check_ret[2]
                                line = re.sub(r"\s*$", "", line)

                                curr_construct = "CASE_CONDITION"
                                # Push case_condition construct
                                self.always_constructs.append(curr_construct)
                                self.dbg("# Pushing construct " + curr_construct)
                                self.dbg(self.always_constructs)

                                # Parse all the input signals in the condition
                                self.parse_conditions(condition)

                            else:
                                append_next_line = 1

                            if line == "":
                                continue

                        ################################################################################
                        # Parsing if / else if / else conditions
                        ################################################################################
                        if_regex = RE_IF.search(line)
                        elseif_regex = RE_ELSEIF.search(line)
                        else_regex = RE_ELSE.search(line)

                        if if_regex or elseif_regex:
                            if if_regex:
                                bracket_check_ret = self.check_for_bracket(
                                    if_regex.group(1)
                                )
                            elif elseif_regex:
                                bracket_check_ret = self.check_for_bracket(
                                    elseif_regex.group(1)
                                )

                            # If the () are matching
                            if bracket_check_ret[0]:
                                condition = bracket_check_ret[1]

                                if if_regex:
                                    curr_construct = "IF"
                                elif elseif_regex:
                                    curr_construct = "ELSE_IF"

                                # Parse all the input signals in the condition
                                self.parse_conditions(condition)

                                # copy the rest after) to line and look for begin
                                line = bracket_check_ret[2]
                                line = re.sub(r"^\s*", "", line)

                                begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                                if begin_begin_regex:
                                    line = begin_begin_regex.group(1)
                                    line = re.sub(r"\s*$", "", line)
                                    curr_construct = curr_construct + "_WITH_BEGIN"
                                    look_for_if_begin = 0
                                    self.always_constructs.append(curr_construct)
                                    self.dbg("# Pushing construct " + curr_construct)
                                    self.dbg(self.always_constructs)
                                    append_next_line = 0
                                else:
                                    a2z_start_regex = RE_A2Z_START.search(line)

                                    if a2z_start_regex:
                                        look_for_if_begin = 0
                                        self.always_constructs.append(curr_construct)
                                        self.dbg(
                                            "# Pushing construct " + curr_construct
                                        )
                                        self.dbg(self.always_constructs)
                                        append_next_line = 0
                                    else:
                                        look_for_if_begin = 1
                                        append_next_line = 1
                            else:
                                append_next_line = 1
                        elif else_regex:  # if (if_regex or elseif_regex):
                            # copy the rest after) to line and look for begin
                            line = else_regex.group(1)
                            line = re.sub(r"\s*$", "", line)
                            line = re.sub(r"^\s*", "", line)
                            curr_construct = "ELSE"

                            begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                            if begin_begin_regex:
                                # Passing the rest after begin to next line
                                line = begin_begin_regex.group(1)
                                line = re.sub(r"\s*$", "", line)
                                curr_construct = curr_construct + "_WITH_BEGIN"
                                look_for_if_begin = 0
                                self.always_constructs.append(curr_construct)
                                self.dbg("# Pushing construct " + curr_construct)
                                self.dbg(self.always_constructs)
                                append_next_line = 0
                            else:
                                a2z_start_regex = RE_A2Z_START.search(line)

                                if a2z_start_regex:
                                    look_for_if_begin = 0
                                    self.always_constructs.append(curr_construct)
                                    self.dbg("# Pushing construct " + curr_construct)
                                    self.dbg(self.always_constructs)
                                    append_next_line = 0
                                else:
                                    look_for_if_begin = 1
                                    append_next_line = 1
                                    prev_line = line
                                    prev_original_line = original_line
                                    prev_line_no = line_no
                                    continue

                        semicolon_regex = RE_SEMICOLON.search(line)

                        ################################################################################
                        # Parsing case expressions
                        ################################################################################
                        # Replace :: for typedef enums before detecting :
                        case_line = line
                        line = line.replace("::", "#-#")

                        if curr_construct == "CASE_CONDITION":
                            # TODO: Need to think if : is part of expression
                            line = line.replace(":", "###", 1)

                            empty_case_expression_regex = (
                                RE_EMPTY_CASE_EXPRESSION.search(line)
                            )
                            case_expression_regex = RE_CASE_EXPRESSION.search(line)

                            if not case_expression_regex:
                                line = line.replace("#-#", "::")
                                append_next_line = 1
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                continue
                            else:
                                # Spliting the assign statment with lhs and rhs
                                line_split_list = line.split("###")
                                line_split_list[0] = line_split_list[0].replace(
                                    "#-#", "::"
                                )
                                self.parse_case_expression(line_split_list[0])

                                # Passing remaing back to line for begin or assignments
                                line = line_split_list[1]
                                line = line.replace("#-#", "::")
                                line = re.sub(r"\s*$", "", line)

                                if empty_case_expression_regex:
                                    pass
                                else:
                                    curr_construct = "CASE_EXPRESSION"

                                    begin_begin_regex = RE_BEGIN_BEGIN.search(line)

                                    if begin_begin_regex:
                                        line = begin_begin_regex.group(1)
                                        curr_construct = curr_construct + "_WITH_BEGIN"
                                        look_for_if_begin = 0
                                        self.always_constructs.append(curr_construct)
                                        self.dbg(
                                            "# Pushing construct " + curr_construct
                                        )
                                        self.dbg(self.always_constructs)

                                        # Need to append the remaining after ; to next line
                                        if self.check_if_parsing_needed(line):
                                            append_next_line = 1
                                    else:
                                        a2z_start_regex = RE_A2Z_START.search(line)

                                        if a2z_start_regex:
                                            look_for_if_begin = 0
                                            self.always_constructs.append(
                                                curr_construct
                                            )
                                            self.dbg(
                                                "# Pushing construct " + curr_construct
                                            )
                                            self.dbg(self.always_constructs)
                                            append_next_line = 0
                                        else:
                                            look_for_if_begin = 1
                                            append_next_line = 1
                                            prev_line = line
                                            prev_original_line = original_line
                                            prev_line_no = line_no
                                            continue

                        line = line.replace("#-#", "::")

                        ################################################################################
                        # Parsing statements inside if / else if condtions
                        ################################################################################
                        if not look_for_if_begin and (
                            curr_construct == "IF"
                            or curr_construct == "ELSE_IF"
                            or curr_construct == "CASE_EXPRESSION"
                        ):
                            for_regex = RE_FOR.search(line)

                            if for_regex:
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                append_next_line = 1
                                continue

                            if semicolon_regex:
                                line_split_list = line.split(";", 1)

                                line = line_split_list[1]
                                # Need to append the remaining after ; to next line
                                if self.check_if_parsing_needed(line):
                                    append_next_line = 1

                                if inside_always_combo_block:
                                    self.parse_assignments(
                                        "ALWAYS_COMBO", line_split_list[0]
                                    )
                                elif inside_always_seq_block:
                                    self.parse_assignments(
                                        "ALWAYS_SEQ", line_split_list[0]
                                    )

                                line = line_split_list[1]
                                line = re.sub(r"\s*$", "", line)

                                self.dbg(self.always_constructs)
                                curr_construct = self.always_constructs.pop()
                                self.dbg("# Popping construct " + curr_construct)

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                self.dbg(self.always_constructs)

                            else:  # Need to append next line
                                append_next_line = 1

                        ################################################################################
                        # Parsing statements inside else condtions
                        ################################################################################
                        semicolon_regex = RE_SEMICOLON.search(line)

                        if not look_for_if_begin and curr_construct == "ELSE":
                            for_regex = RE_FOR.search(line)

                            if for_regex:
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                append_next_line = 1
                                continue

                            if semicolon_regex:
                                line_split_list = line.split(";", 1)

                                line = line_split_list[1]
                                line = re.sub(r"\s*$", "", line)

                                # Need to append the remaining after ; to next line
                                if self.check_if_parsing_needed(line):
                                    append_next_line = 1

                                if inside_always_combo_block:
                                    self.parse_assignments(
                                        "ALWAYS_COMBO", line_split_list[0]
                                    )
                                elif inside_always_seq_block:
                                    self.parse_assignments(
                                        "ALWAYS_SEQ", line_split_list[0]
                                    )

                                line = line_split_list[1]

                                curr_construct = self.always_constructs.pop()
                                self.dbg("# Popping construct " + curr_construct)

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                self.dbg(self.always_constructs)

                                # TODO: Might have to flush other constructs without begin
                                if (
                                    curr_construct == "IF"
                                    or curr_construct == "ELSE_IF"
                                    or curr_construct == "ELSE"
                                    or curr_construct == "ALWAYS_FF"
                                    or curr_construct == "ALWAYS_COMBO"
                                    or curr_construct == "CASE_EXPRESSION"
                                ):

                                    curr_construct = self.always_constructs.pop()
                                    self.dbg(
                                        "# Popping one more construct " + curr_construct
                                    )

                                    if len(self.always_constructs) > 0:
                                        last_construct_loc = (
                                            len(self.always_constructs) - 1
                                        )
                                        curr_construct = self.always_constructs[
                                            last_construct_loc
                                        ]
                                    else:
                                        curr_construct = ""

                                    self.dbg(self.always_constructs)

                                    # TODO: Might have to flush other constructs without begin
                                    if curr_construct == "ELSE":
                                        curr_construct = self.always_constructs.pop()
                                        self.dbg(
                                            "# Popping one more construct "
                                            + curr_construct
                                        )

                                        if len(self.always_constructs) > 0:
                                            last_construct_loc = (
                                                len(self.always_constructs) - 1
                                            )
                                            curr_construct = self.always_constructs[
                                                last_construct_loc
                                            ]
                                        else:
                                            curr_construct = ""

                                        self.dbg(self.always_constructs)

                                        # TODO: Might have to flush other constructs without begin
                                        if curr_construct == "ELSE":
                                            curr_construct = (
                                                self.always_constructs.pop()
                                            )
                                            self.dbg(
                                                "# Popping one more construct "
                                                + curr_construct
                                            )

                                            if len(self.always_constructs) > 0:
                                                last_construct_loc = (
                                                    len(self.always_constructs) - 1
                                                )
                                                curr_construct = self.always_constructs[
                                                    last_construct_loc
                                                ]
                                            else:
                                                curr_construct = ""

                                            self.dbg(self.always_constructs)

                            else:  # Need to append next line
                                append_next_line = 1

                        ################################################################################
                        # If the beginning word is a keyword like if / else / case, then skip rest
                        ################################################################################
                        unique_case_regex = RE_UNIQUE_CASE.search(line)
                        case_regex = RE_CASE.search(line)
                        casez_regex = RE_CASEZ.search(line)
                        casex_regex = RE_CASEX.search(line)
                        if_regex = RE_IF.search(line)
                        elseif_regex = RE_ELSEIF.search(line)
                        else_regex = RE_ELSE.search(line)

                        if (
                            unique_case_regex
                            or case_regex
                            or casez_regex
                            or casex_regex
                            or if_regex
                            or elseif_regex
                            or else_regex
                        ):
                            append_next_line = 1
                            prev_line = line
                            prev_original_line = original_line
                            prev_line_no = line_no
                            continue

                        ################################################################################
                        # Parsing statements inside if_begin / else_if_begin / else_begin condtions
                        ################################################################################
                        semicolon_regex = RE_SEMICOLON.search(line)

                        if (
                            curr_construct == "IF_WITH_BEGIN"
                            or curr_construct == "ELSE_IF_WITH_BEGIN"
                            or curr_construct == "ELSE_WITH_BEGIN"
                            or curr_construct == "CASE_EXPRESSION_WITH_BEGIN"
                        ):
                            for_regex = RE_FOR.search(line)

                            if for_regex:
                                prev_line = line
                                prev_original_line = original_line
                                prev_line_no = line_no
                                append_next_line = 1
                                continue

                            if semicolon_regex:
                                append_next_line = 0
                                line = re.sub(r"\s*$", "", line)
                                line = re.sub(r"^\s*", "", line)
                                line_split_list = line.split(";")
                                line_split_list_size = len(line_split_list)

                                append_to_line = 0

                                for ii in range(0, line_split_list_size):
                                    if append_to_line:
                                        line = line + ";" + line_split_list[ii]
                                    elif ii == line_split_list_size - 1:
                                        line = line_split_list[ii]
                                    else:
                                        if self.check_if_parsing_needed(
                                            line_split_list[ii]
                                        ):
                                            line = line_split_list[ii]
                                            append_to_line = 1
                                        else:
                                            if inside_always_combo_block:
                                                self.parse_assignments(
                                                    "ALWAYS_COMBO", line_split_list[ii]
                                                )
                                            elif inside_always_seq_block:
                                                self.parse_assignments(
                                                    "ALWAYS_SEQ", line_split_list[ii]
                                                )

                                append_to_line = 0
                                line = re.sub(r"\s*$", "", line)

                                # Need to append the remaining after ; to next line
                                if self.check_if_parsing_needed(line):
                                    append_next_line = 1
                            else:  # Need to append next line
                                append_next_line = 1

                        ################################################################################
                        # Parsing end construct and removing the paired construct
                        ################################################################################
                        end_regex = RE_END.search(line)

                        if end_regex:
                            line = end_regex.group(1)
                            line = re.sub(r"\s*$", "", line)
                            append_next_line = 1

                            begin_flag = 0

                            # Need to pop out constructs without begin until it finds with begin
                            while not begin_flag:
                                if (
                                    curr_construct == "IF"
                                    or curr_construct == "ELSE_IF"
                                    or curr_construct == "ELSE"
                                    or curr_construct == "ALWAYS_FF"
                                    or curr_construct == "ALWAYS_COMBO"
                                    or curr_construct == "CASE_EXPRESSION"
                                    or curr_construct == "FOR"
                                ):
                                    begin_flag = 0

                                    if curr_for_construct == "FOR":
                                        self.always_for_loop_count = (
                                            self.always_for_loop_count - 1
                                        )
                                        # Removing the last for loop element
                                        del self.always_for_loops[
                                            self.always_for_loop_count
                                        ]
                                        curr_for_construct == ""

                                    curr_construct = self.always_constructs.pop()
                                    self.dbg(
                                        "# Popping construct until with begin "
                                        + curr_construct
                                        + " for end\n"
                                    )

                                    if len(self.always_constructs) > 0:
                                        last_construct_loc = (
                                            len(self.always_constructs) - 1
                                        )
                                        curr_construct = self.always_constructs[
                                            last_construct_loc
                                        ]
                                    else:
                                        curr_construct = ""

                                    if (
                                        curr_construct == "FOR"
                                        or curr_construct == "FOR_WITH_BEGIN"
                                    ):
                                        curr_for_construct = curr_construct
                                    else:
                                        curr_for_construct = ""

                                    self.dbg(self.always_constructs)
                                else:
                                    begin_flag = 1

                            # curr_construct should have the non for or for_with_begin construct
                            if (
                                curr_for_construct == "FOR"
                                or curr_for_construct == "FOR_WITH_BEGIN"
                            ):
                                if len(self.always_constructs) > 0:
                                    for ii in range(
                                        len(self.always_constructs) - 2, 0, -1
                                    ):

                                        if (
                                            self.always_constructs[ii] != "FOR"
                                            and self.always_constructs[ii]
                                            != "FOR_WITH_BEGIN"
                                        ):
                                            curr_construct = self.always_constructs[ii]
                                            break

                            if (
                                curr_construct == "IF_WITH_BEGIN"
                                or curr_construct == "ELSE_IF_WITH_BEGIN"
                                or curr_construct == "ELSE_WITH_BEGIN"
                                or curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                or curr_construct == "CASE_EXPRESSION_WITH_BEGIN"
                                or curr_construct == "FOR_WITH_BEGIN"
                            ):

                                curr_construct = self.always_constructs.pop()
                                self.dbg(
                                    "# Popping construct "
                                    + curr_construct
                                    + " for end\n"
                                )

                                if (
                                    curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                ):
                                    # Resetting always block data
                                    inside_always_seq_block = 0
                                    inside_always_combo_block = 0

                                if curr_construct == "FOR_WITH_BEGIN":
                                    self.always_for_loop_count = (
                                        self.always_for_loop_count - 1
                                    )
                                    # Removing the last for loop element
                                    del self.always_for_loops[
                                        self.always_for_loop_count
                                    ]

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                if (
                                    curr_construct == "FOR"
                                    or curr_construct == "FOR_WITH_BEGIN"
                                ):
                                    curr_for_construct = curr_construct
                                else:
                                    curr_for_construct = ""

                                # curr_construct should have the non for or for_with_begin construct
                                if (
                                    curr_for_construct == "FOR"
                                    or curr_for_construct == "FOR_WITH_BEGIN"
                                ):
                                    if len(self.always_constructs) > 0:
                                        for ii in range(
                                            len(self.always_constructs) - 2, 0, -1
                                        ):

                                            if (
                                                self.always_constructs[ii] != "FOR"
                                                and self.always_constructs[ii]
                                                != "FOR_WITH_BEGIN"
                                            ):
                                                curr_construct = self.always_constructs[
                                                    ii
                                                ]
                                                break

                                self.dbg(self.always_constructs)

                        ################################################################################
                        # Parsing endcase construct and removing case_condition construct
                        ################################################################################
                        endcase_regex = RE_ENDCASE.search(line)

                        if endcase_regex:
                            line = endcase_regex.group(1)
                            append_next_line = 1

                            if curr_construct != "CASE_CONDITION":
                                self.dbg(
                                    "\nError: Found endcase when current construct is "
                                    + curr_construct
                                    + " at line "
                                    + str(line_no)
                                    + " in "
                                    + self.temporary_file
                                )
                                self.dbg(original_line)
                                print(
                                    "\nError: Found endcase when current construct is "
                                    + curr_construct
                                    + " at line "
                                    + str(line_no)
                                    + " in "
                                    + self.temporary_file
                                )
                                print(original_line)
                                self.found_error = 1

                                if (
                                    curr_construct == "IF_WITH_BEGIN"
                                    or curr_construct == "ELSE_IF_WITH_BEGIN"
                                    or curr_construct == "ELSE_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                    or curr_construct == "CASE_EXPRESSION_WITH_BEGIN"
                                ):
                                    print(
                                        "INFO: end construct is expected for "
                                        + curr_construct
                                    )
                            else:
                                curr_construct = self.always_constructs.pop()
                                self.dbg(
                                    "# Popping construct "
                                    + curr_construct
                                    + " for endcase\n"
                                )

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                self.dbg(self.always_constructs)

                        ################################################################################
                        # Parsing assignments right after always
                        ################################################################################
                        semicolon_regex = RE_SEMICOLON.search(line)
                        end_regex = RE_END.search(line)
                        begin_regex = RE_BEGIN_NO_GROUP.search(line)

                        if not end_regex and not begin_regex:
                            if (
                                curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                or curr_construct == "ALWAYS_SEQ_WITH_BEGIN"
                                or curr_construct == "ALWAYS_COMBO"
                                or curr_construct == "ALWAYS_FF"
                                or curr_construct == "ALWAYS_FF_WITH_BEGIN"
                            ):
                                if semicolon_regex:
                                    append_next_line = 0
                                    line_split_list = line.split(";", 1)

                                    line = line_split_list[1]
                                    line = re.sub(r"\s*$", "", line)

                                    # Need to append the remaining after ; to next line
                                    if self.check_if_parsing_needed(line):
                                        append_next_line = 1

                                    if inside_always_combo_block:
                                        self.parse_assignments(
                                            "ALWAYS_COMBO", line_split_list[0]
                                        )
                                    elif inside_always_seq_block:
                                        self.parse_assignments(
                                            "ALWAYS_SEQ", line_split_list[0]
                                        )

                                    if (
                                        curr_construct == "ALWAYS_COMBO"
                                        or curr_construct == "ALWAYS_FF"
                                    ):
                                        curr_construct = self.always_constructs.pop()
                                        self.dbg(
                                            "# Popping construct "
                                            + curr_construct
                                            + " for end\n"
                                        )

                                        if len(self.always_constructs) > 0:
                                            last_construct_loc = (
                                                len(self.always_constructs) - 1
                                            )
                                            curr_construct = self.always_constructs[
                                                last_construct_loc
                                            ]
                                        else:
                                            curr_construct = ""

                                else:  # Need to append next line
                                    append_next_line = 1

                        ################################################################################
                        # Parsing end construct and removing the paired construct
                        ################################################################################
                        end_regex = RE_END.search(line)

                        if end_regex:
                            line = end_regex.group(1)
                            line = re.sub(r"\s*$", "", line)
                            append_next_line = 1

                            begin_flag = 0

                            # Need to pop out constructs without begin until it finds with begin
                            while not begin_flag:
                                if (
                                    curr_construct == "IF"
                                    or curr_construct == "ELSE_IF"
                                    or curr_construct == "ELSE"
                                    or curr_construct == "ALWAYS_FF"
                                    or curr_construct == "ALWAYS_COMBO"
                                    or curr_construct == "CASE_EXPRESSION"
                                    or curr_construct == "FOR"
                                ):
                                    begin_flag = 0

                                    if curr_for_construct == "FOR":
                                        self.always_for_loop_count = (
                                            self.always_for_loop_count - 1
                                        )
                                        # Removing the last for loop element
                                        del self.always_for_loops[
                                            self.always_for_loop_count
                                        ]
                                        curr_for_construct == ""

                                    curr_construct = self.always_constructs.pop()
                                    self.dbg(
                                        "# Popping construct until with begin "
                                        + curr_construct
                                        + " for end\n"
                                    )

                                    if len(self.always_constructs) > 0:
                                        last_construct_loc = (
                                            len(self.always_constructs) - 1
                                        )
                                        curr_construct = self.always_constructs[
                                            last_construct_loc
                                        ]
                                    else:
                                        curr_construct = ""

                                    if (
                                        curr_construct == "FOR"
                                        or curr_construct == "FOR_WITH_BEGIN"
                                    ):
                                        curr_for_construct = curr_construct
                                    else:
                                        curr_for_construct = ""

                                    self.dbg(self.always_constructs)
                                else:
                                    begin_flag = 1

                            # curr_construct should have the non for or for_with_begin construct
                            if (
                                curr_for_construct == "FOR"
                                or curr_for_construct == "FOR_WITH_BEGIN"
                            ):
                                if len(self.always_constructs) > 0:
                                    for ii in range(
                                        len(self.always_constructs) - 2, 0, -1
                                    ):

                                        if (
                                            self.always_constructs[ii] != "FOR"
                                            and self.always_constructs[ii]
                                            != "FOR_WITH_BEGIN"
                                        ):
                                            curr_construct = self.always_constructs[ii]
                                            break

                            if (
                                curr_construct == "IF_WITH_BEGIN"
                                or curr_construct == "ELSE_IF_WITH_BEGIN"
                                or curr_construct == "ELSE_WITH_BEGIN"
                                or curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                or curr_construct == "CASE_EXPRESSION_WITH_BEGIN"
                                or curr_construct == "FOR_WITH_BEGIN"
                            ):

                                curr_construct = self.always_constructs.pop()
                                self.dbg(
                                    "# Popping construct "
                                    + curr_construct
                                    + " for end\n"
                                )

                                if (
                                    curr_construct == "ALWAYS_FF_WITH_BEGIN"
                                    or curr_construct == "ALWAYS_COMBO_WITH_BEGIN"
                                ):
                                    # Resetting always block data
                                    inside_always_seq_block = 0
                                    inside_always_combo_block = 0

                                if curr_construct == "FOR_WITH_BEGIN":
                                    self.always_for_loop_count = (
                                        self.always_for_loop_count - 1
                                    )
                                    # Removing the last for loop element
                                    del self.always_for_loops[
                                        self.always_for_loop_count
                                    ]

                                if len(self.always_constructs) > 0:
                                    last_construct_loc = len(self.always_constructs) - 1
                                    curr_construct = self.always_constructs[
                                        last_construct_loc
                                    ]
                                else:
                                    curr_construct = ""

                                if (
                                    curr_construct == "FOR"
                                    or curr_construct == "FOR_WITH_BEGIN"
                                ):
                                    curr_for_construct = curr_construct
                                else:
                                    curr_for_construct = ""

                                # curr_construct should have the non for or for_with_begin construct
                                if (
                                    curr_for_construct == "FOR"
                                    or curr_for_construct == "FOR_WITH_BEGIN"
                                ):
                                    if len(self.always_constructs) > 0:
                                        for ii in range(
                                            len(self.always_constructs) - 2, 0, -1
                                        ):

                                            if (
                                                self.always_constructs[ii] != "FOR"
                                                and self.always_constructs[ii]
                                                != "FOR_WITH_BEGIN"
                                            ):
                                                curr_construct = self.always_constructs[
                                                    ii
                                                ]
                                                break

                                self.dbg(self.always_constructs)

                    ################################################################################
                    # Auto Instantiation
                    ################################################################################
                    # &beginInstance   <module_name>   [<instance_name>]     [<file_name>];
                    # &buildCommand    <build_commandline_option>;
                    # &param <submod_param>   <top_param/top_define/constant>;
                    # &connect  <sub_port_name>   <top_port_name>;
                    # &connect  <sub_port_name>   <CONSTANT>;
                    # &connect  <sub_port_name>;
                    # &connect  /*<search_pattern>/   /<replace_pattern>/;
                    # &connect  /<search_pattern>/;
                    # &connect  /<search_pattern>/   /<replace_pattern>/ INPUTS;
                    # &connect  /<search_pattern>/   /<replace_pattern>/ OUTPUTS;
                    # &endInstance;

                    line = re.sub(r"\s*;", ";", line)
                    begininstance_regex = RE_BEGININSTANCE.search(line)
                    endinstance_regex = RE_ENDINSTANCE.search(line)
                    buildcommand_regex = RE_BUILD_COMMAND.search(line)
                    include_regex = RE_INCLUDE.search(line)
                    param_override_regex = RE_PARAM_OVERRIDE.search(line)
                    connect_regex = RE_CONNECT.search(line)

                    if begininstance_regex:
                        look_for_instance_cmds = 1
                        begininstance_space = begininstance_regex.group(1)
                        begininstance_info = begininstance_regex.group(2)
                        begininstance_info = re.sub(r";", "", begininstance_info)
                        begininstance_info = re.sub(r"\s+", " ", begininstance_info)
                        begininstance_info = re.sub(r"^\s+", "", begininstance_info)
                        begininstance_info = re.sub(r"\s+$", "", begininstance_info)
                        begininstance_info_array = begininstance_info.split(" ")

                        file_name = ""
                        file_path = ""

                        if len(begininstance_info_array) == 3:
                            submod_name = begininstance_info_array[0]
                            inst_name = begininstance_info_array[1]
                            file_name = begininstance_info_array[2]
                        elif len(begininstance_info_array) == 2:
                            submod_name = begininstance_info_array[0]
                            inst_name = begininstance_info_array[1]
                        elif len(begininstance_info_array) == 1:
                            submod_name = begininstance_info_array[0]
                            inst_name = "u_" + submod_name

                        submod_format = ""

                        found_submod_file = 0

                        # Look for .psv if gen_dependencies enabled
                        if self.gen_dependencies:
                            # Look for .psv file
                            if file_name == "":
                                file_name_with_ext = submod_name + ".psv"
                            else:
                                file_name_with_ext = file_name

                            submod_file_with_path = file_name_with_ext

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )

                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_format = "PSV"
                                            submod_file_with_path = sub_mode_file_path

                            if not found_submod_file:
                                # Look for .pv file
                                if file_name == "":
                                    file_name_with_ext = submod_name + ".pv"
                                else:
                                    file_name_with_ext = file_name

                                submod_file_with_path = file_name_with_ext

                                if os.path.isfile(
                                    file_name_with_ext
                                ):  # In file doesn't exist
                                    found_submod_file = 1
                                    submod_file_with_path = file_name_with_ext
                                else:
                                    for dir in self.incl_dirs:
                                        if not found_submod_file:
                                            sub_mode_file_path = (
                                                str(dir) + "/" + str(file_name_with_ext)
                                            )

                                            if os.path.isfile(sub_mode_file_path):
                                                found_submod_file = 1
                                                submod_format = "PV"
                                                submod_file_with_path = (
                                                    sub_mode_file_path
                                                )

                        # Look for systemverilog module
                        if not found_submod_file:
                            if file_name == "":
                                file_name_with_ext = submod_name + ".sv"
                            else:
                                file_name_with_ext = file_name

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )

                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_format = "SV"
                                            submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            # Look for verilog module
                            if file_name == "":
                                file_name_with_ext = submod_name + ".v"
                            else:
                                file_name_with_ext = file_name

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )
                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_format = "V"
                                            submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            # Look for verilog module
                            if file_name == "":
                                file_name_with_ext = submod_name + ".vp"
                            else:
                                file_name_with_ext = file_name

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )
                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_format = "VP"
                                            submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            # Process 3rd-party .f files.
                            file_name_with_ext = f"{submod_name}.f"
                            self.dbg("\n  finding file list..." + file_name_with_ext)
                            # Only the memory files are supported currently.
                            third_party_incl_dirs = [
                                d
                                for d in self.incl_dirs
                                if "hls_rtl/" or "third_party/" in d
                            ]

                            for d in third_party_incl_dirs:
                                sub_mode_file_path = os.path.join(d, file_name_with_ext)
                                if os.path.isfile(sub_mode_file_path):
                                    self.filelist.extend(
                                        set(recursive_filelist(sub_mode_file_path))
                                    )
                                    found_submod_file = 1
                                    submod_format = "F"
                                    submod_file_with_path = sub_mode_file_path
                                    break  # Exit on first occurrence.

                        if not found_submod_file:
                            self.dbg(
                                "\nErrror: Unable to find the submodule "
                                + submod_name
                                + " in verilog/systemverilog format under following dirs"
                            )
                            self.dbg("  List of search directories")
                            print(
                                "\nError: Unable to find the submodule "
                                + submod_name
                                + " in verilog/systemverilog format under following dirs"
                            )
                            print("  List of search directories")

                            for dir in self.incl_dirs:
                                self.dbg("    " + str(dir))
                                print("    " + str(dir))
                            sys.exit(1)

                        submod_file_with_path = re.sub(
                            r"//", "/", submod_file_with_path
                        )
                        print(
                            "    - Instantiating MODULE: "
                            + submod_name
                            + " INST: "
                            + inst_name
                            + " FILE: "
                            + submod_file_with_path
                        )

                        if found_submod_file and self.gen_dependencies:
                            if (
                                submod_format == "V"
                                or submod_format == "SV"
                                or submod_format == "VP"
                                or submod_format == "F"
                            ):
                                if submod_file_with_path not in [
                                    keys
                                    for dicts in self.dependencies["verilog_subs"]
                                    for keys in dicts
                                ]:
                                    self.dependencies["verilog_subs"].append(
                                        {
                                            submod_file_with_path: {
                                                "mtime": getmtime(submod_file_with_path)
                                            }
                                        }
                                    )
                            else:
                                if (
                                    submod_file_with_path
                                    not in self.dependencies["veripy_subs"]
                                ):
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ] = {}
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["mtime"] = getmtime(submod_file_with_path)
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["flags"] = []

                        inc_dir = os.path.dirname(submod_file_with_path)
                        if inc_dir not in self.incl_dirs:
                            self.incl_dirs.append(inc_dir)

                        if submod_format == "F":
                            file_name_with_ext = f"{submod_name}.v"
                            verilog_pattern = re.compile(file_name_with_ext)
                            file_name_with_ext = f"{submod_name}.sv"
                            sverilog_pattern = re.compile(file_name_with_ext)

                            for line in open(submod_file_with_path):
                                if re.findall(verilog_pattern, line):
                                    submod_file_with_path = os.path.expandvars(
                                        line.strip("\n")
                                    )
                                elif re.findall(sverilog_pattern, line):
                                    submod_file_with_path = os.path.expandvars(
                                        line.strip("\n")
                                    )

                        ################################################################################
                        # Parsing submodule for ports and params
                        ################################################################################
                        # Initializing all the arrays and varibles for every submodule
                        self.sub_tick_defines = {}
                        self.sub_tick_ifdef_en = 1
                        self.sub_tick_ifdef_arr = []
                        self.sub_tick_decisions = []
                        self.sub_tick_types = []
                        self.sub_tick_served = []
                        self.sub_tick_curr_decision = 1
                        self.sub_tick_curr_type = ""
                        self.sub_tick_curr_served = 0
                        self.sub_last_tick_loc = 0

                        self.sub_packages = []
                        self.sub_packages.append("default")
                        self.sub_typedef_enums = {}
                        self.sub_typedef_logics = {}
                        self.sub_typedef_structs = {}
                        self.sub_typedef_unions = {}
                        self.sub_typedef_bindings = {}

                        # Initializing default package and class to avoid errors
                        self.sub_typedef_enums["default"] = {}
                        self.sub_typedef_enums["default"]["default"] = {}
                        self.sub_typedef_logics["default"] = {}
                        self.sub_typedef_logics["default"]["default"] = {}
                        self.sub_typedef_structs["default"] = {}
                        self.sub_typedef_structs["default"]["default"] = {}
                        self.sub_typedef_unions["default"] = {}
                        self.sub_typedef_unions["default"]["default"] = {}

                        self.sub_ports = {}
                        self.sub_params = {}
                        self.sub_include_files_list = []
                        sub_connect_cmds = []
                        sub_param_cmds = []

                        submod_file_with_path = re.sub(
                            r"//", "/", submod_file_with_path
                        )

                        if submod_format == "V":
                            submod_filelist = re.sub(
                                r"\.v$", ".f", submod_file_with_path
                            )
                        elif submod_format == "SV":
                            submod_filelist = re.sub(
                                r"\.sv$", ".f", submod_file_with_path
                            )
                        elif submod_format == "VP":
                            submod_filelist = re.sub(
                                r"\.vp$", ".f", submod_file_with_path
                            )

                        if (
                            submod_format == "V"
                            or submod_format == "SV"
                            or submod_format == "VP"
                        ):
                            if os.path.isfile(submod_filelist):
                                with open(submod_filelist, "r") as submod_filelist_data:

                                    for c_submod_file in submod_filelist_data:
                                        if c_submod_file not in self.filelist:
                                            if c_submod_file != "":
                                                self.filelist.append(c_submod_file)
                                    # Need to read the filelist and append to the current filelist

                        self.sub_inst_ports[inst_name] = {}
                        self.sub_inst_params[inst_name] = {}
                        self.sub_inst_files[inst_name] = submod_file_with_path
                        prev_line = ""

                        if self.gen_dependencies:
                            continue

                        continue
                    elif endinstance_regex:
                        look_for_instance_cmds = 0

                        if self.gen_dependencies:
                            continue

                        self.get_ports(submod_name, submod_file_with_path)

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# SUB PORTS :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_ports, indent=2))
                        self.dbg("\n")

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# SUB PARAM :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_params, indent=2))
                        self.dbg("\n")

                        for param_cmd in sub_param_cmds:
                            param_cmd = re.sub(r"\s+", "#", param_cmd, 1)

                            param_cmd_hash_regex = RE_HASH.search(param_cmd)

                            if param_cmd_hash_regex:
                                sub_param_name = param_cmd_hash_regex.group(1)
                                top_param_name = param_cmd_hash_regex.group(2)

                                if sub_param_name in self.sub_params:
                                    self.sub_inst_params[inst_name][sub_param_name] = {}
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "name"
                                    ] = sub_param_name
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "topname"
                                    ] = top_param_name
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "type"
                                    ] = self.sub_params[sub_param_name]["type"]
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "val"
                                    ] = self.sub_params[sub_param_name]["val"]
                                    # TODO: Need to recalculate the 'val' after param overriding
                                else:
                                    self.dbg(
                                        "\nError: Unable to find param "
                                        + sub_param_name
                                        + " in submodule "
                                        + submod_name
                                    )
                                    print(
                                        "\nError: Unable to find param "
                                        + sub_param_name
                                        + " in submodule "
                                        + submod_name
                                    )
                                    sys.exit(1)
                            else:
                                self.dbg(
                                    "\nError: Unable to parse &Param override call"
                                )
                                self.dbg(original_line)
                                print("\nError: Unable to parse &Param override call")
                                print(original_line)
                                self.found_error = 1

                        for c_port in self.sub_ports:
                            self.dbg(
                                "### "
                                + c_port
                                + " :: "
                                + self.sub_ports[c_port]["dir"]
                                + " :: "
                                + self.sub_ports[c_port]["bitdef"]
                                + " :: "
                                + str(self.sub_ports[c_port]["uwidth"])
                                + " :: "
                                + str(self.sub_ports[c_port]["lwidth"])
                                + " :: "
                                + (self.sub_ports[c_port]["depth"])
                                + " #"
                            )
                            self.sub_inst_ports[inst_name][c_port] = {}
                            self.sub_inst_ports[inst_name][c_port][
                                "name"
                            ] = self.sub_ports[c_port]["name"]
                            self.sub_inst_ports[inst_name][c_port][
                                "topname"
                            ] = self.sub_ports[c_port]["name"]
                            self.sub_inst_ports[inst_name][c_port][
                                "bitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
                            self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
                            self.sub_inst_ports[inst_name][c_port][
                                "uwidth"
                            ] = self.sub_ports[c_port]["uwidth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "lwidth"
                            ] = self.sub_ports[c_port]["lwidth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "depth"
                            ] = self.sub_ports[c_port]["depth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "dir"
                            ] = self.sub_ports[c_port]["dir"]
                            self.sub_inst_ports[inst_name][c_port][
                                "typedef"
                            ] = self.sub_ports[c_port]["typedef"]
                            self.sub_inst_ports[inst_name][c_port]["origconnect"] = ""
                            self.sub_inst_ports[inst_name][c_port]["comment"] = ""

                            ################################################################################
                            # Applying all the param overriding on each port
                            ################################################################################
                            c_topbitdef = self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ]

                            for c_param in self.sub_inst_params[inst_name].keys():
                                c_topparam = self.sub_inst_params[inst_name][c_param][
                                    "topname"
                                ]
                                c_param_search_str = "\\b" + c_param + "\\b"
                                c_topbitdef = re.sub(
                                    c_param_search_str, c_topparam, c_topbitdef
                                )

                            self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ] = c_topbitdef

                            # Check if the port bit def is a typedef
                            if (
                                self.sub_ports[c_port]["typedef"] != ""
                                and self.sub_ports[c_port]["typedef"] != "LOGIC"
                                and self.sub_ports[c_port]["typedef"] != "REG"
                                and self.sub_ports[c_port]["typedef"] != "WIRE"
                            ):
                                double_colon_regex = RE_DOUBLE_COLON.search(
                                    self.sub_ports[c_port]["bitdef"]
                                )
                                double_double_colon_regex = (
                                    RE_DOUBLE_DOUBLE_COLON.search(
                                        self.sub_ports[c_port]["bitdef"]
                                    )
                                )
                                c_port_typedef = self.sub_ports[c_port]["typedef"]

                                if double_double_colon_regex:
                                    c_port_package = double_colon_regex.group(1)
                                    c_port_class = double_colon_regex.group(2)
                                    c_port_typedef = double_colon_regex.group(3)
                                elif double_colon_regex:
                                    if double_colon_regex.group(1) in list(
                                        self.classes
                                    ):
                                        c_port_package = "default"
                                        c_port_class = double_colon_regex.group(1)
                                        c_port_typedef = double_colon_regex.group(2)
                                    else:
                                        c_port_package = double_colon_regex.group(1)
                                        c_port_class = "default"
                                        c_port_typedef = double_colon_regex.group(2)

                                    if (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_LOGIC"
                                    ):
                                        if self.auto_package_load:
                                            if (
                                                c_port_package
                                                not in self.typedef_logics
                                            ):
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    c_port_package + ".sv",
                                                )

                                        # Checking if package is present
                                        if c_port_package in self.typedef_logics:
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_logics[c_port_package][
                                                    c_port_class
                                                ]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                print(
                                                    "\nWarning: Unable to find - PACKAGE: "
                                                    + c_port_package
                                                    + ", TYPEDEF_LOGIC: "
                                                    + c_port_typedef
                                                    + "\n"
                                                )
                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                    elif (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_STRUCT"
                                    ):
                                        typedef_ref_regex = (
                                            RE_TYPEDEF_DOUBLE_COLON.search(
                                                self.sub_ports[c_port]["bitdef"]
                                            )
                                        )
                                        typedef_ref_regex_double = (
                                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                                self.sub_ports[c_port]["bitdef"]
                                            )
                                        )

                                        if self.auto_package_load:
                                            if (
                                                c_port_package
                                                not in self.typedef_structs
                                            ):
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    c_port_package + ".sv",
                                                )

                                        # Checking if package is present
                                        if c_port_package in self.typedef_structs:
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_structs[c_port_package][
                                                    c_port_class
                                                ]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                print(
                                                    "\nWarning: Unable to find - PACKAGE: "
                                                    + c_port_package
                                                    + ", TYPEDEF_STRUCT: "
                                                    + c_port_typedef
                                                    + "\n"
                                                )
                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""

                                    elif (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_UNION"
                                    ):
                                        if self.auto_package_load:
                                            if (
                                                c_port_package
                                                not in self.typedef_unions
                                            ):
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    c_port_package + ".sv",
                                                )

                                        # Checking if package is present
                                        if c_port_package in self.typedef_unions:
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_unions[c_port_package][
                                                    c_port_class
                                                ]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                print(
                                                    "\nWarning: Unable to find - PACKAGE: "
                                                    + c_port_package
                                                    + ", TYPEDEF_UNION: "
                                                    + c_port_typedef
                                                    + "\n"
                                                )

                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                else:
                                    # Check if the typedef is part of default package
                                    if c_port_typedef in self.typedef_logics["default"]:
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    elif (
                                        c_port_typedef
                                        in self.typedef_structs["default"]
                                    ):
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    elif (
                                        c_port_typedef in self.typedef_unions["default"]
                                    ):
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    else:  # now check for o
                                        sub_io_bitdef_val = self.tickdef_param_getval(
                                            "TOP",
                                            self.sub_ports[c_port]["bitdef"],
                                            "",
                                            "",
                                        )

                                        if sub_io_bitdef_val[0] == "STRING":
                                            # Checking if the bitdef has the multi dimentional array
                                            io_bitdef_packed_regex = (
                                                RE_PACKED_ARRAY.search(
                                                    self.sub_ports[c_port]["bitdef"]
                                                )
                                            )

                                            if io_bitdef_packed_regex:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                        else:
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ] = self.sub_ports[c_port]["bitdef"]
                            else:
                                # Update uwidth and lwidth after param override
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    sub_io_bitdef_val = self.tickdef_param_getval(
                                        "TOP",
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ],
                                        "",
                                        "",
                                    )

                                    if sub_io_bitdef_val[0] == "STRING":
                                        # Checking if the bitdef has the multi dimentional array
                                        io_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                            self.sub_ports[c_port]["bitdef"]
                                        )

                                        if not io_bitdef_packed_regex:
                                            if (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "uwidth"
                                                ]
                                                == ""
                                                or self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["lwidth"]
                                                == ""
                                            ):
                                                print(
                                                    "Warning: Unable to bring the bitdef from submodule to top"
                                                )
                                                print(
                                                    "  # Port: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["name"]
                                                    + "   Bitdef: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                print(
                                                    "Warning: Unable to bring the bitdef from submodule to top"
                                                )
                                                print(
                                                    "  # Port: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["name"]
                                                    + "   Bitdef: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  ## UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                    else:
                                        if sub_io_bitdef_val[0] == "BITDEF":
                                            # Updating numberical values of upper and lower width
                                            bitdef_colon_regex = RE_COLON.search(
                                                str(sub_io_bitdef_val[1])
                                            )
                                            self.sub_inst_ports[inst_name][c_port][
                                                "uwidth"
                                            ] = bitdef_colon_regex.group(1)
                                            self.sub_inst_ports[inst_name][c_port][
                                                "lwidth"
                                            ] = bitdef_colon_regex.group(2)

                                            c_topbitdef = self.sub_inst_ports[
                                                inst_name
                                            ][c_port]["topbitdef"]
                                            c_topbitdef = re.sub(r":", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"-", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\+", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\(", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\)", "", c_topbitdef)

                                            topbitdef_numbers_regex = (
                                                RE_NUMBERS_ONLY.search(c_topbitdef)
                                            )

                                            if topbitdef_numbers_regex:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  ## UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                        else:  # NUMBER
                                            self.sub_inst_ports[inst_name][c_port][
                                                "uwidth"
                                            ] = sub_io_bitdef_val[1]
                                            self.sub_inst_ports[inst_name][c_port][
                                                "lwidth"
                                            ] = sub_io_bitdef_val[1]

                        ################################################################################
                        # Applying all the connect commands
                        ################################################################################
                        for connect_cmd in sub_connect_cmds:
                            single_line_comment_regex = re.search(
                                RE_SINGLE_LINE_COMMENT, connect_cmd
                            )

                            connect_comment = ""

                            if single_line_comment_regex:
                                connect_comment = single_line_comment_regex.group(1)
                                connect_cmd = re.sub(" //.*?$", "", connect_cmd)

                            connect_cmd = re.sub(r";", "", connect_cmd)
                            connect_cmd = re.sub(r"\s+", " ", connect_cmd)
                            connect_cmd = re.sub(r"^\s*", "", connect_cmd)
                            connect_cmd = re.sub(r"\s*$", "", connect_cmd)
                            slash_replace_str = 0

                            self.dbg("### CONNECT :: " + connect_cmd)

                            connect_cmd_array = connect_cmd.split(" ")

                            connect_filter = ""
                            replace_expr_str = ""
                            replace_direct_str = ""

                            if len(connect_cmd_array) > 2:
                                connect_filter = connect_cmd_array[2]

                                replace_slash_regex = RE_REGEX_SLASH.search(
                                    connect_cmd_array[1]
                                )

                                if replace_slash_regex:
                                    replace_expr_str = replace_slash_regex.group(1)
                                    slash_replace_str = 1
                                else:
                                    replace_direct_str = connect_cmd_array[1]
                            elif len(connect_cmd_array) > 1:
                                replace_slash_regex = RE_REGEX_SLASH.search(
                                    connect_cmd_array[1]
                                )

                                if replace_slash_regex:
                                    replace_expr_str = replace_slash_regex.group(1)
                                    slash_replace_str = 1
                                else:
                                    replace_direct_str = connect_cmd_array[1]
                            else:
                                replace_expr_str = ""
                                replace_direct_str = ""

                            replace_direct_str = re.sub(r"\"", "", replace_direct_str)
                            search_slash_regex = RE_REGEX_SLASH.search(
                                connect_cmd_array[0]
                            )

                            if (
                                search_slash_regex
                            ):  # Regular expression on the connect syntax
                                search_expr_str = search_slash_regex.group(1)
                                # search_expr_str = 'r\"' + search_slash_regex.group(1) +'\"'

                                self.dbg(
                                    "  # SEARCH_EXPR: "
                                    + search_expr_str
                                    + "; REPLACE_EXPR: "
                                    + replace_expr_str
                                    + "; TOP_NAME: "
                                    + replace_direct_str
                                    + "; FILTER: "
                                    + connect_filter
                                    + ";"
                                )
                                RE_SEARCH_EXPR_REGEX = re.compile(search_expr_str)
                                for c_port in self.sub_inst_ports[inst_name].keys():
                                    # Skipping ports that are not matching the port direction filter
                                    if (
                                        connect_filter == "INPUTS"
                                        and self.sub_inst_ports[inst_name][c_port][
                                            "dir"
                                        ]
                                        == "output"
                                    ):
                                        continue
                                    elif (
                                        connect_filter == "OUTPUTS"
                                        and self.sub_inst_ports[inst_name][c_port][
                                            "dir"
                                        ]
                                        == "input"
                                    ):
                                        continue

                                    c_port_regex = RE_SEARCH_EXPR_REGEX.search(c_port)

                                    if (
                                        c_port_regex
                                    ):  # if matching the regular expression
                                        self.dbg("    # Matched Port: " + c_port)

                                        if slash_replace_str:
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ] = re.sub(
                                                search_expr_str,
                                                replace_expr_str,
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "name"
                                                ],
                                            )
                                            self.sub_inst_ports[inst_name][c_port][
                                                "origconnect"
                                            ] = ""
                                            self.dbg(
                                                "      # UPDATED TOP NAME: "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topname"]
                                            )
                                            self.sub_inst_ports[inst_name][c_port][
                                                "comment"
                                            ] = connect_comment

                                        else:
                                            if replace_direct_str != "":
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "origconnect"
                                                ] = replace_direct_str
                                                topname_is_concat_regex = (
                                                    RE_OPEN_CURLY.search(
                                                        replace_direct_str
                                                    )
                                                )
                                                topname_has_tick_regex = (
                                                    RE_NUM_TICK.search(
                                                        replace_direct_str
                                                    )
                                                )
                                                topname_is_constant_regex = (
                                                    RE_CONSTANT.search(
                                                        replace_direct_str
                                                    )
                                                )
                                                topname_is_define_regex = (
                                                    RE_DEFINE_TICK_BEGIN.search(
                                                        replace_direct_str
                                                    )
                                                )
                                                topname_has_dot_regex = RE_DOT.search(
                                                    replace_direct_str
                                                )

                                                # If this is a constant or param or define or concat of signals, then topbitdef should be empty
                                                if (
                                                    topname_is_concat_regex
                                                    or topname_has_tick_regex
                                                    or topname_is_constant_regex
                                                    or topname_is_define_regex
                                                    or topname_has_dot_regex
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""

                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ] = replace_direct_str
                                                self.dbg(
                                                    "      # UPDATED TOP NAME: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                )
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "comment"
                                                ] = connect_comment
                                            else:  # Unconnected port
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ] = ""
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                                self.dbg(
                                                    "      # UNCONNECTED PORT AT TOP"
                                                )
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "comment"
                                                ] = connect_comment
                            else:  # Direct mapping of port
                                search_direct_str = connect_cmd_array[0]

                                if search_direct_str in self.sub_inst_ports[inst_name]:
                                    # Skipping port that is not matching the port direction filter
                                    if (
                                        connect_filter == "INPUTS"
                                        and self.sub_inst_ports[inst_name][
                                            search_direct_str
                                        ]["dir"]
                                        == "output"
                                    ):
                                        pass
                                    elif (
                                        connect_filter == "OUTPUTS"
                                        and self.sub_inst_ports[inst_name][
                                            search_direct_str
                                        ]["dir"]
                                        == "input"
                                    ):
                                        pass
                                    else:
                                        if replace_direct_str != "":
                                            # TODO: Need to update topbitdef from connect
                                            topname_is_concat_regex = (
                                                RE_OPEN_CURLY.search(replace_direct_str)
                                            )
                                            topname_has_tick_regex = RE_NUM_TICK.search(
                                                replace_direct_str
                                            )
                                            topname_is_constant_regex = (
                                                RE_CONSTANT.search(replace_direct_str)
                                            )
                                            topname_is_define_regex = (
                                                RE_DEFINE_TICK_BEGIN.search(
                                                    replace_direct_str
                                                )
                                            )
                                            topname_has_dot_regex = RE_DOT.search(
                                                replace_direct_str
                                            )
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["origconnect"] = replace_direct_str

                                            # If this is a constant or param or define or concat of signals, then topbitdef should be empty
                                            if (
                                                topname_is_concat_regex
                                                or topname_has_tick_regex
                                                or topname_is_constant_regex
                                                or topname_is_define_regex
                                                or topname_has_dot_regex
                                            ):
                                                self.sub_inst_ports[inst_name][
                                                    search_direct_str
                                                ]["topbitdef"] = ""
                                                self.sub_inst_ports[inst_name][
                                                    search_direct_str
                                                ]["topname"] = replace_direct_str
                                                self.sub_inst_ports[inst_name][
                                                    search_direct_str
                                                ]["comment"] = connect_comment
                                            else:
                                                topname_bitdef_regex = (
                                                    RE_OPEN_SQBRCT_BITDEF.search(
                                                        replace_direct_str
                                                    )
                                                )

                                                if topname_bitdef_regex:
                                                    self.sub_inst_ports[inst_name][
                                                        search_direct_str
                                                    ][
                                                        "topname"
                                                    ] = topname_bitdef_regex.group(
                                                        1
                                                    )
                                                    topbitdef_tmp = (
                                                        topname_bitdef_regex.group(2)
                                                    )
                                                    topbitdef_tmp = re.sub(
                                                        r"]$", "", topbitdef_tmp
                                                    )
                                                    self.sub_inst_ports[inst_name][
                                                        search_direct_str
                                                    ]["topbitdef"] = topbitdef_tmp
                                                    self.sub_inst_ports[inst_name][
                                                        search_direct_str
                                                    ]["comment"] = connect_comment
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        search_direct_str
                                                    ]["topname"] = replace_direct_str
                                                    self.sub_inst_ports[inst_name][
                                                        search_direct_str
                                                    ]["comment"] = connect_comment

                                            self.dbg(
                                                "      # UPDATED TOP NAME: "
                                                + self.sub_inst_ports[inst_name][
                                                    search_direct_str
                                                ]["topname"]
                                            )
                                        else:  # Unconnected port
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["topname"] = ""
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["topbitdef"] = ""
                                            self.dbg("      # UNCONNECTED PORT AT TOP")
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["comment"] = connect_comment
                                else:
                                    self.dbg(
                                        "\nError: Unable to find submodule port "
                                        + search_direct_str
                                        + " in submodule "
                                        + submod_name
                                    )
                                    print(
                                        "\nError: Unable to find submodule port "
                                        + search_direct_str
                                        + " in submodule "
                                        + submod_name
                                    )
                                    sys.exit(1)
                                    self.found_error = 1
                                    # sys.exit(1)

                        # print(json.dumps(self.sub_inst_ports[inst_name], indent=2))

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# TOP MAPPED SUB PORTS :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_inst_ports[inst_name], indent=2))
                        self.dbg("\n")
                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# TOP MAPPED SUB PARAMS :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_inst_params[inst_name], indent=2))
                        self.dbg("\n")

                        for c_port in self.sub_inst_ports[inst_name]:
                            if (
                                self.sub_inst_ports[inst_name][c_port]["dir"]
                                == "output"
                            ):
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    io_double_colon_regex = (
                                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                        )
                                    )
                                    io_double_double_colon_regex = RE_SUBPORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ]
                                    )

                                    if (
                                        io_double_double_colon_regex
                                        or io_double_colon_regex
                                    ):
                                        io_bind_package = "default"
                                        io_bind_class = "default"

                                        if io_double_double_colon_regex:
                                            io_bind_package = (
                                                io_double_double_colon_regex.group(1)
                                            )
                                            io_bind_class = (
                                                io_double_double_colon_regex.group(2)
                                            )
                                            io_bind_typedef = (
                                                io_double_double_colon_regex.group(3)
                                            )

                                            if io_bind_package not in self.packages:
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    io_bind_package + ".sv",
                                                )

                                            self.binding_typedef(
                                                "TOP",
                                                "FORCE",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ]
                                                + "] "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topname"],
                                            )
                                        else:
                                            io_bind_package = (
                                                io_double_colon_regex.group(1)
                                            )
                                            io_bind_typedef = (
                                                io_double_colon_regex.group(2)
                                            )

                                            if io_bind_package not in self.packages:
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    io_bind_package + ".sv",
                                                )

                                            self.binding_typedef(
                                                "TOP",
                                                "FORCE",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ]
                                                + "] "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topname"],
                                            )

                                        if self.parsing_format == "verilog":
                                            self.parse_signal(
                                                "wire",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                                0,
                                            )
                                        else:
                                            self.parse_signal(
                                                "reg",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                                0,
                                            )
                                    elif (
                                        self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_LOGIC"
                                        or self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_STRUCT"
                                        or self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_UNION"
                                    ):

                                        self.sub_inst_ports[inst_name][c_port][
                                            "topname"
                                        ] = re.sub(
                                            r"[{}\s]",
                                            "",
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ],
                                        )

                                        if (
                                            self.sub_inst_ports[inst_name][c_port][
                                                "depth"
                                            ]
                                            == ""
                                        ):
                                            if (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                not in self.typedef_bindings
                                            ):
                                                self.binding_typedef(
                                                    "TOP",
                                                    "FORCE",
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + " "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"],
                                                )
                                        else:
                                            if (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                not in self.typedef_bindings
                                            ):
                                                self.binding_typedef(
                                                    "TOP",
                                                    "FORCE",
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + " "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                    + "["
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["depth"]
                                                    + "]",
                                                )

                                        if self.parsing_format == "verilog":
                                            self.parse_signal(
                                                "wire",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                                0,
                                            )
                                        else:
                                            self.parse_signal(
                                                "reg",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                                0,
                                            )
                                    else:
                                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )
                                        topname_comma_regex = RE_COMMA.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )

                                        if topname_comma_regex:
                                            topname_assign_str_array = []
                                            # If multiple declarations on the same line, then break it
                                            # removing space, { and }
                                            topname_assign_str = re.sub(
                                                r"[{}\s]",
                                                "",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                            )
                                            topname_assign_str_array = (
                                                topname_assign_str.split(",")
                                            )

                                            for (
                                                curr_topname
                                            ) in topname_assign_str_array:
                                                if self.parsing_format == "verilog":
                                                    self.parse_signal(
                                                        "wire", curr_topname, 0
                                                    )
                                                else:
                                                    self.parse_signal(
                                                        "reg", curr_topname, 0
                                                    )
                                        else:  # Single declaration, then append to the array
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ] = re.sub(
                                                r"[{}\s]",
                                                "",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ],
                                            )

                                            if topname_bitdef_regex:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ] = re.sub(
                                                    r"[{}\s]",
                                                    "",
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"],
                                                )
                                                if self.parsing_format == "verilog":
                                                    self.parse_signal(
                                                        "wire",
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["topname"],
                                                        0,
                                                    )
                                                else:
                                                    self.parse_signal(
                                                        "reg",
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["topname"],
                                                        0,
                                                    )
                                            else:
                                                # TODO: Need to do param overriding replacement on topbitdef
                                                topname_assign_str = (
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                    + "["
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + "]"
                                                )

                                                if (
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["depth"]
                                                    == ""
                                                ):
                                                    if self.parsing_format == "verilog":
                                                        self.parse_signal(
                                                            "wire",
                                                            topname_assign_str,
                                                            0,
                                                        )
                                                    else:
                                                        self.parse_signal(
                                                            "reg", topname_assign_str, 0
                                                        )
                                                else:
                                                    c_top_name = self.sub_inst_ports[
                                                        inst_name
                                                    ][c_port]["topname"]

                                                    # If depth presents, then use sub mod bit definition
                                                    if self.parsing_format == "verilog":
                                                        self.wires[c_top_name] = {}
                                                        self.wires[c_top_name][
                                                            "name"
                                                        ] = c_top_name
                                                        self.wires[c_top_name][
                                                            "bitdef"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "topbitdef"
                                                        ]
                                                        self.wires[c_top_name][
                                                            "uwidth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "uwidth"
                                                        ]
                                                        self.wires[c_top_name][
                                                            "lwidth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "lwidth"
                                                        ]
                                                        self.wires[c_top_name][
                                                            "mode"
                                                        ] = "AUTO"
                                                        self.wires[c_top_name][
                                                            "depth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "depth"
                                                        ]
                                                        self.wires[c_top_name][
                                                            "signed"
                                                        ] = ""
                                                        self.dbg(
                                                            "    # NEW WIRE :: "
                                                            + self.wires[c_top_name][
                                                                "name"
                                                            ]
                                                            + " # "
                                                            + self.wires[c_top_name][
                                                                "mode"
                                                            ]
                                                            + " # "
                                                            + self.wires[c_top_name][
                                                                "bitdef"
                                                            ]
                                                            + " # "
                                                            + str(
                                                                self.wires[c_top_name][
                                                                    "uwidth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + str(
                                                                self.wires[c_top_name][
                                                                    "lwidth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + str(
                                                                self.wires[c_top_name][
                                                                    "depth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + self.wires[c_top_name][
                                                                "signed"
                                                            ]
                                                            + " #"
                                                        )
                                                    else:
                                                        self.parse_signal(
                                                            "reg", topname_assign_str, 0
                                                        )
                                                        self.regs[c_top_name] = {}
                                                        self.regs[c_top_name][
                                                            "name"
                                                        ] = c_top_name
                                                        self.regs[c_top_name][
                                                            "bitdef"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "topbitdef"
                                                        ]
                                                        self.regs[c_top_name][
                                                            "uwidth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "uwidth"
                                                        ]
                                                        self.regs[c_top_name][
                                                            "lwidth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "lwidth"
                                                        ]
                                                        self.regs[c_top_name][
                                                            "mode"
                                                        ] = "AUTO"
                                                        self.regs[c_top_name][
                                                            "depth"
                                                        ] = self.sub_inst_ports[
                                                            inst_name
                                                        ][
                                                            c_port
                                                        ][
                                                            "depth"
                                                        ]
                                                        self.regs[c_top_name][
                                                            "signed"
                                                        ] = ""
                                                        self.dbg(
                                                            "    # NEW REG :: "
                                                            + self.regs[c_top_name][
                                                                "name"
                                                            ]
                                                            + " # "
                                                            + self.regs[c_top_name][
                                                                "mode"
                                                            ]
                                                            + " # "
                                                            + self.regs[c_top_name][
                                                                "bitdef"
                                                            ]
                                                            + " # "
                                                            + str(
                                                                self.regs[c_top_name][
                                                                    "uwidth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + str(
                                                                self.regs[c_top_name][
                                                                    "lwidth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + str(
                                                                self.regs[c_top_name][
                                                                    "depth"
                                                                ]
                                                            )
                                                            + " # "
                                                            + self.regs[c_top_name][
                                                                "signed"
                                                            ]
                                                            + " #"
                                                        )

                                else:
                                    topname_assign_str = self.sub_inst_ports[inst_name][
                                        c_port
                                    ]["topname"]

                                    # topname can be concat of two or more signals
                                    topname_assign_comma_regex = RE_COMMA.search(
                                        topname_assign_str
                                    )

                                    topname_assign_str_array = []
                                    # If multiple declarations on the same line, then break it
                                    if topname_assign_comma_regex:
                                        # removing space, { and }
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array = (
                                            topname_assign_str.split(",")
                                        )
                                    else:  # Single declaration, then append to the array
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array.append(
                                            topname_assign_str
                                        )

                                    for curr_topname in topname_assign_str_array:
                                        if self.parsing_format == "verilog":
                                            self.parse_signal("wire", curr_topname, 0)
                                        else:
                                            self.parse_signal("reg", curr_topname, 0)
                            elif (
                                self.sub_inst_ports[inst_name][c_port]["dir"] == "input"
                            ):  # Sub module port is an input
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    io_double_colon_regex = (
                                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                        )
                                    )
                                    io_double_double_colon_regex = RE_SUBPORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ]
                                    )

                                    if (
                                        io_double_double_colon_regex
                                        or io_double_colon_regex
                                    ):
                                        io_bind_package = "default"
                                        io_bind_class = "default"

                                        if io_double_double_colon_regex:
                                            io_bind_package = (
                                                io_double_double_colon_regex.group(1)
                                            )
                                            io_bind_class = (
                                                io_double_double_colon_regex.group(2)
                                            )
                                            io_bind_typedef = (
                                                io_double_double_colon_regex.group(3)
                                            )

                                            if io_bind_package not in self.packages:
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    io_bind_package + ".sv",
                                                )

                                            self.binding_typedef(
                                                "TOP",
                                                "FORCE",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ]
                                                + "] "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topname"],
                                            )
                                        else:
                                            io_bind_package = (
                                                io_double_colon_regex.group(1)
                                            )
                                            io_bind_typedef = (
                                                io_double_colon_regex.group(2)
                                            )

                                            if io_bind_package not in self.packages:
                                                self.load_import_or_include_file(
                                                    "TOP",
                                                    "IMPORT_COMMANDLINE",
                                                    io_bind_package + ".sv",
                                                )

                                            self.binding_typedef(
                                                "TOP",
                                                "FORCE",
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ]
                                                + "] "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topname"],
                                            )

                                        self.parse_conditions(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )
                                    elif (
                                        self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_LOGIC"
                                        or self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_STRUCT"
                                        or self.sub_inst_ports[inst_name][c_port][
                                            "typedef"
                                        ]
                                        == "TYPEDEF_UNION"
                                    ):
                                        if (
                                            self.sub_inst_ports[inst_name][c_port][
                                                "depth"
                                            ]
                                            == ""
                                        ):
                                            if (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                not in self.typedef_bindings
                                            ):
                                                self.binding_typedef(
                                                    "TOP",
                                                    "FORCE",
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + " "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"],
                                                )
                                        else:
                                            if (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                not in self.typedef_bindings
                                            ):
                                                self.binding_typedef(
                                                    "TOP",
                                                    "FORCE",
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + " "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                    + "["
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["depth"]
                                                    + "]",
                                                )

                                        self.parse_conditions(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )
                                    else:
                                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )
                                        topname_comma_regex = RE_COMMA.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )

                                        if topname_comma_regex:
                                            topname_assign_str_array = []
                                            # If multiple declarations on the same line, then break it
                                            # removing space, { and }
                                            topname_assign_str = re.sub(
                                                r"[{}\s]", "", topname_assign_str
                                            )
                                            topname_assign_str_array = (
                                                topname_assign_str.split(",")
                                            )

                                            for (
                                                curr_topname
                                            ) in topname_assign_str_array:
                                                self.parse_conditions(curr_topname)
                                        else:  # Single declaration, then append to the array
                                            if topname_bitdef_regex:
                                                self.parse_conditions(
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                )
                                            else:
                                                # TODO: Need to do param overriding replacement on topbitdef
                                                topname_assign_str = (
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topname"]
                                                    + "["
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                    + "]"
                                                )

                                                if (
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["depth"]
                                                    == ""
                                                ):
                                                    self.parse_conditions(
                                                        topname_assign_str
                                                    )
                                                else:
                                                    c_top_name = self.sub_inst_ports[
                                                        inst_name
                                                    ][c_port]["topname"]
                                                    self.signals[c_top_name] = {}
                                                    self.signals[c_top_name][
                                                        "name"
                                                    ] = c_top_name
                                                    self.signals[c_top_name][
                                                        "bitdef"
                                                    ] = self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ][
                                                        "topbitdef"
                                                    ]
                                                    self.signals[c_top_name][
                                                        "uwidth"
                                                    ] = self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ][
                                                        "uwidth"
                                                    ]
                                                    self.signals[c_top_name][
                                                        "lwidth"
                                                    ] = self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ][
                                                        "lwidth"
                                                    ]
                                                    self.signals[c_top_name][
                                                        "mode"
                                                    ] = "AUTO"
                                                    self.signals[c_top_name][
                                                        "depth"
                                                    ] = self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ][
                                                        "depth"
                                                    ]
                                                    self.signals[c_top_name][
                                                        "signed"
                                                    ] = ""
                                                    self.dbg(
                                                        "    # NEW SIGNAL :: "
                                                        + self.signals[c_top_name][
                                                            "name"
                                                        ]
                                                        + " # "
                                                        + self.signals[c_top_name][
                                                            "mode"
                                                        ]
                                                        + " # "
                                                        + self.signals[c_top_name][
                                                            "bitdef"
                                                        ]
                                                        + " # "
                                                        + str(
                                                            self.signals[c_top_name][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + " # "
                                                        + str(
                                                            self.signals[c_top_name][
                                                                "lwidth"
                                                            ]
                                                        )
                                                        + " # "
                                                        + str(
                                                            self.signals[c_top_name][
                                                                "depth"
                                                            ]
                                                        )
                                                        + " # "
                                                        + self.signals[c_top_name][
                                                            "signed"
                                                        ]
                                                        + " #"
                                                    )
                                else:
                                    self.parse_conditions(
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topname"
                                        ]
                                    )
                            else:  # Sub module port is an inout
                                c_top_name = self.sub_inst_ports[inst_name][c_port][
                                    "topname"
                                ]
                                if c_port not in self.ports:
                                    # print(self.ports[c_top_name])
                                    self.ports[c_top_name] = {}
                                    self.ports[c_top_name]["name"] = c_top_name
                                    self.ports[c_top_name]["dir"] = "inout"
                                    self.ports[c_top_name][
                                        "bitdef"
                                    ] = self.sub_inst_ports[inst_name][c_port][
                                        "topbitdef"
                                    ]
                                    self.ports[c_top_name][
                                        "uwidth"
                                    ] = self.sub_inst_ports[inst_name][c_port]["uwidth"]
                                    self.ports[c_top_name][
                                        "lwidth"
                                    ] = self.sub_inst_ports[inst_name][c_port]["lwidth"]
                                    self.ports[c_top_name]["mode"] = "AUTO"
                                    self.ports[c_top_name][
                                        "depth"
                                    ] = self.sub_inst_ports[inst_name][c_port]["depth"]
                                    self.ports[c_top_name]["signed"] = ""
                                    self.ports[c_top_name]["typedef"] = ""
                                    self.dbg(
                                        "    # NEW PORT :: "
                                        + self.ports[c_top_name]["name"]
                                        + " # "
                                        + self.ports[c_top_name]["dir"]
                                        + " # "
                                        + self.ports[c_top_name]["mode"]
                                        + " # "
                                        + self.ports[c_top_name]["bitdef"]
                                        + " # "
                                        + str(self.ports[c_top_name]["uwidth"])
                                        + " # "
                                        + str(self.ports[c_top_name]["lwidth"])
                                        + " # "
                                        + str(self.ports[c_top_name]["depth"])
                                        + " # "
                                        + self.ports[c_top_name]["signed"]
                                        + " #"
                                    )

                        self.filelist.append(submod_file_with_path)

                    elif look_for_instance_cmds:
                        if connect_regex:
                            if self.gen_dependencies:
                                continue

                            single_line_comment_regex = re.search(
                                RE_SINGLE_LINE_COMMENT, line
                            )

                            if single_line_comment_regex:
                                sub_connect_cmds.append(
                                    connect_regex.group(1)
                                    + " //"
                                    + single_line_comment_regex.group(1)
                                )
                            else:
                                sub_connect_cmds.append(connect_regex.group(1))
                        elif param_override_regex:
                            # Gather the list of param overrides to process after gathering ports and params of sub-modules
                            sub_param_cmds.append(param_override_regex.group(1))

                            if self.gen_dependencies:
                                continue

                        elif buildcommand_regex:
                            build_cmd = buildcommand_regex.group(1)
                            if self.gen_dependencies:
                                if (
                                    build_cmd
                                    not in self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["flags"]
                                ):
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["flags"].append(build_cmd)

                            continue
                        elif include_regex:
                            loadincludefiles = include_regex.group(1)
                            self.sub_include_files_list = loadincludefiles.split()

                            # if gen_dependencies:
                            # self.sub_include_files_list = loadincludefiles.split()

                            # for c_incl in self.sub_include_files_list:
                            # self.dependencies['include_files'].append(c_incl)

                            continue

                        prev_line = ""
                        continue

                    ################################################################################
                    # Detect typedef usages
                    ################################################################################
                    typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(line)

                    found_in_typedef = ""
                    if typedef_ref_regex:
                        if semicolon_regex:
                            self.binding_typedef("TOP", "MANUAL", line)

                            continue
                        else:
                            gather_till_semicolon = 1
                            prev_line = line
                            prev_original_line = original_line
                            prev_line_no = line_no
                            continue

                    ################################################################################
                    # Check if endmodule declaration by user
                    ################################################################################
                    endmodule_regex = RE_END_MODULE_DECLARATION.search(line)

                    if endmodule_regex:
                        # Resetting always block data since its hard to track without begin
                        inside_always_seq_block = 0
                        inside_always_combo_block = 0
                        self.always_constructs = []
                        continue

                    ################################################################################
                    # Skipping some keywords
                    ################################################################################
                    begin_in_begin_regex = RE_BEGIN_IN_BEGIN.search(line)
                    end_in_begin_regex = RE_END_IN_BEGIN.search(line)
                    if_in_begin_regex = RE_IF_IN_BEGIN.search(line)
                    elseif_in_begin_regex = RE_ELSEIF_IN_BEGIN.search(line)
                    else_in_begin_regex = RE_ELSE_IN_BEGIN.search(line)
                    empty_line_regex = RE_EMPTY_LINE.search(line)
                    ampersand_in_begin_regex = RE_AMBERSAND_IN_BEGIN.search(line)

                    if (
                        begin_in_begin_regex
                        or end_in_begin_regex
                        or if_in_begin_regex
                        or elseif_in_begin_regex
                        or else_in_begin_regex
                        or empty_line_regex
                        or ampersand_in_begin_regex
                    ):
                        prev_line = line
                        prev_original_line = original_line
                        prev_line_no = line_no
                        continue

                    ################################################################################
                    # Manual Instantiation
                    ################################################################################
                    if gather_manual_instance:
                        semicolon_regex = RE_SEMICOLON.search(line)

                        if semicolon_regex:
                            gather_manual_instance = 0
                            manual_instance_line = manual_instance_line + line
                            parse_manual_instance = 1
                        else:
                            manual_instance_line = manual_instance_line + line
                            continue

                    line = line + " "
                    manual_module_regex = RE_MANUAL_MODULE.search(line)
                    manual_module_end_regex = RE_MANUAL_MODULE_END.search(line)

                    if manual_module_regex and parse_manual_instance == 0:
                        module_with_tick_define_regex = RE_DEFINE_TICK_EXTRACT.search(
                            line
                        )

                        if module_with_tick_define_regex:
                            manual_module_name_check = self.get_tick_defval(
                                module_with_tick_define_regex.group(1)
                            )
                        else:
                            manual_module_name_check = manual_module_regex.group(1)

                        submod_file_with_path = self.find_manual_submod(
                            self.gen_dependencies, manual_module_name_check
                        )

                        if submod_file_with_path != 0:
                            gather_manual_instance = 1
                            submod_name = manual_module_name_check
                            inst_name = manual_module_name_check
                            manual_instance_line = line
                            semicolon_regex = RE_SEMICOLON.search(line)

                            if semicolon_regex:
                                gather_manual_instance = 0
                                parse_manual_instance = 1
                            else:
                                continue
                        else:
                            gather_manual_instance = 0

                    elif manual_module_end_regex and parse_manual_instance == 0:
                        submod_file_with_path = self.find_manual_submod(
                            self.gen_dependencies, manual_module_end_regex.group(1)
                        )

                        if submod_file_with_path != 0:
                            submod_name = manual_module_end_regex.group(1)
                            inst_name = manual_module_end_regex.group(1)
                            gather_manual_instance = 1
                            manual_instance_line = line

                            semicolon_regex = RE_SEMICOLON.search(line)

                            if semicolon_regex:
                                gather_manual_instance = 0
                                parse_manual_instance = 1
                            else:
                                continue
                        else:
                            gather_manual_instance = 0

                    if parse_manual_instance:
                        self.filelist.append(submod_file_with_path)

                        submod_file_ext = re.sub(r".*\.", "", submod_file_with_path)

                        if self.gen_dependencies:
                            if submod_file_ext == "psv" or submod_file_ext == "pv":
                                if (
                                    submod_file_with_path
                                    not in self.dependencies["veripy_subs"]
                                ):
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ] = {}
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["flags"] = []
                                    self.dependencies["veripy_subs"][
                                        submod_file_with_path
                                    ]["mtime"] = getmtime(submod_file_with_path)
                            else:
                                if submod_file_with_path not in [
                                    keys
                                    for dicts in self.dependencies["verilog_subs"]
                                    for keys in dicts
                                ]:
                                    self.dependencies["verilog_subs"].append(
                                        {
                                            submod_file_with_path: {
                                                "mtime": getmtime(submod_file_with_path)
                                            }
                                        }
                                    )

                        ################################################################################
                        # Printing all the gathered registers
                        ################################################################################
                        print(
                            "    - Parsing Manual Instance MODULE: "
                            + submod_name
                            + " INST: "
                            + inst_name
                            + " FILE: "
                            + submod_file_with_path
                            + " "
                            + str(line_no)
                        )

                        if self.gen_dependencies:
                            prev_line = ""
                            line = ""
                            gather_manual_instance = 0
                            parse_manual_instance = 0
                            continue

                        manual_instance_line = re.sub(r"\s+", " ", manual_instance_line)

                        # Extract Module Name
                        module_name_regex = RE_NAME_BEGIN.search(manual_instance_line)

                        if module_name_regex:
                            module_with_tick_define_regex = (
                                RE_DEFINE_TICK_EXTRACT.search(manual_instance_line)
                            )

                            if module_with_tick_define_regex:
                                submod_name = self.get_tick_defval(
                                    module_with_tick_define_regex.group(1)
                                )
                            else:
                                submod_name = module_name_regex.group(1)

                            manual_instance_line = module_name_regex.group(2)
                        else:
                            self.dbg(
                                "\nError: Unable to extract module name in the following line"
                            )
                            self.dbg(manual_instance_line)
                            print(
                                "\nError: Unable to extract module name in the following line"
                            )
                            print(manual_instance_line + "\n")
                            sys.exit(1)

                        # Extract Params
                        # RE_PARAMS_EXTRACT = re.compile(r"^\s*#\s*\((.*)\s*\)\s*\)\s*(.*)")
                        RE_PARAMS_EXTRACT = re.compile(
                            r"^\s*#\s*\((.*)\s*\)\s*\)\s*([\w\[\]]+)\s*(\(.*)"
                        )
                        params_extract_regex = RE_PARAMS_EXTRACT.search(
                            manual_instance_line
                        )

                        param_overriding_list = []
                        if params_extract_regex:
                            param_overriding = params_extract_regex.group(1) + ")"
                            param_overriding = re.sub(r"\s+", "", param_overriding)
                            manual_instance_line = (
                                params_extract_regex.group(2)
                                + " "
                                + params_extract_regex.group(3)
                            )
                            param_overriding_list = param_overriding.split(",")

                        # Extract Instance Name
                        inst_name_regex = RE_NAME_BEGIN.search(manual_instance_line)
                        inst_name_bracket_regex = RE_NAME_BRACKET_BEGIN.search(
                            manual_instance_line
                        )

                        connections = ""

                        if inst_name_regex:
                            inst_name = inst_name_regex.group(1)
                            connections = inst_name_regex.group(2)
                        elif inst_name_bracket_regex:
                            inst_name = inst_name_bracket_regex.group(1)
                            connections = "(" + inst_name_bracket_regex.group(2)
                        else:
                            self.dbg(
                                "\nError: Unable to extract instance name in the following line"
                            )
                            self.dbg(manual_instance_line)
                            print(
                                "\nError: Unable to extract instance name in the following line"
                            )
                            print(manual_instance_line + "\n")
                            sys.exit(1)

                        # Extract Connections
                        connections = re.sub(r"\s+", "", connections)
                        connections = re.sub(r",\.", "#", connections)

                        connections_list = connections.split("#")

                        # Finding the file name to parse the submodule
                        # Look for systemverilog module
                        file_name_with_ext = submod_name + ".sv"

                        found_submod_file = 0
                        submod_file_with_path = file_name_with_ext

                        if os.path.isfile(file_name_with_ext):  # In file doesn't exist
                            found_submod_file = 1
                            submod_file_with_path = file_name_with_ext
                        else:
                            for dir in self.incl_dirs:
                                if not found_submod_file:
                                    sub_mode_file_path = (
                                        str(dir) + "/" + str(file_name_with_ext)
                                    )
                                    if os.path.isfile(sub_mode_file_path):
                                        found_submod_file = 1
                                        submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            # Look for verilog module
                            file_name_with_ext = submod_name + ".v"

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )
                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            # Look for verilog module
                            file_name_with_ext = submod_name + ".vp"

                            if os.path.isfile(
                                file_name_with_ext
                            ):  # In file doesn't exist
                                found_submod_file = 1
                                submod_file_with_path = file_name_with_ext
                            else:
                                for dir in self.incl_dirs:
                                    if not found_submod_file:
                                        sub_mode_file_path = (
                                            str(dir) + "/" + str(file_name_with_ext)
                                        )
                                        if os.path.isfile(sub_mode_file_path):
                                            found_submod_file = 1
                                            submod_file_with_path = sub_mode_file_path

                        if not found_submod_file:
                            submod_file_with_path = self.find_in_files(
                                file_name_with_ext
                            )

                            if submod_file_with_path is not None:
                                found_submod_file = 1

                        if not found_submod_file:
                            self.dbg(
                                "\nError: Unable to find the submodule "
                                + submod_name
                                + " in verilog/systemverilog format under following dirs"
                            )
                            self.dbg("  List of search directories")
                            print(
                                "\nError: Unable to find the submodule "
                                + submod_name
                                + " in verilog/systemverilog format under following dirs"
                            )
                            print("  List of search directories")

                            for dir in self.incl_dirs:
                                self.dbg("    " + str(dir))
                                print("    " + str(dir))
                            sys.exit(1)

                        submod_file_with_path = re.sub(
                            r"//", "/", submod_file_with_path
                        )
                        if not parse_manual_instance:
                            print(
                                "    - Parsing SUB-MODULE: "
                                + submod_name
                                + " INST: "
                                + inst_name
                                + " FILE: "
                                + submod_file_with_path
                            )

                        ################################################################################
                        # Parsing submodule for ports and params
                        ################################################################################
                        # Initializing all the arrays and varibles for every submodule
                        self.sub_tick_defines = {}
                        self.sub_tick_ifdef_en = 1
                        self.sub_tick_ifdef_arr = []
                        self.sub_tick_decisions = []
                        self.sub_tick_types = []
                        self.sub_tick_served = []
                        self.sub_tick_curr_decision = 1
                        self.sub_tick_curr_type = ""
                        self.sub_tick_curr_served = 0
                        self.sub_last_tick_loc = 0

                        self.sub_packages = []
                        self.sub_packages.append("default")
                        self.sub_typedef_enums = {}
                        self.sub_typedef_logics = {}
                        self.sub_typedef_structs = {}
                        self.sub_typedef_unions = {}
                        self.sub_typedef_bindings = {}

                        # Initializing default package and class to avoid errors
                        self.sub_typedef_enums["default"] = {}
                        self.sub_typedef_enums["default"]["default"] = {}
                        self.sub_typedef_logics["default"] = {}
                        self.sub_typedef_logics["default"]["default"] = {}
                        self.sub_typedef_structs["default"] = {}
                        self.sub_typedef_structs["default"]["default"] = {}
                        self.sub_typedef_unions["default"] = {}
                        self.sub_typedef_unions["default"]["default"] = {}

                        self.sub_ports = {}
                        self.sub_params = {}
                        self.sub_include_files_list = []
                        sub_connect_cmds = []
                        sub_param_cmds = []

                        submod_file_with_path = re.sub(
                            r"//", "/", submod_file_with_path
                        )
                        self.get_ports(submod_name, submod_file_with_path)

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# SUB PORTS :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_ports, indent=2))
                        self.dbg("\n")

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg(
                            "# SUB PARAM :: Module: "
                            + submod_name
                            + "; Instance: "
                            + inst_name
                        )
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_params, indent=2))
                        self.dbg("\n")

                        self.sub_inst_ports[inst_name] = {}
                        self.sub_inst_params[inst_name] = {}
                        self.sub_inst_files[inst_name] = submod_file_with_path
                        prev_line = ""

                        for c_connection in connections_list:
                            c_connection = re.sub(r"^\(", "", c_connection)
                            c_connection = re.sub(r"^\.", "", c_connection)
                            c_connection = re.sub(r";", "", c_connection)
                            c_connection = re.sub(r"\)+$", "", c_connection)
                            c_connection = re.sub(r"\(", " ", c_connection, 1)
                            sub_connect_cmds.append(c_connection)

                        for param_cmd in param_overriding_list:
                            param_cmd = re.sub(r"^\(", "", param_cmd)
                            param_cmd = re.sub(r"^\.", "", param_cmd)
                            param_cmd = re.sub(r"\)$", "", param_cmd)
                            param_cmd = re.sub(r"\(", " ", param_cmd, 1)
                            param_cmd = re.sub(r"\s+", "#", param_cmd, 1)

                            param_cmd_hash_regex = RE_HASH.search(param_cmd)

                            if param_cmd_hash_regex:
                                sub_param_name = param_cmd_hash_regex.group(1)
                                top_param_name = param_cmd_hash_regex.group(2)

                                if sub_param_name in self.sub_params:
                                    self.sub_inst_params[inst_name][sub_param_name] = {}
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "name"
                                    ] = sub_param_name
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "topname"
                                    ] = top_param_name
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "type"
                                    ] = self.sub_params[sub_param_name]["type"]
                                    self.sub_inst_params[inst_name][sub_param_name][
                                        "val"
                                    ] = self.sub_params[sub_param_name]["val"]
                                    # TODO: Need to recalculate the 'val' after param overriding
                                else:
                                    self.dbg(json.dumps(self.sub_params, indent=2))
                                    self.dbg(
                                        "\nError: Unable to find param "
                                        + sub_param_name
                                        + " in submodule "
                                        + submod_name
                                    )
                                    print(
                                        "\nError: Unable to find param "
                                        + sub_param_name
                                        + " in submodule "
                                        + submod_name
                                    )
                                    sys.exit(1)
                            else:
                                self.dbg(
                                    "\nError: Unable to parse &Param override call"
                                )
                                self.dbg(original_line)
                                print("\nError: Unable to parse &Param override call")
                                print(original_line)
                                self.found_error = 1

                        for c_port in self.sub_ports:
                            self.dbg(
                                "### "
                                + c_port
                                + " :: "
                                + self.sub_ports[c_port]["dir"]
                                + " :: "
                                + self.sub_ports[c_port]["bitdef"]
                                + " :: "
                                + str(self.sub_ports[c_port]["uwidth"])
                                + " :: "
                                + str(self.sub_ports[c_port]["lwidth"])
                                + " :: "
                                + (self.sub_ports[c_port]["depth"])
                                + " #"
                            )
                            self.sub_inst_ports[inst_name][c_port] = {}
                            self.sub_inst_ports[inst_name][c_port][
                                "name"
                            ] = self.sub_ports[c_port]["name"]
                            self.sub_inst_ports[inst_name][c_port][
                                "topname"
                            ] = self.sub_ports[c_port]["name"]
                            self.sub_inst_ports[inst_name][c_port][
                                "bitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
                            self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
                            self.sub_inst_ports[inst_name][c_port][
                                "uwidth"
                            ] = self.sub_ports[c_port]["uwidth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "lwidth"
                            ] = self.sub_ports[c_port]["lwidth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "depth"
                            ] = self.sub_ports[c_port]["depth"]
                            self.sub_inst_ports[inst_name][c_port][
                                "dir"
                            ] = self.sub_ports[c_port]["dir"]
                            self.sub_inst_ports[inst_name][c_port][
                                "typedef"
                            ] = self.sub_ports[c_port]["typedef"]
                            self.sub_inst_ports[inst_name][c_port]["connected"] = 0
                            self.sub_inst_ports[inst_name][c_port]["comment"] = ""

                            ################################################################################
                            # Applying all the param overriding on each port
                            ################################################################################
                            c_topbitdef = self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ]

                            for c_param in self.sub_inst_params[inst_name]:
                                c_topparam = self.sub_inst_params[inst_name][c_param][
                                    "topname"
                                ]
                                c_topbitdef = re.sub(c_param, c_topparam, c_topbitdef)

                            self.sub_inst_ports[inst_name][c_port][
                                "topbitdef"
                            ] = c_topbitdef

                            # Check if the port bit def is a typedef
                            if (
                                self.sub_ports[c_port]["typedef"] != ""
                                and self.sub_ports[c_port]["typedef"] != "LOGIC"
                                and self.sub_ports[c_port]["typedef"] != "REG"
                                and self.sub_ports[c_port]["typedef"] != "WIRE"
                            ):
                                double_colon_regex = RE_DOUBLE_COLON.search(
                                    self.sub_ports[c_port]["bitdef"]
                                )
                                double_double_colon_regex = (
                                    RE_DOUBLE_DOUBLE_COLON.search(
                                        self.sub_ports[c_port]["bitdef"]
                                    )
                                )
                                c_port_typedef = self.sub_ports[c_port]["typedef"]

                                if double_colon_regex or double_double_colon_regex:
                                    if double_double_colon_regex:
                                        c_port_package = double_colon_regex.group(1)
                                        c_port_class = double_colon_regex.group(2)
                                        c_port_typedef = double_colon_regex.group(2)
                                    else:
                                        if double_colon_regex.group(1) in list(
                                            self.sub_classes
                                        ):
                                            c_port_package = "default"
                                            c_port_class = double_colon_regex.group(1)
                                            c_port_typedef = double_colon_regex.group(2)
                                        else:
                                            c_port_package = double_colon_regex.group(1)
                                            c_port_class = "default"
                                            c_port_typedef = double_colon_regex.group(2)

                                    if (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_LOGIC"
                                    ):
                                        # Checking if package and class are present at top
                                        if (
                                            c_port_package in self.typedef_logics
                                            and c_port_class
                                            in self.typedef_logics[c_port_package]
                                        ):
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_logics[c_port_package][
                                                    c_port_class
                                                ]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                    elif (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_STRUCT"
                                    ):
                                        # Checking if package is present
                                        if (
                                            c_port_package in self.typedef_structs
                                            and c_port_class
                                            in self.typedef_structs[c_port_package]
                                        ):
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_structs[c_port_package][
                                                    c_port_class
                                                ]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                    elif (
                                        self.sub_ports[c_port]["typedef"]
                                        == "TYPEDEF_UNION"
                                    ):
                                        # Checking if package is present
                                        if (
                                            c_port_package in self.typedef_unions
                                            and c_port_class
                                            in self.typedef_unions[c_port_class]
                                        ):
                                            # Checking if the typedef logic is part of the package
                                            if (
                                                c_port_typedef
                                                in self.typedef_unions[c_port_package]
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:  # Typedef is not part of the package
                                                if (
                                                    self.sub_ports[c_port]["uwidth"]
                                                    != ""
                                                    and self.sub_ports[c_port]["lwidth"]
                                                    != ""
                                                ):
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = (
                                                        str(
                                                            self.sub_ports[c_port][
                                                                "uwidth"
                                                            ]
                                                        )
                                                        + ":"
                                                        + str(
                                                            self.sub_ports[c_port][
                                                                "lwidth"
                                                            ]
                                                        )
                                                    )
                                                    self.dbg(
                                                        "  # UPDATED TOP BITDEF :: "
                                                        + self.sub_inst_ports[
                                                            inst_name
                                                        ][c_port]["topbitdef"]
                                                    )
                                                else:
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"] = ""
                                        else:  # Package not present at top, so bitdef with numerical vlue
                                            if (
                                                self.sub_ports[c_port]["uwidth"] != ""
                                                and self.sub_ports[c_port]["lwidth"]
                                                != ""
                                            ):
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_ports[c_port]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_ports[c_port]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = ""
                                else:
                                    # Check if the typedef is part of default package
                                    if (
                                        c_port_typedef
                                        in self.typedef_logics["default"]["default"]
                                    ):
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    elif (
                                        c_port_typedef
                                        in self.typedef_structs["default"]["default"]
                                    ):
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    elif (
                                        c_port_typedef
                                        in self.typedef_unions["default"]["default"]
                                    ):
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ] = self.sub_ports[c_port]["bitdef"]
                                    else:  # now check for o
                                        sub_io_bitdef_val = self.tickdef_param_getval(
                                            "TOP",
                                            self.sub_ports[c_port]["bitdef"],
                                            "",
                                            "",
                                        )

                                        if sub_io_bitdef_val[0] == "STRING":
                                            # Checking if the bitdef has the multi dimentional array
                                            io_bitdef_packed_regex = (
                                                RE_PACKED_ARRAY.search(
                                                    self.sub_ports[c_port]["bitdef"]
                                                )
                                            )

                                            if io_bitdef_packed_regex:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = self.sub_ports[c_port]["bitdef"]
                                            else:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  # UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                        else:
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ] = self.sub_ports[c_port]["bitdef"]
                            else:
                                # Update uwidth and lwidth after param override
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    sub_io_bitdef_val = self.tickdef_param_getval(
                                        "TOP",
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topbitdef"
                                        ],
                                        "",
                                        "",
                                    )

                                    if sub_io_bitdef_val[0] == "STRING":
                                        # Checking if the bitdef has the multi dimentional array
                                        io_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                            self.sub_ports[c_port]["bitdef"]
                                        )

                                        if not io_bitdef_packed_regex:
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ] = (
                                                str(
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["uwidth"]
                                                )
                                                + ":"
                                                + str(
                                                    self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["lwidth"]
                                                )
                                            )
                                            self.dbg(
                                                "  ## UPDATED TOP BITDEF :: "
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topbitdef"]
                                            )
                                    else:
                                        if sub_io_bitdef_val[0] == "BITDEF":
                                            # Updating numberical values of upper and lower width
                                            bitdef_colon_regex = RE_COLON.search(
                                                str(sub_io_bitdef_val[1])
                                            )
                                            self.sub_inst_ports[inst_name][c_port][
                                                "uwidth"
                                            ] = bitdef_colon_regex.group(1)
                                            self.sub_inst_ports[inst_name][c_port][
                                                "lwidth"
                                            ] = bitdef_colon_regex.group(2)

                                            c_topbitdef = self.sub_inst_ports[
                                                inst_name
                                            ][c_port]["topbitdef"]
                                            c_topbitdef = re.sub(r":", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"-", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\+", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\(", "", c_topbitdef)
                                            c_topbitdef = re.sub(r"\)", "", c_topbitdef)

                                            topbitdef_numbers_regex = (
                                                RE_NUMBERS_ONLY.search(c_topbitdef)
                                            )

                                            if topbitdef_numbers_regex:
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topbitdef"
                                                ] = (
                                                    str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["uwidth"]
                                                    )
                                                    + ":"
                                                    + str(
                                                        self.sub_inst_ports[inst_name][
                                                            c_port
                                                        ]["lwidth"]
                                                    )
                                                )
                                                self.dbg(
                                                    "  ## UPDATED TOP BITDEF :: "
                                                    + self.sub_inst_ports[inst_name][
                                                        c_port
                                                    ]["topbitdef"]
                                                )
                                        else:  # NUMBER
                                            self.sub_inst_ports[inst_name][c_port][
                                                "uwidth"
                                            ] = sub_io_bitdef_val[1]
                                            self.sub_inst_ports[inst_name][c_port][
                                                "lwidth"
                                            ] = sub_io_bitdef_val[1]

                        ################################################################################
                        # Applying all the connect commands
                        ################################################################################
                        for connect_cmd in sub_connect_cmds:
                            connect_cmd = re.sub(r";", "", connect_cmd)
                            connect_cmd = re.sub(r"\s+", " ", connect_cmd)
                            connect_cmd = re.sub(r"^\s*", "", connect_cmd)
                            connect_cmd = re.sub(r"\s*$", "", connect_cmd)

                            self.dbg("### CONNECT :: " + connect_cmd)

                            connect_cmd_array = connect_cmd.split(" ")

                            connect_filter = ""
                            replace_expr_str = ""
                            replace_direct_str = ""

                            if len(connect_cmd_array) > 2:
                                connect_filter = connect_cmd_array[2]

                                replace_slash_regex = RE_REGEX_SLASH.search(
                                    connect_cmd_array[1]
                                )

                                if replace_slash_regex:
                                    replace_expr_str = replace_slash_regex.group(1)
                                else:
                                    replace_direct_str = connect_cmd_array[1]
                            elif len(connect_cmd_array) > 1:
                                replace_slash_regex = RE_REGEX_SLASH.search(
                                    connect_cmd_array[1]
                                )

                                if replace_slash_regex:
                                    replace_expr_str = replace_slash_regex.group(1)
                                else:
                                    replace_direct_str = connect_cmd_array[1]
                            else:
                                replace_expr_str = ""
                                replace_direct_str = ""

                            # Direct mapping of port
                            search_direct_str = connect_cmd_array[0]
                            search_direct_str = re.sub(r"\s*$", "", search_direct_str)

                            if search_direct_str in self.sub_inst_ports[inst_name]:
                                self.sub_inst_ports[inst_name][search_direct_str][
                                    "connected"
                                ] = 1
                                if replace_direct_str != "":
                                    # TODO: Need to update topbitdef from connect
                                    topname_is_concat_regex = RE_OPEN_CURLY.search(
                                        replace_direct_str
                                    )
                                    topname_has_tick_regex = RE_NUM_TICK.search(
                                        replace_direct_str
                                    )
                                    topname_is_constant_regex = RE_CONSTANT.search(
                                        replace_direct_str
                                    )
                                    topname_is_define_regex = (
                                        RE_DEFINE_TICK_BEGIN.search(replace_direct_str)
                                    )
                                    topname_has_dot_regex = RE_DOT.search(
                                        replace_direct_str
                                    )

                                    # If this is a constant or param or define or concat of self.signals, then topbitdef should be empty
                                    if (
                                        topname_is_concat_regex
                                        or topname_has_tick_regex
                                        or topname_is_constant_regex
                                        or topname_is_define_regex
                                        or topname_has_dot_regex
                                    ):
                                        self.sub_inst_ports[inst_name][
                                            search_direct_str
                                        ]["topbitdef"] = ""
                                        self.sub_inst_ports[inst_name][
                                            search_direct_str
                                        ]["topname"] = replace_direct_str
                                    else:
                                        topname_bitdef_regex = (
                                            RE_OPEN_SQBRCT_BITDEF.search(
                                                replace_direct_str
                                            )
                                        )

                                        if topname_bitdef_regex:
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["topname"] = topname_bitdef_regex.group(1)
                                            topbitdef_tmp = topname_bitdef_regex.group(
                                                2
                                            )
                                            topbitdef_tmp = re.sub(
                                                r"]$", "", topbitdef_tmp
                                            )
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["topbitdef"] = topbitdef_tmp
                                        else:
                                            self.sub_inst_ports[inst_name][
                                                search_direct_str
                                            ]["topname"] = replace_direct_str

                                    self.dbg(
                                        "      # UPDATED TOP NAME: "
                                        + self.sub_inst_ports[inst_name][
                                            search_direct_str
                                        ]["topname"]
                                    )
                                else:  # Unconnected port
                                    self.sub_inst_ports[inst_name][search_direct_str][
                                        "topname"
                                    ] = ""
                                    self.sub_inst_ports[inst_name][search_direct_str][
                                        "topbitdef"
                                    ] = ""
                                    self.dbg("      # UNCONNECTED PORT AT TOP")
                            else:
                                self.dbg(
                                    "\nError: Unable to find submodule port "
                                    + search_direct_str
                                    + " in submodule "
                                    + submod_name
                                )
                                print(
                                    "\nError: Unable to find submodule port "
                                    + search_direct_str
                                    + " in submodule "
                                    + submod_name
                                )
                                sys.exit(1)
                                self.found_error = 1
                                # sys.exit(1)

                        self.dbg(
                            "\n\n################################################################################"
                        )
                        self.dbg("# SUB INST PORTS")
                        self.dbg(
                            "################################################################################"
                        )
                        self.dbg(json.dumps(self.sub_inst_ports[inst_name], indent=2))

                        remove_ports = []
                        for c_port in self.sub_inst_ports[inst_name]:
                            if self.sub_inst_ports[inst_name][c_port]["connected"] == 0:
                                remove_ports.append(c_port)

                        self.dbg("\n")

                        for c_port in remove_ports:
                            self.dbg("### Deleting Manual Instance Port: " + c_port)
                            del self.sub_inst_ports[inst_name][c_port]

                        for c_port in self.sub_inst_ports[inst_name]:
                            self.dbg(
                                "### " + str(self.sub_inst_ports[inst_name][c_port])
                            )
                            if (
                                self.sub_inst_ports[inst_name][c_port]["dir"]
                                == "output"
                            ):
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    # if the bitdef is a binding, then we need to load typedef_bindings as well
                                    topbitdef_typedef_binding_regex = (
                                        RE_TYPEDEF_DOUBLE_COLON.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                        )
                                    )

                                    if topbitdef_typedef_binding_regex:
                                        self.binding_typedef(
                                            "TOP",
                                            "FORCE",
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                            + " "
                                            + self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ],
                                        )
                                        topname_assign_str = self.sub_inst_ports[
                                            inst_name
                                        ][c_port]["topname"]
                                    else:
                                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )

                                        if topname_bitdef_regex:
                                            topname_assign_str = self.sub_inst_ports[
                                                inst_name
                                            ][c_port]["topname"]
                                        else:
                                            # TODO: Need to do param overriding replacement on topbitdef
                                            topname_assign_str = (
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                + "["
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topbitdef"]
                                                + "]"
                                            )

                                    # topname can be concat of two or more self.signals
                                    topname_assign_comma_regex = RE_COMMA.search(
                                        topname_assign_str
                                    )

                                    topname_assign_str_array = []
                                    # If multiple declarations on the same line, then break it
                                    if topname_assign_comma_regex:
                                        # removing space, { and }
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array = (
                                            topname_assign_str.split(",")
                                        )
                                    else:  # Single declaration, then append to the array
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array.append(
                                            topname_assign_str
                                        )

                                    for curr_topname in topname_assign_str_array:
                                        if self.parsing_format == "verilog":
                                            self.parse_signal("wire", curr_topname, 0)
                                        else:
                                            self.parse_signal("reg", curr_topname, 0)
                                else:
                                    topname_assign_str = self.sub_inst_ports[inst_name][
                                        c_port
                                    ]["topname"]

                                    # topname can be concat of two or more self.signals
                                    topname_assign_comma_regex = RE_COMMA.search(
                                        topname_assign_str
                                    )

                                    topname_assign_str_array = []
                                    # If multiple declarations on the same line, then break it
                                    if topname_assign_comma_regex:
                                        # removing space, { and }
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array = (
                                            topname_assign_str.split(",")
                                        )
                                    else:  # Single declaration, then append to the array
                                        topname_assign_str = re.sub(
                                            r"[{}\s]", "", topname_assign_str
                                        )
                                        topname_assign_str_array.append(
                                            topname_assign_str
                                        )

                                    for curr_topname in topname_assign_str_array:
                                        if self.parsing_format == "verilog":
                                            self.parse_signal("wire", curr_topname, 0)
                                        else:
                                            self.parse_signal("reg", curr_topname, 0)

                            else:  # Sub module port is an input
                                if (
                                    self.sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    != ""
                                ):
                                    # if the bitdef is a binding, then we need to load self.typedef_bindings as well
                                    topbitdef_typedef_binding_regex = (
                                        RE_TYPEDEF_DOUBLE_COLON.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                        )
                                    )

                                    if topbitdef_typedef_binding_regex:
                                        self.binding_typedef(
                                            "TOP",
                                            "FORCE",
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topbitdef"
                                            ]
                                            + " "
                                            + self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ],
                                        )
                                        self.parse_conditions(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )
                                    else:
                                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                                            self.sub_inst_ports[inst_name][c_port][
                                                "topname"
                                            ]
                                        )

                                        if topname_bitdef_regex:
                                            self.parse_conditions(
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                            )
                                        else:
                                            # TODO: Need to do param overriding replacement on topbitdef
                                            self.parse_conditions(
                                                self.sub_inst_ports[inst_name][c_port][
                                                    "topname"
                                                ]
                                                + "["
                                                + self.sub_inst_ports[inst_name][
                                                    c_port
                                                ]["topbitdef"]
                                                + "]"
                                            )
                                else:
                                    self.parse_conditions(
                                        self.sub_inst_ports[inst_name][c_port][
                                            "topname"
                                        ]
                                    )

                        # Resetting the manual submodule instance data
                        self.sub_inst_ports[inst_name] = {}
                        self.sub_inst_params[inst_name] = {}
                        manual_instance_line = ""
                        parse_manual_instance = 0
                        continue

                prev_line = line
                prev_original_line = original_line
                prev_line_no = line_no
                continue

        else:  # if parser_on
            pass

        if self.debug:
            self.dbg_file.close()

        if self.profiling:
            with open(self.profiling_file, "a") as pfile:
                if (
                    self.all_time_dict["total_hits"] != 0
                    or self.all_time_callers["total_hits"] != 0
                    or self.all_time_caller_regex["total_hits"] != 0
                ):
                    pfile.write("Total times:\n")
                    self.nice_stats(self.all_time_dict, pfile)
                    pfile.write("Total callers:\n")
                    self.nice_stats(self.all_time_callers, pfile)
                    pfile.write("Total callers regex:\n")
                    self.nice_stats(self.all_time_caller_regex, pfile)
                    pfile.write("\n\n")
