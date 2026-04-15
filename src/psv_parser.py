####################################################################################
#   Copyright () Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

import argparse
import csv
import datetime, time
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
from .utils import *
from .regex import *
from .veripy_parser import veripy_parser
from .verilog_parser import verilog_parser
from .psv_prep import psv_prep


from collections import OrderedDict
from csv import reader
from math import ceil, log
from typing import Dict, Set

import oyaml as yaml


# For Veripy specific parsing

class psv_parser:
    def __init__(
        self,
        module_name,
        lines,
        incl_dirs,
        files,
        flist_lib,
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
        self.flist_lib = flist_lib
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

        self.module_def_preps = {}
        self.sub_preps = {}

        self.ports = {}
        self.regs = {}
        self.wires = {}
        self.signals = {}
        self.inouts = {}
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
        self.sub_inst_modules = {}
        self.sub_inst_params = {}

        self.auto_reset_data = {}
        self.auto_reset_val = ""
        self.auto_reset_vals = {}
        self.auto_reset_index = 0
        self.auto_reset_en = -1  # default -1 (not posedge),set to line_n (when posedge)
        self.auto_reset_lines = {}
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

        self.package_name = "default"
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

        self.instantiated_modules = {}
        
        self.match_lhs_rhs = {}

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

        self.gendrive0_parameter = 0
        self.genparam = 0
        self.genparam_no_gen_rtl = 0

        self.enable_custom_stub = 0
        self.enable_custom_stub_defs = []

        # Instance variables for new veripy parser
        self.cmdline = cmdline
        self.input_file = cmdline.positional
        self.moduledef_name = os.path.splitext(os.path.basename(self.input_file))[0]
        self.temporary_file = f"{self.input_file}.parse_lines"

        self.vp_parser = veripy_parser(self)
        self.sv_parser = verilog_parser(self)
        self.constructs = []
        self.ports_w_comment = {}

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
            m_function_skip = -1
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
                if ((m_file_ext != ".vp" and "pragma protect begin_protected" in m_line)
                    or re.match(r"^\s*`protected", m_line)
                ):
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

                if not self.tick_ifdef_dis and not m_tick_ifdef_en:
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
                            self.found_error += 1

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
                                self.param_proc("SUB", m_module_param.group(1), "", "", "module_header")
                            elif m_module_noparam:
                                m_module_io_declaration = m_module_noparam.group(2)
                                ################################################################################
                                # Parameter parsing
                                ################################################################################
                                self.param_proc(
                                    "SUB", m_module_noparam.group(1), "", "", "module_header"
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
                        if m_function_skip >= 0:
                            self.dbg(
                                f"\nError: Missing paired endfunction for function (line {m_function_skip}) detected."
                            )
                            print(
                                f"\nError: Missing paired endfunction for function (line {m_function_skip}) detected."
                            )
                            self.found_error += 1
                        m_function_skip = m_line_no
                        self.dbg("\n### Skipping function at " + str(m_line_no))
                        continue
                    elif m_endfunction_regex:
                        m_function_skip = -1
                        continue

                    if m_function_skip >= 0:
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
                                self.found_error += 1

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
                            self.param_proc("SUB", m_line, m_package_name, m_class_name, "module_body")
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

            if m_function_skip >= 0:
                self.dbg(
                    f"\nError: Missing paired endfunction for function (line {m_function_skip}) detected."
                )
                print(
                    f"\nError: Missing paired endfunction for function (line {m_function_skip}) detected."
                )
                self.found_error += 1

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

        if not found_submod_file and submod_name.startswith("mem_wrapper_"):
            # Process 3rd-party .f files.
            file_name_with_ext = f"{submod_name}.f"
            self.dbg("\n  finding file list..." + file_name_with_ext)
            # Only the memory files are supported currently.
            third_party_incl_dirs = [
                d for d in self.incl_dirs if "hls_rtl/" or "third_party/" in d
            ]

            for d in third_party_incl_dirs:
                sub_mode_file_path = os.path.join(d, file_name_with_ext)
                if os.path.isfile(sub_mode_file_path):
                    self.filelist.append(f"-f {sub_mode_file_path}")
                    found_submod_file = 1
                    submod_file_with_path = sub_mode_file_path
                    break  # Exit on first occurrence.

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

        if not found_submod_file:
            # Process 3rd-party .f files.
            file_name_with_ext = f"{submod_name}.f"
            self.dbg("\n  finding file list..." + file_name_with_ext)
            # Only the memory files are supported currently.
            third_party_incl_dirs = [
                d for d in self.incl_dirs if "hls_rtl/" or "third_party/" in d
            ]

            for d in third_party_incl_dirs:
                sub_mode_file_path = os.path.join(d, file_name_with_ext)
                if os.path.isfile(sub_mode_file_path):
                    self.filelist.append(f"-f {sub_mode_file_path}")
                    found_submod_file = 1
                    submod_file_with_path = sub_mode_file_path
                    break  # Exit on first occurrence.

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

        # Return in case of a bad parse when there is no variable being defined at all (e.g. cast or package parameter usage in bitdef)
        if len(bind_str_split_list) < 2:
            return

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
                if bind_typedef in self.params:
                    return

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
                self.found_error += 1
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
                if bind_typedef in self.sub_params:
                    return

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
                self.found_error += 1
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
        assign_str = re.sub(r"\binside\b", "*", assign_str)

        # Replace the first = with ###, so that we dont have to worry about the
        # presence of = in comparison
        assign_str = re.sub(r"\s*", "", assign_str)

        auto_reset_val = None
        if assignment_type == "ALWAYS_SEQ":

            assign_str_reset_val_regex = RE_RESET_VAL.search(assign_str)

            if assign_str_reset_val_regex:
                auto_reset_val = assign_str_reset_val_regex.group(2)
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
            self.found_error += 1

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
                        self.parse_signal("wire", curr_lhs)
                    else:
                        self.parse_signal("reg", curr_lhs)
                else:
                    if auto_reset_val != None:
                        self.auto_reset_vals[curr_lhs] = auto_reset_val

                    self.parse_signal("reg", curr_lhs)

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
            self.parse_signal("signal", rhs_signal)

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
            self.parse_signal("signal", cond_signal)

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
            self.parse_signal("signal", cond_signal)

        self.dbg("\n")

        return

    def update_typedef_regs(self, reg_type, reg_mode, reg):
        """
        Function to update regs/logics with manual or force typedefs
        """

        # Removing depth definition if any
        reg = re.sub(r"\s*\[[\w`\s:-]+\]\s*", "", reg)
        reg = re.sub(r"\s+", "", reg)
        reg_list = reg.split(",")

        for reg_name in reg_list:
            try:
                int_class = self.typedef_bindings[reg_name]["class"]
                int_package = self.typedef_bindings[reg_name]["package"]
                typedef = self.typedef_bindings[reg_name]["typedef"]
                signal_bitdef = ""
                signal_uwidth = ""
                signal_lwidth = ""
                signal_depth = ""
            except KeyError:
                print(f"\nError: typydef binding not found for {reg_name}.")
                self.found_error += 1
                return

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

    def parse_signal(self, signal_type, signal_str):
        """
        Function to parse a signal/param/define/constant
        """

        original_signal_str = signal_str
        signal_uwidth = ""
        signal_lwidth = ""
        signal_depth = ""
        signal_bitdef = ""

        # TODO: Need to parse system verilog struct
        signal_str_sqbrct_regex = re.compile(r"(\w*)\s*\[").search(signal_str)
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
        elif (
            signal_str in self.params or (
            signal_str_sqbrct_regex and
            signal_str_sqbrct_regex.group(1) in self.params
            )
        ):
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
        elif (signal_hash_regex and signal_hash_regex.group(2) in self.params) or (
            signal_double_hash_regex
            and signal_double_hash_regex.group(3) in self.params
        ):
            self.dbg("    # Skipping package parameter " + signal_str)
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

            elif member_name in self.params:
                signal_str = signal_str.replace("#", "::")
                self.dbg("    # Skipping imported parameter " + signal_str)

            elif member_name in self.functions_list:
                self.dbg("    # Skipping a function call " + signal_str)

            else:
                signal_str = signal_str.replace("#", "::")

                if signal_str in self.functions_list:
                    self.dbg("    # Skipping a function call " + signal_str)

                else:
                    print("\nError: Unable to parse a signal :: " + signal_str)
                    self.dbg("\nError: Unable to parse a signal :: " + signal_str)
                    self.found_error += 1

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
                ):  # The bitselect is another signal with bitdef, then we need to update it
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
                        self.parse_signal(signal_type, bitsel_signal)

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
                                        signal_type, curr_signal_bitdef
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

        for sname in [signal_name, original_signal_str]:
            if sname in self.auto_reset_vals and self.auto_reset_en >= 0:
                auto_reset_val = self.auto_reset_vals[sname]
                # print(f"signal_name: {signal_name}")
                if signal_name in self.auto_reset_data[self.auto_reset_index]:
                    self.auto_reset_data[self.auto_reset_index][signal_name][
                        "resetval"
                    ] = auto_reset_val
                else:
                    self.auto_reset_data[self.auto_reset_index][signal_name] = {}
                    self.auto_reset_data[self.auto_reset_index][signal_name][
                        "name"
                    ] = signal_name
                    self.auto_reset_data[self.auto_reset_index][signal_name][
                        "resetval"
                    ] = auto_reset_val

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

        if re.search(r"\W+", signal_name):
            return

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

        signal_str = re.sub(r"::", "#", signal_str)
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
            declare_bitdef = declare_bitdef_regex.group(1).strip()
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
                        self.found_error += 1
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
                        self.found_error += 1

        return

    def parse_ios(self, module_type, io_parse_type, io_dir, io_str, module_name=None):
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
        elif io_dir == "output_notype" or io_dir == "input_notype" or io_dir == "inout_notype":
                 io_dir = re.sub("_notype", "", io_dir)
                 io_bitdef_type = "TYPEDEF_NOTYPE"

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
                            self.found_error += 1
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
                            self.found_error += 1
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

                if (
                    module_name is not None
                    and module_name in self.module_def_preps
                    and len(self.module_def_preps[module_name]) > 0
                ):
                    module_def_preps = self.module_def_preps[module_name]
                    for module_def_prep in module_def_preps:
                        if io_str_orig.strip(";") in module_def_prep["intf_ports"]:
                            module_def_prep["ports"].append(io_name)

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
        tick_inc_file = None
        found_tick_inc_file = 0
        is_list_file = False
        actual_pkg_file = ""

        if os.path.isfile(inc_file):  # In file doesn't exist
            found_tick_inc_file = 1
            tick_inc_file = inc_file
        else:
            for dir in self.incl_dirs:
                if not found_tick_inc_file:
                    inc_file_path = str(dir) + "/" + str(inc_file)

                    if os.path.isfile(inc_file_path):
                        found_tick_inc_file = 1
                        tick_inc_file = inc_file_path

        if not found_tick_inc_file:
            file_path = inc_file
            inc_file_path = self.find_in_files(file_path)

            if inc_file_path is None:
                root, ext = os.path.splitext(file_path)
                if ext == ".sv":
                    file_path = root + ".svp"
                    inc_file_path = self.find_in_files(file_path)

            if inc_file_path is not None:
                found_tick_inc_file = 1
                tick_inc_file = inc_file_path

                root, ext = os.path.splitext(tick_inc_file)
                if ext == ".f":
                    is_list_file = True
                    actual_pkg_file = self.find_in_files(file_path,True)

        if not found_tick_inc_file:
            root, ext = os.path.splitext(inc_file)
            if ext == ".sv":
                for alt_ext in [".psv", ".svp"]:
                    if not found_tick_inc_file:
                        alt_inc_file = root + alt_ext

                        for dir in self.incl_dirs:
                            if not found_tick_inc_file:
                                inc_file_path = str(dir) + "/" + str(alt_inc_file)

                                if os.path.isfile(inc_file_path):
                                    found_tick_inc_file = 1
                                    tick_inc_file = inc_file_path
                                    break

                        if not found_tick_inc_file:
                            inc_file_path = self.find_in_files(alt_inc_file)

                            if inc_file_path is not None:
                                found_tick_inc_file = 1
                                tick_inc_file = inc_file_path
                                break

        if found_tick_inc_file:
            self.dbg(
                "\n################################################################################"
            )

            tick_inc_file = re.sub(r"\/\/", "/", tick_inc_file)

            if inc_type == "IMPORT_COMMANDLINE" or inc_type == "IMPORT_EMBEDDED":
                self.dbg(
                    "###load_import_or_include_file Loading Package file"
                    + tick_inc_file
                    + " ###"
                )
                if module_type == "TOP":
                    print("    - Importing package " + tick_inc_file)
                else:
                    print("      + Importing package " + tick_inc_file)
            else:
                self.dbg(
                    "###load_import_or_include_file Loading `include file "
                    + tick_inc_file
                    + " ###"
                )
                if module_type == "TOP":
                    print("    - Loading `include file " + tick_inc_file)
                else:
                    print("      + Loading `include file " + tick_inc_file)

            self.dbg(
                "################################################################################"
            )

            if is_list_file:
                file_to_parse = actual_pkg_file
            else:
                file_to_parse = tick_inc_file

            package_function_skip = -1
            package_name = "default"
            class_name = "default"
            incl_tick_ifdef_en = 1

            with open(file_to_parse, "r") as tick_incl_data:
                tick_incl_block_comment = 0

                self.filelist.append(file_to_parse)

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
                        # Gather multiple lines until ;
                        if tick_incl_gather_till_semicolon:
                            tick_incl_line = prev_tick_incl_line + " " + tick_incl_line

                            tick_incl_semicolon_regex = RE_SEMICOLON.search(tick_incl_line)

                            if tick_incl_semicolon_regex:
                                tick_incl_gather_till_semicolon = 0

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
                            if package_function_skip >= 0:
                                self.dbg(
                                    f"\nError: Missing paired endfunction for function (line {package_function_skip}) detected."
                                )
                                print(
                                    f"\nError: Missing paired endfunction for function (line {package_function_skip}) detected."
                                )
                                self.found_error += 1
                            package_function_skip = incl_line_no
                            if function_name1_regex:
                                # TODO: Calculate the function return width
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
                                self.found_error += 1
                        elif endfunction_regex:
                            package_function_skip = -1
                            continue

                        if package_function_skip >= 0:
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
                                    "package",
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

                            if (
                                inc_type == "IMPORT_COMMANDLINE"
                                or inc_type == "IMPORT_EMBEDDED"
                            ):
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
                                    self.found_error += 1
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

                if package_function_skip >= 0:
                    self.dbg(
                        f"\nError: Missing paired endfunction for function (line {package_function_skip}) detected."
                    )
                    print(
                        f"\nError: Missing paired endfunction for function (line {package_function_skip}) detected."
                    )
                    self.found_error += 1

            root, ext = os.path.splitext(tick_inc_file)
            if self.gen_dependencies:
                psvfile = re.sub(r"\brtl_[A-Za-z0-9]+\b", "src", root) + ".psv"
                if os.path.isfile(psvfile):
                    if os.path.dirname(psvfile) == os.getcwd():
                        psvfile = os.path.basename(psvfile)

                    if psvfile not in self.dependencies["veripy_subs"]:
                        self.dependencies["veripy_subs"][psvfile] = {}
                        self.dependencies["veripy_subs"][psvfile][
                            "mtime"
                        ] = getmtime(psvfile)
                        self.dependencies["veripy_subs"][psvfile]["flags"] = []
                else:
                    self.dependencies["include_files"].append(
                        {tick_inc_file: {"mtime": getmtime(tick_inc_file)}}
                    )
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
                                # self.found_error += 1
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
                            self.found_error += 1
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
                            self.found_error += 1
                            sys.exit(1)

            if parse_type == "STRUCT":
                self.dbg("  # STRUCT: " + struct_name + ", WIDTH: " + str(struct_width))
            else:
                self.dbg("  # UNION: " + struct_name + ", WIDTH: " + str(struct_width))
        else:
            self.dbg("\nError: Unable to detect struct or union")
            self.dbg("    # " + struct_str)
            print("\nError: Unable to detect struct or union")
            print("    # " + struct_str)
            self.found_error += 1

        return

    def param_proc(self, module_type, param_str, package, class_name, scope):
        """
        Function to parse parameter or localparam
        """

        if scope == "module_body" and re.match(r"^\s*localparam\s+.*;", param_str):
            scope = "module_body_local"
        param_str = re.sub(r"\s+", " ", param_str)
        self.dbg(module_type + ":: " + param_str)

        # Removing parameter keywords and bitwidth and spaces
        param_str = re.sub(r"^\s*parameter\s+", "", param_str)
        param_str = re.sub(r",\s*parameter\s+", ",", param_str)
        param_str = re.sub(r"^\s*localparam\s+", "", param_str)
        param_str = re.sub(
            r"\s*\b(shortint|int|longint|byte|bit|logic|reg|integer|time|real|shortreal)\b\s*",
            "",
            param_str,
        )
        param_str = re.sub(r"^(signed|unsigned)\b\s*", "", param_str)
        param_str = re.sub(r"^\s*\[.*\]\s*", "", param_str)
        param_str = re.sub(r"\s*\[[\w:]+\]\s*", "", param_str)
        param_str = re.sub(r";", "", param_str)
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
                param_name = param_name.split(" ")[-1]
                # TODO: Need to pass package
                param_val_ret = self.tickdef_param_getval(
                    module_type, re.sub(r"\s*", "", param_split_regex.group(2)), int_package, int_class
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
                        self.params[param_name]["scope"] = scope
                    else:
                        self.sub_params[param_name] = {}
                        self.sub_params[param_name]["type"] = param_val_ret[0]
                        self.sub_params[param_name]["val"] = param_split_regex.group(2)
                        self.sub_params[param_name]["exp"] = param_split_regex.group(2)
                        self.sub_params[param_name]["scope"] = scope
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
                        self.params[param_name]["scope"] = scope
                    else:
                        self.sub_params[param_name] = {}
                        self.sub_params[param_name]["type"] = param_val_ret[0]
                        self.sub_params[param_name]["val"] = param_val_ret[1]
                        self.sub_params[param_name]["exp"] = param_str
                        self.sub_params[param_name]["scope"] = scope

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
                    if not enum_number_regex:
                        self.params[enum_name]["type"] = "STRING"
                    else:
                        self.params[enum_name]["type"] = "NUMBER"

                    self.params[enum_name]["val"] = enum_val
                    self.params[enum_name]["exp"] = enum_val
                    self.params[enum_name]["scope"] = "enum"
                else:
                    self.sub_params[enum_name] = {}
                    if enum_number_regex:
                        self.sub_params[enum_name]["type"] = "STRING"
                    else:
                        self.sub_params[enum_name]["type"] = "NUMBER"

                    self.sub_params[enum_name]["val"] = enum_val
                    self.sub_params[enum_name]["exp"] = enum_val
                    self.sub_params[enum_name]["scope"] = "enum"

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
                        self.params[c_enum_name]["scope"] = "enum"
                    else:
                        self.sub_params[c_enum_name] = {}
                        self.sub_params[c_enum_name]["type"] = "NUMBER"
                        self.sub_params[c_enum_name]["val"] = enum_val
                        self.sub_params[c_enum_name]["exp"] = enum_val
                        self.sub_params[c_enum_name]["scope"] = "enum"

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
                    "\nError: There is no pending ifdef/elif in the buffer, but reaching #endif."
                )
                print(
                    "\nError: There is no pending ifdef/elif in the buffer, but reaching #endif."
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
                self.found_error += 1

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
                            "\nWarning: Unable to calculate $bits for the following\n"
                        )
                        self.dbg("  # " + dollar_string)
                        print(
                            "\nWarning: Unable to calculate $bits for the following\n"
                        )
                        print("  # " + dollar_string)
                        # self.found_error += 1
                else:
                    dollar_bits_width = 1
                    self.dbg("\nWarning: Unable to calculate $bits for the following\n")
                    self.dbg("  # " + dollar_string)
                    print("\nWarning: Unable to calculate $bits for the following\n")
                    print("  # " + dollar_string)
                    # self.found_error += 1
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
                            "\nWarning: Unable to calculate $bits for the following\n"
                        )
                        self.dbg("  # " + dollar_string)
                        print(
                            "\nWarning: Unable to calculate $bits for the following\n"
                        )
                        print("  # " + dollar_string)
                        # self.found_error += 1
                else:
                    dollar_bits_width = 1
                    self.dbg("\nWarning: Unable to calculate $bits for the following\n")
                    self.dbg("  # " + dollar_string)
                    print("\nWarning: Unable to calculate $bits for the following\n")
                    print("  # " + dollar_string)
                    # self.found_error += 1

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

        # Possible reference to an SV package if it is used in the parameter/define
        param_double_colon_regex = RE_TYPEDEF_DOUBLE_COLON.search(tick_def_exp)
        param_double_double_colon_regex = RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
            tick_def_exp
        )
        if param_double_colon_regex and not param_double_double_colon_regex:
            param_package = param_double_colon_regex.group(1)
            if param_package not in self.sub_packages:
                self.load_import_or_include_file(
                    "SUB",
                    "IMPORT_COMMANDLINE",
                    param_package + ".sv",
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
        tick_ternary_param = RE_TICK_TERNARY_PARAM.search(tick_eval_string)

        if tick_def_is_bitdef and not tick_ternary_param:
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

    def find_module_in_file(self, module_name, file_name):
        if not os.path.exists(file_name):
            return False

        try:
            with open(file_name) as fp:
                for line in fp:
                    if re.match(f"^\s*module\s+{module_name}\\b.*$", line):
                        return True
                return False
        except UnicodeDecodeError:
            return False

    def find_in_files(self, filename, is_flist=False):
        """
        Function to print a debug string in a debug dump file
        """

        module_name, module_ext = os.path.splitext(filename)
        for flist in self.flist_lib:
            for c_file in self.flist_lib[flist]:
                file_search_regex = "\\b" + filename + "$"
                RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
                search_file_regex = RE_SEARCH_FILE_REGEX.search(c_file)

                if search_file_regex and os.path.isfile(c_file):
                    if is_flist:
                        return c_file
                    else:
                        return flist
        for flist in self.flist_lib:
            for c_file in self.flist_lib[flist]:
                c_file_root, c_file_ext = os.path.splitext(c_file)
                if (
                    (RE_IP_FILE_REGEX.search(c_file) or
                    (re.match(f"^{module_name}", os.path.basename(c_file_root))
                    and module_ext == c_file_ext)
                    ) and
                    self.find_module_in_file(module_name, c_file)
                ):
                    if is_flist:
                        return c_file
                    else:
                        return flist

        for c_file in self.files:
            file_search_regex = "\\b" + filename + "$"
            RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
            search_file_regex = RE_SEARCH_FILE_REGEX.search(c_file)

            if search_file_regex and  os.path.isfile(c_file):
                return c_file

        for c_file in self.files:
            c_file_root, c_file_ext = os.path.splitext(c_file)
            if (
                (RE_IP_FILE_REGEX.search(c_file) or
                 (re.match(f"^{module_name}", os.path.basename(c_file_root))
                 and module_ext == c_file_ext)
                ) and
                self.find_module_in_file(module_name, c_file)
            ):
                return c_file

        return

    def parse_param_cmds(self, instantiation, sub_param_cmds):
        (submod_name, inst_name, inst_index) = instantiation
        overriden_sub_params = set()
        for param_cmd in reversed(sub_param_cmds):
            param_cmd = re.sub(r"\s+", "#", param_cmd, 1)

            param_cmd_hash_regex = RE_HASH.search(param_cmd)

            replace_slash_str = 0
            replace_expr_str = ""
            replace_direct_str = ""
            if param_cmd_hash_regex:
                sub_param_name = param_cmd_hash_regex.group(1)
                top_param_name = param_cmd_hash_regex.group(2)

                replace_slash_regex = RE_REGEX_SLASH.search(top_param_name)

                if replace_slash_regex:
                    replace_expr_str = replace_slash_regex.group(1)
                    replace_slash_str = 1
                    try:
                        repl_func = eval(replace_expr_str)
                        if callable(repl_func):
                            replace_expr_str = repl_func
                    except:
                        pass
                else:
                    replace_direct_str = top_param_name

                search_slash_regex = RE_REGEX_SLASH.search(sub_param_name)
                if search_slash_regex:
                    search_expr_str = search_slash_regex.group(1)
                    RE_SEARCH_EXPR_REGEX = re.compile(search_expr_str)
                    sub_params = {
                        sub_param: self.sub_params[sub_param]
                        for sub_param in self.sub_params if self.sub_params[sub_param]["scope"] == "module_header"
                    }
                    for sub_param in sub_params:
                        if sub_params[sub_param]["scope"] != "module_header":
                            continue

                        sub_param_match = RE_SEARCH_EXPR_REGEX.search(sub_param)
                        if sub_param_match:
                            self.dbg(f"    # Matched sub inst param: {sub_param}")
                            if sub_param in overriden_sub_params:
                                print(f"\nWarning: Param {sub_param} has been overridden, ignored.")
                                continue
                            else:
                                overriden_sub_params.add(sub_param)
                            if replace_slash_str:
                                top_name = re.sub(search_expr_str, replace_expr_str, sub_param)
                            else:
                                top_name = replace_direct_str

                            if not top_name or top_name == '""':
                                continue

                            if  re.match(r"^[A-Za-z]\w+$", top_name) and top_name not in self.params:
                                self.params[top_name] = {}
                                self.params[top_name]["type"] = self.sub_params[sub_param]["type"]
                                self.params[top_name]["val"] = self.sub_params[sub_param]["val"]
                                self.params[top_name]["exp"] = self.sub_params[sub_param]["exp"]
                                self.params[top_name]["scope"] = "module_header"
                                if self.module_param_line != "":
                                    new_module_params = []
                                    module_params = self.module_param_line.split(",")
                                    for module_param in module_params:
                                        module_param.strip()
                                        if module_param.startswith("parameter "):
                                            module_param += ", "
                                            module_param += f"{top_name} = {self.params[top_name]['val']}"

                                        new_module_params.append(module_param)
                                    self.module_param_line = ", ".join(new_module_params)
                                else:
                                    self.module_param_line = f"parameter {top_name} = {self.params[top_name]['val']}"

                            self.sub_inst_params[instantiation][sub_param] = {}
                            self.sub_inst_params[instantiation][sub_param]["topname"] = top_name
                            self.sub_inst_params[instantiation][sub_param]["name"] = sub_param
                            self.sub_inst_params[instantiation][sub_param]["type"] = self.sub_params[sub_param]["type"]
                            self.sub_inst_params[instantiation][sub_param]["val"] = self.sub_params[sub_param]["val"]
                else:
                    if sub_param_name in self.sub_params:
                        if sub_param_name in overriden_sub_params:
                            print(f"\nWarning: Param {sub_param_name} has been overridden, ignored.")
                            continue
                        else:
                            overriden_sub_params.add(sub_param_name)

                        # if re.match(r"^[A-Za-z]\w+$", top_param_name) and top_param_name not in self.params:
                        #     self.params[top_param_name] = {}
                        #     self.params[top_param_name]["type"] = self.sub_params[sub_param_name]["type"]
                        #     self.params[top_param_name]["val"] = self.sub_params[sub_param_name]["val"]
                        #     self.params[top_param_name]["exp"] = self.sub_params[sub_param_name]["exp"]
                        #     self.params[top_param_name]["local"] = False
                        #     if self.module_param_line != "":
                        #         new_module_params = []
                        #         module_params = self.module_param_line.split(",")
                        #         for module_param in module_params:
                        #             module_param.strip()
                        #             if module_param.startswith("parameter "):
                        #                 module_param += ", "
                        #                 module_param += f"{top_param_name} = {self.params[top_param_name]['val']}"
                        #
                        #             new_module_params.append(module_param)
                        #         self.module_param_line = ", ".join(new_module_params)
                        # else:
                        # self.module_param_line = f"parameter {top_param_name} = {self.params[top_param_name]['val']}"

                        self.sub_inst_params[instantiation][sub_param_name] = {}
                        self.sub_inst_params[instantiation][sub_param_name][
                            "name"
                        ] = sub_param_name
                        self.sub_inst_params[instantiation][sub_param_name][
                            "topname"
                        ] = top_param_name
                        self.sub_inst_params[instantiation][sub_param_name][
                            "type"
                        ] = self.sub_params[sub_param_name]["type"]
                        self.sub_inst_params[instantiation][sub_param_name][
                            "val"
                        ] = self.sub_params[sub_param_name]["val"]
                    else:
                        print(f"\nError: Unable to find param {sub_param_name} in submodule {submod_name}.")
                        sys.exit(1)
            else:
                print(f"\nError: Unable to parse &Param override call {param_cmd}")
                self.found_error += 1

    def parse_sub_ports(self, instantiation):
        (submod_name, inst_name, inst_index) = instantiation
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
            self.sub_inst_ports[instantiation][c_port] = {}
            self.sub_inst_ports[instantiation][c_port]["name"] = self.sub_ports[
                c_port
            ]["name"]
            self.sub_inst_ports[instantiation][c_port]["topname"] = self.sub_ports[
                c_port
            ]["name"]
            self.sub_inst_ports[instantiation][c_port]["bitdef"] = self.sub_ports[
                c_port
            ]["bitdef"]
            self.sub_inst_ports[instantiation][c_port][
                "topbitdef"
            ] = self.sub_ports[c_port]["bitdef"]
            self.sub_inst_ports[instantiation][c_port]["uwidth"] = self.sub_ports[
                c_port
            ]["uwidth"]
            self.sub_inst_ports[instantiation][c_port]["lwidth"] = self.sub_ports[
                c_port
            ]["lwidth"]
            self.sub_inst_ports[instantiation][c_port]["depth"] = self.sub_ports[
                c_port
            ]["depth"]
            self.sub_inst_ports[instantiation][c_port]["dir"] = self.sub_ports[
                c_port
            ]["dir"]
            self.sub_inst_ports[instantiation][c_port]["typedef"] = self.sub_ports[
                c_port
            ]["typedef"]
            self.sub_inst_ports[instantiation][c_port]["origconnect"] = ""
            self.sub_inst_ports[instantiation][c_port]["comment"] = ""

            ################################################################################
            # Applying all the param overriding on each port
            ################################################################################
            c_topbitdef = self.sub_inst_ports[instantiation][c_port]["topbitdef"]

            is_param_subed = False
            for c_param in self.sub_inst_params[instantiation].keys():
                c_topparam = self.sub_inst_params[instantiation][c_param]["topname"]
                # Replace param with param value if param scope is module_body or module_local
                # if c_topparam in self.params and self.params[c_topparam]["scope"] in ["module_body", "module_body_local"]:
                #     c_param_val = str(self.params[c_topparam]["val"])
                #     if not re.search(r"==.*?.*:.*", c_param_val):
                #         c_topparam = str(self.params[c_topparam]["val"])

                if c_param == c_topparam:
                    continue

                c_sep = "(?P<sep>\W*)"
                c_param_str = f"\\b{c_param}\\b"
                c_param_search_str = c_sep + c_param_str
                mat = re.search(c_param_search_str, c_topbitdef)
                if mat and (mat[1] == ""  or mat[1] not in ["::"]):
                    c_topbitdef = re.sub(
                        c_param_str, c_topparam, c_topbitdef
                    )
                    is_param_subed = True

            for c_sub_param in self.sub_params.keys():
                if (
                    self.sub_params[c_sub_param]["scope"] not in ["module_header", "module_body", "module_body_local"] or
                    c_sub_param == "" or
                    re.search(r"\W+", c_sub_param) or
                    c_sub_param in self.sub_inst_params[instantiation]
                    or re.search(r"==.*?.*:.*", str(self.sub_params[c_sub_param]['val']))
                    or c_sub_param in self.params
                ):
                    continue

                c_sep = "(?P<sep>\W*)"
                c_sub_param_str = f"\\b{c_sub_param}\\b"
                c_sub_param_search_str = c_sep + c_sub_param_str
                mat = re.search(c_sub_param_search_str, c_topbitdef)
                if mat and  (mat[1] == ""  or mat[1] not in ["::"]):
                    c_topbitdef = re.sub(
                        c_sub_param_str, str(self.sub_params[c_sub_param]['val']), c_topbitdef
                    )
                    is_param_subed = True

            # if is_param_subed:
            try:
                mat = re.match(r"^([^:]+):([^:]+)$", c_topbitdef)
                if mat:
                    c_topbit1 = mat[1]
                    c_topbit2 = mat[2]
                    c_topbit1_val = int(eval(c_topbit1))
                    c_topbitdef = f"{str(c_topbit1_val)}:{c_topbit2}"
            except Exception:
                pass

            if c_topbitdef != self.sub_inst_ports[instantiation][c_port]["topbitdef"]:
                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = c_topbitdef

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
                double_double_colon_regex = RE_DOUBLE_DOUBLE_COLON.search(
                    self.sub_ports[c_port]["bitdef"]
                )
                c_port_typedef = self.sub_ports[c_port]["typedef"]

                if double_double_colon_regex:
                    c_port_package = double_colon_regex.group(1)
                    c_port_class = double_colon_regex.group(2)
                    c_port_typedef = double_colon_regex.group(3)
                elif double_colon_regex:
                    if double_colon_regex.group(1) in list(self.classes):
                        c_port_package = "default"
                        c_port_class = double_colon_regex.group(1)
                        c_port_typedef = double_colon_regex.group(2)
                    else:
                        c_port_package = double_colon_regex.group(1)
                        c_port_class = "default"
                        c_port_typedef = double_colon_regex.group(2)

                    if self.sub_ports[c_port]["typedef"] == "TYPEDEF_LOGIC":
                        if self.auto_package_load:
                            if c_port_package not in self.typedef_logics:
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
                                self.sub_inst_ports[instantiation][c_port][
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
                                        self.sub_ports[c_port]["uwidth"] != ""
                                        and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                            str(self.sub_ports[c_port]["uwidth"])
                                            + ":"
                                            + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][
                                            c_port
                                        ]["topbitdef"]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = ""
                    elif self.sub_ports[c_port]["typedef"] == "TYPEDEF_STRUCT":
                        typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                            self.sub_ports[c_port]["bitdef"]
                        )
                        typedef_ref_regex_double = (
                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                                self.sub_ports[c_port]["bitdef"]
                            )
                        )

                        if self.auto_package_load:
                            if c_port_package not in self.typedef_structs:
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
                                self.sub_inst_ports[instantiation][c_port][
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
                                        self.sub_ports[c_port]["uwidth"] != ""
                                        and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                            str(self.sub_ports[c_port]["uwidth"])
                                            + ":"
                                            + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][
                                            c_port
                                        ]["topbitdef"]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = ""

                    elif self.sub_ports[c_port]["typedef"] == "TYPEDEF_UNION":
                        if self.auto_package_load:
                            if c_port_package not in self.typedef_unions:
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
                                self.sub_inst_ports[instantiation][c_port][
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
                                        self.sub_ports[c_port]["uwidth"] != ""
                                        and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                            str(self.sub_ports[c_port]["uwidth"])
                                            + ":"
                                            + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][
                                            c_port
                                        ]["topbitdef"]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = ""
                else:
                    # Check if the typedef is part of default package
                    if c_port_typedef in self.typedef_logics["default"]:
                        self.sub_inst_ports[instantiation][c_port][
                            "topbitdef"
                        ] = self.sub_ports[c_port]["bitdef"]
                    elif c_port_typedef in self.typedef_structs["default"]:
                        self.sub_inst_ports[instantiation][c_port][
                            "topbitdef"
                        ] = self.sub_ports[c_port]["bitdef"]
                    elif c_port_typedef in self.typedef_unions["default"]:
                        self.sub_inst_ports[instantiation][c_port][
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
                            io_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                self.sub_ports[c_port]["bitdef"]
                            )

                            if io_bitdef_packed_regex:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = self.sub_ports[c_port]["bitdef"]
                            else:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(
                                            self.sub_inst_ports[instantiation][c_port][
                                                "uwidth"
                                            ]
                                        )
                                        + ":"
                                        + str(
                                    self.sub_inst_ports[instantiation][c_port][
                                        "lwidth"
                                    ]
                                )
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                        else:
                            self.sub_inst_ports[instantiation][c_port][
                                "topbitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
            else:
                # Update uwidth and lwidth after param override
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    sub_io_bitdef_val = self.tickdef_param_getval(
                        "TOP",
                        self.sub_inst_ports[instantiation][c_port]["topbitdef"],
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
                                    self.sub_inst_ports[instantiation][c_port]["uwidth"]
                                    == ""
                                    or self.sub_inst_ports[instantiation][c_port][
                                "lwidth"
                            ]
                                    == ""
                            ):
                                print(
                                    "Warning: Unable to bring the bitdef from submodule to top"
                                )
                                print(
                                    "  # Port: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "name"
                                    ]
                                    + "   Bitdef: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                print(
                                    "Warning: Unable to bring the bitdef from submodule to top"
                                )
                                print(
                                    "  # Port: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "name"
                                    ]
                                    + "   Bitdef: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(
                                            self.sub_inst_ports[instantiation][c_port][
                                                "uwidth"
                                            ]
                                        )
                                        + ":"
                                        + str(
                                    self.sub_inst_ports[instantiation][c_port][
                                        "lwidth"
                                    ]
                                )
                                )
                                self.dbg(
                                    "  ## UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                    else:
                        if sub_io_bitdef_val[0] == "BITDEF":
                            # Updating numberical values of upper and lower width
                            bitdef_colon_regex = RE_COLON.search(
                                str(sub_io_bitdef_val[1])
                            )
                            self.sub_inst_ports[instantiation][c_port][
                                "uwidth"
                            ] = bitdef_colon_regex.group(1)
                            self.sub_inst_ports[instantiation][c_port][
                                "lwidth"
                            ] = bitdef_colon_regex.group(2)

                            c_topbitdef = self.sub_inst_ports[instantiation][
                                c_port
                            ]["topbitdef"]
                            c_topbitdef = re.sub(r":", "", c_topbitdef)
                            c_topbitdef = re.sub(r"-", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\+", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\(", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\)", "", c_topbitdef)

                            topbitdef_numbers_regex = RE_NUMBERS_ONLY.search(
                                c_topbitdef
                            )

                            if topbitdef_numbers_regex:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = (
                                        str(
                                            self.sub_inst_ports[instantiation][c_port][
                                                "uwidth"
                                            ]
                                        )
                                        + ":"
                                        + str(
                                    self.sub_inst_ports[instantiation][c_port][
                                        "lwidth"
                                    ]
                                )
                                )
                                self.dbg(
                                    "  ## UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                        else:  # NUMBER
                            self.sub_inst_ports[instantiation][c_port][
                                "uwidth"
                            ] = sub_io_bitdef_val[1]
                            self.sub_inst_ports[instantiation][c_port][
                                "lwidth"
                            ] = sub_io_bitdef_val[1]

    def parse_connect_cmds(self, instantiation, sub_connect_cmds):
        (submod_name, inst_name, inst_index) = instantiation
        for connect_cmd in sub_connect_cmds:
            connect_cmd = re.sub(r"##", "//", connect_cmd)
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

            if re.search(r"([^,]+)\s*,\s*\/([^,]+)\/(,\s*([^,]+))?", connect_cmd):
                connect_cmd_array = [val.strip() for val in connect_cmd.split(",")]
            else:
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
                    try:
                        repl_func = eval(replace_expr_str)
                        if callable(repl_func):
                            replace_expr_str = repl_func
                    except:
                        pass
                else:
                    replace_direct_str = connect_cmd_array[1]
            else:
                replace_expr_str = ""
                replace_direct_str = ""

            replace_direct_str = re.sub(r"\"", "", replace_direct_str)
            search_slash_regex = RE_REGEX_SLASH.search(connect_cmd_array[0])

            if search_slash_regex:  # Regular expression on the connect syntax
                search_expr_str = search_slash_regex.group(1)
                # search_expr_str = 'r\"' + search_slash_regex.group(1) +'\"'

                self.dbg(
                    "  # SEARCH_EXPR: "
                    + search_expr_str
                    + "; REPLACE_EXPR: "
                    + str(replace_expr_str)
                    + "; TOP_NAME: "
                    + replace_direct_str
                    + "; FILTER: "
                    + connect_filter
                    + ";"
                )
                RE_SEARCH_EXPR_REGEX = re.compile(search_expr_str)
                for c_port in self.sub_inst_ports[instantiation].keys():
                    # Skipping ports that are not matching the port direction filter
                    if (
                            connect_filter == "INPUTS"
                            and self.sub_inst_ports[instantiation][c_port]["dir"]
                            == "output"
                    ):
                        continue
                    elif (
                            connect_filter == "OUTPUTS"
                            and self.sub_inst_ports[instantiation][c_port]["dir"]
                            == "input"
                    ):
                        continue

                    c_port_regex = RE_SEARCH_EXPR_REGEX.search(c_port)

                    if c_port_regex:  # if matching the regular expression
                        self.dbg("    # Matched Port: " + c_port)

                        if slash_replace_str:
                            self.sub_inst_ports[instantiation][c_port][
                                "topname"
                            ] = re.sub(
                                search_expr_str,
                                replace_expr_str,
                                self.sub_inst_ports[instantiation][c_port]["name"],
                            )
                            self.sub_inst_ports[instantiation][c_port][
                                "origconnect"
                            ] = ""
                            self.dbg(
                                "      # UPDATED TOP NAME: "
                                + self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ]
                            )
                            self.sub_inst_ports[instantiation][c_port][
                                "comment"
                            ] = connect_comment

                        else:
                            if replace_direct_str != "":
                                self.sub_inst_ports[instantiation][c_port][
                                    "origconnect"
                                ] = replace_direct_str
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
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""

                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ] = replace_direct_str
                                self.dbg(
                                    "      # UPDATED TOP NAME: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                )
                                self.sub_inst_ports[instantiation][c_port][
                                    "comment"
                                ] = connect_comment
                            else:  # Unconnected port
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ] = ""
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = ""
                                self.dbg("      # UNCONNECTED PORT AT TOP")
                                self.sub_inst_ports[instantiation][c_port][
                                    "comment"
                                ] = connect_comment
            else:  # Direct mapping of port
                search_direct_str = connect_cmd_array[0]

                if search_direct_str in self.sub_inst_ports[instantiation]:
                    # Skipping port that is not matching the port direction filter
                    if (
                            connect_filter == "INPUTS"
                            and self.sub_inst_ports[instantiation][search_direct_str][
                        "dir"
                    ]
                            == "output"
                    ):
                        pass
                    elif (
                            connect_filter == "OUTPUTS"
                            and self.sub_inst_ports[instantiation][search_direct_str][
                                "dir"
                            ]
                            == "input"
                    ):
                        pass
                    else:
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
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "origconnect"
                            ] = replace_direct_str

                            # If this is a constant or param or define or concat of signals, then topbitdef should be empty
                            if (
                                    topname_is_concat_regex
                                    or topname_has_tick_regex
                                    or topname_is_constant_regex
                                    or topname_is_define_regex
                                    or topname_has_dot_regex
                            ):
                                self.sub_inst_ports[instantiation][
                                    search_direct_str
                                ]["topbitdef"] = ""
                                self.sub_inst_ports[instantiation][
                                    search_direct_str
                                ]["topname"] = replace_direct_str
                                self.sub_inst_ports[instantiation][
                                    search_direct_str
                                ]["comment"] = connect_comment
                            else:
                                topname_bitdef_regex = (
                                    RE_OPEN_SQBRCT_BITDEF.search(
                                        replace_direct_str
                                    )
                                )

                                if topname_bitdef_regex:
                                    self.sub_inst_ports[instantiation][
                                        search_direct_str
                                    ]["topname"] = topname_bitdef_regex.group(1)
                                    topbitdef_tmp = topname_bitdef_regex.group(
                                        2
                                    )
                                    topbitdef_tmp = re.sub(
                                        r"]$", "", topbitdef_tmp
                                    )
                                    self.sub_inst_ports[instantiation][
                                        search_direct_str
                                    ]["topbitdef"] = topbitdef_tmp
                                    self.sub_inst_ports[instantiation][
                                        search_direct_str
                                    ]["comment"] = connect_comment
                                else:
                                    self.sub_inst_ports[instantiation][
                                        search_direct_str
                                    ]["topname"] = replace_direct_str
                                    self.sub_inst_ports[instantiation][
                                        search_direct_str
                                    ]["comment"] = connect_comment

                            self.dbg(
                                "      # UPDATED TOP NAME: "
                                + self.sub_inst_ports[instantiation][
                                    search_direct_str
                                ]["topname"]
                            )
                        else:  # Unconnected port
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "topname"
                            ] = ""
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "topbitdef"
                            ] = ""
                            self.dbg("      # UNCONNECTED PORT AT TOP")
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "comment"
                            ] = connect_comment
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
                    self.found_error += 1
                    sys.exit(1)

    def match(self, pattern, name):
        slash_regex = RE_REGEX_SLASH.search(pattern)
        if slash_regex:
            RE_SLASH_REGEX = re.compile(slash_regex.group(1))
            if RE_SLASH_REGEX.search(name):
                return True
            else:
                return False
        else:
            if pattern == name:
                return True
            else:
                return False

    def sub_prep_cmd_filter(self, port, filter):
        matched = self.match(filter["match"], port)
        if not matched:
            return False
        to_exclude = any([self.match(exclude, port) for exclude in filter["excludes"].split()])
        return not to_exclude


    def parse_prep_cmds(self, instantiation):
        (submod_name, inst_name, inst_index) = instantiation
        self.sub_preps[instantiation].append(
            {
                "text": "",
                "filters": [],
                "ports": [],
            }
        )

        for c_port in self.sub_inst_ports[instantiation]:
            in_prep = False
            for prep_cmd in self.sub_preps[instantiation]:
                if prep_cmd["text"] is None:
                    continue

                filters = prep_cmd.get("filters", [])

                for filter in filters:
                    if self.sub_prep_cmd_filter(c_port, filter):
                        if c_port not in prep_cmd["ports"]:
                            prep_cmd["ports"].append(c_port)
                        in_prep = True

            if not in_prep:
                self.sub_preps[instantiation][-1]["ports"].append(c_port)


    def is_forced_internal(self, inst_port):
        for c_internal in self.force_internals:
            c_internal = re.sub(r"[;,]", r"", c_internal)
            c_internal = re.sub(r"\s+", r" ", c_internal)
            c_internal = re.sub(r"\s*$", r"", c_internal)
            c_internal = re.sub(r"^\s*", r"", c_internal)
            force_internal_slash_regex = re.search(RE_REGEX_SLASH, c_internal)

            if force_internal_slash_regex:
                regex_width = force_internal_slash_regex.group(1)
            else:
                regex_width = ""

            RE_FORCE_REGEX = re.compile(regex_width)
            if regex_width != "":
                force_internal_slash_regex = re.search(RE_FORCE_REGEX, inst_port)

                if force_internal_slash_regex:
                    return True
            else:
                if c_internal == inst_port:
                    return True
        return False

    def parse_sub_inst_ports(self, instantiation):
        (submod_name, inst_name, inst_index) = instantiation
        for c_port in self.sub_inst_ports[instantiation]:
            orig_top_name = topname_assign_str = self.sub_inst_ports[instantiation][c_port]["topname"]
            if topname_assign_str == "":
                continue
            if (
                    self.sub_inst_ports[instantiation][c_port]["dir"] == "output" or
                    (self.sub_inst_ports[instantiation][c_port]["dir"] == "inout" and
                     (topname_assign_str in self.inouts or self.is_forced_internal(topname_assign_str))
                    )
            ):
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    io_double_colon_regex = (
                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                        )
                    )
                    io_double_double_colon_regex = (
                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                        )
                    )

                    if io_double_double_colon_regex or io_double_colon_regex:
                        io_bind_package = "default"
                        io_bind_class = "default"

                        if io_double_double_colon_regex:
                            io_bind_package = (
                                io_double_double_colon_regex.group(1)
                            )
                            io_bind_class = io_double_double_colon_regex.group(
                                2
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
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ]
                                + "] "
                                + self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                        else:
                            io_bind_package = io_double_colon_regex.group(1)
                            io_bind_typedef = io_double_colon_regex.group(2)

                            if io_bind_package not in self.packages:
                                self.load_import_or_include_file(
                                    "TOP",
                                    "IMPORT_COMMANDLINE",
                                    io_bind_package + ".sv",
                                )

                            self.binding_typedef(
                                "TOP",
                                "FORCE",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ]
                                + "] "
                                + self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )

                        if self.parsing_format == "verilog":
                            self.parse_signal(
                                "wire",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                        else:
                            self.parse_signal(
                                "reg",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                    elif (
                            self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_LOGIC"
                            or self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_STRUCT"
                            or self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_UNION"
                    ):

                        self.sub_inst_ports[instantiation][c_port][
                            "topname"
                        ] = re.sub(
                            r"[{}\s]",
                            "",
                            self.sub_inst_ports[instantiation][c_port]["topname"],
                        )

                        if (
                                self.sub_inst_ports[instantiation][c_port]["depth"]
                                == ""
                        ):
                            if (
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    not in self.typedef_bindings
                            ):
                                self.binding_typedef(
                                    "TOP",
                                    "FORCE",
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                    + " "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ],
                                )
                        else:
                            if (
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    not in self.typedef_bindings
                            ):
                                self.binding_typedef(
                                    "TOP",
                                    "FORCE",
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                    + " "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    + "["
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "depth"
                                    ]
                                    + "]",
                                )

                        if self.parsing_format == "verilog":
                            self.parse_signal(
                                "wire",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                        else:
                            self.parse_signal(
                                "reg",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                    else:
                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )
                        topname_comma_regex = RE_COMMA.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )

                        if topname_comma_regex:
                            topname_assign_str_array = []
                            # If multiple declarations on the same line, then break it
                            # removing space, { and }
                            topname_assign_str = re.sub(
                                r"[{}\s]",
                                "",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                            topname_assign_str_array = topname_assign_str.split(
                                ","
                            )

                            for curr_topname in topname_assign_str_array:
                                if self.parsing_format == "verilog":
                                    self.parse_signal("wire", curr_topname)
                                else:
                                    self.parse_signal("reg", curr_topname)
                        else:  # Single declaration, then append to the array
                            self.sub_inst_ports[instantiation][c_port][
                                "topname"
                            ] = re.sub(
                                r"[{}\s]",
                                "",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )

                            if topname_bitdef_regex:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ] = re.sub(
                                    r"[{}\s]",
                                    "",
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ],
                                )
                                if self.parsing_format == "verilog":
                                    self.parse_signal(
                                        "wire",
                                        self.sub_inst_ports[instantiation][c_port][
                                            "topname"
                                        ],
                                    )
                                else:
                                    self.parse_signal(
                                        "reg",
                                        self.sub_inst_ports[instantiation][c_port][
                                            "topname"
                                        ],
                                    )
                            else:
                                # TODO: Need to do param overriding replacement on topbitdef
                                topname_assign_str = (
                                        self.sub_inst_ports[instantiation][c_port][
                                            "topname"
                                        ]
                                        + "["
                                        + self.sub_inst_ports[instantiation][c_port][
                                            "topbitdef"
                                        ]
                                        + "]"
                                )

                                if (
                                        self.sub_inst_ports[instantiation][c_port][
                                            "depth"
                                        ]
                                        == ""
                                ):
                                    if self.parsing_format == "verilog":
                                        self.parse_signal(
                                            "wire",
                                            topname_assign_str,
                                        )
                                    else:
                                        self.parse_signal(
                                            "reg", topname_assign_str
                                        )
                                else:
                                    c_top_name = self.sub_inst_ports[instantiation][
                                        c_port
                                    ]["topname"]

                                    # If depth presents, then use sub mod bit definition
                                    if self.parsing_format == "verilog":
                                        self.wires[c_top_name] = {}
                                        self.wires[c_top_name][
                                            "name"
                                        ] = c_top_name
                                        self.wires[c_top_name][
                                            "bitdef"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "topbitdef"
                                        ]
                                        self.wires[c_top_name][
                                            "uwidth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "uwidth"
                                        ]
                                        self.wires[c_top_name][
                                            "lwidth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "lwidth"
                                        ]
                                        self.wires[c_top_name]["mode"] = "AUTO"
                                        self.wires[c_top_name][
                                            "depth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "depth"
                                        ]
                                        self.wires[c_top_name]["signed"] = ""
                                        self.dbg(
                                            "    # NEW WIRE :: "
                                            + self.wires[c_top_name]["name"]
                                            + " # "
                                            + self.wires[c_top_name]["mode"]
                                            + " # "
                                            + self.wires[c_top_name]["bitdef"]
                                            + " # "
                                            + str(
                                                self.wires[c_top_name]["uwidth"]
                                            )
                                            + " # "
                                            + str(
                                                self.wires[c_top_name]["lwidth"]
                                            )
                                            + " # "
                                            + str(
                                                self.wires[c_top_name]["depth"]
                                            )
                                            + " # "
                                            + self.wires[c_top_name]["signed"]
                                            + " #"
                                        )
                                    else:
                                        self.parse_signal(
                                            "reg", topname_assign_str
                                        )
                                        self.regs[c_top_name] = {}
                                        self.regs[c_top_name][
                                            "name"
                                        ] = c_top_name
                                        self.regs[c_top_name][
                                            "bitdef"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "topbitdef"
                                        ]
                                        self.regs[c_top_name][
                                            "uwidth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "uwidth"
                                        ]
                                        self.regs[c_top_name][
                                            "lwidth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "lwidth"
                                        ]
                                        self.regs[c_top_name]["mode"] = "AUTO"
                                        self.regs[c_top_name][
                                            "depth"
                                        ] = self.sub_inst_ports[instantiation][
                                            c_port
                                        ][
                                            "depth"
                                        ]
                                        self.regs[c_top_name]["signed"] = ""
                                        self.dbg(
                                            "    # NEW REG :: "
                                            + self.regs[c_top_name]["name"]
                                            + " # "
                                            + self.regs[c_top_name]["mode"]
                                            + " # "
                                            + self.regs[c_top_name]["bitdef"]
                                            + " # "
                                            + str(
                                                self.regs[c_top_name]["uwidth"]
                                            )
                                            + " # "
                                            + str(
                                                self.regs[c_top_name]["lwidth"]
                                            )
                                            + " # "
                                            + str(
                                                self.regs[c_top_name]["depth"]
                                            )
                                            + " # "
                                            + self.regs[c_top_name]["signed"]
                                            + " #"
                                        )

                else:
                    topname_assign_str = self.sub_inst_ports[instantiation][c_port][
                        "topname"
                    ]

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
                        topname_assign_str_array = topname_assign_str.split(",")
                    else:  # Single declaration, then append to the array
                        topname_assign_str = re.sub(
                            r"[{}\s]", "", topname_assign_str
                        )
                        topname_assign_str_array.append(topname_assign_str)

                    uwidth = self.sub_inst_ports[instantiation][c_port]["uwidth"]
                    lwidth = self.sub_inst_ports[instantiation][c_port]["lwidth"]
                    for curr_topname in topname_assign_str_array:
                        curr_topname_bitdef = curr_topname
                        if len(topname_assign_str_array) == 1 and uwidth and uwidth != "0":
                            curr_topname_bitdef = f"{curr_topname}[{uwidth}:{lwidth}]"
                        if self.parsing_format == "verilog":
                            self.parse_signal("wire", curr_topname_bitdef)
                        else:
                            self.parse_signal("reg", curr_topname_bitdef)

                if self.sub_inst_ports[instantiation][c_port]["dir"] == "inout":
                    if orig_top_name in self.inouts:
                        if orig_top_name in self.ports and self.ports[orig_top_name]["mode"] != "FORCE":
                            del self.ports[orig_top_name]
                        if orig_top_name in self.regs:
                            self.regs[orig_top_name]["type"] = "LOCAL"
                        self.inouts[orig_top_name].append((inst_name, c_port))
                    else:
                        self.inouts[orig_top_name] = [(inst_name, c_port)]

            elif (
                    self.sub_inst_ports[instantiation][c_port]["dir"] == "input"
            ):  # Sub module port is an input
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    io_double_colon_regex = (
                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_COLON.search(
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                        )
                    )
                    io_double_double_colon_regex = (
                        RE_SUBPORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                        )
                    )

                    if io_double_double_colon_regex or io_double_colon_regex:
                        io_bind_package = "default"
                        io_bind_class = "default"

                        if io_double_double_colon_regex:
                            io_bind_package = (
                                io_double_double_colon_regex.group(1)
                            )
                            io_bind_class = io_double_double_colon_regex.group(
                                2
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
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ]
                                + "] "
                                + self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )
                        else:
                            io_bind_package = io_double_colon_regex.group(1)
                            io_bind_typedef = io_double_colon_regex.group(2)

                            if io_bind_package not in self.packages:
                                self.load_import_or_include_file(
                                    "TOP",
                                    "IMPORT_COMMANDLINE",
                                    io_bind_package + ".sv",
                                )

                            self.binding_typedef(
                                "TOP",
                                "FORCE",
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ]
                                + "] "
                                + self.sub_inst_ports[instantiation][c_port][
                                    "topname"
                                ],
                            )

                        self.parse_conditions(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )
                    elif (
                            self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_LOGIC"
                            or self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_STRUCT"
                            or self.sub_inst_ports[instantiation][c_port]["typedef"]
                            == "TYPEDEF_UNION"
                    ):
                        if (
                                self.sub_inst_ports[instantiation][c_port]["depth"]
                                == ""
                        ):
                            if (
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    not in self.typedef_bindings
                            ):
                                self.binding_typedef(
                                    "TOP",
                                    "FORCE",
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                    + " "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ],
                                )
                        else:
                            if (
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    not in self.typedef_bindings
                            ):
                                self.binding_typedef(
                                    "TOP",
                                    "FORCE",
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                    + " "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                    + "["
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "depth"
                                    ]
                                    + "]",
                                )

                        self.parse_conditions(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )
                    else:
                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )
                        topname_comma_regex = RE_COMMA.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )

                        if topname_comma_regex:
                            topname_assign_str_array = []
                            # If multiple declarations on the same line, then break it
                            # removing space, { and }
                            topname_assign_str = re.sub(
                                r"[{}\s]", "", topname_assign_str
                            )
                            topname_assign_str_array = topname_assign_str.split(
                                ","
                            )

                            for curr_topname in topname_assign_str_array:
                                self.parse_conditions(curr_topname)
                        else:  # Single declaration, then append to the array
                            if topname_bitdef_regex:
                                self.parse_conditions(
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topname"
                                    ]
                                )
                            else:
                                # TODO: Need to do param overriding replacement on topbitdef
                                topname_assign_str = (
                                        self.sub_inst_ports[instantiation][c_port][
                                            "topname"
                                        ]
                                        + "["
                                        + self.sub_inst_ports[instantiation][c_port][
                                            "topbitdef"
                                        ]
                                        + "]"
                                )

                                if (
                                        self.sub_inst_ports[instantiation][c_port][
                                            "depth"
                                        ]
                                        == ""
                                ):
                                    self.parse_conditions(topname_assign_str)
                                else:
                                    c_top_name = self.sub_inst_ports[instantiation][
                                        c_port
                                    ]["topname"]
                                    self.signals[c_top_name] = {}
                                    self.signals[c_top_name][
                                        "name"
                                    ] = c_top_name
                                    self.signals[c_top_name][
                                        "bitdef"
                                    ] = self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                    self.signals[c_top_name][
                                        "uwidth"
                                    ] = self.sub_inst_ports[instantiation][c_port][
                                        "uwidth"
                                    ]
                                    self.signals[c_top_name][
                                        "lwidth"
                                    ] = self.sub_inst_ports[instantiation][c_port][
                                        "lwidth"
                                    ]
                                    self.signals[c_top_name]["mode"] = "AUTO"
                                    self.signals[c_top_name][
                                        "depth"
                                    ] = self.sub_inst_ports[instantiation][c_port][
                                        "depth"
                                    ]
                                    self.signals[c_top_name]["signed"] = ""
                                    self.dbg(
                                        "    # NEW SIGNAL :: "
                                        + self.signals[c_top_name]["name"]
                                        + " # "
                                        + self.signals[c_top_name]["mode"]
                                        + " # "
                                        + self.signals[c_top_name]["bitdef"]
                                        + " # "
                                        + str(
                                            self.signals[c_top_name]["uwidth"]
                                        )
                                        + " # "
                                        + str(
                                            self.signals[c_top_name]["lwidth"]
                                        )
                                        + " # "
                                        + str(self.signals[c_top_name]["depth"])
                                        + " # "
                                        + self.signals[c_top_name]["signed"]
                                        + " #"
                                    )
                else:
                    self.parse_conditions(
                        self.sub_inst_ports[instantiation][c_port]["topname"]
                    )
            elif (self.sub_inst_ports[instantiation][c_port]["dir"] == "inout" and
                  topname_assign_str not in self.inouts
            ):  # Sub module port is an inout
                c_top_name = self.sub_inst_ports[instantiation][c_port]["topname"]
                if c_top_name not in self.inouts:
                    self.inouts[c_top_name] = [(inst_name, c_port)]

                if c_top_name != "" and c_top_name not in self.ports:
                    # print(self.ports[c_top_name])
                    self.ports[c_top_name] = {}
                    self.ports[c_top_name]["name"] = c_top_name
                    self.ports[c_top_name]["dir"] = "inout"
                    self.ports[c_top_name]["bitdef"] = self.sub_inst_ports[
                        instantiation
                    ][c_port]["topbitdef"]
                    self.ports[c_top_name]["uwidth"] = self.sub_inst_ports[
                        instantiation
                    ][c_port]["uwidth"]
                    self.ports[c_top_name]["lwidth"] = self.sub_inst_ports[
                        instantiation
                    ][c_port]["lwidth"]
                    self.ports[c_top_name]["mode"] = "AUTO"
                    self.ports[c_top_name]["depth"] = self.sub_inst_ports[
                        instantiation
                    ][c_port]["depth"]
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

    def parse_auto_instance(self, lines):
        look_for_instance_cmds = 0
        for line in lines:
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
                                    submod_format = "PSV"
                                    submod_file_with_path = sub_mode_file_path

                    if not found_submod_file:
                        # Look for .pv file
                        if file_name == "":
                            file_name_with_ext = submod_name + ".pv"
                        else:
                            file_name_with_ext = file_name

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
                                        submod_format = "PV"
                                        submod_file_with_path = sub_mode_file_path

                # Look for systemverilog module
                if not found_submod_file and submod_name.startswith("mem_wrapper_"):
                    # Process 3rd-party .f files.
                    file_name_with_ext = f"{submod_name}.f"
                    self.dbg("\n  finding file list..." + file_name_with_ext)
                    # Only the memory files are supported currently.
                    third_party_incl_dirs = [
                        d for d in self.incl_dirs if "hls_rtl/" or "third_party/" in d
                    ]

                    for d in third_party_incl_dirs:
                        sub_mode_file_path = os.path.join(d, file_name_with_ext)
                        if os.path.isfile(sub_mode_file_path):
                            self.filelist.append(f"-f {sub_mode_file_path}")
                            found_submod_file = 1
                            submod_format = "F"
                            submod_file_with_path = sub_mode_file_path
                            break  # Exit on first occurrence.

                if not found_submod_file:
                    if file_name == "":
                        file_name_with_ext = submod_name + ".sv"
                    else:
                        file_name_with_ext = file_name

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
                                    submod_format = "SV"
                                    submod_file_with_path = sub_mode_file_path

                if not found_submod_file:
                    submod_file_with_path = self.find_in_files(file_name_with_ext)

                    if submod_file_with_path is not None:
                        found_submod_file = 1

                if not found_submod_file:
                    # Look for verilog module
                    if file_name == "":
                        file_name_with_ext = submod_name + ".v"
                    else:
                        file_name_with_ext = file_name

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
                                    submod_format = "V"
                                    submod_file_with_path = sub_mode_file_path

                if not found_submod_file:
                    submod_file_with_path = self.find_in_files(file_name_with_ext)

                    if submod_file_with_path is not None:
                        found_submod_file = 1

                if not found_submod_file:
                    # Look for verilog module
                    if file_name == "":
                        file_name_with_ext = submod_name + ".vp"
                    else:
                        file_name_with_ext = file_name

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
                                    submod_format = "VP"
                                    submod_file_with_path = sub_mode_file_path

                if not found_submod_file:
                    submod_file_with_path = self.find_in_files(file_name_with_ext)

                    if submod_file_with_path is not None:
                        found_submod_file = 1

                if not found_submod_file:
                    # Process 3rd-party .f files.
                    file_name_with_ext = f"{submod_name}.f"
                    self.dbg("\n  finding file list..." + file_name_with_ext)
                    # Only the memory files are supported currently.
                    third_party_incl_dirs = [
                        d for d in self.incl_dirs if "hls_rtl/" or "third_party/" in d
                    ]

                    for d in third_party_incl_dirs:
                        sub_mode_file_path = os.path.join(d, file_name_with_ext)
                        if os.path.isfile(sub_mode_file_path):
                            self.filelist.append(f"-f {sub_mode_file_path}")
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

                submod_file_with_path = re.sub(r"//", "/", submod_file_with_path)
                print(
                    "    - Instantiating MODULE: "
                    + submod_name
                    + " INST: "
                    + inst_name
                    + " FILE: "
                    + submod_file_with_path
                )

                if (submod_name, inst_name, submod_file_with_path) not in self.instantiated_modules:
                    self.instantiated_modules[(submod_name, inst_name, submod_file_with_path)] = 0
                    inst_index = 0
                else:
                    self.instantiated_modules[(submod_name, inst_name, submod_file_with_path)] += 1
                    inst_index = self.instantiated_modules[(submod_name, inst_name, submod_file_with_path)]

                instantiation = (submod_name, inst_name, inst_index)

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
                            self.dependencies["veripy_subs"][submod_file_with_path] = {}
                            self.dependencies["veripy_subs"][submod_file_with_path][
                                "mtime"
                            ] = getmtime(submod_file_with_path)
                            self.dependencies["veripy_subs"][submod_file_with_path][
                                "flags"
                            ] = []

                inc_dir = os.path.dirname(submod_file_with_path)
                if inc_dir not in self.incl_dirs:
                    self.incl_dirs.append(inc_dir)

                if submod_format == "F":
                    file_name_with_ext = f"{submod_name}.v"
                    verilog_pattern = re.compile(file_name_with_ext)
                    file_name_with_ext = f"{submod_name}.sv"
                    sverilog_pattern = re.compile(file_name_with_ext)

                    for l in open(submod_file_with_path):
                        if re.findall(verilog_pattern, l):
                            submod_file_with_path = os.path.expandvars(l.strip("\n"))
                        elif re.findall(sverilog_pattern, l):
                            submod_file_with_path = os.path.expandvars(l.strip("\n"))

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

                submod_file_with_path = re.sub(r"//", "/", submod_file_with_path)

                if submod_format == "V":
                    submod_filelist = re.sub(r"\.v$", ".f", submod_file_with_path)
                elif submod_format == "SV":
                    submod_filelist = re.sub(r"\.sv$", ".f", submod_file_with_path)
                elif submod_format == "VP":
                    submod_filelist = re.sub(r"\.vp$", ".f", submod_file_with_path)

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

                if (
                    instantiation in self.sub_inst_files
                    and submod_file_with_path != self.sub_inst_files[instantiation]
                ):
                    print(
                        "\nWarning: Repeated instance name is defined: "
                        + inst_name
                        + "\nmodule:"
                        + submod_name
                        + "\nmodule files:"
                        + str(
                            [
                                submod_file_with_path,
                                self.sub_inst_files[instantiation],
                            ]
                        )
                    )

                self.sub_inst_ports[instantiation] = {}
                self.sub_inst_params[instantiation] = {}
                self.sub_inst_files[instantiation] = submod_file_with_path
                self.sub_inst_modules[instantiation] = submod_name
                self.prev_line = ""
                self.sub_preps[instantiation] = []

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
                    "# SUB PORTS :: Module: " + submod_name + "; Instance: " + inst_name
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
                    "# SUB PARAM :: Module: " + submod_name + "; Instance: " + inst_name
                )
                self.dbg(
                    "################################################################################"
                )
                self.dbg(json.dumps(self.sub_params, indent=2))
                self.dbg("\n")

                self.parse_param_cmds(instantiation, sub_param_cmds)

                self.parse_sub_ports(instantiation)

                ################################################################################
                # Applying all the connect commands
                ################################################################################
                self.parse_connect_cmds(instantiation, sub_connect_cmds)

                self.parse_prep_cmds(instantiation)

                # print(json.dumps(self.sub_inst_ports[instantiation], indent=2))

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
                self.dbg(json.dumps(self.sub_inst_ports[instantiation], indent=2))
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
                self.dbg(json.dumps(self.sub_inst_params[instantiation], indent=2))
                self.dbg("\n")

                self.parse_sub_inst_ports(instantiation)

                self.filelist.append(submod_file_with_path)

            elif look_for_instance_cmds:
                printtext_regex = RE_PRINTTEXT.search(line)
                printio_regex = RE_PRINTIO.search(line)
                if connect_regex:
                    if self.gen_dependencies:
                        continue

                    single_line_comment_regex = re.search(RE_SINGLE_LINE_COMMENT, line)

                    if single_line_comment_regex:
                        sub_connect_cmds.append(
                            connect_regex.group(1)
                            + " //"
                            + single_line_comment_regex.group(1)
                        )
                    else:
                        sub_connect_cmds.append(connect_regex.group(1))
                elif param_override_regex:
                    param_overriding_str = param_override_regex.group(1)

                    if re.search(r"(\S+)\s*=\s*(\S+)", param_overriding_str):
                        print(
                            "\nWarning: '=' in &Param will be removed: "
                            + param_overriding_str
                        )
                        param_overriding_str = re.sub(r"=", "", param_overriding_str)

                    # Gather the list of param overrides to process after gathering ports and params of sub-modules
                    sub_param_cmds.append(param_override_regex.group(1))

                    # Possible reference to an SV package if it is used in the parameter/define
                    param_name = param_override_regex.group(1)
                    param_double_colon_regex = RE_DOUBLE_COLON.search(param_name)
                    if param_double_colon_regex:
                        param_package = param_double_colon_regex.group(1)
                        if param_package not in self.sub_packages:
                            self.load_import_or_include_file(
                                "SUB",
                                "IMPORT_COMMANDLINE",
                                param_package + ".sv",
                            )

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
                            self.dependencies["veripy_subs"][submod_file_with_path][
                                "flags"
                            ].append(build_cmd)

                    continue
                elif include_regex:
                    loadincludefiles = include_regex.group(1)
                    self.sub_include_files_list = loadincludefiles.split()

                    # if gen_dependencies:
                    # self.sub_include_files_list = loadincludefiles.split()

                    # for c_incl in self.sub_include_files_list:
                    # self.dependencies['include_files'].append(c_incl)

                    continue
                elif printtext_regex:
                    print(f"Line: {line}")
                    if self.gen_dependencies:
                        continue

                    self.sub_preps[instantiation].append(
                        {
                            "text": printtext_regex.group(1),
                            "filters": [],
                            "ports": [],
                        }
                    )
                elif printio_regex:
                    print(f"Line: {line}")
                    if self.gen_dependencies:
                        continue

                    match, excludes =  [exp.strip() for exp in printio_regex.group(1).split(",")]
                    self.sub_preps[instantiation][-1]["filters"].append(
                        {
                            "match": match,
                            "excludes": excludes,
                        }
                    )

                continue

    def parse_pkg2assign_assign2pkg(self, pkg2assign_regex, assign2pkg_regex):
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

        typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(p2a_pkgmember)
        typedef_ref_regex_double = RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(p2a_pkgmember)

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

        if typedef_name in self.typedef_logics[typedef_package][typedef_class]:
            found_in_typedef = "LOGICS"
            # print('### LOGICS ###',self.typedef_logics[typedef_package][typedef_class][typedef_name])
            pass
        elif typedef_name in self.typedef_structs[typedef_package][typedef_class]:
            found_in_typedef = "STRUCTS"
            gen_lines = []

            for c_member in self.typedef_structs[typedef_package][typedef_class][
                typedef_name
            ].keys():
                reserved_regex = RE_RESERVED.search(c_member)

                if c_member != "struct" and c_member != "width" and not reserved_regex:
                    if (
                        self.typedef_structs[typedef_package][typedef_class][
                            typedef_name
                        ][c_member]["uwidth"]
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
                                self.typedef_structs[typedef_package][typedef_class][
                                    typedef_name
                                ][c_member]["width"]
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

            if pkg2assign_regex:
                self.pkg2assign_info[self.pkg2assign_index] = []
                self.pkg2assign_info[self.pkg2assign_index] = gen_lines
                self.pkg2assign_index = self.pkg2assign_index + 1
            else:
                self.assign2pkg_info[self.assign2pkg_index] = []
                self.assign2pkg_info[self.assign2pkg_index] = gen_lines
                self.assign2pkg_index = self.assign2pkg_index + 1
        elif typedef_name in self.typedef_unions[typedef_package][typedef_class]:
            # print('### UNIONS ###',self.typedef_unions[typedef_package][typedef_class][typedef_name])
            found_in_typedef = "UNIONS"

    def parse_manual_instance(
        self, manual_instance_line, submod_file_with_path, submod_name, inst_name
    ):
        self.filelist.append(submod_file_with_path)

        submod_file_ext = re.sub(r".*\.", "", submod_file_with_path)

        if self.gen_dependencies:
            if submod_file_ext == "psv" or submod_file_ext == "pv":
                if submod_file_with_path not in self.dependencies["veripy_subs"]:
                    self.dependencies["veripy_subs"][submod_file_with_path] = {}
                    self.dependencies["veripy_subs"][submod_file_with_path][
                        "flags"
                    ] = []
                    self.dependencies["veripy_subs"][submod_file_with_path][
                        "mtime"
                    ] = getmtime(submod_file_with_path)
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
        )

        if self.gen_dependencies:
            self.prev_line = ""
            line = ""
            gather_manual_instance = 0
            parse_manual_instance = 0
            return

        manual_instance_line = re.sub(r"\s+", " ", manual_instance_line)

        # Extract Module Name
        module_name_regex = RE_NAME_BEGIN.search(manual_instance_line)

        if module_name_regex:
            module_with_tick_define_regex = RE_DEFINE_TICK_EXTRACT.search(
                manual_instance_line
            )

            if module_with_tick_define_regex:
                submod_name = self.get_tick_defval(
                    module_with_tick_define_regex.group(1)
                )
            else:
                submod_name = module_name_regex.group(1)

            manual_instance_line = module_name_regex.group(2)
        else:
            self.dbg("\nError: Unable to extract module name in the following line")
            self.dbg(manual_instance_line)
            print("\nError: Unable to extract module name in the following line")
            print(manual_instance_line + "\n")
            sys.exit(1)

        # Extract Params
        # RE_PARAMS_EXTRACT = re.compile(r"^\s*#\s*\((.*)\s*\)\s*\)\s*(.*)")
        RE_PARAMS_EXTRACT = re.compile(
            r"^\s*#\s*\((.*)\s*\)\s*\)\s*([\w\[\]]+)\s*(\(.*)"
        )
        params_extract_regex = RE_PARAMS_EXTRACT.search(manual_instance_line)

        param_overriding_list = []
        if params_extract_regex:
            param_overriding = params_extract_regex.group(1) + ")"
            param_overriding = re.sub(r"\s+", "", param_overriding)
            manual_instance_line = (
                params_extract_regex.group(2) + " " + params_extract_regex.group(3)
            )
            param_overriding_list = param_overriding.split(",")

        # Extract Instance Name
        inst_name_regex = RE_NAME_BEGIN.search(manual_instance_line)
        inst_name_bracket_regex = RE_NAME_BRACKET_BEGIN.search(manual_instance_line)

        connections = ""

        if inst_name_regex:
            inst_name = inst_name_regex.group(1)
            connections = inst_name_regex.group(2)
        elif inst_name_bracket_regex:
            inst_name = inst_name_bracket_regex.group(1)
            connections = "(" + inst_name_bracket_regex.group(2)
        else:
            self.dbg("\nError: Unable to extract instance name in the following line")
            self.dbg(manual_instance_line)
            print("\nError: Unable to extract instance name in the following line")
            print(manual_instance_line + "\n")
            sys.exit(1)

        # Extract Connections
        connections = re.sub(r"\s+", "", connections)
        connections = re.sub(r"^\(\.?", "", connections)
        connections = re.sub(r",?\);$", "", connections)
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
                    sub_mode_file_path = str(dir) + "/" + str(file_name_with_ext)
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
                for dir in self.incl_dirs:
                    if not found_submod_file:
                        sub_mode_file_path = str(dir) + "/" + str(file_name_with_ext)
                        if os.path.isfile(sub_mode_file_path):
                            found_submod_file = 1
                            submod_file_with_path = sub_mode_file_path

        if not found_submod_file:
            submod_file_with_path = self.find_in_files(file_name_with_ext)

            if submod_file_with_path is not None:
                found_submod_file = 1

        if not found_submod_file:
            # Look for verilog module
            file_name_with_ext = submod_name + ".vp"

            if os.path.isfile(file_name_with_ext):  # In file doesn't exist
                found_submod_file = 1
                submod_file_with_path = file_name_with_ext
            else:
                for dir in self.incl_dirs:
                    if not found_submod_file:
                        sub_mode_file_path = str(dir) + "/" + str(file_name_with_ext)
                        if os.path.isfile(sub_mode_file_path):
                            found_submod_file = 1
                            submod_file_with_path = sub_mode_file_path

        if not found_submod_file:
            submod_file_with_path = self.find_in_files(file_name_with_ext)

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

        submod_file_with_path = re.sub(r"//", "/", submod_file_with_path)
        print(
            "    - Parsing SUB-MODULE: "
            + submod_name
            + " INST: "
            + inst_name
            + " FILE: "
            + submod_file_with_path
        )

        if (submod_name, inst_name) not in self.instantiated_modules:
            self.instantiated_modules[(submod_name, inst_name)] = 0
            inst_index = 0
        else:
            self.instantiated_modules[(submod_name, inst_name)] += 1
            inst_index = self.instantiated_modules[(submod_name, inst_name)]

        instantiation = (submod_name, inst_name, inst_index)

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

        submod_file_with_path = re.sub(r"//", "/", submod_file_with_path)
        self.get_ports(submod_name, submod_file_with_path)

        self.dbg(
            "\n\n################################################################################"
        )
        self.dbg("# SUB PORTS :: Module: " + submod_name + "; Instance: " + inst_name)
        self.dbg(
            "################################################################################"
        )
        self.dbg(json.dumps(self.sub_ports, indent=2))
        self.dbg("\n")

        self.dbg(
            "\n\n################################################################################"
        )
        self.dbg("# SUB PARAM :: Module: " + submod_name + "; Instance: " + inst_name)
        self.dbg(
            "################################################################################"
        )
        self.dbg(json.dumps(self.sub_params, indent=2))
        self.dbg("\n")

        if (
            instantiation in self.sub_inst_files
            and submod_file_with_path != self.sub_inst_files[instantiation]
        ):
            print(
                "\nWarning: Repeated instance name is defined: "
                + inst_name
                + "\nmodule:"
                + submod_name
                + "\nmodule files:"
                + str(
                    [
                        submod_file_with_path,
                        self.sub_inst_files[instantiation],
                    ]
                )
            )

        self.sub_inst_ports[instantiation] = {}
        self.sub_inst_params[instantiation] = {}
        self.sub_inst_files[instantiation] = submod_file_with_path
        self.sub_inst_modules[instantiation] = submod_name
        self.prev_line = ""

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
                    self.sub_inst_params[instantiation][sub_param_name] = {}
                    self.sub_inst_params[instantiation][sub_param_name][
                        "name"
                    ] = sub_param_name
                    self.sub_inst_params[instantiation][sub_param_name][
                        "topname"
                    ] = top_param_name
                    self.sub_inst_params[instantiation][sub_param_name][
                        "type"
                    ] = self.sub_params[sub_param_name]["type"]
                    self.sub_inst_params[instantiation][sub_param_name][
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
                    self.found_error += 1
                    sys.exit(1)
            else:
                self.dbg("\nError: Unable to parse &Param override call")
                self.dbg(param_cmd)
                print("\nError: Unable to parse &Param override call")
                print(param_cmd)
                self.found_error += 1

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
            self.sub_inst_ports[instantiation][c_port] = {}
            self.sub_inst_ports[instantiation][c_port]["name"] = self.sub_ports[c_port][
                "name"
            ]
            self.sub_inst_ports[instantiation][c_port]["topname"] = self.sub_ports[c_port][
                "name"
            ]
            self.sub_inst_ports[instantiation][c_port]["bitdef"] = self.sub_ports[c_port][
                "bitdef"
            ]
            self.sub_inst_ports[instantiation][c_port]["topbitdef"] = self.sub_ports[
                c_port
            ]["bitdef"]
            self.sub_inst_ports[instantiation][c_port]["uwidth"] = self.sub_ports[c_port][
                "uwidth"
            ]
            self.sub_inst_ports[instantiation][c_port]["lwidth"] = self.sub_ports[c_port][
                "lwidth"
            ]
            self.sub_inst_ports[instantiation][c_port]["depth"] = self.sub_ports[c_port][
                "depth"
            ]
            self.sub_inst_ports[instantiation][c_port]["dir"] = self.sub_ports[c_port][
                "dir"
            ]
            self.sub_inst_ports[instantiation][c_port]["typedef"] = self.sub_ports[c_port][
                "typedef"
            ]
            self.sub_inst_ports[instantiation][c_port]["connected"] = 0
            self.sub_inst_ports[instantiation][c_port]["comment"] = ""

            ################################################################################
            # Applying all the param overriding on each port
            ################################################################################
            c_topbitdef = self.sub_inst_ports[instantiation][c_port]["topbitdef"]

            is_param_subed = False
            for c_param in self.sub_inst_params[instantiation]:
                c_topparam = self.sub_inst_params[instantiation][c_param]["topname"]
                # Replace param with param value if param scope is module_body or module_local
                # if c_topparam in self.params and self.params[c_topparam]["scope"] in ["module_body", "module_body_local"]:
                #     c_param_val = str(self.params[c_topparam]["val"])
                #     if not re.search(r"==.*?.*:.*", c_param_val):
                #         c_topparam = str(self.params[c_topparam]["val"])

                if c_param == c_topparam:
                    continue

                c_sep = "(?P<sep>\W*)"
                c_param_str = f"\\b{c_param}\\b"
                c_param_search_str = c_sep + c_param_str
                mat = re.search(c_param_search_str, c_topbitdef)
                if mat and (mat[1] == ""  or mat[1] not in ["::"]):
                    c_topbitdef = re.sub(
                        c_param_str, c_topparam, c_topbitdef
                    )
                    is_param_subed = True

            for c_sub_param in self.sub_params.keys():
                if (
                    self.sub_params[c_sub_param]["scope"] not in ["module_header", "module_body", "module_body_local"] or
                    c_sub_param == "" or
                    re.search(r"\W+", c_sub_param) or
                    c_sub_param in self.sub_inst_params[instantiation]
                    or re.search(r"==.*?.*:.*", str(self.sub_params[c_sub_param]['val']))
                    or c_sub_param in self.params
                ):
                    continue

                c_sep = "(?P<sep>\W*)"
                c_sub_param_str = f"\\b{c_sub_param}\\b"
                c_sub_param_search_str = c_sep + c_sub_param_str
                mat = re.search(c_sub_param_search_str, c_topbitdef)
                if mat and  (mat[1] == ""  or mat[1] not in ["::"]):
                    c_topbitdef = re.sub(
                        c_sub_param_str, str(self.sub_params[c_sub_param]['val']), c_topbitdef
                    )
                    is_param_subed = True

            # if is_param_subed:
            try:
                mat = re.match(r"^([^:]+):([^:]+)$", c_topbitdef)
                if mat:
                    c_topbit1 = mat[1]
                    c_topbit2 = mat[2]
                    c_topbit1_val = int(eval(c_topbit1))
                    c_topbitdef = f"{str(c_topbit1_val)}:{c_topbit2}"
            except Exception:
                pass

            if c_topbitdef != self.sub_inst_ports[instantiation][c_port]["topbitdef"]:
                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = c_topbitdef

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
                double_double_colon_regex = RE_DOUBLE_DOUBLE_COLON.search(
                    self.sub_ports[c_port]["bitdef"]
                )
                c_port_typedef = self.sub_ports[c_port]["typedef"]

                if double_colon_regex or double_double_colon_regex:
                    if double_double_colon_regex:
                        c_port_package = double_colon_regex.group(1)
                        c_port_class = double_colon_regex.group(2)
                        c_port_typedef = double_colon_regex.group(2)
                    else:
                        if double_colon_regex.group(1) in list(self.sub_classes):
                            c_port_package = "default"
                            c_port_class = double_colon_regex.group(1)
                            c_port_typedef = double_colon_regex.group(2)
                        else:
                            c_port_package = double_colon_regex.group(1)
                            c_port_class = "default"
                            c_port_typedef = double_colon_regex.group(2)

                    if self.sub_ports[c_port]["typedef"] == "TYPEDEF_LOGIC":
                        # Checking if package and class are present at top
                        if (
                            c_port_package in self.typedef_logics
                            and c_port_class in self.typedef_logics[c_port_package]
                        ):
                            # Checking if the typedef logic is part of the package
                            if (
                                c_port_typedef
                                in self.typedef_logics[c_port_package][c_port_class]
                            ):
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = self.sub_ports[c_port]["bitdef"]
                            else:  # Typedef is not part of the package
                                if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][c_port][
                                            "topbitdef"
                                        ]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                self.sub_ports[c_port]["uwidth"] != ""
                                and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                    str(self.sub_ports[c_port]["uwidth"])
                                    + ":"
                                    + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = ""
                    elif self.sub_ports[c_port]["typedef"] == "TYPEDEF_STRUCT":
                        # Checking if package is present
                        if (
                            c_port_package in self.typedef_structs
                            and c_port_class in self.typedef_structs[c_port_package]
                        ):
                            # Checking if the typedef logic is part of the package
                            if (
                                c_port_typedef
                                in self.typedef_structs[c_port_package][c_port_class]
                            ):
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = self.sub_ports[c_port]["bitdef"]
                            else:  # Typedef is not part of the package
                                if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][c_port][
                                            "topbitdef"
                                        ]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                self.sub_ports[c_port]["uwidth"] != ""
                                and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                    str(self.sub_ports[c_port]["uwidth"])
                                    + ":"
                                    + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = ""
                    elif self.sub_ports[c_port]["typedef"] == "TYPEDEF_UNION":
                        # Checking if package is present
                        if (
                            c_port_package in self.typedef_unions
                            and c_port_class in self.typedef_unions[c_port_class]
                        ):
                            # Checking if the typedef logic is part of the package
                            if c_port_typedef in self.typedef_unions[c_port_package]:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = self.sub_ports[c_port]["bitdef"]
                            else:  # Typedef is not part of the package
                                if (
                                    self.sub_ports[c_port]["uwidth"] != ""
                                    and self.sub_ports[c_port]["lwidth"] != ""
                                ):
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = (
                                        str(self.sub_ports[c_port]["uwidth"])
                                        + ":"
                                        + str(self.sub_ports[c_port]["lwidth"])
                                    )
                                    self.dbg(
                                        "  # UPDATED TOP BITDEF :: "
                                        + self.sub_inst_ports[instantiation][c_port][
                                            "topbitdef"
                                        ]
                                    )
                                else:
                                    self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ] = ""
                        else:  # Package not present at top, so bitdef with numerical vlue
                            if (
                                self.sub_ports[c_port]["uwidth"] != ""
                                and self.sub_ports[c_port]["lwidth"] != ""
                            ):
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                    str(self.sub_ports[c_port]["uwidth"])
                                    + ":"
                                    + str(self.sub_ports[c_port]["lwidth"])
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                            else:
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = ""
                else:
                    # Check if the typedef is part of default package
                    if c_port_typedef in self.typedef_logics["default"]["default"]:
                        self.sub_inst_ports[instantiation][c_port][
                            "topbitdef"
                        ] = self.sub_ports[c_port]["bitdef"]
                    elif c_port_typedef in self.typedef_structs["default"]["default"]:
                        self.sub_inst_ports[instantiation][c_port][
                            "topbitdef"
                        ] = self.sub_ports[c_port]["bitdef"]
                    elif c_port_typedef in self.typedef_unions["default"]["default"]:
                        self.sub_inst_ports[instantiation][c_port][
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
                            io_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                                self.sub_ports[c_port]["bitdef"]
                            )

                            if io_bitdef_packed_regex:
                                self.sub_inst_ports[instantiation][c_port][
                                    "topbitdef"
                                ] = self.sub_ports[c_port]["bitdef"]
                            else:
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                    str(
                                        self.sub_inst_ports[instantiation][c_port]["uwidth"]
                                    )
                                    + ":"
                                    + str(
                                        self.sub_inst_ports[instantiation][c_port]["lwidth"]
                                    )
                                )
                                self.dbg(
                                    "  # UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                        else:
                            self.sub_inst_ports[instantiation][c_port][
                                "topbitdef"
                            ] = self.sub_ports[c_port]["bitdef"]
            else:
                # Update uwidth and lwidth after param override
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    sub_io_bitdef_val = self.tickdef_param_getval(
                        "TOP",
                        self.sub_inst_ports[instantiation][c_port]["topbitdef"],
                        "",
                        "",
                    )

                    if sub_io_bitdef_val[0] == "STRING":
                        # Checking if the bitdef has the multi dimentional array
                        io_bitdef_packed_regex = RE_PACKED_ARRAY.search(
                            self.sub_ports[c_port]["bitdef"]
                        )

                        if not io_bitdef_packed_regex:
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                str(self.sub_inst_ports[instantiation][c_port]["uwidth"])
                                + ":"
                                + str(self.sub_inst_ports[instantiation][c_port]["lwidth"])
                            )
                            self.dbg(
                                "  ## UPDATED TOP BITDEF :: "
                                + self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                            )
                    else:
                        if sub_io_bitdef_val[0] == "BITDEF":
                            # Updating numberical values of upper and lower width
                            bitdef_colon_regex = RE_COLON.search(
                                str(sub_io_bitdef_val[1])
                            )
                            self.sub_inst_ports[instantiation][c_port][
                                "uwidth"
                            ] = bitdef_colon_regex.group(1)
                            self.sub_inst_ports[instantiation][c_port][
                                "lwidth"
                            ] = bitdef_colon_regex.group(2)

                            c_topbitdef = self.sub_inst_ports[instantiation][c_port][
                                "topbitdef"
                            ]
                            c_topbitdef = re.sub(r":", "", c_topbitdef)
                            c_topbitdef = re.sub(r"-", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\+", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\(", "", c_topbitdef)
                            c_topbitdef = re.sub(r"\)", "", c_topbitdef)

                            topbitdef_numbers_regex = RE_NUMBERS_ONLY.search(
                                c_topbitdef
                            )

                            if topbitdef_numbers_regex:
                                self.sub_inst_ports[instantiation][c_port]["topbitdef"] = (
                                    str(
                                        self.sub_inst_ports[instantiation][c_port]["uwidth"]
                                    )
                                    + ":"
                                    + str(
                                        self.sub_inst_ports[instantiation][c_port]["lwidth"]
                                    )
                                )
                                self.dbg(
                                    "  ## UPDATED TOP BITDEF :: "
                                    + self.sub_inst_ports[instantiation][c_port][
                                        "topbitdef"
                                    ]
                                )
                        else:  # NUMBER
                            self.sub_inst_ports[instantiation][c_port][
                                "uwidth"
                            ] = sub_io_bitdef_val[1]
                            self.sub_inst_ports[instantiation][c_port][
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

                replace_slash_regex = RE_REGEX_SLASH.search(connect_cmd_array[1])

                if replace_slash_regex:
                    replace_expr_str = replace_slash_regex.group(1)
                else:
                    replace_direct_str = connect_cmd_array[1]
            elif len(connect_cmd_array) > 1:
                replace_slash_regex = RE_REGEX_SLASH.search(connect_cmd_array[1])

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

            if search_direct_str in self.sub_inst_ports[instantiation]:
                self.sub_inst_ports[instantiation][search_direct_str]["connected"] = 1
                if replace_direct_str != "":
                    # TODO: Need to update topbitdef from connect
                    topname_is_concat_regex = RE_OPEN_CURLY.search(replace_direct_str)
                    topname_has_tick_regex = RE_NUM_TICK.search(replace_direct_str)
                    topname_is_constant_regex = RE_CONSTANT.search(replace_direct_str)
                    topname_is_define_regex = RE_DEFINE_TICK_BEGIN.search(
                        replace_direct_str
                    )
                    topname_has_dot_regex = RE_DOT.search(replace_direct_str)

                    # If this is a constant or param or define or concat of self.signals, then topbitdef should be empty
                    if (
                        topname_is_concat_regex
                        or topname_has_tick_regex
                        or topname_is_constant_regex
                        or topname_is_define_regex
                        or topname_has_dot_regex
                    ):
                        self.sub_inst_ports[instantiation][search_direct_str][
                            "topbitdef"
                        ] = ""
                        self.sub_inst_ports[instantiation][search_direct_str][
                            "topname"
                        ] = replace_direct_str
                    else:
                        topname_bitdef_regex = RE_OPEN_SQBRCT_BITDEF.search(
                            replace_direct_str
                        )

                        if topname_bitdef_regex:
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "topname"
                            ] = topname_bitdef_regex.group(1)
                            topbitdef_tmp = topname_bitdef_regex.group(2)
                            topbitdef_tmp = re.sub(r"]$", "", topbitdef_tmp)
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "topbitdef"
                            ] = topbitdef_tmp
                        else:
                            self.sub_inst_ports[instantiation][search_direct_str][
                                "topname"
                            ] = replace_direct_str

                    self.dbg(
                        "      # UPDATED TOP NAME: "
                        + self.sub_inst_ports[instantiation][search_direct_str]["topname"]
                    )
                else:  # Unconnected port
                    self.sub_inst_ports[instantiation][search_direct_str]["topname"] = ""
                    self.sub_inst_ports[instantiation][search_direct_str]["topbitdef"] = ""
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
                self.found_error += 1
                sys.exit(1)

        self.dbg(
            "\n\n################################################################################"
        )
        self.dbg("# SUB INST PORTS")
        self.dbg(
            "################################################################################"
        )
        self.dbg(json.dumps(self.sub_inst_ports[instantiation], indent=2))

        remove_ports = []
        for c_port in self.sub_inst_ports[instantiation]:
            if self.sub_inst_ports[instantiation][c_port]["connected"] == 0:
                remove_ports.append(c_port)

        self.dbg("\n")

        for c_port in remove_ports:
            self.dbg("### Deleting Manual Instance Port: " + c_port)
            del self.sub_inst_ports[instantiation][c_port]

        for c_port in self.sub_inst_ports[instantiation]:
            self.dbg("### " + str(self.sub_inst_ports[instantiation][c_port]))
            if self.sub_inst_ports[instantiation][c_port]["dir"] == "output":
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    # if the bitdef is a binding, then we need to load typedef_bindings as well
                    topbitdef_typedef_binding_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                        self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                    )

                    if topbitdef_typedef_binding_regex:
                        self.binding_typedef(
                            "TOP",
                            "FORCE",
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                            + " "
                            + self.sub_inst_ports[instantiation][c_port]["topname"],
                        )
                        topname_assign_str = self.sub_inst_ports[instantiation][c_port][
                            "topname"
                        ]
                    else:
                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )

                        if topname_bitdef_regex:
                            topname_assign_str = self.sub_inst_ports[instantiation][c_port][
                                "topname"
                            ]
                        else:
                            # TODO: Need to do param overriding replacement on topbitdef
                            topname_assign_str = (
                                self.sub_inst_ports[instantiation][c_port]["topname"]
                                + "["
                                + self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                                + "]"
                            )

                    # topname can be concat of two or more self.signals
                    topname_assign_comma_regex = RE_COMMA.search(topname_assign_str)

                    topname_assign_str_array = []
                    # If multiple declarations on the same line, then break it
                    if topname_assign_comma_regex:
                        # removing space, { and }
                        topname_assign_str = re.sub(r"[{}\s]", "", topname_assign_str)
                        topname_assign_str_array = topname_assign_str.split(",")
                    else:  # Single declaration, then append to the array
                        topname_assign_str = re.sub(r"[{}\s]", "", topname_assign_str)
                        topname_assign_str_array.append(topname_assign_str)

                    for curr_topname in topname_assign_str_array:
                        if self.parsing_format == "verilog":
                            self.parse_signal("wire", curr_topname)
                        else:
                            self.parse_signal("reg", curr_topname)
                else:
                    topname_assign_str = self.sub_inst_ports[instantiation][c_port][
                        "topname"
                    ]

                    # topname can be concat of two or more self.signals
                    topname_assign_comma_regex = RE_COMMA.search(topname_assign_str)

                    topname_assign_str_array = []
                    # If multiple declarations on the same line, then break it
                    if topname_assign_comma_regex:
                        # removing space, { and }
                        topname_assign_str = re.sub(r"[{}\s]", "", topname_assign_str)
                        topname_assign_str_array = topname_assign_str.split(",")
                    else:  # Single declaration, then append to the array
                        topname_assign_str = re.sub(r"[{}\s]", "", topname_assign_str)
                        topname_assign_str_array.append(topname_assign_str)

                    for curr_topname in topname_assign_str_array:
                        if self.parsing_format == "verilog":
                            self.parse_signal("wire", curr_topname)
                        else:
                            self.parse_signal("reg", curr_topname)

            else:  # Sub module port is an input
                if self.sub_inst_ports[instantiation][c_port]["topbitdef"] != "":
                    # if the bitdef is a binding, then we need to load self.typedef_bindings as well
                    topbitdef_typedef_binding_regex = RE_TYPEDEF_DOUBLE_COLON.search(
                        self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                    )

                    if topbitdef_typedef_binding_regex:
                        self.binding_typedef(
                            "TOP",
                            "FORCE",
                            self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                            + " "
                            + self.sub_inst_ports[instantiation][c_port]["topname"],
                        )
                        self.parse_conditions(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )
                    else:
                        topname_bitdef_regex = RE_OPEN_SQBRCT.search(
                            self.sub_inst_ports[instantiation][c_port]["topname"]
                        )

                        if topname_bitdef_regex:
                            self.parse_conditions(
                                self.sub_inst_ports[instantiation][c_port]["topname"]
                            )
                        else:
                            # TODO: Need to do param overriding replacement on topbitdef
                            self.parse_conditions(
                                self.sub_inst_ports[instantiation][c_port]["topname"]
                                + "["
                                + self.sub_inst_ports[instantiation][c_port]["topbitdef"]
                                + "]"
                            )
                else:
                    self.parse_conditions(
                        self.sub_inst_ports[instantiation][c_port]["topname"]
                    )

        # Resetting the manual submodule instance data
        self.sub_inst_ports[instantiation] = {}
        self.sub_inst_params[instantiation] = {}
        manual_instance_line = ""

    def parse_compiler_directives(self, line):
        tick_define_regex = RE_TICK_DEFINE.search(line)

        if tick_define_regex:
            tick_def_exp = tick_define_regex.group(1)
            tick_def_exp = re.sub(r"\s*\(", " (", tick_def_exp, 1)
            line = re.sub(r"\s*\(", " (", line, 1)

            self.tick_def_proc("TOP", tick_def_exp)
            return True

        tick_undef_regex = RE_TICK_UNDEF.search(line)

        if tick_undef_regex:
            if tick_undef_regex.group(1) not in self.tick_defines:
                print(
                    "\nWarning: Unable to find #define to undef\n"
                    + tick_undef_regex.group(0)
                    + "\n"
                )
            else:
                del self.tick_defines[tick_undef_regex.group(1)]
                self.dbg(
                    "  # Removed #define " + tick_undef_regex.group(1) + " for undef"
                )

            return True

        ################################################################################
        # `ifdef/endif ENABLE_CUSTOM_STUB processing
        ################################################################################
        tick_ifdef_enable_custom_stub_regex = (
            RE_TICK_IFDEF_ENABLE_CUSTOM_STUB.search(line)
        )

        if tick_ifdef_enable_custom_stub_regex:
            self.enable_custom_stub = 1
            return True
        elif self.enable_custom_stub == 1:
            if RE_TICK_ENDIF.search(line):
                self.enable_custom_stub = 0
            else:
                match = re.match(RE_CUSTOM_STUB_DEF, line)
                if match:
                    def_line = {
                        "output_port": match.group("oport"),
                        "rhs_value": match.group("rhs_value"),
                        "line": line,
                    }
                else:
                    def_line = line
                self.enable_custom_stub_defs.append(def_line)
            return True

        tick_ifdef_regex = RE_TICK_IFDEF.search(line)
        tick_ifndef_regex = RE_TICK_IFNDEF.search(line)
        tick_elif_regex = RE_TICK_ELSIF.search(line)
        tick_else_regex = RE_TICK_ELSE.search(line)
        tick_endif_regex = RE_TICK_ENDIF.search(line)

        if tick_ifdef_regex:
            self.tick_ifdef_en = self.tick_ifdef_proc(
                "ifdef", tick_ifdef_regex.group(1)
            )
            return True
        elif tick_ifndef_regex:
            self.tick_ifdef_en = self.tick_ifdef_proc(
                "ifndef", tick_ifndef_regex.group(1)
            )
            return True
        elif tick_elif_regex:
            self.tick_ifdef_en = self.tick_ifdef_proc("elif", tick_elif_regex.group(1))
            return True
        elif tick_else_regex:
            self.tick_ifdef_en = self.tick_ifdef_proc("else", "")
            return True
        elif tick_endif_regex:
            self.tick_ifdef_en = self.tick_ifdef_proc("endif", "")
            return True

        return False

    def parse_psv(self):
        """
        Function to parse the expaned psv file with either old parser or new parser.
        """
        time1 = time.perf_counter()

        self.parse_mixed_psv()

        time2 = time.perf_counter()
        print(f"  # psv_parser() - Total run time: {time2 - time1}")

    def prepare_psv(self):
        psv_preper = psv_prep(self)
        self.constructs = psv_preper.prepare_psv(self.parse_lines)

    def parse_psv_constructs(self):
        """
        Function to parsed all construct sections that contains veripy or systemverilog constructs.
        """
        error_count = 0

        # sv_parser = verilog_parser(self)
        # vp_parser = veripy_parser(self)

        for index, construct in enumerate(self.constructs):
            if construct["context"] == "sv":
                error_count += self.sv_parser.parse_and_process(index, construct)
            else:
                error_count += self.vp_parser.parse_and_process(index, construct)

        return error_count

    def parse_mixed_psv(self):
        """
        Function to parse expanded psv with mixed sv/vp based on occurrence order
        """

        if self.verilog_define_files is not None:
            for c_verilog_define_file in self.verilog_define_files:
                self.load_import_or_include_file(
                    "TOP", "INCLUDE", c_verilog_define_file
                )

        if self.parser_on:
            time1 = time.perf_counter()

            if self.parsing_format == "verilog":
                print("  # Analysing expanded verilog file")
            else:
                print("  # Analysing expanded system verilog file")

            self.prepare_psv()

            error_count = self.parse_psv_constructs()

            time2 = time.perf_counter()
            elapsed = time2 - time1
            totalTime = elapsed

            if self.debug:
                print(f"\nparse_mixed_psv() - Total run time: {time2 - time1}")
                print(f"Total psv lines: {len(self.parse_lines)}")
                print(
                    f"Average lines/sec: {(len(self.parse_lines) / (time2 - time1)):.1f}\n"
                )
            print(f"  # Syntax error count: {error_count}")
            self.found_error += error_count
