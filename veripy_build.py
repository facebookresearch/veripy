#!/usr/bin/env python3
####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################
################################################################################
# veripy_build.py is a python based build script to automate bottom-up build   #
# of veripy at a block level. The user needs to parse the top psv file name as #
# input along with other run command options for veripy. It gathers all the    #
# dependencies for every module in a hierarchical fashion and generates the    #
# bottom buid flow for veripy.                                                 #
#                                                                              #
#     Author: Baheerathan Anandharengan                                        #
#     E-Mail: baheerathan@meta.com                                               #
#                                                                              #
#     Key Contributor: Dheepak Jayaraman                                       #
#     E-Mail: dheepak@meta.com                                        #
#                                                                              #
################################################################################
"""
!@package veripy_build
veripy_build.py is a script to generate the TARGETS files containing Verilog and VeriPy
dependencies for a given file or set of files.
"""

import argparse
import json
import logging
import math
import os
import os.path
import re
import string
import subprocess
import sys
import warnings
from os.path import getmtime

import yaml as yaml


def gen_dependency(c_dep):
    """!
    Generate the ref path for buck target.

    @param cdep String containing dependency path
    """

    global RE_SLASH
    c_dep_slash_regex = RE_SLASH.search(c_dep)

    if c_dep_slash_regex:
        dep_map = c_dep_slash_regex.group(1) + ":" + c_dep_slash_regex.group(2)
        dep_map = re.sub(r".*\/infra_asic_fpga\/", r"//infra_asic_fpga/", dep_map)

        # Process 3rd-party memory .f files.
        if "third_party/" in dep_map:
            dep_map = dep_map.replace("/sim_ver", "")
    else:
        dep_map = ":" + c_dep

    return dep_map


def get_filename(c_dep):
    """!
    Parse filename (possibly with full path) to get just filename.

    @param c_dep String containing dependency path
    """

    global RE_SLASH
    c_dep_slash_regex = RE_SLASH.search(c_dep)

    if c_dep_slash_regex:
        filename = c_dep_slash_regex.group(2)
    else:
        filename = c_dep

    return filename


def check_dir(c_dep):
    """!
    Check if a given file is in the current directory.

    @param c_dep String containing the dependency filename
    """

    global RE_SLASH
    c_dep_slash_regex = RE_SLASH.search(c_dep)

    if c_dep_slash_regex:
        if c_dep_slash_regex.group(1) != os.getcwd():
            check_val = 1
        else:
            check_val = 0
    else:
        check_val = 0

    return check_val


def up_to_date_file_in_dict(fname, dictionary, old_dict):
    """!
    Check whether a file is stored in a dictionary. If it is, check if it and
    its dependencies are up to date.

    @param fname Filename of dependency
    @param dictionary Python dict object containing all dependencies generated thus far
    @param old_dict Boolean variable to reuse dictionary from previous runs (may lead to speedup)
    """

    categories = [
        "include_files",
        "header_files",
        "verilog_subs",
        "spec_files",
        "interface_files",
        "module_files",
        "depends",
    ]

    if fname in dictionary:
        # Check if using dictionary from previous run
        # If not, file modification times are irrelevant
        if old_dict:
            mtime = getmtime(fname)
            mtime_stored = dictionary[fname + " mtime"]

            # File has been modified since last run
            if mtime > mtime_stored:
                return False

            # Modification time is same as stored value. Check dependencies
            # to see if any of them have changed since last run
            else:
                for category in dictionary[fname][fname]:
                    if category in categories:
                        for dep in dictionary[fname][fname][category]:
                            mtime = getmtime(next(iter(dep)))
                            mtime_stored = dep[next(iter(dep))]["mtime"]
                            if mtime > mtime_stored:
                                return False

                    elif category == "veripy_subs":
                        for dep in dictionary[fname][fname]["veripy_subs"].keys():
                            mtime = getmtime(str(dep))
                            mtime_stored = dictionary[fname][fname]["veripy_subs"][dep][
                                "mtime"
                            ]
                            if mtime > mtime_stored:
                                return False

                # If none of the above checks fail, neither this file
                # nor its dependencies have been modified since previous run
                return True

        else:
            return True
    else:
        return False


def dbg(dbg_info):
    """
    Write out debug dump file.

    @param dbg_info Variable containing the debugging information string(s)
    """

    first = 1
    global debug
    if debug:
        if type(dbg_info) is list:
            for curr_str in dbg_info:
                if first:
                    first = 0
                    print(str(curr_str))
                else:
                    print(", " + str(curr_str))

            print()
        else:
            print(str(dbg_info))

    return


def get_cmd_line_args():
    print(
        "#############################################################################################"
    )
    print(
        "###             Running veripy_build.py - A Build script for veripy automation            ###"
    )
    print(
        "#############################################################################################"
    )

    ################################################################################
    # Command line arguments processing                                            #
    ################################################################################
    parser = argparse.ArgumentParser(
        description="veripy_build.py is a Python based build script to automate \
         bottom-up build of veripy at a block level. The user needs to parse the \
         top psv file name as input along with other run command options for \
         veripy. It gathers all the dependencies for every module in a hierarchical \
         fashion and generates the bottom buid flow for veripy."
    )

    # Input .psv or .pv filename
    parser.add_argument(
        "positional",
        action="store",
        help="Input filename with a mix of verilog|systemverilog along with embedded \
        python code. <filename>.pv - Input file with mix of verilog and embedded \
        python. <filename>.psv - Input file with mix of system verilog and embedded \
        python.",
    )

    # -format option
    parser.add_argument(
        "-fo",
        "--format",
        action="store",
        default="systemverilog",
        dest="format",
        help="By default, the parser runs in verilog parsing mode. To parse \
        systemverilog, systemverilog as format to be used in the command line.",
    )

    # -include option
    parser.add_argument(
        "-inc",
        "--include",
        nargs="*",
        dest="include_dir",
        help="Optional include directory to search for include files, sub-module \
        files. User can add multiple include directories. First current directory \
        is searched for submodule or include files and then the order include \
        directories in the command line.",
    )

    # -output option
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        default="",
        dest="output_file",
        help="Optional output file name to rename the output file. The output \
        filename will be <filename>.v or <filename>.sv based on -format option.",
    )

    # -destination_dir option
    parser.add_argument(
        "-de",
        "--destination",
        action="store",
        default="",
        dest="destination_dir",
        help="By default, the parser runs in verilog parsing mode. To parse \
        systemverilog, systemverilog as format to be used in the command line.",
    )

    # -interface spec option
    parser.add_argument(
        "-ifs",
        "--interface_spec",
        nargs="*",
        dest="intf_specs",
        help="Interface specification that has the details of input/output signals \
        for each interface in structures format.",
    )

    # -intf definition option
    parser.add_argument(
        "-ifd",
        "--interface_def",
        nargs="*",
        dest="intf_defs",
        help="Interface definition file that has interface name, type and other \
        parameter like bus width",
    )

    # -module spec option
    parser.add_argument(
        "-md",
        "--module_def",
        nargs="*",
        dest="mod_defs",
        help="Module definition file with list of interfaces per module. Once the \
        tool populates the input and output ports after parsing the \
        verilog/systemverilog code, it compares the populated ports with the module \
        specification. If any ports popped up other than the list per the module \
        spec, it will prompt error.  This helps avoiding unnecessary ports pop up \
        at top level due to auto build that causes compile errors.",
    )

    # -file option
    parser.add_argument(
        "-fi",
        "--file",
        nargs="*",
        dest="files",
        help="Optional -file option to pass in a file name to look for submodules \
        / include / package / spec files",
    )

    # -list option
    parser.add_argument(
        "-l",
        "--list",
        nargs="*",
        dest="lists",
        help="Optional -list option to pass in a file that has the list of files to \
        look for submodules / include / package / spec files",
    )

    # -hash_define_vars option
    parser.add_argument(
        "-hdv",
        "--hash_define_vars",
        nargs="*",
        dest="hash_define_vars",
        help="#define for pre-processing. This is like C pre-processor that is used \
        in #ifdef/#elif to control the code generation by passing in the #define. \
        This option is for the user to pass the #define as a command line. These \
        #defines can be accessed by user in embedded python code.",
    )

    # -define_file option
    parser.add_argument(
        "-hdf",
        "--hash_define_files",
        nargs="*",
        dest="hash_define_files",
        help="This option let the user to list all the #defines in a file and pass \
        it as command line. This is like a project or module level #defines file \
        that control the configurable code generations.",
    )

    # -define_file option
    parser.add_argument(
        "-vdf",
        "--verilog_define_files",
        nargs="*",
        dest="verilog_define_files",
        help="This option let the user to list all the verilog define and parameter \
        files and pass it as command line. This is like a project or module level \
        #defines file that control the configurable code generations.",
    )

    # -debug option
    parser.add_argument(
        "-deb",
        "--debug",
        action="store_true",
        default=False,
        dest="debug",
        help="Option to generate debug dump from the tool for debugging any code \
        generation issue.",
    )

    # -remove_code option
    parser.add_argument(
        "-rm",
        "--remove_code",
        action="store_true",
        default=False,
        dest="remove_code",
        help="Option to not to print the disabled code by #ifdef/elif pre-processing \
        in the final .v or .sv file.",
    )

    # -parser_off option
    parser.add_argument(
        "-pars",
        "--parser_off",
        action="store_false",
        default=True,
        dest="parser_on",
        help="Option to turn off the verilog/systemverilog parser. This enables the \
        script to be used only for preprocessing and embedded python.",
    )

    # -package option
    parser.add_argument(
        "-pac",
        "--package",
        nargs="*",
        dest="package_files",
        help="Option for loading the system verilog package files. User can load \
        multiple files with mutliple times calling this option. When we load \
        commandline these packages, same list of packages will be loaded for the \
        sub-module instantiation as well.",
    )

    # -sort_ports option
    parser.add_argument(
        "-so",
        "--sort_ports",
        action="store_true",
        default=False,
        dest="sort_ios",
        help="By default it does not sort the ports. With this option, it sorts \
        and generates module ports.",
    )

    # -ungroup_ports option
    parser.add_argument(
        "-u",
        "--ungroup_ports",
        action="store_false",
        default=True,
        dest="group_ios_on_dir",
        help="By default, it generates input and output ports separately. With \
        -ungroup option, it generates mix of input and output ports. This option \
        can be used with -sort_ports option.",
    )

    # -stub option
    parser.add_argument(
        "-st",
        "--stub",
        action="store_true",
        default=False,
        dest="generate_stub",
        help="Generate stub modules from *.pv or *.psv or *.v or *.sv. You still \
        have to call &GenDrive0; or GenDriveZ; or GenDrive0andZ; If the stubs from \
        *.v or *.sv then use -output option to rename the output file.",
    )

    # -generate_parse option
    parser.add_argument(
        "-g",
        "--generate_disable",
        action="store_false",
        default=True,
        dest="parse_generate",
        help="By default generate blocks are parsed. With this option, the user can \
        turn it off.",
    )

    # -dependencies option
    parser.add_argument(
        "-dep",
        "--dependancy_list",
        action="store_true",
        default=False,
        dest="generate_dependancies",
        help="This option generates all the dependencies for building the current \
        block. The dependencies are printed in the -output file.",
    )

    # -veripy script path
    parser.add_argument(
        "-v",
        "--veripy_path",
        action="store",
        default="",
        dest="veripy_path",
        help="Path to veripy script from the run directory.",
    )

    # -update_inc option
    parser.add_argument(
        "-ui",
        "--update_inc",
        action="store_true",
        default=False,
        dest="update_inc",
        help="Generate makefile.inc. By default it generates TARGETS file.",
    )

    # -root path
    parser.add_argument(
        "-rp",
        "--root_path",
        action="store",
        default="",
        dest="root_path",
        help="Root directory to replace with $(ROOT).",
    )

    parser.add_argument(
        "-gv",
        "--gather_verilog_includes",
        action="store_true",
        default=False,
        dest="gather_verilog_subs_include_files",
        help="Option to parse verilog sub modules to gather include or package files \
        as dependencies.",
    )

    # -user_options
    parser.add_argument(
        "-uo",
        "--user_options",
        nargs="*",
        dest="user_options",
        help="Option to pass user option from make flow to add the user option part \
        of target_args in TARGETS",
    )

    # -disable_tick_ifdefs
    parser.add_argument(
        "-dti",
        "--disable_tick_ifdefs",
        action="store_true",
        default=False,
        dest="disable_tick_ifdefs",
        help="This option disables `ifdef parsing in the verilog code.",
    )

    # -auto_package option
    parser.add_argument(
        "-dap",
        "--disable_auto_package",
        action="store_false",
        default=True,
        dest="auto_package_load",
        help="This option disables auto loading of system verilog packages.",
    )

    # -python option
    parser.add_argument(
        "-py",
        "--python",
        nargs="*",
        dest="python_files",
        help="Optional --python option to load python scripts that can have python \
        variables/dictionaries to be used in embedded python.",
    )

    # -all_vendors option
    parser.add_argument(
        "-av",
        "--all_vendors",
        action="store_true",
        default=False,
        dest="target_vendors",
        help="Optional to add all vendors.",
    )

    # -build_subdirs_dict option
    parser.add_argument(
        "-dict",
        "--build_subdirs_dict",
        action="store",
        default="",
        dest="build_subdirs_dict_json",
        help="Optional specification for the name of the pickle file that will hold \
        the dictionary for dependencies.",
    )

    # -use_prev_dict option
    parser.add_argument(
        "-upd",
        "--use_prev_dict",
        action="store_true",
        default=False,
        dest="use_prev_dict",
        help="Option to use prevous dictionary file to load dependencies (faster \
        for subsequent runs, slower for initial run).",
    )

    # -profiling
    parser.add_argument(
        "-prof",
        "--profiling",
        action="store",
        default="",
        dest="profiling_file",
        help="By default, no profiling file is generated. If a filename is \
        specified, it will be written to with the profiling data.",
    )

    parser.add_argument(
        "-targetdir",
        "--targetdir",
        action="store",
        default="./rtl_b",
        dest="targetdir",
        help="target directory such as rtl_bc5,rtl_bc7. ",
    )

    cmdline = parser.parse_args()

    in_file = cmdline.positional
    parsing_format = cmdline.format

    if cmdline.include_dir is not None:
        incl_dirs = cmdline.include_dir
    else:
        incl_dirs = ""

    output_file = cmdline.output_file
    destination_dir = cmdline.destination_dir
    interface_spec_files = cmdline.intf_specs
    interface_def_files = cmdline.intf_defs
    module_def_files = cmdline.mod_defs

    if cmdline.files is None:
        files = []
    else:
        files = cmdline.files

    if cmdline.lists is None:
        file_lists = []
    else:
        file_lists = cmdline.lists

    hash_define_vars = cmdline.hash_define_vars
    hash_define_files = cmdline.hash_define_files
    verilog_define_files = cmdline.verilog_define_files
    debug = cmdline.debug
    remove_code = cmdline.remove_code
    parser_on = cmdline.parser_on
    package_files = cmdline.package_files
    sort_ios = cmdline.sort_ios
    group_ios_on_dir = cmdline.group_ios_on_dir
    generate_stub = cmdline.generate_stub
    parse_generate = cmdline.parse_generate
    gen_dependancies = cmdline.generate_dependancies
    veripy_path = cmdline.veripy_path
    update_inc = cmdline.update_inc
    root_path = os.path.abspath(cmdline.root_path)
    user_options = cmdline.user_options
    disable_tick_ifdefs = cmdline.disable_tick_ifdefs
    auto_package_load = cmdline.auto_package_load
    python_files = cmdline.python_files
    target_vendors = cmdline.target_vendors
    build_subdirs_dict_json = cmdline.build_subdirs_dict_json
    use_prev_dict = cmdline.use_prev_dict
    profiling_file = cmdline.profiling_file
    targetdir = cmdline.targetdir

    gather_verilog_subs_include_files = cmdline.gather_verilog_subs_include_files
    if gather_verilog_subs_include_files:
        warnings.warn(
            "Option --gather_verilog_includes/-gv is not used and has been deprecated.",
            DeprecationWarning,
        )

    if update_inc:
        update_targets = False
    else:
        update_targets = True

    ################################################################################
    # Gathering commandline options to call Veripy script                          #
    ################################################################################
    IN_FILE_OPTION = in_file

    FORMAT = "--format " + parsing_format

    if incl_dirs is not None:
        INCL_DIRS_OPTION = "--include ./ " + " ".join(incl_dirs)
    else:
        INCL_DIRS_OPTION = "--include ./ "

    INTERFACE_SPECS_OPTION = ""
    if interface_spec_files is not None:
        if len(interface_spec_files) > 0:
            INTERFACE_SPECS_OPTION += " --interface_spec " + " ".join(
                interface_spec_files
            )

    INTERFACE_DEFS_OPTION = ""
    if interface_def_files is not None:
        if len(interface_def_files) > 0:
            INTERFACE_DEFS_OPTION += " --interface_def " + " ".join(interface_def_files)

    MODULE_DEFS_OPTION = ""
    if module_def_files is not None:
        if len(module_def_files) > 0:
            MODULE_DEFS_OPTION += " --module_def " + " ".join(module_def_files)

    FILES_OPTION = ""
    if files is not None:
        if len(files) > 0:
            FILES_OPTION += " --file " + " ".join(files)

    LIST_OPTION = ""
    if file_lists is not None:
        if len(file_lists) > 0:
            LIST_OPTION += " --list " + " ".join(file_lists)

    DEFINE_VARS_OPTION = ""
    if hash_define_vars is not None:
        if len(hash_define_vars) > 0:
            DEFINE_VARS_OPTION += " --hash_define_vars " + " ".join(hash_define_vars)

    DEFINE_FILES_OPTION = ""
    if hash_define_files is not None:
        if len(hash_define_files) > 0:
            DEFINE_FILES_OPTION += " --hash_define_files " + " ".join(hash_define_files)

    VERILOG_DEFINE_FILES_OPTION = ""
    if verilog_define_files is not None:
        if len(verilog_define_files) > 0:
            VERILOG_DEFINE_FILES_OPTION += " --verilog_define_file " + " ".join(
                verilog_define_files
            )

    if debug:
        DEBUG_OPTION = debug
    else:
        DEBUG_OPTION = False

    REMOVE_CODE_OPTION = remove_code

    PARSER_ON_OPTION = parser_on

    DESTINATION_OPTION = ""
    if destination_dir != "":
        DESTINATION_OPTION = " --destination " + destination_dir

    PACKAGES_OPTION = ""
    if package_files is not None:
        if len(package_files) > 0:
            PACKAGES_OPTION += " --package " + " ".join(package_files)

    SORT_IOS_OPTION = sort_ios

    GROUP_IOS_ON_DIR_OPTION = group_ios_on_dir

    if parse_generate:
        PARSE_GENERATE_OPTION = ""
    else:
        PARSE_GENERATE_OPTION = "--generate_disable"

    DEPENDENCIES_OPTION = " --dependancy_list "

    USER_OPTIONS = ""
    if user_options is not None:
        if len(user_options) > 0:
            USER_OPTIONS = " ".join(user_options)

    if veripy_path is not None:
        VERIPY_SCRIPT = veripy_path + " "
    else:
        VERIPY_SCRIPT = "$(VERIPY_SCRIPT) "

    if disable_tick_ifdefs:
        DISABLE_TICK_IFDEFS_OPTION = ""
    else:
        DISABLE_TICK_IFDEFS_OPTION = "--disable_tick_ifdefs"

    if auto_package_load:
        DISABLE_AUTO_PACKAGE_OPTION = ""
    else:
        DISABLE_AUTO_PACKAGE_OPTION = "--disable_auto_package"

    if update_targets:
        UPDATE_TARGETS_OPTION = True
    else:
        UPDATE_TARGETS_OPTION = False

    PYTHON_FILES_OPTION = ""
    if python_files is not None:
        if len(python_files) > 0:
            PYTHON_FILES_OPTION += " --python " + " ".join(python_files)

    if build_subdirs_dict_json != "":
        use_dict = True
        if os.path.exists(build_subdirs_dict_json):
            with open(build_subdirs_dict_json, "r") as fp:
                build_subdirs_dict = json.load(fp)
        else:
            build_subdirs_dict = {}
    else:
        use_dict = False
        build_subdirs_dict = {}

    if profiling_file != "":
        PROFILING_FILE_OPTION = "-prof " + profiling_file + " "
    else:
        PROFILING_FILE_OPTION = " "

    if targetdir != "":
        DEST_DIR = targetdir

    return (
        IN_FILE_OPTION,
        FORMAT,
        INCL_DIRS_OPTION,
        INTERFACE_SPECS_OPTION,
        INTERFACE_DEFS_OPTION,
        MODULE_DEFS_OPTION,
        FILES_OPTION,
        LIST_OPTION,
        DEFINE_VARS_OPTION,
        DEFINE_FILES_OPTION,
        VERILOG_DEFINE_FILES_OPTION,
        DEBUG_OPTION,
        REMOVE_CODE_OPTION,
        PARSER_ON_OPTION,
        DESTINATION_OPTION,
        PACKAGES_OPTION,
        SORT_IOS_OPTION,
        GROUP_IOS_ON_DIR_OPTION,
        PARSE_GENERATE_OPTION,
        DEPENDENCIES_OPTION,
        USER_OPTIONS,
        VERIPY_SCRIPT,
        DISABLE_TICK_IFDEFS_OPTION,
        DISABLE_AUTO_PACKAGE_OPTION,
        UPDATE_TARGETS_OPTION,
        PYTHON_FILES_OPTION,
        build_subdirs_dict_json,
        build_subdirs_dict,
        use_dict,
        use_prev_dict,
        update_inc,
        root_path,
        target_vendors,
        PROFILING_FILE_OPTION,
        DEST_DIR,
    )


def gen_dependencies(
    IN_FILE_OPTION,
    FORMAT,
    INCL_DIRS_OPTION,
    INTERFACE_SPECS_OPTION,
    INTERFACE_DEFS_OPTION,
    MODULE_DEFS_OPTION,
    FILES_OPTION,
    LIST_OPTION,
    DEFINE_VARS_OPTION,
    DEFINE_FILES_OPTION,
    VERILOG_DEFINE_FILES_OPTION,
    DEBUG_OPTION,
    REMOVE_CODE_OPTION,
    PARSER_ON_OPTION,
    DESTINATION_OPTION,
    PACKAGES_OPTION,
    SORT_IOS_OPTION,
    GROUP_IOS_ON_DIR_OPTION,
    PARSE_GENERATE_OPTION,
    DEPENDENCIES_OPTION,
    USER_OPTIONS,
    VERIPY_SCRIPT,
    DISABLE_TICK_IFDEFS_OPTION,
    DISABLE_AUTO_PACKAGE_OPTION,
    UPDATE_TARGETS_OPTION,
    PYTHON_FILES_OPTION,
    build_subdirs_dict_json,
    build_subdirs_dict,
    use_dict,
    use_prev_dict,
    PROFILING_FILE_OPTION,
    DEST_DIR,
):
    """!
    Get dependencies for file hierarchy

    @param IN_FILE_OPTION Option passed to veripy.py command containing the input filename
    @param FORMAT Option passed to veripy.py command containing the input file format (Verilog/SystemVerilog)
    @param INCL_DIRS_OPTION Option passed to veripy.py containing a list of the directories to be checked
    @param INTERFACE_SPECS_OPTION Option passed to veripy.py containing interface specs
    @param INTERFACE_DEFS_OPTION Option passed to veripy.py containing interface defs
    @param MODULE_DEFS_OPTION Option passed to veripy.py containing module defs
    @param FILES_OPTION Option passed to veripy.py containing additional files to check for submodules / include / package / spec
    @param LIST_OPTION Option passed to veripy.py containing filelists to check for submodules / include / package / spec
    @param DEFINE_VARS_OPTION Option passed to veripy.py containing #define vars passed through the command line
    @param DEFINE_FILES_OPTION Option passed to veripy.py containing a file containing #define vars to be passed to the script
    @param VERILOG_DEFINE_FILES_OPTION Option passed to veripy.py containing a Verilog file containing #define vars to be passed to the script
    @param DEBUG_OPTION Option passed to veripy.py telling script to generate debug file
    @param REMOVE_CODE_OPTION Option passed to veripy.py to remove code disabled by ifdef
    @param PARSER_ON_OPTION Option passed to veripy.py to turn off parser and only perform preprocessing and embedded Python
    @param DESTINATION_OPTION Option passed to veripy.py to select the destination directory
    @param PACKAGES_OPTION Option passed to veripy.py to load SystemVerilog package files
    @param SORT_IOS_OPTION Option passed to veripy.py to sort module ports
    @param GROUP_IOS_ON_DIR_OPTION Option passed to veripy.py to group module ports by direction
    @param PARSE_GENERATE_OPTION Option passed to veripy.py to turn off parsing of generate blocks
    @param DEPENDENCIES_OPTION Option passed to veripy.py to generate all dependencies for building current block
    @param USER_OPTIONS Option passed to veripy.py to specify additional options
    @param VERIPY_SCRIPT String containing Bash variable pointer to the main VeriPy script
    @param DISABLE_TICK_IFDEFS_OPTION Option passed to veripy.py to disable `ifdef parsing
    @param DISABLE_AUTO_PACKAGE_OPTION Option passed to veripy.py to disable auto loading packages
    @param UPDATE_TARGETS_OPTION Set to 'True', tells script to update TARGETS file
    @param PYTHON_FILES_OPTION Option passed to veripy.py to load additional Python files that contain variables/dictionaries used
    @param build_subdirs_dict_json String containing file path for JSON file containing the Python dict object to store build subdirectories
    @param build_subdirs_dict Python dict object containing build dependencies
    @param use_dict Boolean to turn on/off the use of a dict to store build dependencies
    @param use_prev_dict Boolean to determine whether to generate a new dict for this run or load a previous one
    @param PROFILING_FILE_OPTION Option passed to veripy.py to enable a file to store profiling data
    """

    hierarchical_dependencies = {}

    global RE_SLASH
    RE_SLASH = re.compile(r"(.*)\/(.*)")

    top_module = 1
    exit_loop = False
    level = 0
    next_level = level + 1
    files_hierarchy = {}
    files_hierarchy[level] = {}
    files_hierarchy[level][IN_FILE_OPTION] = {}
    files_hierarchy[level][IN_FILE_OPTION]["PARENT"] = ""

    while not exit_loop:
        next_level = level + 1

        files_hierarchy[next_level] = {}

        for c_file in files_hierarchy[level]:
            if DEBUG_OPTION:
                print(json.dumps(files_hierarchy[level], indent=2))

            if use_dict and up_to_date_file_in_dict(
                str(c_file), build_subdirs_dict, use_prev_dict
            ):
                hierarchical_dependencies.update(build_subdirs_dict[str(c_file)])
                print("### Dependencies found for " + str(c_file))

            else:
                parent_file = files_hierarchy[level][c_file]["PARENT"]

                if "BUILD_CMD" in files_hierarchy[level][c_file]:
                    ADDL_BUILD_CMD = " ".join(
                        files_hierarchy[level][c_file]["BUILD_CMD"]
                    )
                else:
                    ADDL_BUILD_CMD = ""

                IN_FILE = c_file
                OUTPUT_FILE = c_file + ".dep_list"
                RUN_LOG = c_file + ".run.log"

                c_file_slash_regex = RE_SLASH.search(c_file)

                # If the *.psv or *.pv is not in the current directory
                if c_file_slash_regex:
                    hierarchical_dependencies[IN_FILE] = {}

                    if top_module:
                        hierarchical_dependencies[IN_FILE]["topmodule"] = "NONE"
                    else:
                        hierarchical_dependencies[IN_FILE]["topmodule"] = parent_file

                    continue

                # Create run command for calling Veripy script to generate dependencies
                RUN_CMD = VERIPY_SCRIPT
                RUN_CMD = (
                    RUN_CMD
                    + " "
                    + IN_FILE
                    + " "
                    + FORMAT
                    + " "
                    + INCL_DIRS_OPTION
                    + " "
                    + INTERFACE_SPECS_OPTION
                    + " "
                    + INTERFACE_DEFS_OPTION
                    + " "
                    + MODULE_DEFS_OPTION
                    + " "
                    + FILES_OPTION
                    + " "
                    + LIST_OPTION
                    + " "
                    + DEFINE_VARS_OPTION
                    + " "
                    + DEFINE_FILES_OPTION
                    + " "
                    + DEPENDENCIES_OPTION
                    + " "
                    + "--output "
                    + OUTPUT_FILE
                    + " "
                    + PARSE_GENERATE_OPTION
                    + " "
                    + ADDL_BUILD_CMD
                    + " "
                    + USER_OPTIONS
                    + " "
                    + DISABLE_TICK_IFDEFS_OPTION
                    + " "
                    + DISABLE_AUTO_PACKAGE_OPTION
                    + " "
                    + PYTHON_FILES_OPTION
                    + " "
                    + PROFILING_FILE_OPTION
                )
                run_cmd_split = re.split(r"--", RUN_CMD)

                c_first_options = run_cmd_split[0]

                c_cmd_count = 0

                fixed_run_cmd = {}
                for c_run_cmd in run_cmd_split:
                    if c_cmd_count > 0:
                        c_run_cmd_split = re.split(r"\s+", c_run_cmd, 1)

                        if c_run_cmd_split[0] in fixed_run_cmd:
                            fixed_run_cmd[c_run_cmd_split[0]] = (
                                fixed_run_cmd[c_run_cmd_split[0]]
                                + " "
                                + c_run_cmd_split[1]
                            )
                        else:
                            fixed_run_cmd[c_run_cmd_split[0]] = c_run_cmd_split[1]

                    c_cmd_count += 1

                UPDATED_RUN_CMD = c_first_options

                for c_key, c_value in fixed_run_cmd.items():
                    UPDATED_RUN_CMD += "--" + c_key + " " + c_value

                RUN_CMD = UPDATED_RUN_CMD

                print("### Gathering Dependencies for " + IN_FILE)

                if DEBUG_OPTION:
                    print("  # RUN COMMAND: " + RUN_CMD)

                # Run veripy.py to generate dependency list
                p = subprocess.Popen(RUN_CMD, stdout=subprocess.PIPE, shell=True)
                out, err = p.communicate()
                if p.returncode != 0:
                    print(out)
                    print("\n\nError: Please fix the build error for " + IN_FILE + "\n")
                    print("RUN COMMAND: " + RUN_CMD + "\n")
                    sys.exit(1)

                c_dependancies = {}

                # Load dependency list from file generated by Veripy script
                with open(OUTPUT_FILE, "r") as Yamlparameters:
                    c_dependancies = yaml.safe_load(Yamlparameters)

                if level > 0:
                    c_dependancies["build_cmd"] = files_hierarchy[level][IN_FILE][
                        "BUILD_CMD"
                    ]

                if len(c_dependancies["veripy_subs"]) > 0:
                    for veripy_sub in c_dependancies["veripy_subs"]:
                        if files_hierarchy[next_level] is None:
                            files_hierarchy[next_level] = {}

                        files_hierarchy[next_level][veripy_sub] = {}
                        files_hierarchy[next_level][veripy_sub]["PARENT"] = c_file

                        if c_dependancies["veripy_subs"][veripy_sub]["flags"] != "":
                            files_hierarchy[next_level][veripy_sub]["BUILD_CMD"] = (
                                c_dependancies["veripy_subs"][veripy_sub]["flags"]
                            )

                for category in list(c_dependancies.keys()):
                    if len(c_dependancies[category]) > 0:
                        print("  + " + category.upper() + ":")
                        for c_dep in c_dependancies[category]:
                            if not isinstance(c_dep, str):
                                print("    - " + next(iter(c_dep)))
                            else:
                                print("    - " + c_dep)
                    else:
                        del c_dependancies[category]

                hierarchical_dependencies[IN_FILE] = c_dependancies

                if top_module:
                    hierarchical_dependencies[IN_FILE]["topmodule"] = "NONE"
                else:
                    hierarchical_dependencies[IN_FILE]["topmodule"] = parent_file

                if use_dict:
                    build_subdirs_dict[IN_FILE] = hierarchical_dependencies
                    build_subdirs_dict[IN_FILE + " mtime"] = getmtime(IN_FILE)

                print()

                if not DEBUG_OPTION:
                    os.remove(OUTPUT_FILE)

        if files_hierarchy[next_level] is not None:
            if len(files_hierarchy[next_level]) == 0:
                del files_hierarchy[next_level]
                exit_loop = True

        # print(json.dumps(files_hierarchy, indent=2))
        top_module = 0
        level += 1

    if use_dict:
        with open(build_subdirs_dict_json, "w") as fp:
            json.dump(build_subdirs_dict, fp)

    if DEBUG_OPTION:
        print(
            "\n\n################################################################################"
        )
        print("#   Hierarchical Order of Modules")
        print(
            "################################################################################"
        )
        print(json.dumps(files_hierarchy, indent=2))

        print(
            "\n\n################################################################################"
        )
        print("#   Dependency List for all the Modules")
        print(
            "################################################################################"
        )
        print(json.dumps(hierarchical_dependencies, indent=2))

    return hierarchical_dependencies


def gen_makeinc(
    update_inc, root_path, hierarchical_dependencies, UPDATE_TARGETS_OPTION, DEST_DIR
):
    """
    Generating makefile.inc
    """

    subdirs_list = []

    if update_inc:
        root_path = re.sub(r"\?", r"\\?", root_path)

        with open("makefile.inc.new", "w") as makeinc:
            for c_mod in hierarchical_dependencies:
                # c_lib = re.sub(r"\..*", r"", c_mod)
                c_lib = os.path.splitext(c_mod)[0]
                c_lib_slash_regex = RE_SLASH.search(c_lib)

                if c_lib_slash_regex:
                    sub_dir = c_lib_slash_regex.group(1)
                    c_lib = c_lib_slash_regex.group(2) + "_lib"

                    target_line = "$(RUN_DIR)/" + c_lib + ": "
                    target_line = re.sub(root_path, r"$(ROOT)", target_line)
                    print_line = target_line
                    makeinc.write(print_line + "\n")

                    # Pushing the sub dir to array for clean and other targets
                    subdirs_list.append(sub_dir)

                    print_line = "ifeq ($(BUILD_SUBS),1)"
                    makeinc.write(print_line + "\n")

                    print_line = "\tmake -C " + sub_dir + " Build"
                    print_line = re.sub(root_path, r"$(ROOT)", print_line)
                    makeinc.write(print_line + "\n")

                    print_line = "endif"
                    makeinc.write(print_line + "\n")

                    c_lib = re.sub(root_path, r"$(ROOT)", c_lib)
                    print_line = "\t" + "touch $(RUN_DIR)/" + c_lib
                    makeinc.write(print_line + "\n")

                    print_line = "\n"
                    makeinc.write(print_line + "\n")
                else:
                    c_lib += "_lib"
                    target_line = "$(RUN_DIR)/" + c_lib + ": " + c_mod + " "

                    addl_build_cmd = ""

                    for c_cat in hierarchical_dependencies[c_mod]:
                        for c_dep in hierarchical_dependencies[c_mod][c_cat]:
                            if c_cat == "veripy_subs":
                                # c_dep = re.sub(r"\..*", r"", c_dep)
                                c_dep = os.path.splitext(c_dep)[0]
                                c_dep_slash_regex = RE_SLASH.search(c_dep)

                                if c_dep_slash_regex:
                                    target_line += (
                                        "$(RUN_DIR)/"
                                        + c_dep_slash_regex.group(2)
                                        + "_lib "
                                    )
                                else:
                                    target_line += "$(RUN_DIR)/" + c_dep + "_lib "
                            elif c_cat == "include_files":
                                target_line += next(iter(c_dep)) + " "
                            elif c_cat == "spec_files":
                                target_line += next(iter(c_dep)) + " "
                            elif c_cat == "interface_files":
                                target_line += next(iter(c_dep)) + " "
                            elif c_cat == "module_files":
                                target_line += next(iter(c_dep)) + " "
                            elif c_cat == "build_cmd":
                                for c_cmd in hierarchical_dependencies[c_mod][c_cat]:
                                    addl_build_cmd += str(c_cmd) + " "

                    target_line = re.sub(root_path, r"$(ROOT)", target_line)
                    print_line = target_line
                    makeinc.write(print_line + "\n")

                    RUN_CMD = (
                        "$(VERIPY_LIB) "
                        + c_mod
                        + " $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION) \
                        $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION) \
                        $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION) \
                        $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION) \
                        $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS) \
                        $(ADDITIONAL_OPTIONS) "
                        + str(addl_build_cmd)
                    )

                    RUN_CMD = re.sub(root_path, r"$(ROOT)", RUN_CMD)
                    print_line = "\t" + RUN_CMD
                    makeinc.write(print_line + "\n")

                    c_lib = re.sub(root_path, r"$(ROOT)", c_lib)
                    print_line = "\t" + "touch $(RUN_DIR)/" + c_lib
                    makeinc.write(print_line + "\n\n\n")


def gen_targets(
    UPDATE_TARGETS_OPTION,
    DEBUG_OPTION,
    hierarchical_dependencies,
    target_vendors,
    USER_OPTIONS,
    INCL_DIRS_OPTION,
    DEST_DIR,
):
    """
    Generating TARGETS file for Buck Build
    """

    global debug
    debug = DEBUG_OPTION
    subdirs_list = []

    incdirs = list()
    incdir_string = ""
    inc_string = re.sub(r"--include\s*", "", INCL_DIRS_OPTION)

    if inc_string:
        incdirs = inc_string.split()
        for onedir in incdirs:
            if (
                (not re.search(r"fbsource/fbcode/infra_asic_fpga", onedir))
                and (not onedir == DEST_DIR)
                and (not onedir == "./")
            ):
                incdir_string += onedir + " "
    else:
        incdir_string = ""
    dbg("incdir_string    : " + incdir_string)
    dbg("INCL_DIRS_OPTION " + "\n".join(incdirs))
    dbg("UPDATE_TARGETS_OPTION : " + str(UPDATE_TARGETS_OPTION))
    current_dir = os.getcwd()

    if UPDATE_TARGETS_OPTION:
        with open("TARGETS.new", "w") as targets_file:
            # print_line = "load(\"@fbcode_macros//build_defs:python_library.bzl\", \"python_library\")"
            # targets_file.write(print_line + '\n')
            # dbg(print_line)

            print_line = "load("
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = (
                "    " + '"//infra_asic_fpga/common/tools/src/buck:asic_macros.bzl",'
            )
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + '"VERIPY_TARGET",'
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + '"asic_library",'
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = ")"
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "asic_library("
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + 'name = "rtl_f_list",'
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + "srcs = ["
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + '"rtl/filelist.txt",'
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = "    " + "],"
            targets_file.write(print_line + "\n")
            dbg(print_line)

            ### incdirs = []
            ### print_line = '    ' + "incdirs = ["
            ### dbg(print_line)
            ### targets_file.write(print_line + '\n')
            ### for onedir in incdirs:
            ###     print_line = '    ' + '"' + onedir  + '",'
            ###     targets_file.write(print_line + '\n')
            ###     dbg(print_line)
            ### print_line = '    ' + '],'
            ### targets_file.write(print_line + '\n')
            ### dbg(print_line)

            print_line = "    deps = ["
            targets_file.write(print_line + "\n")
            dbg(print_line)

            if hierarchical_dependencies:
                top_module_hier = list(hierarchical_dependencies)
                top_module_hier_no_ext = re.sub(r"\.psv", r"", top_module_hier[0])
                top_module_hier_no_ext1 = re.sub(r"\.sv", r"", top_module_hier_no_ext)
                print_line = '        ":' + top_module_hier_no_ext1 + '",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

            print_line = "    " + "],"
            targets_file.write(print_line + "\n")
            dbg(print_line)

            print_line = ")"
            targets_file.write(print_line + "\n")
            dbg(print_line)
            if target_vendors:
                ####
                print_line = "asic_library("
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    " + 'name = "rtl_b_f_list",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    " + "srcs = ["
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    " + '"rtl_b/filelist.txt",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    " + "],"
                targets_file.write(print_line + "\n")
                dbg(print_line)

                ### incdirs = []
                ###  print_line = '    ' + "incdirs = ["
                ###  dbg(print_line)
                ###  targets_file.write(print_line + '\n')
                ###  for onedir in incdirs:
                ###      print_line = '    ' + '"' + onedir  + '",'
                ###      targets_file.write(print_line + '\n')
                ###      dbg(print_line)
                ###  print_line = '    ' + '],'
                ###  targets_file.write(print_line + '\n')
                ###  dbg(print_line)

                print_line = "    deps = ["
                targets_file.write(print_line + "\n")
                dbg(print_line)

                if hierarchical_dependencies:
                    top_module_hier = list(hierarchical_dependencies)
                    top_module_hier_no_ext = re.sub(r"\.psv", r"", top_module_hier[0])
                    top_module_hier_no_ext1 = re.sub(
                        r"\.sv", r"", top_module_hier_no_ext
                    )
                    print_line = '        ":' + top_module_hier_no_ext1 + '",'
                    targets_file.write(print_line + "\n")
                    dbg(print_line)

                print_line = "    " + "],"
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = ")"
                targets_file.write(print_line + "\n")
                dbg(print_line)
                ####

            for c_mod in hierarchical_dependencies:
                dbg("### ### ### " + c_mod)

                c_target_args = ""

                c_target_args = " " + USER_OPTIONS

                c_deps_list = []

                c_mod_in_diff_dir = check_dir(c_mod)
                if c_mod_in_diff_dir:
                    continue

                for c_dep_category in hierarchical_dependencies[c_mod]:
                    if c_dep_category == "include_files":
                        for c_dep in hierarchical_dependencies[c_mod][c_dep_category]:
                            c_dep = gen_dependency(next(iter(c_dep)))
                            c_deps_list.append(c_dep)
                            dbg("    ### ### " + c_dep)

                    elif c_dep_category == "header_files":
                        dbg("    ### ### " + c_dep_category)

                        if len(hierarchical_dependencies[c_mod][c_dep_category]) > 0:
                            c_dep_filenames = set()

                            for c_dep in hierarchical_dependencies[c_mod][
                                c_dep_category
                            ]:
                                c_dep_map = gen_dependency(next(iter(c_dep)))
                                c_deps_list.append(c_dep_map)

                                c_dep_filenames.add(get_filename(next(iter(c_dep))))
                                dbg("        ### " + c_dep_map)

                            c_target_args = (
                                c_target_args
                                + " --hash_define_files "
                                + " ".join(sorted(c_dep_filenames))
                            )

                    elif c_dep_category == "verilog_subs":
                        dbg("    ### ### " + c_dep_category)
                        for c_dep in hierarchical_dependencies[c_mod][c_dep_category]:
                            c_dep_map = gen_dependency(next(iter(c_dep)))
                            c_deps_list.append(c_dep_map)
                            dbg("        ### " + c_dep_map)

                    elif c_dep_category == "veripy_subs":
                        dbg("    ### ### " + c_dep_category)
                        for c_dep in hierarchical_dependencies[c_mod][c_dep_category]:
                            c_dep_map = gen_dependency(c_dep)
                            c_deps_list.append(c_dep_map)
                            dbg("        ### " + c_dep_map)

                    elif c_dep_category == "spec_files":
                        dbg("    ### ### " + c_dep_category)

                        if len(hierarchical_dependencies[c_mod][c_dep_category]) > 0:
                            c_dep_filenames = set()

                            for c_dep in hierarchical_dependencies[c_mod][
                                c_dep_category
                            ]:
                                c_dep_map = gen_dependency(next(iter(c_dep)))
                                c_deps_list.append(c_dep_map)

                                c_dep_filenames.add(get_filename(next(iter(c_dep))))
                                dbg("        ### " + c_dep_map)

                            c_target_args = (
                                c_target_args
                                + " --interface_spec "
                                + " ".join(sorted(c_dep_filenames))
                            )

                    elif c_dep_category == "interface_files":
                        dbg("    ### ### " + c_dep_category)

                        if len(hierarchical_dependencies[c_mod][c_dep_category]) > 0:
                            c_dep_filenames = set()

                            for c_dep in hierarchical_dependencies[c_mod][
                                c_dep_category
                            ]:
                                c_dep_map = gen_dependency(next(iter(c_dep)))
                                c_deps_list.append(c_dep_map)

                                c_dep_filenames.add(get_filename(next(iter(c_dep))))
                                dbg("        ### " + c_dep_map)

                            c_target_args = (
                                c_target_args
                                + " --interface_def "
                                + " ".join(sorted(c_dep_filenames))
                            )

                    elif c_dep_category == "module_files":
                        dbg("    ### ### " + c_dep_category)

                        if len(hierarchical_dependencies[c_mod][c_dep_category]) > 0:
                            c_dep_filenames = set()

                            for c_dep in hierarchical_dependencies[c_mod][
                                c_dep_category
                            ]:
                                c_dep_map = gen_dependency(next(iter(c_dep)))
                                c_deps_list.append(c_dep_map)

                                c_dep_filenames.add(get_filename(next(iter(c_dep))))
                                dbg("        ### " + c_dep_map)

                            c_target_args = (
                                c_target_args
                                + " --module_def "
                                + " ".join(sorted(c_dep_filenames))
                            )

                    elif c_dep_category == "depends":
                        dbg("    ### ### " + c_dep_category)
                        for c_dep in hierarchical_dependencies[c_mod][c_dep_category]:
                            c_deps_list.append(next(iter(c_dep)))
                            dbg("        ### " + next(iter(c_dep)))

                    elif c_dep_category == "build_cmd":
                        dbg("    ### ### " + c_dep_category)
                        c_target_args += " " + " ".join(
                            hierarchical_dependencies[c_mod][c_dep_category]
                        )
                        dbg("        ### " + c_target_args)

                print_line = "asic_library("
                targets_file.write("\n" + print_line + "\n")
                dbg(print_line)

                c_mod_wo_ext = re.sub(r"\..*", r"", c_mod)

                print_line = '    name = "' + c_mod_wo_ext + '",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

                ### incdirs = []
                ### print_line = '    ' + "incdirs = ["
                ### dbg(print_line)
                ### targets_file.write(print_line + '\n')
                ### for onedir in incdirs:
                ###     print_line = '    ' + '"' + onedir  + '",'
                ###     targets_file.write(print_line + '\n')
                ###     dbg(print_line)
                ### print_line = '    ' + '],'
                ### targets_file.write(print_line + '\n')
                ### dbg(print_line)

                print_line = "    srcs = ["
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = '        "src/' + c_mod + '",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    ],"
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    embedded_generator = VERIPY_TARGET,"
                targets_file.write(print_line + "\n")
                dbg(print_line)

                print_line = "    input_arg = None,"
                targets_file.write(print_line + "\n")
                dbg(print_line)

                if incdir_string:
                    dbg("    ### ### INCLUDE")
                    c_target_args = c_target_args + " --include"
                    c_target_args += " " + incdir_string
                    dbg("        ### " + incdir_string)

                print_line = '    target_args = "' + c_target_args + '",'
                targets_file.write(print_line + "\n")
                dbg(print_line)

                if len(c_deps_list) > 0:
                    print_line = "    deps = ["
                    targets_file.write(print_line + "\n")
                    dbg(print_line)

                    c_deps_list = sorted(set(c_deps_list))

                    for c_dep in c_deps_list:
                        dep_regex = re.search(re.compile(r"^:"), c_dep)

                        if dep_regex:
                            c_dep_wo_ext = re.sub(r"\.psv", r"", c_dep)
                            c_dep_wo_ext = re.sub(r"\.pv", r"", c_dep_wo_ext)
                            c_dep_wo_ext = re.sub(r"\/src:", r":", c_dep_wo_ext)
                            print_line = '        "' + c_dep_wo_ext + '",'
                            targets_file.write(print_line + "\n")
                            dbg(print_line)

                    for c_dep in c_deps_list:
                        dep_regex = re.search(re.compile(r"^\/\/"), c_dep)

                        if dep_regex:
                            c_dep_wo_ext = re.sub(r"\.psv", r"", c_dep)
                            c_dep_wo_ext = re.sub(r"\.pv", r"", c_dep_wo_ext)

                            c_dep_wo_ext = re.sub(
                                r"\/src:(.*)$", r":rtl_f_list", c_dep_wo_ext
                            )

                            print_line = '        "' + c_dep_wo_ext + '",'
                            targets_file.write(print_line + "\n")
                            dbg(print_line)

                    print_line = "    ],"
                    targets_file.write(print_line + "\n")
                    dbg(print_line)

                print_line = ")"
                targets_file.write(print_line + "\n")
                dbg(print_line + "\n")


def main():
    """
    Main function to run in script.
    """

    (
        IN_FILE_OPTION,
        FORMAT,
        INCL_DIRS_OPTION,
        INTERFACE_SPECS_OPTION,
        INTERFACE_DEFS_OPTION,
        MODULE_DEFS_OPTION,
        FILES_OPTION,
        LIST_OPTION,
        DEFINE_VARS_OPTION,
        DEFINE_FILES_OPTION,
        VERILOG_DEFINE_FILES_OPTION,
        DEBUG_OPTION,
        REMOVE_CODE_OPTION,
        PARSER_ON_OPTION,
        DESTINATION_OPTION,
        PACKAGES_OPTION,
        SORT_IOS_OPTION,
        GROUP_IOS_ON_DIR_OPTION,
        PARSE_GENERATE_OPTION,
        DEPENDENCIES_OPTION,
        USER_OPTIONS,
        VERIPY_SCRIPT,
        DISABLE_TICK_IFDEFS_OPTION,
        DISABLE_AUTO_PACKAGE_OPTION,
        UPDATE_TARGETS_OPTION,
        PYTHON_FILES_OPTION,
        build_subdirs_dict_json,
        build_subdirs_dict,
        use_dict,
        use_prev_dict,
        update_inc,
        root_path,
        target_vendors,
        PROFILING_FILE_OPTION,
        DEST_DIR,
    ) = get_cmd_line_args()

    hierarchical_dependencies = gen_dependencies(
        IN_FILE_OPTION,
        FORMAT,
        INCL_DIRS_OPTION,
        INTERFACE_SPECS_OPTION,
        INTERFACE_DEFS_OPTION,
        MODULE_DEFS_OPTION,
        FILES_OPTION,
        LIST_OPTION,
        DEFINE_VARS_OPTION,
        DEFINE_FILES_OPTION,
        VERILOG_DEFINE_FILES_OPTION,
        DEBUG_OPTION,
        REMOVE_CODE_OPTION,
        PARSER_ON_OPTION,
        DESTINATION_OPTION,
        PACKAGES_OPTION,
        SORT_IOS_OPTION,
        GROUP_IOS_ON_DIR_OPTION,
        PARSE_GENERATE_OPTION,
        DEPENDENCIES_OPTION,
        USER_OPTIONS,
        VERIPY_SCRIPT,
        DISABLE_TICK_IFDEFS_OPTION,
        DISABLE_AUTO_PACKAGE_OPTION,
        UPDATE_TARGETS_OPTION,
        PYTHON_FILES_OPTION,
        build_subdirs_dict_json,
        build_subdirs_dict,
        use_dict,
        use_prev_dict,
        PROFILING_FILE_OPTION,
        DEST_DIR,
    )

    gen_makeinc(
        update_inc,
        root_path,
        hierarchical_dependencies,
        UPDATE_TARGETS_OPTION,
        DEST_DIR,
    )

    gen_targets(
        UPDATE_TARGETS_OPTION,
        DEBUG_OPTION,
        hierarchical_dependencies,
        target_vendors,
        USER_OPTIONS,
        INCL_DIRS_OPTION,
        DEST_DIR,
    )


if __name__ == "__main__":
    main()
