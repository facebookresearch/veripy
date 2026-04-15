####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

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
from collections import OrderedDict
from csv import reader
from math import ceil, log
from typing import Dict, Set

import oyaml as yaml

from .regex import (
    RE_EQUAL_EXTRACT,
    RE_IF_PREFIX_ITER_CHECK,
    RE_IF_SUFFIX_ITER_CHECK,
    RE_TICK_DEFINE,
    RE_TICK_ELSE,
    RE_TICK_ELSIF,
    RE_TICK_ENDIF,
    RE_TICK_IFDEF,
    RE_TICK_IFNDEF,
    RE_TICK_UNDEF,
)


################################################################################
# Spec flow to parse all the spec files and generate ports and params details
################################################################################
class spec_flow:
    def __init__(
        self,
        if_spec_files,
        if_def_files,
        mod_def_files,
        mod_name,
        incl_dirs,
        files,
        debug_en,
        parser,
    ):
        self.interface_spec_files = if_spec_files
        self.interface_def_files = if_def_files
        self.module_def_files = mod_def_files
        self.module_name = mod_name
        self.incl_dirs = incl_dirs
        self.files = files
        self.debug = debug_en
        self.parser = parser
        self.if_specs = {}
        self.if_defs = {}
        self.mod_defs = {}

        # Output variables
        self.found_error = 0
        self.debug_info = []
        self.module_info = {}
        self.inports_w_comment = {}

    ################################################################################
    # Function to print a debug string in a debug dump file
    ################################################################################
    def dbg(self, dbg_info):
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

    ################################################################################
    # Function to print a debug string in a debug dump file
    ################################################################################
    def find_in_files(self, filename):
        for c_file in self.files:
            file_search_regex = "\\b" + filename + "$"
            RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
            search_file_regex = re.search(RE_SEARCH_FILE_REGEX, c_file)

            if search_file_regex:
                return c_file
        return

    def parse_compiler_directives(self, line):
        tick_define_regex = RE_TICK_DEFINE.search(line)

        if tick_define_regex:
            if self.parser.tick_ifdef_en:
                tick_def_exp = tick_define_regex.group(1)
                tick_def_exp = re.sub(r"\s*\(", " (", tick_def_exp, 1)
                self.parser.tick_def_proc("TOP", tick_def_exp)
            return True

        tick_undef_regex = RE_TICK_UNDEF.search(line)

        if tick_undef_regex:
            if self.parser.tick_ifdef_en:
                if tick_undef_regex.group(1) not in self.parser.tick_defines:
                    print(
                        "\nWarning: Unable to find #define to undef\n"
                        + tick_undef_regex.group(0)
                        + "\n"
                    )
                else:
                    del self.parser.tick_defines[tick_undef_regex.group(1)]
                    self.parser.dbg(
                        "  # Removed #define "
                        + tick_undef_regex.group(1)
                        + " for undef"
                    )
            return True

        ################################################################################
        # `ifdef/`ifndef/`elif/`endif processing
        ################################################################################
        tick_ifdef_regex = RE_TICK_IFDEF.search(line)
        tick_ifndef_regex = RE_TICK_IFNDEF.search(line)
        tick_elif_regex = RE_TICK_ELSIF.search(line)
        tick_else_regex = RE_TICK_ELSE.search(line)
        tick_endif_regex = RE_TICK_ENDIF.search(line)

        if tick_ifdef_regex:
            if not self.parser.tick_ifdef_dis:
                self.parser.tick_ifdef_en = self.parser.tick_ifdef_proc(
                    "ifdef", tick_ifdef_regex.group(1)
                )
            return True
        elif tick_ifndef_regex:
            if not self.parser.tick_ifdef_dis:
                self.parser.tick_ifdef_en = self.parser.tick_ifdef_proc(
                    "ifndef", tick_ifndef_regex.group(1)
                )
            return True
        elif tick_elif_regex:
            if not self.parser.tick_ifdef_dis:
                self.parser.tick_ifdef_en = self.parser.tick_ifdef_proc(
                    "elif", tick_elif_regex.group(1)
                )
            return True
        elif tick_else_regex:
            if not self.parser.tick_ifdef_dis:
                self.parser.tick_ifdef_en = self.parser.tick_ifdef_proc("else", "")
            return True
        elif tick_endif_regex:
            if not self.parser.tick_ifdef_dis:
                self.parser.tick_ifdef_en = self.parser.tick_ifdef_proc("endif", "")
            return True

        return False

    def prep_old(self, lines):
        preped_lines = []
        for line_no, line in enumerate(lines):
            if self.parse_compiler_directives(line):
                continue

            if not self.parser.tick_ifdef_dis and not self.parser.tick_ifdef_en:
                continue

            preped_lines.append(line)

        return "\n".join(preped_lines)

    def prep(self, lines):
        preped_lines = []
        module_name = None
        prep_context = None
        for line_no, line in enumerate(lines):
            module_match = re.match(r"^\s*(\w+)\s*:", line)
            tick_match = re.match(r"^\s*`(ifdef|ifndef|elif|else|endif)", line)
            interface_match = re.match(r"^\s*-\s*(.*)\s*$", line)
            if module_match:
                preped_lines.append(line)
                match_name = module_match.group(1)
                if match_name not in [
                    "INCLUDE",
                    "PARAM",
                    "IN",
                    "OUT",
                    "INOUT",
                    "IN_NOTYPE",
                    "OUT_NOTYPE",
                ]:
                    module_name = match_name
                    self.parser.module_def_preps[module_name] = []
                    prep_context = None
            elif module_name:
                if tick_match:
                    self.parser.module_def_preps[module_name].append(
                        {
                            "text": line,
                            "interfaces": [],
                            "intf_ports": [],
                            "ports": [],
                            "port_declarations": [],
                        }
                    )
                    prep_context = tick_match.group(1)
                    if tick_match.group(1) == "endif":
                        prep_context = None
                else:
                    if prep_context and interface_match:
                        self.parser.module_def_preps[module_name][-1][
                            "interfaces"
                        ].append(interface_match.group(1))
                    preped_lines.append(line)
            else:
                preped_lines.append(line)

        return "\n".join(preped_lines)

    def load_files(self):
        # Loading Interface Specs
        if self.interface_spec_files is not None:
            for c_file in self.interface_spec_files:
                self.dbg("Read Interface Spec :  " + c_file)
                found_c_file = 0

                if os.path.isfile(c_file):  # if the file exists
                    found_c_file = 1
                else:
                    for dir in self.incl_dirs:
                        if not found_c_file:
                            c_file_path = str(dir) + "/" + str(c_file)
                            if os.path.isfile(c_file_path):
                                found_c_file = 1
                                c_file = c_file_path

                if not found_c_file:
                    c_file_path_int = self.find_in_files(c_file)

                    if c_file_path_int is not None:
                        found_c_file = 1
                        c_file = c_file_path_int

                if not found_c_file:
                    print("\nError: Unable to find the file " + c_file)
                    print("  List of search directories")
                    print(("\nError: Unable to find the file " + c_file))
                    print("  List of search directories")

                    for dir in self.incl_dirs:
                        print("    " + str(dir))
                        print(("    " + str(dir)))
                    sys.exit(1)

                print("    - Loading Interface Spec " + c_file)
                fileh = open(c_file, "r")
                fdata = fileh.read()
                c_file_if_specs = yaml.load(fdata, Loader=yaml.FullLoader)
                fileh.close()

                if c_file_if_specs is None:
                    print(
                        "\nError: Unable to load the Interface Spec  " + c_file + "\n"
                    )
                    self.found_error = 1
                    sys.exit(1)

                self.if_specs.update(c_file_if_specs)

        # Loading Interface Definitions
        if self.interface_def_files is not None:
            for c_file in self.interface_def_files:
                self.dbg("Read Interface Def :  " + c_file)
                found_c_file = 0

                if os.path.isfile(c_file):  # if the file exists
                    found_c_file = 1
                else:
                    for dir in self.incl_dirs:
                        if not found_c_file:
                            c_file_path = str(dir) + "/" + str(c_file)
                            if os.path.isfile(c_file_path):
                                found_c_file = 1
                                c_file = c_file_path

                if not found_c_file:
                    c_file_path_int = self.find_in_files(c_file)

                    if c_file_path_int is not None:
                        found_c_file = 1
                        c_file = c_file_path_int

                if not found_c_file:
                    print("\nError: Unable to find the file " + c_file)
                    print("  List of search directories")
                    print(("\nError: Unable to find the file " + c_file))
                    print("  List of search directories")

                    for dir in self.incl_dirs:
                        print("    " + str(dir))
                        print(("    " + str(dir)))
                    sys.exit(1)

                print("    - Loading Interface Def " + c_file)
                fileh = open(c_file, "r")
                fdata = fileh.read()
                c_file_if_defs = yaml.load(fdata, Loader=yaml.FullLoader)
                fileh.close()

                if c_file_if_defs is None:
                    print("\nError: Unable to load the Interface Def  " + c_file + "\n")
                    self.found_error = 1
                    sys.exit(1)

                self.if_defs.update(c_file_if_defs)

        # Loading Module Definitions
        if self.module_def_files is not None:
            for c_file in self.module_def_files:
                self.dbg("Read Module Def :  " + c_file)
                found_c_file = 0

                if os.path.isfile(c_file):  # if the file exists
                    found_c_file = 1
                else:
                    for dir in self.incl_dirs:
                        if not found_c_file:
                            c_file_path = str(dir) + "/" + str(c_file)
                            if os.path.isfile(c_file_path):
                                found_c_file = 1
                                c_file = c_file_path

                if not found_c_file:
                    c_file_path_int = self.find_in_files(c_file)

                    if c_file_path_int is not None:
                        found_c_file = 1
                        c_file = c_file_path_int

                if not found_c_file:
                    print("\nError: Unable to find the file " + c_file)
                    print("  List of search directories")
                    print(("\nError: Unable to find the file " + c_file))
                    print("  List of search directories")

                    for dir in self.incl_dirs:
                        print("    " + str(dir))
                        print(("    " + str(dir)))
                    sys.exit(1)

                print("    - Loading Module Def " + c_file)
                fileh = open(c_file, "r")
                fdata = fileh.read()
                fdata = self.prep(fdata.split("\n"))
                c_file_mod_defs = yaml.load(fdata, Loader=yaml.FullLoader)
                fileh.close()

                if c_file_mod_defs is None:
                    print("\nError: Unable to load the Module Def  " + c_file + "\n")
                    self.found_error = 1
                    sys.exit(1)

                self.mod_defs.update(c_file_mod_defs)

    ################################################################################
    # Function to gather ports from spec flow
    ################################################################################
    def get_module_definition(self, module_name):
        module_info = {
            "PARAM": [],
            "LOCALPARAM": [],
            "PRINT": [],
            "IN": [],
            "OUT": [],
            "INOUT": [],
            "IN_NOTYPE": [],
            "OUT_NOTYPE": [],
            "INOUT_NOTYPE": [],
        }
        module_info_keys = list(module_info.keys())
        port_dir = ["IN", "OUT", "INOUT"]

        if module_name in self.mod_defs:
            if "INCLUDE" in self.mod_defs[module_name]:
                inc_mod_defs = self.mod_defs[module_name]["INCLUDE"]
                for inc_mod_def in inc_mod_defs:
                    if inc_mod_def in self.mod_defs:
                        inc_module_info = self.get_module_definition(inc_mod_def)
                        for category in module_info_keys:
                            entries = inc_module_info[category]
                            for entry in entries:
                                if entry not in module_info[category]:
                                    module_info[category].append(entry)
                    else:
                        print(
                            "\nError: Unable to include the module def "
                            + inc_mod_def
                            + " in "
                            + module_name
                            + ".\n"
                        )
                        self.found_error = 1
                        sys.exit(1)

            if (
                "PARAM" in self.mod_defs[module_name]
                and self.mod_defs[module_name]["PARAM"] is not None
            ):
                for c_param in self.mod_defs[module_name]["PARAM"]:
                    module_info["PARAM"].append(c_param)

            if (
                "LOCALPARAM" in self.mod_defs[module_name]
                and self.mod_defs[module_name]["LOCALPARAM"] is not None
            ):
                for c_param in self.mod_defs[module_name]["LOCALPARAM"]:
                    module_info["LOCALPARAM"].append(c_param)

            if (
                "PRINT" in self.mod_defs[module_name]
                and self.mod_defs[module_name]["PRINT"] is not None
            ):
                for c_param in self.mod_defs[module_name]["PRINT"]:
                    if c_param.startswith("include"):
                        c_param = "`" + c_param
                    module_info["PRINT"].append(c_param)

            for c_dir in ["IN_NOTYPE", "OUT_NOTYPE", "INOUT_NOTYPE"]:
                if c_dir not in self.mod_defs[module_name]:
                    continue

                module_info[c_dir] = []
                for c_intf in self.mod_defs[module_name][c_dir]:
                    module_info[c_dir] += re.split(r"\s+", c_intf)

            for c_dir in port_dir:
                if (
                    c_dir in self.mod_defs[module_name]
                    and self.mod_defs[module_name][c_dir] is not None
                ):
                    for c_intf in self.mod_defs[module_name][c_dir]:
                        self.dbg("new spec_flow debug c_intf 1: " + c_intf)
                        if c_dir == "IN":
                            line_comment_regex = re.search(
                                r"(.*)(\/{2,}.*)", c_intf, re.I
                            )
                            if line_comment_regex:
                                c_intf = line_comment_regex.group(1).strip()
                                self.inports_w_comment[f"input {c_intf}"] = (
                                    line_comment_regex.group(2)
                                )

                        c_intf_split = re.split(r"\s+", c_intf)
                        c_intf_name = c_intf_split[0]
                        self.dbg("new spec_flow debug 2: " + c_intf_name)

                        c_intf_input_list = []
                        c_intf_output_list = []
                        c_intf_inout_list = []

                        if c_intf_name in self.if_defs:
                            self.dbg("new spec_flow debug c_intf_name :" + c_intf_name)
                            c_intf_prefix_iter_list = []
                            c_intf_suffix_iter_list = []
                            c_intf_prefix_suffix_iter_list = []

                            if len(c_intf_split) > 1:
                                self.dbg(
                                    "new spec_flow debug c_intf_split[0] :"
                                    + c_intf_split[0]
                                )
                                self.dbg(
                                    "new spec_flow debug c_intf_split[1] :"
                                    + c_intf_split[1]
                                )
                                c_intf_prefix_iter_regex = re.search(
                                    RE_IF_PREFIX_ITER_CHECK, c_intf_split[1]
                                )
                                c_intf_suffix_iter_regex = re.search(
                                    RE_IF_SUFFIX_ITER_CHECK, c_intf_split[1]
                                )

                                if (
                                    c_intf_prefix_iter_regex
                                    and not c_intf_suffix_iter_regex
                                ):
                                    c_intf_prefix_iter_list = (
                                        c_intf_prefix_iter_regex.group(1).split(",")
                                    )

                                if (
                                    c_intf_suffix_iter_regex
                                    and not c_intf_prefix_iter_regex
                                ):
                                    c_intf_suffix_iter_list = (
                                        c_intf_suffix_iter_regex.group(1).split(",")
                                    )

                            if len(c_intf_split) > 2:
                                c_intf_prefix_iter_list = []
                                c_intf_suffix_iter_list = []
                                self.dbg(
                                    "new spec_flow debug c_intf_split[0] :"
                                    + c_intf_split[0]
                                )
                                self.dbg(
                                    "new spec_flow debug c_intf_split[1] :"
                                    + c_intf_split[1]
                                )
                                self.dbg(
                                    "new spec_flow debug c_intf_split[2] :"
                                    + c_intf_split[2]
                                )

                                if re.search(RE_IF_PREFIX_ITER_CHECK, c_intf_split[1]):
                                    c_intf_prefix_iter_regex = re.search(
                                        RE_IF_PREFIX_ITER_CHECK, c_intf_split[1]
                                    )
                                    c_intf_suffix_iter_regex = re.search(
                                        RE_IF_SUFFIX_ITER_CHECK, c_intf_split[2]
                                    )
                                else:
                                    c_intf_prefix_iter_regex = re.search(
                                        RE_IF_PREFIX_ITER_CHECK, c_intf_split[2]
                                    )
                                    c_intf_suffix_iter_regex = re.search(
                                        RE_IF_SUFFIX_ITER_CHECK, c_intf_split[1]
                                    )

                                if (
                                    c_intf_suffix_iter_regex
                                    and c_intf_prefix_iter_regex
                                ):
                                    c_intf_prefix_iter_list_0 = (
                                        c_intf_prefix_iter_regex.group(1).split(",")
                                    )
                                    c_intf_suffix_iter_list_0 = (
                                        c_intf_suffix_iter_regex.group(1).split(",")
                                    )
                                    for one_prefix_name in c_intf_prefix_iter_list_0:
                                        for (
                                            one_suffix_name
                                        ) in c_intf_suffix_iter_list_0:
                                            c_intf_prefix_suffix_iter_list.append(
                                                one_prefix_name + " " + one_suffix_name
                                            )
                                            self.dbg(
                                                "new spec_flow debug both prefix and suffix "
                                                + one_prefix_name
                                                + " "
                                                + one_suffix_name
                                            )
                                else:
                                    print(
                                        "\nError: both SUFFIX or PREFIX in  "
                                        + c_intf
                                        + "\n"
                                    )
                                    self.found_error = 1
                                    sys.exit(1)

                            c_intf_def = self.if_defs[c_intf_name]
                            c_intf_def_split = re.split(r"\s+", c_intf_def)
                            c_intf_type = c_intf_def_split[0]

                            self.dbg(
                                "new spec_flow debug c_intf_type 3:"
                                + c_intf_type
                                + "\n"
                            )

                            if c_intf_type in self.if_specs:
                                # Gather all the ports in a list

                                if "INOUTS" not in self.if_specs[c_intf_type].keys():
                                    self.if_specs[c_intf_type]["INOUTS"] = {}

                                if self.if_specs[c_intf_type]["INOUTS"] is not None:
                                    for c_port in self.if_specs[c_intf_type]["INOUTS"]:
                                        c_port_iter = c_port

                                        if len(c_intf_prefix_iter_list) > 0:
                                            for c_iter in list(c_intf_prefix_iter_list):
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", c_iter, c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", "", c_port_iter
                                                )
                                                c_intf_inout_list.append(c_port_iter)

                                        if len(c_intf_suffix_iter_list) > 0:
                                            for c_iter in list(c_intf_suffix_iter_list):
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", c_iter, c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", "", c_port_iter
                                                )
                                                c_intf_inout_list.append(c_port_iter)

                                        if (
                                            len(c_intf_prefix_iter_list) == 0
                                            and len(c_intf_suffix_iter_list) == 0
                                            and len(c_intf_prefix_suffix_iter_list) == 0
                                        ):
                                            c_port_iter = re.sub(
                                                r"<PREFIX>", "", c_port
                                            )
                                            c_port_iter = re.sub(
                                                r"<SUFFIX>", "", c_port_iter
                                            )
                                            c_intf_inout_list.append(c_port_iter)

                                        if (
                                            len(c_intf_prefix_iter_list) == 0
                                            and len(c_intf_suffix_iter_list) == 0
                                            and len(c_intf_prefix_suffix_iter_list) >= 1
                                        ):
                                            for c_iter in list(
                                                c_intf_prefix_suffix_iter_list
                                            ):
                                                c_prefix, c_suffix = c_iter.split(" ")
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", c_prefix, c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", c_suffix, c_port_iter
                                                )
                                                c_intf_inout_list.append(c_port_iter)

                                if self.if_specs[c_intf_type]["INPUTS"] is not None:
                                    ### debug begin
                                    for one in self.if_specs[c_intf_type]["INPUTS"]:
                                        self.dbg(
                                            "  new spec flow debug INPUTS "
                                            + c_intf_type
                                            + " : self.if_specs[c_intf_type]['INPUTS'] :"
                                            + one
                                        )
                                    ### debug end
                                    for c_port in self.if_specs[c_intf_type]["INPUTS"]:
                                        c_port_iter = c_port
                                        self.dbg(
                                            "  new spec flow debug  INPUTS c_port_iter  :"
                                            + c_port_iter
                                        )
                                        self.dbg(
                                            "  new spec flow debug  INPUTS c_port       :"
                                            + c_port
                                        )

                                        if c_dir == "IN":
                                            if len(c_intf_prefix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_prefix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", "", c_port_iter
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                            if len(c_intf_suffix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_suffix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", "", c_port_iter
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                == 0
                                            ):
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", "", c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", "", c_port_iter
                                                )
                                                c_intf_input_list.append(c_port_iter)

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                >= 1
                                            ):
                                                for c_iter in list(
                                                    c_intf_prefix_suffix_iter_list
                                                ):
                                                    c_prefix, c_suffix = c_iter.split(
                                                        " "
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_prefix, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>",
                                                        c_suffix,
                                                        c_port_iter,
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                        else:
                                            ### not sure if we need this branch
                                            if len(c_intf_prefix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_prefix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", "", c_port_iter
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                            if len(c_intf_suffix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_suffix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", "", c_port_iter
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                == 0
                                            ):
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", "", c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", "", c_port_iter
                                                )
                                                c_intf_output_list.append(c_port_iter)

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                >= 1
                                            ):
                                                for c_iter in list(
                                                    c_intf_prefix_suffix_iter_list
                                                ):
                                                    c_prefix, c_suffix = c_iter.split(
                                                        " "
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_prefix, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>",
                                                        c_suffix,
                                                        c_port_iter,
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                if self.if_specs[c_intf_type]["OUTPUTS"] is not None:
                                    ### debug begin
                                    for one in self.if_specs[c_intf_type]["OUTPUTS"]:
                                        self.dbg(
                                            "  new spec flow debug OUTPUTS if_specs[c_intf_type]['OUTPUTS'] :"
                                            + one
                                        )
                                    ### debug end

                                    for c_port in self.if_specs[c_intf_type]["OUTPUTS"]:
                                        c_port_iter = c_port
                                        self.dbg(
                                            "  new spec flow debug OUTPUTS c_port_iter  :"
                                            + c_port_iter
                                        )
                                        self.dbg(
                                            "  new spec flow debug OUTPUTS c_port       :"
                                            + c_port
                                        )

                                        if c_dir == "IN":
                                            if len(c_intf_prefix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_prefix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", "", c_port_iter
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                            if len(c_intf_suffix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_suffix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", "", c_port_iter
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                == 0
                                            ):
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", "", c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", "", c_port_iter
                                                )
                                                c_intf_output_list.append(c_port_iter)

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                >= 1
                                            ):
                                                for c_iter in list(
                                                    c_intf_prefix_suffix_iter_list
                                                ):
                                                    c_prefix, c_suffix = c_iter.split(
                                                        " "
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_prefix, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>",
                                                        c_suffix,
                                                        c_port_iter,
                                                    )
                                                    c_intf_output_list.append(
                                                        c_port_iter
                                                    )

                                        else:
                                            if len(c_intf_prefix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_prefix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", "", c_port_iter
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                            if len(c_intf_suffix_iter_list) > 0:
                                                for c_iter in list(
                                                    c_intf_suffix_iter_list
                                                ):
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>", c_iter, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", "", c_port_iter
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                == 0
                                            ):
                                                c_port_iter = re.sub(
                                                    r"<PREFIX>", "", c_port
                                                )
                                                c_port_iter = re.sub(
                                                    r"<SUFFIX>", "", c_port_iter
                                                )
                                                c_intf_input_list.append(c_port_iter)

                                            if (
                                                len(c_intf_prefix_iter_list) == 0
                                                and len(c_intf_suffix_iter_list) == 0
                                                and len(c_intf_prefix_suffix_iter_list)
                                                >= 1
                                            ):
                                                for c_iter in list(
                                                    c_intf_prefix_suffix_iter_list
                                                ):
                                                    c_prefix, c_suffix = c_iter.split(
                                                        " "
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<PREFIX>", c_prefix, c_port
                                                    )
                                                    c_port_iter = re.sub(
                                                        r"<SUFFIX>",
                                                        c_suffix,
                                                        c_port_iter,
                                                    )
                                                    c_intf_input_list.append(
                                                        c_port_iter
                                                    )

                                # Replace <INTERFACE_NAME_LC> and <INTERFACE_NAME_UC>
                                for jj in range(0, len(c_intf_input_list)):
                                    c_intf_input_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_LC>",
                                        c_intf_name.lower(),
                                        c_intf_input_list[jj],
                                    )
                                    c_intf_input_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_UC>",
                                        c_intf_name.upper(),
                                        c_intf_input_list[jj],
                                    )

                                for jj in range(0, len(c_intf_output_list)):
                                    c_intf_output_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_LC>",
                                        c_intf_name.lower(),
                                        c_intf_output_list[jj],
                                    )
                                    c_intf_output_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_UC>",
                                        c_intf_name.upper(),
                                        c_intf_output_list[jj],
                                    )

                                for jj in range(0, len(c_intf_inout_list)):
                                    c_intf_inout_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_LC>",
                                        c_intf_name.lower(),
                                        c_intf_inout_list[jj],
                                    )
                                    c_intf_inout_list[jj] = re.sub(
                                        r"<INTERFACE_NAME_UC>",
                                        c_intf_name.upper(),
                                        c_intf_inout_list[jj],
                                    )

                                # Replace <SRC>, <DST> and <BUS>
                                match = re.match(
                                    r"(?P<src>\w+)2(?P<dst>[^_]+)_(?P<bus>\w+)",
                                    c_intf_name,
                                )
                                if match:
                                    src = match.group("src")
                                    dst = match.group("dst")
                                    bus = match.group("bus")

                                    for jj in range(0, len(c_intf_input_list)):
                                        c_intf_input_list[jj] = re.sub(
                                            r"<SRC>",
                                            src.lower(),
                                            c_intf_input_list[jj],
                                        )
                                        c_intf_input_list[jj] = re.sub(
                                            r"<DST>",
                                            dst.lower(),
                                            c_intf_input_list[jj],
                                        )
                                        c_intf_input_list[jj] = re.sub(
                                            r"<BUS>",
                                            bus.lower(),
                                            c_intf_input_list[jj],
                                        )

                                    for jj in range(0, len(c_intf_output_list)):
                                        c_intf_output_list[jj] = re.sub(
                                            r"<SRC>",
                                            src.lower(),
                                            c_intf_output_list[jj],
                                        )
                                        c_intf_output_list[jj] = re.sub(
                                            r"<DST>",
                                            dst.lower(),
                                            c_intf_output_list[jj],
                                        )
                                        c_intf_output_list[jj] = re.sub(
                                            r"<BUS>",
                                            bus.lower(),
                                            c_intf_output_list[jj],
                                        )

                                    for jj in range(0, len(c_intf_inout_list)):
                                        c_intf_inout_list[jj] = re.sub(
                                            r"<SRC>",
                                            src.lower(),
                                            c_intf_inout_list[jj],
                                        )
                                        c_intf_inout_list[jj] = re.sub(
                                            r"<DST>",
                                            dst.lower(),
                                            c_intf_inout_list[jj],
                                        )
                                        c_intf_inout_list[jj] = re.sub(
                                            r"<BUS>",
                                            bus.lower(),
                                            c_intf_inout_list[jj],
                                        )

                                if len(c_intf_def_split) > 1:
                                    for arg_index in range(1, len(c_intf_def_split)):
                                        c_intf_arg_equal_regex = re.search(
                                            RE_EQUAL_EXTRACT,
                                            c_intf_def_split[arg_index],
                                        )

                                        # Named argument replacement
                                        if c_intf_arg_equal_regex:
                                            search_str = c_intf_arg_equal_regex.group(1)
                                            replace_str = c_intf_arg_equal_regex.group(
                                                2
                                            )

                                            for kk in range(0, len(c_intf_input_list)):
                                                c_intf_input_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_input_list[kk],
                                                )

                                            for kk in range(0, len(c_intf_output_list)):
                                                c_intf_output_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_output_list[kk],
                                                )

                                            for kk in range(0, len(c_intf_inout_list)):
                                                c_intf_inout_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_inout_list[kk],
                                                )

                                        # Positional argument replacement
                                        else:
                                            search_str = self.if_specs[c_intf_type][
                                                "ARGS"
                                            ][arg_index - 1]
                                            replace_str = c_intf_def_split[arg_index]

                                            for kk in range(0, len(c_intf_input_list)):
                                                c_intf_input_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_input_list[kk],
                                                )

                                            for kk in range(0, len(c_intf_output_list)):
                                                c_intf_output_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_output_list[kk],
                                                )

                                            for kk in range(0, len(c_intf_inout_list)):
                                                c_intf_inout_list[kk] = re.sub(
                                                    search_str,
                                                    replace_str,
                                                    c_intf_inout_list[kk],
                                                )

                            else:
                                print(
                                    (
                                        "\nError: Unable to find the interface spec for "
                                        + c_intf_type
                                        + "\n"
                                    )
                                )
                                print(
                                    "\nError: Unable to find the interface spec for "
                                    + c_intf_type
                                    + "\n"
                                )
                                self.found_error = 1
                                sys.exit(1)

                        else:  #  Default is WIRE type
                            if len(c_intf_split) == 1:
                                if c_dir == "IN":
                                    c_intf_input_list.append(c_intf_split[0])
                                elif c_dir == "INOUT":
                                    c_intf_inout_list.append(c_intf_split[0])
                                else:
                                    c_intf_output_list.append(c_intf_split[0])
                            if len(c_intf_split) == 2:
                                if c_dir == "IN":
                                    c_intf_input_list.append(
                                        c_intf_split[1] + " " + c_intf_split[0]
                                    )
                                elif c_dir == "INOUT":
                                    c_intf_inout_list.append(
                                        c_intf_split[1] + " " + c_intf_split[0]
                                    )
                                else:
                                    c_intf_output_list.append(
                                        c_intf_split[1] + " " + c_intf_split[0]
                                    )
                            if len(c_intf_split) == 3:
                                if c_dir == "IN":
                                    c_intf_input_list.append(
                                        c_intf_split[1]
                                        + " "
                                        + c_intf_split[0]
                                        + c_intf_split[2]
                                    )
                                elif c_dir == "INOUT":
                                    c_intf_inout_list.append(
                                        c_intf_split[1]
                                        + " "
                                        + c_intf_split[0]
                                        + c_intf_split[2]
                                    )
                                else:
                                    c_intf_output_list.append(
                                        c_intf_split[1]
                                        + " "
                                        + c_intf_split[0]
                                        + c_intf_split[2]
                                    )

                        module_info["OUT"] += c_intf_output_list

                        module_info["IN"] += c_intf_input_list

                        module_info["INOUT"] += c_intf_inout_list

                        if len(self.parser.module_def_preps[module_name]) > 0:
                            module_def_preps = self.parser.module_def_preps[module_name]
                            for module_def_prep in module_def_preps:
                                if c_intf in module_def_prep["interfaces"]:
                                    module_def_prep["intf_ports"] += c_intf_output_list
                                    module_def_prep["intf_ports"] += c_intf_input_list
                                    module_def_prep["intf_ports"] += c_intf_inout_list

            self.dbg(json.dumps(module_info, indent=2))
            return module_info

        else:
            print("\nError: Unable to find the module def for " + module_name + "\n")
            self.found_error = 1
            sys.exit(1)


# if __name__ == "__main__":
#
#   i_spec_flow = spec_flow(interface_spec_files, interface_def_files, module_def_files, self.module_name, incl_dirs, files, debug)
#
#   i_spec_flow.get_module_definition()
#
#   self.module_info = i_spec_flow.module_info
#
#   # Check if any errors when running spec flow
#   if i_spec_flow.found_error:
#       self.found_error = 1
#
#   print(i_spec_flow.debug_info)
#
#   print(json.dumps(i_spec_flow.module_info, indent=2))
