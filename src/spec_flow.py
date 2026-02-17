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


import csv
import io
import itertools
import json
import logging
import os
import os.path
import re
import sys
from csv import reader

import yaml as yaml
from src.regex import RE_EQUAL_EXTRACT, RE_IF_PREFIX_ITER_CHECK, RE_IF_SUFFIX_ITER_CHECK


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
    ):
        self.interface_spec_files = if_spec_files
        self.interface_def_files = if_def_files
        self.module_def_files = mod_def_files
        self.module_name = mod_name
        self.incl_dirs = incl_dirs
        self.files = files
        self.debug = debug_en

        # Output variables
        self.found_error = 0
        self.debug_info = []
        self.module_info = {}
        self.module_info["params"] = []
        self.module_info["inputs"] = []
        self.module_info["outputs"] = []
        self.module_info["inouts"] = []

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
            file_search_regex = filename + "$"
            RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
            search_file_regex = re.search(RE_SEARCH_FILE_REGEX, c_file)

            if search_file_regex:
                return c_file
        return

    ################################################################################
    # Function to gather ports from spec flow
    ################################################################################
    def get_module_definition(self):
        port_dir = ["IN", "OUT", "INOUT"]

        # Loading Interface Specs
        fdata = ""
        if_specs = {}

        if self.interface_spec_files is not None:
            for c_file in self.interface_spec_files:
                print("    - Loading Interface Spec " + c_file)
                self.dbg(
                    "---------- debug  get_module_definition  - Loading Interface Spec "
                    + c_file
                )
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

                self.dbg("read interface spec :  " + c_file)

                with open(c_file, "r") as Yamlparameters:
                    c_file_if_specs = yaml.safe_load(Yamlparameters)

                if c_file_if_specs is None:
                    print(
                        "\nError: Unable to load the Interface Spec  " + c_file + "\n"
                    )
                    self.found_error = 1
                    sys.exit(1)

                if_specs.update(c_file_if_specs)

        # Loading Interface Definitions
        fdata = ""
        if_defs = {}

        if self.interface_def_files is not None:
            for c_file in self.interface_def_files:
                print("    - Loading Interface Def " + c_file)
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

                self.dbg("read interface Def :  " + c_file)

                with open(c_file, "r") as Yamlparameters:
                    c_file_if_defs = yaml.safe_load(Yamlparameters)

                if c_file_if_defs is None:
                    print("\nError: Unable to load the Interface Def  " + c_file + "\n")
                    self.found_error = 1
                    sys.exit(1)

                if_defs.update(c_file_if_defs)

        # Loading Module Definitions
        fdata = ""
        mod_defs = {}

        if self.module_def_files is not None:
            for c_file in self.module_def_files:
                self.dbg("    - Loading Module Def " + c_file)
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

                with open(c_file, "r") as Yamlparameters:
                    c_file_mod_defs = yaml.safe_load(Yamlparameters)

                if c_file_mod_defs is None:
                    print("\nError: Unable to load the Module Def  " + c_file + "\n")
                    self.found_error = 1
                    sys.exit(1)

                mod_defs.update(c_file_mod_defs)

        if self.module_name in mod_defs:
            if mod_defs[self.module_name]["PARAM"] is not None:
                for c_param in mod_defs[self.module_name]["PARAM"]:
                    self.module_info["params"].append(c_param)

            for c_dir in port_dir:
                if c_dir in mod_defs[self.module_name]:
                    for c_intf in mod_defs[self.module_name][c_dir]:
                        self.dbg("new spec_flow debug c_intf 1: " + c_intf)
                        c_intf_split = re.split(r"\s+", c_intf)
                        c_intf_name = c_intf_split[0]
                        self.dbg("new spec_flow debug 2: " + c_intf_name)

                        c_intf_input_list = []
                        c_intf_output_list = []
                        c_intf_inout_list = []

                        if c_intf_name in if_defs:
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

                            c_intf_def = if_defs[c_intf_name]
                            c_intf_def_split = re.split(r"\s+", c_intf_def)
                            c_intf_type = c_intf_def_split[0]

                            self.dbg(
                                "new spec_flow debug c_intf_type 3:"
                                + c_intf_type
                                + "\n"
                            )

                            if c_intf_type in if_specs:
                                # Gather all the ports in a list

                                if "INOUTS" not in if_specs[c_intf_type].keys():
                                    if_specs[c_intf_type]["INOUTS"] = {}

                                if if_specs[c_intf_type]["INOUTS"] is not None:
                                    for c_port in if_specs[c_intf_type]["INOUTS"]:
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

                                if if_specs[c_intf_type]["INPUTS"] is not None:
                                    ### debug begin
                                    for one in if_specs[c_intf_type]["INPUTS"]:
                                        self.dbg(
                                            "  new spec flow debug INPUTS "
                                            + c_intf_type
                                            + " : if_specs[c_intf_type]['INPUTS'] :"
                                            + one
                                        )
                                    ### debug end
                                    for c_port in if_specs[c_intf_type]["INPUTS"]:
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

                                if if_specs[c_intf_type]["OUTPUTS"] is not None:
                                    ### debug begin
                                    for one in if_specs[c_intf_type]["OUTPUTS"]:
                                        self.dbg(
                                            "  new spec flow debug OUTPUTS if_specs[c_intf_type]['OUTPUTS'] :"
                                            + one
                                        )
                                    ### debug end

                                    for c_port in if_specs[c_intf_type]["OUTPUTS"]:
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
                                            search_str = if_specs[c_intf_type]["ARGS"][
                                                arg_index - 1
                                            ]
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

                        self.module_info["outputs"] += c_intf_output_list

                        self.module_info["inputs"] += c_intf_input_list

                        self.module_info["inouts"] += c_intf_inout_list

            self.dbg(json.dumps(self.module_info, indent=2))

        else:
            print(
                (
                    "\nError: Unable to find the module def for "
                    + self.module_name
                    + "\n"
                )
            )
            print(
                "\nError: Unable to find the module def for " + self.module_name + "\n"
            )
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
