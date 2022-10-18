#!/usr/bin/env python3
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

import yaml as yaml
from src.codegen import *
from src.verilog_parser import *
from src.spec_flow import *
from src.utils import *
from src.regex import *
from collections import OrderedDict
from csv import reader
from math import ceil, log
from typing import Dict, Set

from src.memgen import memgen

sys.setrecursionlimit(3000)

if __name__ == "__main__":
    debug = 0  # To enable debug dump
    debug_file = "veripy.debug"  # Default debug file name
    parser_on = 1
    parsing_format = "systemverilog"  # Default format is verilog
    remove_code = 0
    incl_dirs = []
    package_files = []

    group_ios_on_dir = 1
    sort_ios = 0
    parse_generate = 1
    generate_stub = 0
    generate_stub_z = 0
    generate_stub_0 = 0

    found_error = 0

    hash_define_vars = []
    hash_define_files = []

    stub_override_val = {}

    clock = "clk"
    async_reset = "arst_n"
    sync_reset = "rst_n"
    reset_type = "ASYNC"

    ############################################################################
    # Command line arguments processing
    ############################################################################
    parser = argparse.ArgumentParser(
        description="Veripy is a python based \
            automation for Verilog or SystemVerilog design. It autogenerates \
            module declaration, reg/logic/wire generation, instantiation, \
            embedded python. It has C-like preprocessing capabilities to \
            preprocess the input code with \
            #defines/#ifdef/#ifndef/#elsif/#else."
    )

    # Input .psv or .pv filename
    parser.add_argument(
        "positional",
        action="store",
        help="Input filename \
            with a mix of verilog|systemverilog along with embedded python \
            code. <filename>.pv - Input file with mix of verilog and embedded \
            python. <filename>.psv - Input file with mix of system verilog \
            and embedded python.",
    )

    # -format option
    parser.add_argument(
        "-fo",
        "--format",
        action="store",
        default="systemverilog",
        dest="format",
        help="By default, the \
            parser runs in verilog parsing mode. To parse systemverilog, \
            systemverilog as format to be used in the command line",
    )

    # -include option
    parser.add_argument(
        "-inc",
        "--include",
        nargs="*",
        dest="include_dir",
        help="Optional include directory to search for include files, \
            sub-module files. User can add multiple include directories. \
            First current directory is searched for submodule or include \
            files and then the order include directories in the command line.",
    )

    # -output option
    parser.add_argument(
        "-o",
        "--output",
        action="store",
        default="",
        dest="output_file",
        help="Optional output file name to rename \
            the output file. The output filename will be <filename>.v or \
            <filename>.sv based on -format option.",
    )

    # -destination_dir option
    parser.add_argument(
        "-de",
        "--destination",
        action="store",
        default="",
        dest="destination_dir",
        help="By default, the parser runs in \
            verilog parsing mode. To parse systemverilog, systemverilog as \
            format to be used in the command line",
    )

    # -interface spec option
    parser.add_argument(
        "-ifs",
        "--interface_spec",
        nargs="*",
        dest="intf_specs",
        help="Interface specification that has the details of input/output signals for each interface in structures format.",
    )

    # -intf definition option
    parser.add_argument(
        "-ifd",
        "--interface_def",
        nargs="*",
        dest="intf_defs",
        help="Interface definition file that has interface name, type and \
            other parameter like bus width",
    )

    # -module spec option
    parser.add_argument(
        "-md",
        "--module_def",
        nargs="*",
        dest="mod_defs",
        help="Module definition file with list of interfaces per module. \
            Once the tool populates the input and output ports after parsing \
            the verilog/systemverilog code, it compares the populated ports \
            with the module specification. If any ports popped up other than \
            the list per the module spec, it will prompt error.  This helps \
            avoiding unnecessary ports pop up at top level due to auto build \
            that causes compile errors.",
    )

    # --python option
    parser.add_argument(
        "-py",
        "--python",
        nargs="*",
        dest="python_files",
        help="Optional --python option to load python scripts that can \
            have python variables/dictionaries to be used in embedded python.",
    )

    # -file option
    parser.add_argument(
        "-fi",
        "--file",
        nargs="*",
        dest="files",
        help="Optional -file option to pass in a file name to look for \
            submodules / include / package / spec files",
    )

    # -list option
    parser.add_argument(
        "-l",
        "--list",
        nargs="*",
        dest="lists",
        help="Optional -list option to pass in a file that has the list \
            of files to look for submodules / include / package / spec files",
    )

    # -hash_define_vars option
    parser.add_argument(
        "-hdv",
        "--hash_define_vars",
        nargs="*",
        dest="hash_define_vars",
        help="#define for pre-processing. This \
            is like C pre-processor that is used in #ifdef/#elif to control \
            the code generation by passing in the #define. This option is for \
            the user to pass the #define as a command line. These #defines \
            can be accessed by user in embedded python code.",
    )

    # -define_file option
    parser.add_argument(
        "-hdf",
        "--hash_define_files",
        nargs="*",
        dest="hash_define_files",
        help="This option let the user to list \
            all the #defines in a file and pass it as command line. This is \
            like a project or module level #defines file that control the \
            configurable code generations.",
    )

    # -verilog_define_file option
    parser.add_argument(
        "-vdf",
        "--verilog_define_files",
        nargs="*",
        dest="verilog_define_files",
        help="This option let the user to \
            list all the verilog define or parameter files and pass it as \
            command line. This is like a project or module level #defines \
            file that control the configurable code generations.",
    )

    # -debug option
    parser.add_argument(
        "-deb",
        "--debug",
        action="store_true",
        default=False,
        dest="debug",
        help="Option to generate debug \
            dump from the tool for debugging any code generation issue.",
    )

    # -remove_code option
    parser.add_argument(
        "-rm",
        "--remove_code",
        action="store_true",
        default=False,
        dest="remove_code",
        help="Option to not to print \
            the disabled code by #ifdef/elif pre-processing in the final .v \
            or .sv file.",
    )

    # -parser_off option
    parser.add_argument(
        "-pars",
        "--parser_off",
        action="store_false",
        default=True,
        dest="parser_on",
        help="Option to turn off the \
            verilog/systemverilog parser. This enables the script to be \
            used only for preprocessing and embedded python.",
    )

    # -package option
    parser.add_argument(
        "-pac",
        "--package",
        nargs="*",
        dest="package_files",
        help="Option for loading the system verilog package files. User \
            can load multiple files with mutliple times calling this option. \
            When we load commandline these packages, same list of packages \
            will be loaded for the sub-module instantiation as well.",
    )

    # -sort_ports option
    parser.add_argument(
        "-so",
        "--sort_ports",
        action="store_true",
        default=False,
        dest="sort_ios",
        help="By default it does not \
            sort the ports. With this option, it sorts and generates module \
            ports.",
    )

    # -ungroup_ports option
    parser.add_argument(
        "-u",
        "--ungroup_ports",
        action="store_false",
        default=True,
        dest="group_ios_on_dir",
        help="By default, it \
            generates input and output ports separately. With -ungroup \
            option, it generates mix of input and output ports. This option \
            can be used with -sort_ports option",
    )

    # -stub option
    parser.add_argument(
        "-st",
        "--stub",
        action="store_true",
        default=False,
        dest="generate_stub",
        help="Generate stub modules from *.pv or \
            *.psv or *.v or *.sv. You still have to call &GenDrive0; or \
            GenDriveZ; or GenDrive0andZ; If the stubs from *.v or *.sv then \
            use -output option to rename the output file.",
    )

    # -generate_parse option
    parser.add_argument(
        "-gdis",
        "--generate_disable",
        action="store_false",
        default=True,
        dest="parse_generate",
        help="By default generate \
            blocks are parsed. With this option, the user canturn it off.",
    )

    # -dependencies option
    parser.add_argument(
        "-dep",
        "--dependancy_list",
        action="store_true",
        default=False,
        dest="generate_dependancies",
        help="This option \
            generates all the dependencies for building the current block. \
            The dependencies are printed in the -output file.",
    )

    # -auto_package option
    parser.add_argument(
        "-dap",
        "--disable_auto_package",
        action="store_false",
        default=True,
        dest="auto_package_load",
        help="This option disables \
            auto loading of system verilog packages.",
    )

    # -gen_filelist option
    parser.add_argument(
        "-gf",
        "--gen_filelist",
        action="store_true",
        default=False,
        dest="generate_filelist",
        help="This option \
            generates filelist for the top module. It gathers filelist from \
            sub-modules.",
    )

    # -disable_tick_ifdefs
    parser.add_argument(
        "-dti",
        "--disable_tick_ifdefs",
        action="store_true",
        default=False,
        dest="disable_tick_ifdefs",
        help="This option \
            disables `ifdef parsing in the verilog code.`.",
    )

    # -profiling
    parser.add_argument(
        "-prof",
        "--profiling",
        action="store",
        default="",
        dest="profiling_file",
        help="By default, no profiling file is \
            generated. If a filename is specified, it will be written to with \
            the profiling data.",
    )

    cmdline = parser.parse_args()

    in_file = cmdline.positional
    parsing_format = cmdline.format

    if cmdline.include_dir is not None:
        incl_dirs = [os.getcwd()] + [
            os.path.abspath(idir) for idir in cmdline.include_dir
        ]
    else:
        incl_dirs = [os.getcwd()]

    if cmdline.destination_dir is not None and cmdline.destination_dir != "":
        cmdline.destination_dir = os.path.abspath(cmdline.destination_dir)
        incl_dirs.append(cmdline.destination_dir)

    output_file = cmdline.output_file
    destination_dir = cmdline.destination_dir
    interface_spec_files = cmdline.intf_specs
    interface_def_files = cmdline.intf_defs
    module_def_files = cmdline.mod_defs

    if cmdline.files is None:
        files = []
    else:
        files = cmdline.files

    if cmdline.python_files is None:
        python_files = []
    else:
        python_files = cmdline.python_files

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
    gen_dependencies = cmdline.generate_dependancies
    auto_package_load = cmdline.auto_package_load
    generate_filelist = cmdline.generate_filelist
    disable_tick_ifdefs = cmdline.disable_tick_ifdefs

    if cmdline.profiling_file != "":
        profiling = True
        profiling_file = cmdline.profiling_file
    else:
        profiling = False
        profiling_file = ""

    ############################################################################
    # Opening debug file for debug dump
    ############################################################################
    if debug:
        debug_file = in_file + ".debug"
        dbg_file = open(debug_file + ".write", "w")

    ############################################################################
    # Gatering all the files in the files list
    ############################################################################
    filelist = set()
    list_file = list()
    if file_lists is not None:
        for c_list in file_lists:
            if os.path.isfile(c_list):  # List file doesn't exist
                with open(c_list) as filep:
                    for c_file in nonblank_lines(filep):
                        lline = c_file.rstrip("\n")
                        list_file.append(lline)
                filep.close
                # list_file = [line.rstrip('\n') for line in open(c_list)]
                for c_file in list_file:
                    c_file = c_file.rstrip()
                    c_filepath = os.path.expandvars(c_file)
                    if re.search("^-f ", c_file):
                        data = re.sub(r"-f ", r"", c_filepath)
                        a = recursive_filelist(data)
                        filelist.update(a)
                    elif re.search("filelist.txt$", c_filepath):
                        data = re.sub(r"-f ", r"", c_filepath)
                        a = recursive_filelist(data)
                        filelist.update(a)
                    else:
                        filelist.add(c_filepath)
            else:
                dbg(debug, "\nError: Unable to open file " + in_file)
                print(("\nError: Unable to open file " + in_file))
                sys.exit(1)

    files = list(filelist)
    ############################################################################
    # if no input file, then error out
    ############################################################################
    try:
        in_file
        in_file_name = re.sub(r".*\/", r"", in_file)
    except NameError:
        print("\nError: Missing input file option\n")
        sys.exit(1)

    ############################################################################
    # If no output file passed in command line, then outfile name is derived
    ############################################################################
    if output_file == "":
        split_arr = in_file.split(".")

        if parsing_format == "verilog":
            output_file = split_arr[0] + ".v"
        else:
            output_file = split_arr[0] + ".sv"

        split_arr = in_file_name.split(".")
        module_name = split_arr[0]

    try:
        output_file
        split_arr = in_file_name.split(".")
        module_name = split_arr[0]
    except NameError:
        split_arr = in_file.split(".")

        if parsing_format == "verilog":
            output_file = split_arr[0] + ".v"
        else:
            output_file = split_arr[0] + ".sv"

        split_arr = in_file_name.split(".")
        module_name = split_arr[0]

    output_list = re.sub(r"\.sv$", r".f", output_file)

    if destination_dir != "":
        destination_dir = re.sub(r"/$", r"", destination_dir)
        output_file = destination_dir + "/" + output_file
        output_list = destination_dir + "/" + output_list

    ############################################################################
    # Error out if input file does not exist
    ############################################################################
    if not os.path.isfile(in_file):  # In file doesn't exist
        dbg(debug, "\nError: Unable to open file " + in_file)
        print(("\nError: Unable to open file " + in_file))
        sys.exit(1)

    temporary_file = in_file + ".expanded"

    if debug_file == "veripy.debug":
        debug_file = in_file + ".debug"

    print(
        (
            "### IN: "
            + in_file
            + " MODULE: "
            + module_name
            + " OUT: "
            + output_file
            + " ###"
        )
    )

    # Checking if the output file is same as input to avoid overwriting
    if in_file == output_file:
        print("Error: Input File Name is same as Output File Name")
        print("       Use -output option to modify the output file name")
        sys.exit(1)

    print(("  # Loading input file " + in_file))

    ############################################################################
    # Loading python files if any
    ############################################################################
    if python_files is not None:
        for c_py_file in python_files:
            print("  # Loading Python file", c_py_file)
            # exec(open(c_py_file).read())
            f = open(c_py_file, "r")
            exec(f.read())
            f.close()

    ############################################################################
    # Step: 1
    # =======
    # Parse #ifdef and work on only enabled code
    # Expand embedded python code output
    ############################################################################
    i_codegen = codegen(
        in_file,
        remove_code,
        incl_dirs,
        files,
        debug,
        debug_file,
        gen_dependencies,
        cmdline,
    )

    ############################################################################
    # Loading hash define variables
    ############################################################################
    if hash_define_vars is not None:
        for c_define_var in hash_define_vars:
            i_codegen.hash_def_proc(c_define_var)

    ############################################################################
    # Loading hash define files
    ############################################################################
    if hash_define_files is not None:
        for c_define_file in hash_define_files:
            i_codegen.load_hash_include_file(c_define_file)

    ############################################################################
    # Calling code generation function
    ############################################################################
    i_codegen.generate_code(module_name)

    stub_override_val = i_codegen.stub_override_val

    parse_lines = []
    parse_lines = list(i_codegen.lines)

    # Adding empty lines to flush remaining appended code to be parsed
    parse_lines.append("\n\n\n\n\n\n\n\n\n\n")

    ############################################################################
    # Wrting out temporary_file for debug
    # TODO: Need to enable dumping when error or debug mode enabled
    ############################################################################
    temp_file = open(temporary_file, "w")

    for line in parse_lines:
        line = line.rstrip()
        temp_file.write(line + "\n")

    ############################################################################
    # Creating verilog_parser object to parse the generated code
    ############################################################################
    i_verilog_parser = verilog_parser(
        module_name,
        parse_lines,
        incl_dirs,
        files,
        package_files,
        i_codegen.hash_defines,
        parsing_format,
        debug,
        debug_file,
        disable_tick_ifdefs,
        verilog_define_files,
        i_codegen.functions_list,
        profiling,
        profiling_file,
        cmdline,
    )
    i_verilog_parser.parse_verilog()

    dependencies = {}
    dependencies = i_verilog_parser.dependencies

    if gen_dependencies:
        # dependencies['header_files'] = i_codegen.header_files
        for header_file in i_codegen.header_files:
            dependencies["header_files"].append(
                {header_file: {"mtime": getmtime(header_file)}}
            )

    regs = i_verilog_parser.regs
    wires = i_verilog_parser.wires
    signals = i_verilog_parser.signals
    ports = i_verilog_parser.ports
    typedef_structs = i_verilog_parser.typedef_structs
    typedef_unions = i_verilog_parser.typedef_unions
    typedef_logics = i_verilog_parser.typedef_logics
    typedef_bindings = i_verilog_parser.typedef_bindings
    functions_list = i_verilog_parser.functions_list
    params = i_verilog_parser.params
    sub_inst_ports = i_verilog_parser.sub_inst_ports
    sub_inst_params = i_verilog_parser.sub_inst_params
    tick_defines = i_verilog_parser.tick_defines
    auto_reset_data = i_verilog_parser.auto_reset_data
    force_internals = i_verilog_parser.force_internals
    force_widths = i_verilog_parser.force_widths
    module_found = i_verilog_parser.module_found
    module_param_line = i_verilog_parser.module_param_line
    sub_inst_files = i_verilog_parser.sub_inst_files
    filelist = i_verilog_parser.filelist
    pkg2assign_info = i_verilog_parser.pkg2assign_info
    assign2pkg_info = i_verilog_parser.assign2pkg_info
    manual_ports = i_verilog_parser.manual_ports

    pkg2assign_index = 0
    assign2pkg_index = 0

    if i_verilog_parser.found_error:
        print("Error: Found errors during verilog/system verilog parsing.")
        sys.exit(1)

    if gen_dependencies:
        out_file = open(output_file, "w")
        out_file.write(json.dumps(dependencies, indent=2))
        dbg(debug, json.dumps(dependencies, indent=2))

        # Closing the debug dump file if debug is on
        if debug:
            dbg_file.close()
            print(("  # Generated debug file " + debug_file))
        else:
            if not found_error:
                if os.path.isfile(temporary_file):
                    os.remove(temporary_file)

                if os.path.isfile(debug_file):
                    if os.path.isfile(debug_file):
                        os.remove(debug_file)

                    if os.path.isfile(debug_file + ".codegen"):
                        os.remove(debug_file + ".codegen")

                    if os.path.isfile(debug_file + ".parser"):
                        os.remove(debug_file + ".parser")

                    if os.path.isfile(debug_file + ".write"):
                        os.remove(debug_file + ".write")
            else:
                print(("  # Generated expanded input .pv/psv file " + temporary_file))

                if debug:
                    print(("  # Generated debug file " + debug_file))

        if found_error:
            print(("  # Generated " + output_file + " with Errors"))
            print("\nError: Please review the run log for errors\n")
            sys.exit(1)
        else:
            print(("  # Successfully generated " + output_file + "\n"))

        out_file.close()
        temp_file.close()
        sys.exit(0)

    ############################################################################
    # Printing all the gathered registers
    ############################################################################
    # dbg(debug,"\n\n#########################################################")
    dbg(debug, "# All the gathered registers")
    dbg(debug, "#########################################################")
    dbg(debug, json.dumps(regs, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered wires
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered wires")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(wires, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered signals
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered signals")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(signals, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the inputs and outputs
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the inputs and outputs")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(ports, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered structs
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered structs")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(typedef_structs, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered unions
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered unions")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(typedef_unions, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered logics
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered logics")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(typedef_logics, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered typedef bindings
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered typedef bindings")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(typedef_bindings, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered functions
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered functions")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(functions_list, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the parameters
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered parameters")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(params, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the parameters
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered `defines")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(tick_defines, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the gathered auto reset signals and values
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the gathered auto reset signals and values")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(auto_reset_data, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Updating the bitdef between signals and wire/regs
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Updating the bitdef between signals and wire/regs")
    dbg(debug, "##############################################################")
    # TODO: May have to add some warnings if the register width is less
    # than the signal width
    for c_signal in signals:
        if c_signal in list(regs.keys()):  # Keep the biggest bitdef for regs
            # Keep the highest
            if regs[c_signal]["mode"] != "FORCE":
                if int(signals[c_signal]["uwidth"]) > int(regs[c_signal]["uwidth"]):
                    regs[c_signal]["uwidth"] = signals[c_signal]["uwidth"]
                    reg_bitdef_colon_regex = re.search(
                        RE_COLON, regs[c_signal]["bitdef"]
                    )
                    signal_bitdef_colon_regex = re.search(
                        RE_COLON, signals[c_signal]["bitdef"]
                    )

                    # Update bitdef with bitdef only if its broken with :
                    if reg_bitdef_colon_regex and signal_bitdef_colon_regex:
                        regs[c_signal]["bitdef"] = (
                            signal_bitdef_colon_regex.group(1)
                            + ":"
                            + reg_bitdef_colon_regex.group(2)
                        )
                        dbg(
                            debug,
                            "  # Updated U_BITDEF REG: "
                            + c_signal
                            + " :: "
                            + regs[c_signal]["bitdef"],
                        )
                    else:  # Otherwise use the uwdith and lwidth for bitdef
                        regs[c_signal]["bitdef"] = (
                            str(signals[c_signal]["uwidth"])
                            + ":"
                            + str(regs[c_signal]["lwidth"])
                        )
                        dbg(
                            debug,
                            "  # Updated U_BITDEF (NUM) REG: "
                            + c_signal
                            + " :: "
                            + regs[c_signal]["bitdef"],
                        )

                # Keep the lowest
                if int(signals[c_signal]["lwidth"]) < int(regs[c_signal]["lwidth"]):
                    regs[c_signal]["lwidth"] = signals[c_signal]["lwidth"]
                    reg_bitdef_colon_regex = re.search(
                        RE_COLON, regs[c_signal]["bitdef"]
                    )
                    signal_bitdef_colon_regex = re.search(
                        RE_COLON, signals[c_signal]["bitdef"]
                    )

                    if reg_bitdef_colon_regex and signal_bitdef_colon_regex:
                        regs[c_signal]["bitdef"] = (
                            reg_bitdef_colon_regex.group(1)
                            + ":"
                            + signal_bitdef_colon_regex.group(2)
                        )
                        dbg(
                            debug,
                            "  # Updated L_BITDEF REG: "
                            + c_signal
                            + " :: "
                            + regs[c_signal]["bitdef"],
                        )
                    else:
                        regs[c_signal]["bitdef"] = (
                            str(regs[c_signal]["uwidth"])
                            + ":"
                            + str(signals[c_signal]["lwidth"])
                        )
                        dbg(
                            debug,
                            "  # Updated L_BITDEF (NUM) REG: "
                            + c_signal
                            + " :: "
                            + regs[c_signal]["bitdef"],
                        )

        if c_signal in list(wires.keys()):  # Keep the biggest bitdef for wires
            # Keep the highest
            if wires[c_signal]["mode"] != "FORCE":
                if int(signals[c_signal]["uwidth"]) > int(wires[c_signal]["uwidth"]):
                    wires[c_signal]["uwidth"] = signals[c_signal]["uwidth"]
                    wire_bitdef_colon_regex = re.search(
                        RE_COLON, wires[c_signal]["bitdef"]
                    )
                    signal_bitdef_colon_regex = re.search(
                        RE_COLON, signals[c_signal]["bitdef"]
                    )

                    # Update bitdef with bitdef only if its broken with :
                    if wire_bitdef_colon_regex and signal_bitdef_colon_regex:
                        wires[c_signal]["bitdef"] = (
                            signal_bitdef_colon_regex.group(1)
                            + ":"
                            + wire_bitdef_colon_regex.group(2)
                        )
                        dbg(
                            debug,
                            "  # Updated U_BITDEF WIRE: "
                            + c_signal
                            + " :: "
                            + wires[c_signal]["bitdef"],
                        )
                    else:  # Otherwise use the uwdith and lwidth for bitdef
                        wires[c_signal]["bitdef"] = (
                            str(signals[c_signal]["uwidth"])
                            + ":"
                            + str(wires[c_signal]["lwidth"])
                        )
                        dbg(
                            debug,
                            "  # Updated U_BITDEF (NUM) WIRE: "
                            + c_signal
                            + " :: "
                            + wires[c_signal]["bitdef"],
                        )

                # Keep the lowest
                if int(signals[c_signal]["lwidth"]) < int(wires[c_signal]["lwidth"]):
                    wires[c_signal]["lwidth"] = signals[c_signal]["lwidth"]
                    wire_bitdef_colon_regex = re.search(
                        RE_COLON, wires[c_signal]["bitdef"]
                    )
                    signal_bitdef_colon_regex = re.search(
                        RE_COLON, signals[c_signal]["bitdef"]
                    )

                    if wire_bitdef_colon_regex and signal_bitdef_colon_regex:
                        wires[c_signal]["bitdef"] = (
                            wire_bitdef_colon_regex.group(1)
                            + ":"
                            + signal_bitdef_colon_regex.group(2)
                        )
                        dbg(
                            debug,
                            "  # Updated L_BITDEF WIRE: "
                            + c_signal
                            + " :: "
                            + wires[c_signal]["bitdef"],
                        )
                    else:
                        wires[c_signal]["bitdef"] = (
                            str(wires[c_signal]["uwidth"])
                            + ":"
                            + str(signals[c_signal]["lwidth"])
                        )
                        dbg(
                            debug,
                            "  # Updated L_BITDEF (NUM) WIRE: "
                            + c_signal
                            + " :: "
                            + wires[c_signal]["bitdef"],
                        )

    dbg(debug, "\n")

    ############################################################################
    # Checking all the signals with regs and wires and update input ports
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Checking all the signals with regs and wires and update ports")
    dbg(debug, "##############################################################")
    for c_signal in list(signals.keys()):
        dbg(
            debug,
            "# "
            + signals[c_signal]["name"]
            + " :: "
            + signals[c_signal]["mode"]
            + " :: "
            + signals[c_signal]["bitdef"]
            + " :: "
            + str(signals[c_signal]["uwidth"])
            + " :: "
            + str(signals[c_signal]["lwidth"])
            + " :: "
            + str(signals[c_signal]["depth"])
            + " ::",
        )

        signal_found = 0

        # Check if its locally generated as a reg/logic
        if c_signal in regs:
            signal_found = 1

        # Check if its locally generated as a wire
        if c_signal in wires:
            signal_found = 1

        if signal_found:
            signals[c_signal]["type"] = "LOCAL"
        else:
            if c_signal in ports:
                dbg(
                    debug,
                    "  # SKIP PORT :: "
                    + ports[c_signal]["name"]
                    + " :: "
                    + ports[c_signal]["dir"]
                    + " :: "
                    + " :: "
                    + ports[c_signal]["mode"]
                    + " :: "
                    + ports[c_signal]["typedef"]
                    + " :: "
                    + ports[c_signal]["bitdef"]
                    + " :: "
                    + str(ports[c_signal]["uwidth"])
                    + " :: "
                    + str(ports[c_signal]["lwidth"])
                    + " :: "
                    + str(ports[c_signal]["depth"])
                    + " ::",
                )
            else:
                # Move this signal to input port
                ports[c_signal] = {}
                ports[c_signal]["name"] = signals[c_signal]["name"]
                ports[c_signal]["dir"] = "input"
                ports[c_signal]["depth"] = signals[c_signal]["depth"]
                ports[c_signal]["lwidth"] = signals[c_signal]["lwidth"]
                ports[c_signal]["bitdef"] = signals[c_signal]["bitdef"]
                ports[c_signal]["uwidth"] = signals[c_signal]["uwidth"]
                ports[c_signal]["mode"] = signals[c_signal]["mode"]
                ports[c_signal]["signed"] = ""

                if c_signal in typedef_bindings:
                    if typedef_bindings[c_signal]["packed"] == "":
                        ports[c_signal]["typedef"] = (
                            "TYPEDEF_" + typedef_bindings[c_signal]["type"]
                        )
                        ports[c_signal]["depth"] = typedef_bindings[c_signal]["depth"]
                    else:
                        ports[c_signal]["typedef"] = (
                            "TYPEDEF_" + typedef_bindings[c_signal]["type"]
                        )
                        ports[c_signal]["bitdef"] = typedef_bindings[c_signal]["packed"]
                else:
                    ports[c_signal]["typedef"] = ""

                dbg(
                    debug,
                    "  # NEW  PORT :: "
                    + ports[c_signal]["name"]
                    + " :: "
                    + ports[c_signal]["dir"]
                    + " :: "
                    + " :: "
                    + ports[c_signal]["mode"]
                    + " :: "
                    + ports[c_signal]["typedef"]
                    + " :: "
                    + ports[c_signal]["bitdef"]
                    + " :: "
                    + str(ports[c_signal]["uwidth"])
                    + " :: "
                    + str(ports[c_signal]["lwidth"])
                    + " :: "
                    + str(ports[c_signal]["depth"])
                    + " ::",
                )

            # Deleting the signal from the list
            del signals[c_signal]

    dbg(debug, "\n")

    ############################################################################
    # Checking all the reg/logics with signals and update output ports
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Checking all the regs/logics with signals and update ports")
    dbg(debug, "##############################################################")
    for c_reg in list(regs.keys()):
        dbg(
            debug,
            "# "
            + regs[c_reg]["name"]
            + " :: "
            + regs[c_reg]["mode"]
            + " :: "
            + regs[c_reg]["bitdef"]
            + " :: "
            + str(regs[c_reg]["uwidth"])
            + " :: "
            + str(regs[c_reg]["lwidth"])
            + " :: "
            + str(regs[c_reg]["depth"])
            + " ::",
        )

        signal_found = 0
        # Check if its locally generated as a reg/logic
        if c_reg in signals:
            regs[c_reg]["type"] = "LOCAL"
        else:
            if c_reg in ports:
                dbg(
                    debug,
                    "  # SKIP PORT :: "
                    + ports[c_reg]["name"]
                    + " :: "
                    + ports[c_reg]["dir"]
                    + " :: "
                    + " :: "
                    + ports[c_reg]["mode"]
                    + " :: "
                    + ports[c_reg]["typedef"]
                    + " :: "
                    + ports[c_reg]["bitdef"]
                    + " :: "
                    + str(ports[c_reg]["uwidth"])
                    + " :: "
                    + str(ports[c_reg]["lwidth"])
                    + " :: "
                    + str(ports[c_reg]["depth"])
                    + " ::",
                )
                regs[c_reg]["type"] = "PORT"
            else:
                # Move this signal to input port
                if regs[c_reg]["mode"] == "MANUAL" or regs[c_reg]["mode"] == "FORCE":
                    pass
                else:
                    ports[c_reg] = {}
                    ports[c_reg]["name"] = regs[c_reg]["name"]
                    ports[c_reg]["dir"] = "output"
                    ports[c_reg]["depth"] = regs[c_reg]["depth"]
                    ports[c_reg]["lwidth"] = regs[c_reg]["lwidth"]
                    ports[c_reg]["bitdef"] = regs[c_reg]["bitdef"]
                    ports[c_reg]["uwidth"] = regs[c_reg]["uwidth"]
                    ports[c_reg]["mode"] = "AUTO"
                    ports[c_reg]["signed"] = regs[c_reg]["signed"]
                    regs[c_reg]["type"] = "PORT"

                    if c_reg in typedef_bindings:
                        if typedef_bindings[c_reg]["packed"] == "":
                            ports[c_reg]["typedef"] = (
                                "TYPEDEF_" + typedef_bindings[c_reg]["type"]
                            )
                            ports[c_reg]["depth"] = typedef_bindings[c_reg]["depth"]
                        else:
                            ports[c_reg]["typedef"] = (
                                "TYPEDEF_" + typedef_bindings[c_reg]["type"]
                            )
                            ports[c_reg]["bitdef"] = typedef_bindings[c_reg]["packed"]
                    else:
                        ports[c_reg]["typedef"] = "REG"

                    dbg(
                        debug,
                        "  # NEW  PORT :: "
                        + ports[c_reg]["name"]
                        + " :: "
                        + ports[c_reg]["dir"]
                        + " :: "
                        + " :: "
                        + ports[c_reg]["mode"]
                        + " :: "
                        + ports[c_reg]["typedef"]
                        + " :: "
                        + ports[c_reg]["bitdef"]
                        + " :: "
                        + str(ports[c_reg]["uwidth"])
                        + " :: "
                        + str(ports[c_reg]["lwidth"])
                        + " :: "
                        + str(ports[c_reg]["depth"])
                        + " ::",
                    )

    dbg(debug, "\n")

    ############################################################################
    # Checking all the wires with signals and update output ports
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Checking all the wires with signals and update ports")
    dbg(debug, "##############################################################")
    for c_wire in wires:
        dbg(
            debug,
            "# "
            + wires[c_wire]["name"]
            + " :: "
            + wires[c_wire]["mode"]
            + " :: "
            + wires[c_wire]["bitdef"]
            + " :: "
            + str(wires[c_wire]["uwidth"])
            + " :: "
            + str(wires[c_wire]["lwidth"])
            + " :: "
            + str(wires[c_wire]["depth"])
            + " ::",
        )

        signal_found = 0

        # Check if its locally generated as a reg/logic
        if c_wire in list(signals.keys()):
            wires[c_wire]["type"] = "LOCAL"
        else:
            if c_wire in ports:
                dbg(
                    debug,
                    "  # SKIP PORT :: "
                    + ports[c_wire]["name"]
                    + " :: "
                    + ports[c_wire]["dir"]
                    + " :: "
                    + " :: "
                    + ports[c_wire]["mode"]
                    + " :: "
                    + ports[c_wire]["typedef"]
                    + " :: "
                    + ports[c_wire]["bitdef"]
                    + " :: "
                    + str(ports[c_wire]["uwidth"])
                    + " :: "
                    + str(ports[c_wire]["lwidth"])
                    + " :: "
                    + str(ports[c_wire]["depth"])
                    + " ::",
                )
                wires[c_wire]["type"] = "PORT"
            else:
                # Move this signal to input port
                if (
                    wires[c_wire]["mode"] == "MANUAL"
                    or wires[c_wire]["mode"] == "FORCE"
                ):
                    pass
                else:
                    ports[c_wire] = {}
                    ports[c_wire]["name"] = wires[c_wire]["name"]
                    ports[c_wire]["dir"] = "output"
                    ports[c_wire]["depth"] = wires[c_wire]["depth"]
                    ports[c_wire]["lwidth"] = wires[c_wire]["lwidth"]
                    ports[c_wire]["bitdef"] = wires[c_wire]["bitdef"]
                    ports[c_wire]["uwidth"] = wires[c_wire]["uwidth"]
                    ports[c_wire]["mode"] = "AUTO"
                    ports[c_wire]["signed"] = wires[c_wire]["signed"]
                    wires[c_wire]["type"] = "PORT"

                    if c_wire in typedef_bindings:
                        if typedef_bindings[c_wire]["packed"] == "":
                            ports[c_wire]["typedef"] = (
                                "TYPEDEF_" + typedef_bindings[c_wire]["type"]
                            )
                            ports[c_wire]["depth"] = typedef_bindings[c_wire]["depth"]
                        else:
                            ports[c_wire]["typedef"] = (
                                "TYPEDEF_" + typedef_bindings[c_wire]["type"]
                            )
                            ports[c_wire]["bitdef"] = typedef_bindings[c_wire]["packed"]
                    else:
                        ports[c_wire]["typedef"] = "WIRE"

                    dbg(
                        debug,
                        "  # NEW  PORT :: "
                        + ports[c_wire]["name"]
                        + " :: "
                        + ports[c_wire]["dir"]
                        + " :: "
                        + " :: "
                        + ports[c_wire]["mode"]
                        + " :: "
                        + ports[c_wire]["typedef"]
                        + " :: "
                        + ports[c_wire]["bitdef"]
                        + " :: "
                        + str(ports[c_wire]["uwidth"])
                        + " :: "
                        + str(ports[c_wire]["lwidth"])
                        + " :: "
                        + str(ports[c_wire]["depth"])
                        + " ::",
                    )

    dbg(debug, "\n")

    ############################################################################
    # Applying any force internal commands
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Applying any force internal commands")
    dbg(debug, "##############################################################")
    for c_internal in force_internals:
        c_internal = re.sub(r";", r"", c_internal)
        c_internal = re.sub(r"\s+", r" ", c_internal)
        c_internal = re.sub(r"\s*$", r"", c_internal)
        c_internal = re.sub(r"^\s*", r"", c_internal)
        dbg(debug, "\n### FORCE INTERNAL: " + c_internal)
        force_internal_slash_regex = re.search(RE_REGEX_SLASH, c_internal)

        if force_internal_slash_regex:
            regex_width = force_internal_slash_regex.group(1)
        else:
            regex_width = ""

        RE_FORCE_REGEX = re.compile(regex_width)

        for c_port in list(ports.keys()):
            dbg(debug, "  # PORT: " + ports[c_port]["dir"] + " :: " + c_port)

            match_found = 0

            if regex_width != "":
                force_internal_slash_regex = re.search(RE_FORCE_REGEX, c_port)

                if force_internal_slash_regex:
                    if ports[c_port]["dir"] == "output":
                        match_found = 1
            else:
                if c_internal == c_port:
                    if ports[c_port]["dir"] == "output":
                        match_found = 1

            if match_found:  # move the port to reg/wire declarations
                dbg(debug, "    # MATCHED PORT: " + c_port + " :: " + c_internal)

                if ports[c_port]["typedef"] == "REG":
                    if c_port in regs:
                        regs[c_port]["type"] = "LOCAL"
                    else:
                        regs[c_port]["type"] = "LOCAL"

                    dbg(
                        debug,
                        "    # REG :: "
                        + regs[c_port]["name"]
                        + " # "
                        + regs[c_port]["mode"]
                        + " # "
                        + regs[c_port]["type"]
                        + " # "
                        + regs[c_port]["bitdef"]
                        + " # "
                        + str(regs[c_port]["uwidth"])
                        + " # "
                        + str(regs[c_port]["lwidth"])
                        + " # "
                        + str(regs[c_port]["depth"]),
                    )
                elif ports[c_port]["typedef"] == "WIRE":
                    if c_port in wires:
                        wires[c_port]["type"] = "LOCAL"
                    else:
                        wires[c_port]["type"] = "LOCAL"

                    dbg(
                        debug,
                        "    # WIRE :: "
                        + wires[c_port]["name"]
                        + " # "
                        + wires[c_port]["mode"]
                        + " # "
                        + wires[c_port]["type"]
                        + " # "
                        + wires[c_port]["bitdef"]
                        + " # "
                        + str(wires[c_port]["uwidth"])
                        + " # "
                        + str(wires[c_port]["lwidth"])
                        + " # "
                        + str(wires[c_port]["depth"]),
                    )
                elif (
                    ports[c_port]["typedef"] == "TYPEDEF_STRUCTS"
                    or ports[c_port]["typedef"] == "TYPEDEF_STRUCT"
                    or ports[c_port]["typedef"] == "TYPEDEF_UNIONS"
                    or ports[c_port]["typedef"] == "TYPEDEF_UNION"
                    or ports[c_port]["typedef"] == "TYPEDEF_LOGICS"
                    or ports[c_port]["typedef"] == "TYPEDEF_LOGIC"
                ):

                    # If the port is found in wires, then make it local wire
                    # for declaration
                    if c_port in wires:
                        wires[c_port]["type"] = "LOCAL"

                    # If the port is found in regs, then make it local reg
                    # for declaration
                    if c_port in regs:
                        regs[c_port]["type"] = "LOCAL"

                # Deleting the port from the list
                del ports[c_port]

    dbg(debug, "\n")

    ############################################################################
    # Applying any force width commands
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Applying any force width commands")
    dbg(debug, "##############################################################")
    for c_width in force_widths:
        c_width = re.sub(r";", r"", c_width)
        c_width = re.sub(r"\s+", r" ", c_width)
        c_width = re.sub(r"\s*$", r"", c_width)
        c_width = re.sub(r"^\s*", r"", c_width)
        dbg(debug, "### WIDTH: " + c_width)

        force_bitdef = ""
        force_uwdith = ""
        force_lwdith = ""
        force_width_split = c_width.split(" ")

        force_name = force_width_split[0]
        force_width = force_width_split[1]

        width_numbers_regex = re.search(RE_NUMBERS, force_width)

        if width_numbers_regex:
            force_uwdith = int(force_width) - 1
            force_lwdith = 0
            force_bitdef = str(force_uwdith) + ":" + str(force_lwdith)
        else:
            # calculating numerical value if its not a number
            force_width_val = i_verilog_parser.tickdef_param_getval(
                "TOP", force_width, "", ""
            )

            if force_width_val[0] == "STRING":
                force_bitdef = force_width + "-1:0"
            else:
                force_uwdith = force_width_val[1] - 1
                force_lwdith = 0
                force_bitdef = force_width + "-1:0"

        force_width_slash_regex = re.search(RE_REGEX_SLASH, force_name)

        if force_width_slash_regex:
            regex_width = force_width_slash_regex.group(1)
        else:
            regex_width = ""

        # Updating ports if match found
        for c_port in list(ports.keys()):
            match_found = 0

            RE_FORCE_REGEX = re.compile(regex_width)
            if regex_width != "":
                force_width_slash_regex = re.search(RE_FORCE_REGEX, c_port)

                if force_width_slash_regex:
                    match_found = 1
            else:
                if force_name == c_port:
                    dbg(debug, "  # REG : " + c_port + " :: " + force_name + " :: ")
                    match_found = 1

            if match_found:
                ports[c_port]["bitdef"] = force_bitdef
                ports[c_port]["uwidth"] = force_uwdith
                ports[c_port]["lwidth"] = force_lwdith
                dbg(
                    debug,
                    "    # FORCE REG WIDTH :: "
                    + ports[c_port]["name"]
                    + " # "
                    + ports[c_port]["mode"]
                    + " # "
                    + ports[c_port]["bitdef"]
                    + " # "
                    + str(ports[c_port]["uwidth"])
                    + " # "
                    + str(ports[c_port]["lwidth"])
                    + " # "
                    + str(ports[c_port]["depth"]),
                )

        # Updating regs if match found
        for c_reg in list(regs.keys()):
            match_found = 0

            RE_FORCE_REGEX = re.compile(regex_width)

            if regex_width != "":
                force_width_slash_regex = re.search(RE_FORCE_REGEX, c_reg)

                if force_width_slash_regex:
                    match_found = 1
            else:
                if force_name == c_reg:
                    dbg(debug, "  # REG : " + c_reg + " :: " + force_name + " :: ")
                    match_found = 1

            if match_found:
                regs[c_reg]["bitdef"] = force_bitdef
                regs[c_reg]["uwidth"] = force_uwdith
                regs[c_reg]["lwidth"] = force_lwdith
                dbg(
                    debug,
                    "    # FORCE REG WIDTH :: "
                    + regs[c_reg]["name"]
                    + " # "
                    + regs[c_reg]["mode"]
                    + " # "
                    + regs[c_reg]["bitdef"]
                    + " # "
                    + str(regs[c_reg]["uwidth"])
                    + " # "
                    + str(regs[c_reg]["lwidth"])
                    + " # "
                    + str(regs[c_reg]["depth"]),
                )

        # Updating wires if match found
        for c_wire in list(wires.keys()):
            match_found = 0

            RE_FORCE_REGEX = re.compile(regex_width)

            if regex_width != "":
                force_width_slash_regex = re.search(RE_FORCE_REGEX, c_wire)

                if force_width_slash_regex:
                    match_found = 1
            else:
                if force_name == c_wire:
                    dbg(debug, "  # REG : " + c_wire + " :: " + force_name + " :: ")
                    match_found = 1

            if match_found:
                wires[c_wire]["bitdef"] = force_bitdef
                wires[c_wire]["uwidth"] = force_uwdith
                wires[c_wire]["lwidth"] = force_lwdith
                dbg(
                    debug,
                    "    # FORCE WIRE WIDTH :: "
                    + wires[c_wire]["name"]
                    + " # "
                    + wires[c_wire]["mode"]
                    + " # "
                    + wires[c_wire]["bitdef"]
                    + " # "
                    + str(wires[c_wire]["uwidth"])
                    + " # "
                    + str(wires[c_wire]["lwidth"])
                    + " # "
                    + str(wires[c_wire]["depth"]),
                )

    dbg(debug, "\n")

    ############################################################################
    # Remove if port is duplicated in wire/regs/signals
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# Remove if port is duplicated in wire/regs/signals")
    dbg(debug, "##############################################################")
    for c_port in list(ports.keys()):
        if c_port in wires:
            del wires[c_port]

        if c_port in regs:
            del regs[c_port]

        if c_port in signals:
            del signals[c_port]

    dbg(debug, "\n")

    ############################################################################
    # Printing all the Final registers
    ############################################################################
    dbg(debug, "\n\n##########################################################")
    dbg(debug, "# All the Final registers")
    dbg(debug, "##########################################################")
    dbg(debug, json.dumps(regs, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the Final wires
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the Final wires")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(wires, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the Final signals
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the Final signals")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(signals, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Printing all the Final inputs and outputs
    ############################################################################
    dbg(debug, "##############################################################")
    dbg(debug, "# All the Final inputs and outputs")
    dbg(debug, "##############################################################")
    dbg(debug, json.dumps(ports, indent=2))
    dbg(debug, "\n")

    ############################################################################
    # Step: 3
    # =======
    # Generated all the input/output/wire/reg declarations
    # Expand post embedded python code output
    ############################################################################
    print(("  # Generating verilog/systemverilog output file " + output_file))

    skip_auto_reset_line = 0
    remove_reset_val = 0
    auto_reset_index = 0
    gendrive_space = ""
    line_no = 0
    block_comment = 0
    look_for_instance_cmds = 0
    endmodule_found = 0
    generate_endmodule = 0
    gather_till_semicolon = 0
    prev_line = ""

    out_file = open(output_file, "w")

    dbg(debug, "\n############################################################")
    dbg(debug, "### Generating verilog/systemverilog file")
    dbg(debug, "############################################################")

    doing_python = 0

    for line in i_codegen.lines:
        line_no = line_no + 1

        # Remove space in the end
        line = line.rstrip()

        if remove_reset_val:
            line = re.sub(r"<[s0-9A-Za-z\'_]+=", r"<=", line)

        original_line = line

        ########################################################################
        # if the whole line is commented from the beginning
        ########################################################################
        single_comment_begin_start_regex = re.search(
            RE_SINGLE_COMMENT_BEGIN_START, line
        )
        if single_comment_begin_start_regex:
            out_file.write(original_line + "\n")
            dbg(debug, original_line)
            continue

        ########################################################################
        # Block comment skip
        ########################################################################
        block_comment_begin_start_regex = re.search(RE_BLOCK_COMMENT_BEGIN_START, line)
        block_comment_begin_regex = re.search(RE_BLOCK_COMMENT_BEGIN, line)
        block_comment_end_regex = re.search(RE_BLOCK_COMMENT_END, line)

        if block_comment_end_regex:
            block_comment = 0
            out_file.write(original_line + "\n")
            dbg(debug, original_line)
            continue

        if block_comment:
            out_file.write(original_line + "\n")
            dbg(debug, original_line)
            continue

        if block_comment_begin_start_regex:
            block_comment = 1
            out_file.write(original_line + "\n")
            dbg(debug, original_line)
            continue
        elif block_comment_begin_regex:
            block_comment = 1

        if gather_till_semicolon:
            semicolon_regex = re.search(RE_SEMICOLON, line)
            line = prev_line + " " + line
            gather_till_semicolon = 0

        ########################################################################
        # Stub generation from a verilog file where commands are commented out
        ########################################################################
        if generate_stub:
            gendrivez_verilog_regex = re.search(RE_GENDRIVEZ_VERILOG, line)
            gendrive0_verilog_regex = re.search(RE_GENDRIVE0_VERILOG, line)
            gendrive0andz_verilog_regex = re.search(RE_GENDRIVE0ANDZ_VERILOG, line)

            if gendrivez_verilog_regex:
                out_file.write(line + "\n")
                dbg(debug, line)

                for c_port in ports:
                    if (
                        ports[c_port]["dir"] == "output"
                        and ports[c_port]["mode"] == "MANUAL"
                    ):
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrivez_verilog_regex.group(1)
                                + "assign "
                                + ports[c_port]["name"]
                                + " = \
                                    {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrivez_verilog_regex.group(1)
                                + "assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)
                endmodule_found = 1
                break

            if gendrive0_verilog_regex:
                out_file.write(line + "\n")
                dbg(debug, line)

                for c_port in ports:
                    if (
                        ports[c_port]["dir"] == "output"
                        and ports[c_port]["mode"] == "MANUAL"
                    ):
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0_verilog_regex.group(1)
                                + "assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0_verilog_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0_verilog_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)
                endmodule_found = 1
                break

            if gendrive0andz_verilog_regex:
                generate_stub_z = 1
                generate_stub_0 = 1

                out_file.write(line + "\n")
                dbg(debug, line)

                print_line = (
                    gendrive0andz_verilog_regex.group(1)
                    + "`ifdef "
                    + module_name.upper()
                    + "_DRIVE_0"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if (
                        ports[c_port]["dir"] == "output"
                        and ports[c_port]["mode"] == "MANUAL"
                    ):
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0andz_verilog_regex.group(1)
                                + "  assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0andz_verilog_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0andz_verilog_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_verilog_regex.group(1) + "`else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = (
                    gendrive0andz_verilog_regex.group(1)
                    + "  `ifdef "
                    + module_name.upper()
                    + "_DRIVE_Z"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if (
                        ports[c_port]["dir"] == "output"
                        and ports[c_port]["mode"] == "MANUAL"
                    ):
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrive0andz_verilog_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrive0andz_verilog_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_verilog_regex.group(1) + "  `endif"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = gendrive0andz_verilog_regex.group(1) + "`endif"
                out_file.write(print_line + "\n\n")
                dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                endmodule_found = 1
                break

        if skip_auto_reset_line:
            skip_auto_reset_line = 0
            continue

        ########################################################################
        # Declare module definition if its called
        ########################################################################
        original_module_def_space_regex = re.search(RE_MODULE_DEF_SPACE, original_line)
        original_module_space_regex = re.search(RE_MODULE_SPACE, original_line)

        module_def_space_regex = re.search(RE_MODULE_DEF_SPACE, line)
        module_space_regex = re.search(RE_MODULE_SPACE, line)

        if not module_found:  # Check if the module declaration is already there
            if module_def_space_regex or module_space_regex:
                semicolon_regex = re.search(RE_SEMICOLON, line)

                if original_module_def_space_regex:
                    begin_space = original_module_def_space_regex.group(1)
                elif original_module_space_regex:
                    begin_space = original_module_space_regex.group(1)

                if semicolon_regex:
                    gather_till_semicolon = 0
                    generate_endmodule = 1

                    if original_module_def_space_regex or original_module_space_regex:
                        ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    else:
                        begin_space_regex = re.search(RE_BEGIN_SPACE, original_line)

                        if begin_space_regex:
                            ampersand_line = (
                                begin_space_regex.group(1)
                                + "//"
                                + begin_space_regex.group(2)
                            )
                        else:
                            ampersand_line = re.sub(r"^\s*", r"//", original_line, 1)
                            ampersand_line = begin_space + ampersand_line

                    out_file.write(ampersand_line + "\n")
                    dbg(debug, ampersand_line)

                    if module_def_space_regex:
                        module_param_line = ""
                        ii = 1
                        if len(i_verilog_parser.module_info["params"]) > 0:
                            module_param_line = "parameter "

                            for c_param in i_verilog_parser.module_info["params"]:
                                if ii == len(i_verilog_parser.module_info["params"]):
                                    module_param_line += c_param
                                else:
                                    module_param_line += c_param + ","

                                ii += 1
                else:
                    gather_till_semicolon = 1

                    if original_module_def_space_regex or original_module_space_regex:
                        ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    else:
                        begin_space_regex = re.search(RE_BEGIN_SPACE, original_line)

                        if begin_space_regex:
                            ampersand_line = (
                                begin_space_regex.group(1)
                                + "//"
                                + begin_space_regex.group(2)
                            )
                        else:
                            ampersand_line = re.sub(r"^\s*", r"//", original_line, 1)
                            ampersand_line = begin_space + ampersand_line

                    out_file.write(ampersand_line + "\n")
                    dbg(debug, ampersand_line)
                    prev_line = line
                    continue

                dbg(
                    debug,
                    "###################################################\
                           #############################",
                )
                dbg(debug, "# Generating Module Declaration")
                dbg(
                    debug,
                    "###################################################\
                           #############################",
                )

                port_declarations = []
                in_port_declarations = []
                out_port_declarations = []
                inout_port_declarations = []

                if sort_ios:
                    ports_list = sorted(ports.keys())
                else:
                    ports_list = ports

                for c_port in ports_list:
                    c_port_dir = ports[c_port]["dir"]
                    c_port_name = c_port
                    c_port_declare_type = "#"
                    c_port_bitdef = "#"
                    c_port_signed = "#"

                    if module_def_space_regex:
                        if ports[c_port]["mode"] != "SPEC":
                            found_error = 1
                            print(
                                (
                                    "Error: New port that is not part of the \
                                    module spec at "
                                    + module_name
                                )
                            )
                            dbg(
                                debug,
                                "Error: New port that is not part of the \
                                    module spec at "
                                + module_name,
                            )
                            if c_port_bitdef == "#":
                                print(("    " + c_port_dir + " " + c_port_name + ";"))
                                dbg(
                                    debug, "    " + c_port_dir + " " + c_port_name + ";"
                                )
                            else:
                                print(
                                    (
                                        "    "
                                        + c_port_dir
                                        + " "
                                        + c_port_bitdef
                                        + " "
                                        + c_port_name
                                        + ";"
                                    )
                                )
                                dbg(
                                    debug,
                                    "    "
                                    + c_port_dir
                                    + " "
                                    + c_port_bitdef
                                    + " "
                                    + c_port_name
                                    + ";",
                                )

                    if ports[c_port]["signed"] != "":
                        c_port_signed = ports[c_port]["signed"]

                    bitdef_has_typedef = 0
                    bitdef_typedef = ""

                    if (
                        ports[c_port]["typedef"] == "LOGIC"
                        or ports[c_port]["typedef"] == ""
                        or ports[c_port]["typedef"] == "TYPEDEF_LOGICS"
                        or ports[c_port]["typedef"] == "TYPEDEF_LOGIC"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCTS"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCT"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNIONS"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNION"
                    ):
                        curr_bitdef_package = "default"
                        curr_bitdef_class = "default"
                        curr_bitdef_typedef_regex = re.search(
                            RE_TYPEDEF_BEFORE_BITDEF, ports[c_port]["bitdef"]
                        )
                        curr_bitdef_typedef_double_regex = re.search(
                            RE_TYPEDEF_DOUBLE_COLON_BEFORE_BITDEF,
                            ports[c_port]["bitdef"],
                        )
                        curr_bitdef_typedef_double_double_regex = re.search(
                            RE_TYPEDEF_DOUBLE_DOUBLE_COLON_BEFORE_BITDEF,
                            ports[c_port]["bitdef"],
                        )

                        if curr_bitdef_typedef_double_double_regex:
                            bitdef_has_typedef = 1
                            bitdef_typedef = (
                                curr_bitdef_typedef_double_double_regex.group(1)
                                + "::"
                                + curr_bitdef_typedef_double_double_regex.group(2)
                                + "::"
                                + curr_bitdef_typedef_double_double_regex.group(3)
                            )
                            ports[c_port][
                                "bitdef"
                            ] = curr_bitdef_typedef_double_double_regex.group(4)
                        elif curr_bitdef_typedef_double_regex:
                            bitdef_has_typedef = 1
                            bitdef_typedef = (
                                curr_bitdef_typedef_double_regex.group(1)
                                + "::"
                                + curr_bitdef_typedef_double_regex.group(2)
                            )
                            ports[c_port][
                                "bitdef"
                            ] = curr_bitdef_typedef_double_regex.group(3)
                        elif curr_bitdef_typedef_regex:
                            if (
                                curr_bitdef_typedef_regex.group(1)
                                in typedef_logics[curr_bitdef_package][
                                    curr_bitdef_class
                                ]
                            ):
                                bitdef_has_typedef = 1
                                bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                                ports[c_port][
                                    "bitdef"
                                ] = curr_bitdef_typedef_regex.group(2)
                            elif (
                                curr_bitdef_typedef_regex.group(1)
                                in typedef_structs[curr_bitdef_package][
                                    curr_bitdef_class
                                ]
                            ):
                                bitdef_has_typedef = 1
                                bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                                ports[c_port][
                                    "bitdef"
                                ] = curr_bitdef_typedef_regex.group(2)
                            elif (
                                curr_bitdef_typedef_regex.group(1)
                                in typedef_unions[curr_bitdef_package][
                                    curr_bitdef_class
                                ]
                            ):
                                bitdef_has_typedef = 1
                                bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                                ports[c_port][
                                    "bitdef"
                                ] = curr_bitdef_typedef_regex.group(2)

                    if ports[c_port]["typedef"] == "LOGIC":
                        if bitdef_has_typedef:
                            c_port_declare_type = bitdef_typedef
                            c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                        else:
                            c_port_declare_type = "logic"

                            if ports[c_port]["bitdef"] != "":
                                c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                    elif ports[c_port]["typedef"] == "REG":
                        if parsing_format == "verilog":
                            c_port_declare_type = "reg"
                        else:
                            c_port_declare_type = "logic"

                        if ports[c_port]["bitdef"] != "":
                            c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                    elif ports[c_port]["typedef"] == "WIRE":
                        if parsing_format == "verilog":
                            c_port_declare_type = "wire"
                        else:
                            # TODO: May be declared as wire
                            c_port_declare_type = "logic"

                        if ports[c_port]["bitdef"] != "":
                            c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                    elif (
                        ports[c_port]["typedef"] == "TYPEDEF_LOGICS"
                        or ports[c_port]["typedef"] == "TYPEDEF_LOGIC"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCTS"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCT"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNIONS"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNION"
                    ):
                        if bitdef_has_typedef:
                            c_port_declare_type = bitdef_typedef
                            c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                        else:
                            c_port_declare_type = ports[c_port]["bitdef"]
                            c_port_bitdef = ""
                    else:
                        if parsing_format == "systemverilog":
                            if bitdef_has_typedef:
                                c_port_declare_type = bitdef_typedef
                                c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                            else:
                                c_port_declare_type = "logic"

                                if ports[c_port]["bitdef"] != "":
                                    c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                        else:
                            if ports[c_port]["bitdef"] == "":
                                c_port_bitdef = ""
                            else:
                                c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"

                    if ports[c_port]["depth"] != "":
                        c_port_name = c_port_name + "[" + ports[c_port]["depth"] + "]"

                    if group_ios_on_dir:
                        if c_port_dir == "input":
                            in_port_declarations.append(
                                c_port_dir
                                + ","
                                + c_port_declare_type
                                + ","
                                + c_port_signed
                                + ","
                                + c_port_bitdef
                                + ","
                                + c_port_name
                            )
                        elif c_port_dir == "inout":
                            inout_port_declarations.append(
                                c_port_dir
                                + ","
                                + c_port_declare_type
                                + ","
                                + c_port_signed
                                + ","
                                + c_port_bitdef
                                + ","
                                + c_port_name
                            )
                        else:
                            out_port_declarations.append(
                                c_port_dir
                                + ","
                                + c_port_declare_type
                                + ","
                                + c_port_signed
                                + ","
                                + c_port_bitdef
                                + ","
                                + c_port_name
                            )
                    else:
                        port_declarations.append(
                            c_port_dir
                            + ","
                            + c_port_declare_type
                            + ","
                            + c_port_signed
                            + ","
                            + c_port_bitdef
                            + ","
                            + c_port_name
                        )

                if module_param_line != "":
                    # module_param_line = \
                    #     re.sub(r',\s*parameter\s+', r',', module_param_line)
                    module_param_line = re.sub(r"\s*,\s*", r",", module_param_line)
                    module_param_line = re.sub(r"\s*=\s*", r" = ", module_param_line)
                    module_param_line = re.sub(r"^\s*", r"", module_param_line)
                    out_file.write(begin_space + "module " + module_name + " # (\n")
                    dbg(debug, begin_space + "module " + module_name + " (")
                    module_param_line_array = module_param_line.split(",")
                    module_param_line_array_len = len(module_param_line_array)

                    param_line_no = 1
                    for c_mod_param in module_param_line_array:
                        if param_line_no == 1:
                            if param_line_no == module_param_line_array_len:
                                out_file.write(begin_space + "  " + c_mod_param + "\n")
                                dbg(debug, begin_space + "  " + c_mod_param)
                            else:
                                out_file.write(begin_space + "  " + c_mod_param + ",\n")
                                dbg(debug, begin_space + "  " + c_mod_param + ",")
                        elif param_line_no == module_param_line_array_len:
                            out_file.write(
                                begin_space + "            " + c_mod_param + "\n"
                            )
                            dbg(debug, begin_space + "            " + c_mod_param)
                        else:
                            out_file.write(
                                begin_space + "            " + c_mod_param + ",\n"
                            )
                            dbg(debug, begin_space + "            " + c_mod_param + ",")

                        param_line_no = param_line_no + 1

                    out_file.write(begin_space + ") (\n")
                    dbg(debug, begin_space + ") (")
                else:
                    out_file.write(begin_space + "module " + module_name + " (\n")
                    dbg(debug, begin_space + "module " + module_name + " (")

                if group_ios_on_dir:
                    port_declarations = (
                        inout_port_declarations
                        + out_port_declarations
                        + in_port_declarations
                    )
                    port_declarations = indent_array(port_declarations, ",", "#")
                else:
                    port_declarations = indent_array(port_declarations, ",", "#")

                num_ports = len(port_declarations)

                for c_port in port_declarations:
                    if num_ports != 1:
                        out_file.write(begin_space + "  " + c_port + "," + "\n")
                        dbg(debug, begin_space + "#  " + c_port + ",")
                    else:
                        out_file.write(begin_space + "  " + c_port + "\n")
                        dbg(debug, begin_space + "#  " + c_port)

                    num_ports = num_ports - 1

                out_file.write(begin_space + "); \n")
                dbg(debug, begin_space + ");")

                continue

        ########################################################################
        # Declare ports definition if its called
        ########################################################################
        ports_regex = re.search(RE_PORTS, original_line)

        begin_space = ""

        if ports_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            begin_space = ports_regex.group(1)

            port_declarations = []
            in_port_declarations = []
            out_port_declarations = []

            if sort_ios:
                ports_list = sorted(ports.keys())
            else:
                ports_list = list(ports.keys())

            for c_port in ports_list:
                c_port_dir = ports[c_port]["dir"]
                c_port_name = c_port
                c_port_declare_type = "#"
                c_port_bitdef = "#"
                c_port_signed = "#"
                bitdef_has_typedef = 0

                if ports[c_port]["mode"] != "MANUAL":
                    if ports[c_port]["signed"] != "":
                        c_port_signed = ports[c_port]["signed"]

                    curr_bitdef_package = "default"
                    curr_bitdef_class = "default"
                    curr_bitdef_typedef_regex = re.search(
                        RE_TYPEDEF_BEFORE_BITDEF, ports[c_port]["bitdef"]
                    )
                    curr_bitdef_typedef_double_regex = re.search(
                        RE_TYPEDEF_DOUBLE_COLON_BEFORE_BITDEF, ports[c_port]["bitdef"]
                    )
                    curr_bitdef_typedef_double_double_regex = re.search(
                        RE_TYPEDEF_DOUBLE_DOUBLE_COLON_BEFORE_BITDEF,
                        ports[c_port]["bitdef"],
                    )

                    if curr_bitdef_typedef_double_double_regex:
                        bitdef_has_typedef = 1
                        bitdef_typedef = (
                            curr_bitdef_typedef_double_double_regex.group(1)
                            + "::"
                            + curr_bitdef_typedef_double_double_regex.group(2)
                            + "::"
                            + curr_bitdef_typedef_double_double_regex.group(3)
                        )
                        ports[c_port][
                            "bitdef"
                        ] = curr_bitdef_typedef_double_double_regex.group(4)
                    elif curr_bitdef_typedef_double_regex:
                        bitdef_has_typedef = 1
                        bitdef_typedef = (
                            curr_bitdef_typedef_double_regex.group(1)
                            + "::"
                            + curr_bitdef_typedef_double_regex.group(2)
                        )
                        ports[c_port][
                            "bitdef"
                        ] = curr_bitdef_typedef_double_regex.group(3)
                    elif curr_bitdef_typedef_regex:
                        if (
                            curr_bitdef_typedef_regex.group(1)
                            in typedef_logics[curr_bitdef_package][curr_bitdef_class]
                        ):
                            bitdef_has_typedef = 1
                            bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                            ports[c_port]["bitdef"] = curr_bitdef_typedef_regex.group(2)
                        elif (
                            curr_bitdef_typedef_regex.group(1)
                            in typedef_structs[curr_bitdef_package][curr_bitdef_class]
                        ):
                            bitdef_has_typedef = 1
                            bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                            ports[c_port]["bitdef"] = curr_bitdef_typedef_regex.group(2)
                        elif (
                            curr_bitdef_typedef_regex.group(1)
                            in typedef_unions[curr_bitdef_package][curr_bitdef_class]
                        ):
                            bitdef_has_typedef = 1
                            bitdef_typedef = curr_bitdef_typedef_regex.group(1)
                            ports[c_port]["bitdef"] = curr_bitdef_typedef_regex.group(2)

                    if ports[c_port]["typedef"] == "REG":
                        c_port_declare_type = "logic"
                        if ports[c_port]["bitdef"] != "":
                            c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                    elif (
                        ports[c_port]["typedef"] == "TYPEDEF_LOGICS"
                        or ports[c_port]["typedef"] == "TYPEDEF_LOGIC"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCTS"
                        or ports[c_port]["typedef"] == "TYPEDEF_STRUCT"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNIONS"
                        or ports[c_port]["typedef"] == "TYPEDEF_UNION"
                    ):
                        c_port_declare_type = ports[c_port]["bitdef"]
                    else:
                        if ports[c_port]["bitdef"] != "":
                            if bitdef_has_typedef:
                                c_port_declare_type = bitdef_typedef
                                c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                            else:
                                c_port_declare_type = "logic"
                                c_port_bitdef = "[" + ports[c_port]["bitdef"] + "]"
                        else:
                            c_port_declare_type = "logic"

                    if ports[c_port]["depth"] != "":
                        c_port_name = c_port_name + "[" + ports[c_port]["depth"] + "]"

                    if group_ios_on_dir:
                        if c_port_dir == "input":
                            in_port_declarations.append(
                                c_port_dir
                                + ","
                                + c_port_declare_type
                                + ","
                                + c_port_signed
                                + ","
                                + c_port_bitdef
                                + ","
                                + c_port_name
                            )
                        else:
                            out_port_declarations.append(
                                c_port_dir
                                + ","
                                + c_port_declare_type
                                + ","
                                + c_port_signed
                                + ","
                                + c_port_bitdef
                                + ","
                                + c_port_name
                            )
                    else:
                        port_declarations.append(
                            c_port_dir
                            + ","
                            + c_port_declare_type
                            + ","
                            + c_port_signed
                            + ","
                            + c_port_bitdef
                            + ","
                            + c_port_name
                        )

            if group_ios_on_dir:
                port_declarations = out_port_declarations + in_port_declarations
                port_declarations = indent_array(port_declarations, ",", "#")
            else:
                port_declarations = indent_array(port_declarations, ",", "#")

            port_declarations_size = len(port_declarations)
            c_port_index = 1

            for c_port in port_declarations:
                if manual_ports:
                    out_file.write(begin_space + c_port + ",\n")
                    dbg(debug, begin_space + c_port + ",")
                else:
                    if c_port_index == port_declarations_size:
                        out_file.write(begin_space + c_port + "\n")
                        dbg(debug, begin_space + c_port)
                    else:
                        out_file.write(begin_space + c_port + ",\n")
                        dbg(debug, begin_space + c_port + ",")

                c_port_index = c_port_index + 1

            continue

        ########################################################################
        # Declare regs/logic definition if its called
        ########################################################################
        regs_regex = re.search(RE_REGS, original_line)
        logics_regex = re.search(RE_LOGICS, original_line)

        begin_space = ""

        if regs_regex or logics_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            if logics_regex:
                begin_space = logics_regex.group(1)
            elif regs_regex:
                begin_space = regs_regex.group(1)

            reg_declarations = []
            binding_declarations = []

            if parsing_format == "verilog":
                c_reg_type = "reg"
            else:
                c_reg_type = "logic"

            for c_reg in list(regs.keys()):
                if (
                    regs[c_reg]["mode"] == "AUTO" and regs[c_reg]["type"] == "LOCAL"
                ) or regs[c_reg]["mode"] == "FORCE":
                    c_reg_name = c_reg
                    if regs[c_reg]["signed"] == "":
                        c_reg_signed = "#"
                    else:
                        c_reg_signed = regs[c_reg]["signed"]

                    c_reg_declare_type = "#"
                    c_reg_bitdef = "#"

                    if c_reg_name in typedef_bindings:
                        if typedef_bindings[c_reg]["packed"] != "":
                            c_reg_bdef_pkg = "default"
                            c_reg_bitdef_class = "default"
                            c_reg_bdef_tdef_regex = re.search(
                                RE_TYPEDEF_BEFORE_BITDEF,
                                typedef_bindings[c_reg]["packed"],
                            )
                            c_reg_bdef_tdef_dub_regex = re.search(
                                RE_TYPEDEF_DOUBLE_COLON_BEFORE_BITDEF,
                                typedef_bindings[c_reg]["packed"],
                            )
                            c_reg_bdef_tdef_dubdub_regex = re.search(
                                RE_TYPEDEF_DOUBLE_DOUBLE_COLON_BEFORE_BITDEF,
                                typedef_bindings[c_reg]["packed"],
                            )

                            if c_reg_bdef_tdef_dubdub_regex:
                                bitdef_has_typedef = 1
                                bitdef_typedef = (
                                    c_reg_bdef_tdef_dubdub_regex.group(1)
                                    + "::"
                                    + c_reg_bdef_tdef_dubdub_regex.group(2)
                                    + "::"
                                    + c_reg_bdef_tdef_dubdub_regex.group(3)
                                )
                                packed_bitdef = c_reg_bdef_tdef_dubdub_regex.group(4)
                            elif c_reg_bdef_tdef_dub_regex:
                                bitdef_has_typedef = 1
                                bitdef_typedef = (
                                    c_reg_bdef_tdef_dub_regex.group(1)
                                    + "::"
                                    + c_reg_bdef_tdef_dub_regex.group(2)
                                )
                                packed_bitdef = c_reg_bdef_tdef_dub_regex.group(3)
                            elif c_reg_bdef_tdef_regex:
                                if (
                                    c_reg_bdef_tdef_regex.group(1)
                                    in typedef_logics[c_reg_bdef_pkg][
                                        c_reg_bitdef_class
                                    ]
                                ):
                                    bitdef_has_typedef = 1
                                    bitdef_typedef = c_reg_bdef_tdef_regex.group(1)
                                    packed_bitdef = c_reg_bdef_tdef_regex.group(2)
                                elif (
                                    c_reg_bdef_tdef_regex.group(1)
                                    in typedef_structs[c_reg_bdef_pkg][
                                        c_reg_bitdef_class
                                    ]
                                ):
                                    bitdef_has_typedef = 1
                                    bitdef_typedef = c_reg_bdef_tdef_regex.group(1)
                                    packed_bitdef = c_reg_bdef_tdef_regex.group(2)
                                elif (
                                    c_reg_bdef_tdef_regex.group(1)
                                    in typedef_unions[c_reg_bdef_pkg][
                                        c_reg_bitdef_class
                                    ]
                                ):
                                    bitdef_has_typedef = 1
                                    bitdef_typedef = c_reg_bdef_tdef_regex.group(1)
                                    packed_bitdef = c_reg_bdef_tdef_regex.group(2)

                        if typedef_bindings[c_reg]["mode"] == "FORCE":
                            if typedef_bindings[c_reg]["package"] == "default":
                                if typedef_bindings[c_reg]["class"] == "default":
                                    if typedef_bindings[c_reg]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_reg]["typedef"]
                                            + ","
                                            + c_reg_name
                                            + " ["
                                            + typedef_bindings[c_reg]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            if bitdef_has_typedef:
                                                binding_declarations.append(
                                                    bitdef_typedef
                                                    + " ["
                                                    + packed_bitdef
                                                    + "],"
                                                    + c_reg_name
                                                )
                                            else:
                                                binding_declarations.append(
                                                    typedef_bindings[c_reg]["typedef"]
                                                    + " ["
                                                    + typedef_bindings[c_reg]["packed"]
                                                    + "],"
                                                    + c_reg_name
                                                )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_reg]["typedef"]
                                                + ","
                                                + c_reg_name
                                            )
                                else:
                                    if typedef_bindings[c_reg]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_reg]["class"]
                                            + "::"
                                            + typedef_bindings[c_reg]["typedef"]
                                            + ","
                                            + c_reg_name
                                            + " ["
                                            + typedef_bindings[c_reg]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            if bitdef_has_typedef:
                                                binding_declarations.append(
                                                    bitdef_typedef
                                                    + " ["
                                                    + packed_bitdef
                                                    + "],"
                                                    + c_reg_name
                                                )
                                            else:
                                                binding_declarations.append(
                                                    typedef_bindings[c_reg]["class"]
                                                    + "::"
                                                    + typedef_bindings[c_reg]["typedef"]
                                                    + " ["
                                                    + typedef_bindings[c_reg]["packed"]
                                                    + "],"
                                                    + c_reg_name
                                                )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_reg]["class"]
                                                + "::"
                                                + typedef_bindings[c_reg]["typedef"]
                                                + ","
                                                + c_reg_name
                                            )
                            else:  # if a package is associated with typedef
                                if typedef_bindings[c_reg]["class"] == "default":
                                    if typedef_bindings[c_reg]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_reg]["package"]
                                            + "::"
                                            + typedef_bindings[c_reg]["typedef"]
                                            + ","
                                            + c_reg_name
                                            + " ["
                                            + typedef_bindings[c_reg]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            if bitdef_has_typedef:
                                                binding_declarations.append(
                                                    bitdef_typedef
                                                    + " ["
                                                    + packed_bitdef
                                                    + "],"
                                                    + c_reg_name
                                                )
                                            else:
                                                binding_declarations.append(
                                                    typedef_bindings[c_reg]["package"]
                                                    + "::"
                                                    + typedef_bindings[c_reg]["typedef"]
                                                    + " ["
                                                    + typedef_bindings[c_reg]["packed"]
                                                    + "],"
                                                    + c_reg_name
                                                )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_reg]["package"]
                                                + "::"
                                                + typedef_bindings[c_reg]["typedef"]
                                                + ","
                                                + c_reg_name
                                            )
                                else:
                                    if typedef_bindings[c_reg]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_reg]["package"]
                                            + "::"
                                            + typedef_bindings[c_reg]["class"]
                                            + "::"
                                            + typedef_bindings[c_reg]["typedef"]
                                            + ","
                                            + c_reg_name
                                            + " ["
                                            + typedef_bindings[c_reg]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            binding_declarations.append(
                                                typedef_bindings[c_reg]["package"]
                                                + "::"
                                                + typedef_bindings[c_reg]["class"]
                                                + "::"
                                                + typedef_bindings[c_reg]["typedef"]
                                                + " ["
                                                + typedef_bindings[c_reg]["packed"]
                                                + "],"
                                                + c_reg_name
                                            )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_reg]["package"]
                                                + "::"
                                                + typedef_bindings[c_reg]["class"]
                                                + "::"
                                                + typedef_bindings[c_reg]["typedef"]
                                                + ","
                                                + c_reg_name
                                            )
                    else:  # reg/logic declarations
                        if regs[c_reg]["bitdef"] != "":
                            c_reg_bitdef = "[" + regs[c_reg]["bitdef"] + "]"

                        if regs[c_reg]["depth"] != "":
                            c_reg_name = c_reg_name + "[" + regs[c_reg]["depth"] + "]"

                        reg_declarations.append(
                            c_reg_type
                            + ","
                            + c_reg_signed
                            + ","
                            + c_reg_bitdef
                            + ","
                            + c_reg_name
                        )

            # reg/logic declaration
            if len(reg_declarations) >= 1:
                # Indentation of reg/logic definition
                reg_declarations = indent_array(reg_declarations, ",", "#")

                for c_reg in reg_declarations:
                    out_file.write(begin_space + c_reg + ";\n")
                    dbg(debug, begin_space + c_reg + ";")

            # typedef binding
            if len(binding_declarations) >= 1:
                out_file.write("\n")
                dbg(debug, "")

                # Indentation of reg/logic definition
                binding_declarations = indent_array(binding_declarations, ",", "#")

                for c_bind in binding_declarations:
                    out_file.write(begin_space + c_bind + ";\n")
                    dbg(debug, begin_space + c_bind + ";")

            continue

        ########################################################################
        # Declare wires definition if its called
        ########################################################################
        # RE_WIRES = re.compile(r"^\s*&[Ww][Ii][Rr][Ee][Ss]")
        wires_regex = re.search(RE_WIRES, line)

        begin_space = ""

        if wires_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            begin_space = wires_regex.group(1)

            wire_declarations = []
            binding_declarations = []

            if parsing_format == "verilog":
                c_wire_type = "wire"
            else:
                c_wire_type = "logic"

            for c_wire in list(wires.keys()):
                if (
                    wires[c_wire]["mode"] == "AUTO" and wires[c_wire]["type"] == "LOCAL"
                ) or wires[c_wire]["mode"] == "FORCE":
                    c_wire_name = c_wire
                    if wires[c_wire]["signed"] == "":
                        c_wire_signed = "#"
                    else:
                        c_wire_signed = wires[c_wire]["signed"]

                    c_wire_declare_type = "#"
                    c_wire_bitdef = "#"

                    if c_wire_name in typedef_bindings:
                        if typedef_bindings[c_wire]["mode"] == "FORCE":
                            if typedef_bindings[c_wire]["package"] == "default":
                                if typedef_bindings[c_wire]["class"] == "default":
                                    if typedef_bindings[c_wire]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_wire]["typedef"]
                                            + ","
                                            + c_wire_name
                                            + " ["
                                            + typedef_bindings[c_wire]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["typedef"]
                                                + " ["
                                                + typedef_bindings[c_reg]["packed"]
                                                + "],"
                                                + c_wire_name
                                            )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["typedef"]
                                                + ","
                                                + c_wire_name
                                            )
                                else:
                                    if typedef_bindings[c_wire]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_wire]["class"]
                                            + "::"
                                            + typedef_bindings[c_wire]["typedef"]
                                            + ","
                                            + c_wire_name
                                            + " ["
                                            + typedef_bindings[c_wire]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["class"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + " ["
                                                + typedef_bindings[c_reg]["packed"]
                                                + "],"
                                                + c_wire_name
                                            )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["class"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + ","
                                                + c_wire_name
                                            )
                            else:  # if a package is associated with typedef
                                if typedef_bindings[c_wire]["class"] == "default":
                                    if typedef_bindings[c_wire]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_wire]["package"]
                                            + "::"
                                            + typedef_bindings[c_wire]["typedef"]
                                            + ","
                                            + c_wire_name
                                            + " ["
                                            + typedef_bindings[c_wire]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["package"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + " ["
                                                + typedef_bindings[c_reg]["packed"]
                                                + "],"
                                                + c_wire_name
                                            )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["package"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + ","
                                                + c_wire_name
                                            )
                                else:
                                    if typedef_bindings[c_wire]["depth"] != "":
                                        binding_declarations.append(
                                            typedef_bindings[c_wire]["package"]
                                            + "::"
                                            + typedef_bindings[c_wire]["class"]
                                            + "::"
                                            + typedef_bindings[c_wire]["typedef"]
                                            + ","
                                            + c_wire_name
                                            + " ["
                                            + typedef_bindings[c_wire]["depth"]
                                            + "]"
                                        )
                                    else:
                                        if typedef_bindings[c_reg]["packed"] != "":
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["package"]
                                                + "::"
                                                + typedef_bindings[c_wire]["class"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + " ["
                                                + typedef_bindings[c_reg]["packed"]
                                                + "],"
                                                + c_wire_name
                                            )
                                        else:
                                            binding_declarations.append(
                                                typedef_bindings[c_wire]["package"]
                                                + "::"
                                                + typedef_bindings[c_wire]["class"]
                                                + "::"
                                                + typedef_bindings[c_wire]["typedef"]
                                                + ","
                                                + c_wire_name
                                            )
                    else:  # reg/logic declarations
                        if wires[c_wire]["bitdef"] != "":
                            c_wire_bitdef = "[" + wires[c_wire]["bitdef"] + "]"

                        if wires[c_wire]["depth"] != "":
                            c_wire_name = (
                                c_wire_name + "[" + wires[c_wire]["depth"] + "]"
                            )

                        wire_declarations.append(
                            c_wire_type
                            + ","
                            + c_wire_signed
                            + ","
                            + c_wire_bitdef
                            + ","
                            + c_wire_name
                        )

            # wire declarations
            if len(wire_declarations) >= 1:
                # Indentation of reg/logic definition
                wire_declarations = indent_array(wire_declarations, ",", "#")

                for c_wire in wire_declarations:
                    out_file.write(begin_space + c_wire + ";\n")
                    dbg(debug, begin_space + c_wire + ";")

            # typedef binding
            if len(binding_declarations) >= 1:
                out_file.write("\n")
                dbg(debug, "")

                # Indentation of reg/logic definition
                binding_declarations = indent_array(binding_declarations, ",", "#")

                for c_bind in binding_declarations:
                    out_file.write(begin_space + c_bind + ";\n")
                    dbg(debug, begin_space + c_bind + ";")

            continue

        ########################################################################
        # Post Embedded python script processing
        ########################################################################
        post_python_begin_regex = re.search(RE_POST_PYTHON_BLOCK_BEGIN, line)
        post_python_end_regex = re.search(RE_POST_PYTHON_BLOCK_END, line)

        if not doing_python and post_python_begin_regex:
            begin_python_space = post_python_begin_regex.group(1)
            doing_python = 1
            code_block = ""
            print(("    # Executing embedded python code at line " + str(line_no)))

            ampersand_line = re.sub(r"^", r"//", original_line, 1)
            out_file.write(ampersand_line + "\n")

            comment_indent = post_python_begin_regex.group(1)
            # auto_indent = comment_indent
            continue
        elif doing_python and post_python_end_regex:
            ampersand_line = re.sub(r"^", r"//", original_line, 1)
            out_file.write(ampersand_line + "\n")

            doing_python = 0

            stdout_ = sys.stdout  # Keep track of the previous value.
            stream = io.StringIO()
            sys.stdout = stream
            try:
                exec(code_block)
            except Exception:
                print(("Error in code:\n" + code_block + "\n"))
                raise

            sys.stdout = stdout_  # restore the previous stdout.
            exec_data = stream.getvalue()
            exec_data = re.sub(r"[\n]+$", r"", exec_data)
            exec_data = re.sub(r"[\n]+", r"\n", exec_data)
            exec_data_array = exec_data.split("\n")
            stream.close()

            for c_exec_line in exec_data_array:
                out_file.write(begin_python_space + c_exec_line + "\n")

            continue
        elif doing_python:
            dum = re.sub(r"^(" + comment_indent + r")", r"", line)
            code_block += dum + "\n"

            ampersand_line = re.sub(r"^", r"//", original_line, 1)
            out_file.write(ampersand_line + "\n")

            continue

        ########################################################################
        # Declare module instantiation
        ########################################################################
        begininstance_regex = re.search(RE_BEGININSTANCE, line)
        endinstance_regex = re.search(RE_ENDINSTANCE, line)
        buildcommand_regex = re.search(RE_BUILD_COMMAND, line)
        include_regex = re.search(RE_INCLUDE, line)
        param_override_regex = re.search(RE_PARAM_OVERRIDE, line)
        connect_regex = re.search(RE_CONNECT, line)

        if begininstance_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            look_for_instance_cmds = 1
            begininstance_space = begininstance_regex.group(1)
            begininstance_info = begininstance_regex.group(2)
            begininstance_info = re.sub(r";", r"", begininstance_info)
            begininstance_info = re.sub(r"\s+", r" ", begininstance_info)
            begininstance_info = re.sub(r"^\s+", r"", begininstance_info)
            begininstance_info = re.sub(r"\s+$", r"", begininstance_info)
            begininstance_info_array = begininstance_info.split(" ")

            if len(begininstance_info_array) == 3:
                submod_name = begininstance_info_array[0]
                inst_name = begininstance_info_array[1]
            elif len(begininstance_info_array) == 2:
                submod_name = begininstance_info_array[0]
                inst_name = begininstance_info_array[1]
            elif len(begininstance_info_array) == 1:
                submod_name = begininstance_info_array[0]
                inst_name = "u_" + submod_name

            continue
        elif endinstance_regex:
            look_for_instance_cmds = 0
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            if inst_name not in sub_inst_files:
                continue

            inst_path = re.sub(
                r".*\/infra_asic_fpga\/",
                r"$INFRA_ASIC_FPGA_ROOT/",
                sub_inst_files[inst_name],
            )
            inst_line = begininstance_space + "//FILE: " + inst_path
            out_file.write(inst_line + "\n")
            dbg(debug, inst_line)

            ####################################################################
            # Instantiating a submodule
            ####################################################################
            # Checking if PARAM override is needed for this instance
            if len(sub_inst_params[inst_name]) > 0:
                inst_line = begininstance_space + submod_name + " # ("
                out_file.write(inst_line + "\n")
                dbg(debug, inst_line)

                inst_array = []
                array_size = len(sub_inst_params[inst_name])

                for c_param in list(sub_inst_params[inst_name].keys()):
                    if array_size == 1:  # last param
                        inst_array.append(
                            "."
                            + sub_inst_params[inst_name][c_param]["name"]
                            + " ("
                            + sub_inst_params[inst_name][c_param]["topname"]
                            + ")"
                        )
                    else:
                        inst_array.append(
                            "."
                            + sub_inst_params[inst_name][c_param]["name"]
                            + " ("
                            + sub_inst_params[inst_name][c_param]["topname"]
                            + "),"
                        )

                    array_size = array_size - 1

                inst_array = indent_array(inst_array, " ", "#")

                for c_param in inst_array:
                    inst_line = begininstance_space + "    " + c_param
                    out_file.write(inst_line + "\n")
                    dbg(debug, inst_line)

                inst_line = begininstance_space + ") " + inst_name + " ("
                out_file.write(inst_line + "\n")
                dbg(debug, inst_line)
            else:
                inst_line = begininstance_space + submod_name + " " + inst_name + " ("
                out_file.write(inst_line + "\n")
                dbg(debug, inst_line)

            inst_array = []
            array_size = len(sub_inst_ports[inst_name])

            for c_port in sub_inst_ports[inst_name]:
                topname_sqbrct_regex = re.search(
                    RE_OPEN_SQBRCT, sub_inst_ports[inst_name][c_port]["topname"]
                )
                sqbrct_2d_regex = re.search(
                    RE_CLOSE_2D_SQBRCT, sub_inst_ports[inst_name][c_port]["topbitdef"]
                )

                if sub_inst_ports[inst_name][c_port]["comment"] != "":
                    c_connect_comment = (
                        " //" + sub_inst_ports[inst_name][c_port]["comment"]
                    )
                else:
                    c_connect_comment = ""

                if array_size == 1:  # last port
                    if (
                        sub_inst_ports[inst_name][c_port]["topbitdef"] == ""
                        or sqbrct_2d_regex
                    ):
                        if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                            inst_array.append(
                                "."
                                + sub_inst_ports[inst_name][c_port]["name"]
                                + " ("
                                + sub_inst_ports[inst_name][c_port]["topname"]
                                + ")"
                                + c_connect_comment
                            )
                        else:
                            inst_array.append(
                                "."
                                + sub_inst_ports[inst_name][c_port]["name"]
                                + " ("
                                + sub_inst_ports[inst_name][c_port]["origconnect"]
                                + ")"
                                + c_connect_comment
                            )
                    else:
                        double_colon_regex = re.search(
                            RE_DOUBLE_COLON,
                            sub_inst_ports[inst_name][c_port]["topbitdef"],
                        )

                        if (
                            topname_sqbrct_regex
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_LOGIC"
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_STRUCT"
                            or double_colon_regex
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_UNION"
                        ):
                            if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["topname"]
                                    + ")"
                                    + c_connect_comment
                                )
                            else:
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["origconnect"]
                                    + ")"
                                    + c_connect_comment
                                )
                        else:
                            if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                                if (
                                    sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    == "0:0"
                                ):
                                    inst_array.append(
                                        "."
                                        + sub_inst_ports[inst_name][c_port]["name"]
                                        + " ("
                                        + sub_inst_ports[inst_name][c_port]["topname"]
                                        + ")"
                                        + c_connect_comment
                                    )
                                else:
                                    inst_array.append(
                                        "."
                                        + sub_inst_ports[inst_name][c_port]["name"]
                                        + " ("
                                        + sub_inst_ports[inst_name][c_port]["topname"]
                                        + "["
                                        + sub_inst_ports[inst_name][c_port]["topbitdef"]
                                        + "])"
                                        + c_connect_comment
                                    )
                            else:
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["origconnect"]
                                    + ")"
                                    + c_connect_comment
                                )
                else:
                    if (
                        sub_inst_ports[inst_name][c_port]["topbitdef"] == ""
                        or sqbrct_2d_regex
                    ):
                        if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                            inst_array.append(
                                "."
                                + sub_inst_ports[inst_name][c_port]["name"]
                                + " ("
                                + sub_inst_ports[inst_name][c_port]["topname"]
                                + "),"
                                + c_connect_comment
                            )
                        else:
                            inst_array.append(
                                "."
                                + sub_inst_ports[inst_name][c_port]["name"]
                                + " ("
                                + sub_inst_ports[inst_name][c_port]["origconnect"]
                                + "),"
                                + c_connect_comment
                            )
                    else:
                        double_colon_regex = re.search(
                            RE_DOUBLE_COLON,
                            sub_inst_ports[inst_name][c_port]["topbitdef"],
                        )

                        if (
                            topname_sqbrct_regex
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_LOGIC"
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_STRUCT"
                            or double_colon_regex
                            or sub_inst_ports[inst_name][c_port]["typedef"]
                            == "TYPEDEF_UNION"
                        ):
                            if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["topname"]
                                    + "),"
                                    + c_connect_comment
                                )
                            else:
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["origconnect"]
                                    + "),"
                                    + c_connect_comment
                                )
                        else:
                            if sub_inst_ports[inst_name][c_port]["origconnect"] == "":
                                if (
                                    sub_inst_ports[inst_name][c_port]["topbitdef"]
                                    == "0:0"
                                ):
                                    inst_array.append(
                                        "."
                                        + sub_inst_ports[inst_name][c_port]["name"]
                                        + " ("
                                        + sub_inst_ports[inst_name][c_port]["topname"]
                                        + "),"
                                        + c_connect_comment
                                    )
                                else:
                                    inst_array.append(
                                        "."
                                        + sub_inst_ports[inst_name][c_port]["name"]
                                        + " ("
                                        + sub_inst_ports[inst_name][c_port]["topname"]
                                        + "["
                                        + sub_inst_ports[inst_name][c_port]["topbitdef"]
                                        + "]),"
                                        + c_connect_comment
                                    )
                            else:
                                inst_array.append(
                                    "."
                                    + sub_inst_ports[inst_name][c_port]["name"]
                                    + " ("
                                    + sub_inst_ports[inst_name][c_port]["origconnect"]
                                    + "),"
                                    + c_connect_comment
                                )

                array_size = array_size - 1

            inst_array = indent_array(inst_array, " ", "#")

            for c_port in inst_array:
                inst_line = begininstance_space + "    " + c_port
                out_file.write(inst_line + "\n")
                dbg(debug, inst_line)

            inst_line = begininstance_space + ");"
            out_file.write(inst_line + "\n")
            dbg(debug, inst_line)

            continue
        elif look_for_instance_cmds:
            if (
                buildcommand_regex
                or param_override_regex
                or connect_regex
                or include_regex
            ):
                ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                out_file.write(ampersand_line + "\n")
                dbg(debug, ampersand_line)

            continue

        ########################################################################
        # &Posedge, &Negedge, &Clock, &SyncReset and &Asyncreset
        ########################################################################
        clock_regex = re.search(RE_CLOCK, line)

        if clock_regex:
            clock = clock_regex.group(1)
            print(("    - Setting Clock as " + clock))
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            continue

        asyncreset_regex = re.search(RE_ASYNCRESET, line)

        if asyncreset_regex:
            async_reset = asyncreset_regex.group(1)
            reset_type = "ASYNC"
            print(("    - Setting AsyncReset as " + async_reset))
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            continue

        syncreset_regex = re.search(RE_SYNCRESET, line)

        if syncreset_regex:
            sync_reset = syncreset_regex.group(1)
            reset_type = "SYNC"
            print(("    - Setting SyncReset as " + sync_reset))
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            continue

        posedge_regex = re.search(RE_R_POSEDGE, line)
        negedge_regex = re.search(RE_R_NEGEDGE, line)

        if posedge_regex or negedge_regex:
            if posedge_regex:
                auto_reset_space = posedge_regex.group(1)
            else:
                auto_reset_space = negedge_regex.group(1)

            remove_reset_val = 1
            skip_auto_reset_line = 1
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            if parsing_format == "systemverilog":
                if posedge_regex:
                    if reset_type == "ASYNC":
                        print_line = (
                            auto_reset_space
                            + "always_ff @ (posedge "
                            + clock
                            + " or negedge "
                            + async_reset
                            + ") begin"
                        )
                    else:
                        print_line = (
                            auto_reset_space
                            + "always_ff @ (posedge "
                            + clock
                            + ") begin"
                        )
                else:
                    if reset_type == "ASYNC":
                        print_line = (
                            auto_reset_space
                            + "always_ff @ (negedge "
                            + clock
                            + " or negedge "
                            + async_reset
                            + ") begin"
                        )
                    else:
                        print_line = (
                            auto_reset_space
                            + "always_ff @ (negedge "
                            + clock
                            + ") begin"
                        )

                out_file.write(print_line + "\n")
                dbg(debug, print_line)
            else:
                if posedge_regex:
                    if reset_type == "ASYNC":
                        print_line = (
                            auto_reset_space
                            + "always @ (posedge "
                            + clock
                            + " or negedge "
                            + async_reset
                            + ") begin"
                        )
                    else:
                        print_line = (
                            auto_reset_space + "always @ (posedge " + clock + ") begin"
                        )
                else:
                    if reset_type == "ASYNC":
                        print_line = (
                            auto_reset_space
                            + "always @ (negedge "
                            + clock
                            + " or negedge "
                            + async_reset
                            + ") begin"
                        )
                    else:
                        print_line = (
                            auto_reset_space + "always @ (negedge " + clock + ") begin"
                        )

                out_file.write(print_line + "\n")
                dbg(debug, print_line)

            if reset_type == "ASYNC":
                print_line = auto_reset_space + "  if (~" + async_reset + ") begin"
            else:
                print_line = auto_reset_space + "  if (~" + sync_reset + ") begin"

            out_file.write(print_line + "\n")
            dbg(debug, print_line)

            try:
                c_signals = auto_reset_data[auto_reset_index]
            except KeyError:
                print(
                    "\nError: Unable to find auto reset index. This may be caused by incomplete auto reset data.\n"
                )
                sys.exit(1)

            for c_signal in auto_reset_data[auto_reset_index]:
                reset_val = auto_reset_data[auto_reset_index][c_signal]["resetval"]

                if c_signal in regs:
                    if regs[c_signal]["bitdef"] == "":
                        c_signal_width = 1
                    else:
                        c_signal_bitdef_regex = re.search(
                            RE_COLON, regs[c_signal]["bitdef"]
                        )

                        # Checking if the bitwidth can be split by :
                        if c_signal_bitdef_regex:
                            c_signal_ubitdef = c_signal_bitdef_regex.group(1)

                            c_signal_ubitdef_minus1_regex = re.search(
                                RE_MINUS1, c_signal_ubitdef
                            )

                            if c_signal_ubitdef_minus1_regex:
                                c_signal_width = re.sub(
                                    r"-\s*1$", r"", c_signal_ubitdef
                                )
                            else:
                                c_signal_ubitdef_number_regex = re.search(
                                    RE_NUMBERS_ONLY, str(c_signal_ubitdef)
                                )

                                if c_signal_ubitdef_number_regex:
                                    c_signal_width = int(c_signal_ubitdef) + 1
                                else:
                                    c_signal_width = c_signal_ubitdef + "+1"
                        else:  # use numerical value of bitdef
                            c_signal_width = int(regs[c_signal]["uwidth"]) + 1
                elif c_signal in ports:
                    if ports[c_signal]["bitdef"] == "":
                        c_signal_width = 1
                    else:
                        c_signal_bitdef_regex = re.search(
                            RE_COLON, ports[c_signal]["bitdef"]
                        )

                        # Checking if the bitwidth can be split by :
                        if c_signal_bitdef_regex:
                            c_signal_ubitdef = c_signal_bitdef_regex.group(1)

                            c_signal_ubitdef_minus1_regex = re.search(
                                RE_MINUS1, c_signal_ubitdef
                            )

                            if c_signal_ubitdef_minus1_regex:
                                c_signal_width = re.sub(
                                    r"-\s*1$", r"", c_signal_ubitdef
                                )
                            else:
                                c_signal_ubitdef_number_regex = re.search(
                                    RE_NUMBERS_ONLY, str(c_signal_ubitdef)
                                )

                                if c_signal_ubitdef_number_regex:
                                    c_signal_width = int(c_signal_ubitdef) + 1
                                else:
                                    c_signal_width = c_signal_ubitdef + "+1"
                        else:  # use numerical value of bitdef
                            c_signal_width = int(ports[c_signal]["uwidth"]) + 1

                if reset_val == "0":
                    if c_signal_width == 1:
                        if parsing_format == "systemverilog":
                            print_line = (
                                auto_reset_space
                                + "    "
                                + c_signal
                                + " <= {$bits("
                                + c_signal
                                + "){1'b0}};"
                            )
                        else:
                            print_line = (
                                auto_reset_space + "    " + c_signal + " <= 1'b0;"
                            )
                    else:
                        if parsing_format == "systemverilog":
                            print_line = (
                                auto_reset_space
                                + "    "
                                + c_signal
                                + " <= {$bits("
                                + c_signal
                                + "){1'b0}};"
                            )
                        else:
                            print_line = (
                                auto_reset_space
                                + "    "
                                + c_signal
                                + " <= {"
                                + str(c_signal_width)
                                + "{1'b0}};"
                            )

                    out_file.write(print_line + "\n")
                    dbg(debug, print_line)
                elif reset_val == "1":
                    if c_signal_width == 1:
                        print_line = auto_reset_space + "    " + c_signal + " <= 1'b1;"
                    else:
                        if parsing_format == "systemverilog":
                            print_line = (
                                auto_reset_space
                                + "    "
                                + c_signal
                                + " <= {$bits("
                                + c_signal
                                + "){1'b1}};"
                            )
                        else:
                            print_line = (
                                auto_reset_space
                                + "    "
                                + c_signal
                                + " <= {"
                                + str(c_signal_width)
                                + "{1'b1}};"
                            )

                    out_file.write(print_line + "\n")
                    dbg(debug, print_line)
                else:
                    print_line = (
                        auto_reset_space + "    " + c_signal + " <= " + reset_val + ";"
                    )
                    out_file.write(print_line + "\n")
                    dbg(debug, print_line)

            print_line = auto_reset_space + "  end"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)

            print_line = auto_reset_space + "  else begin"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)
            continue

        endnegedge_regex = re.search(RE_R_ENDNEGEDGE, line)

        if endnegedge_regex:
            remove_reset_val = 0
            print_line = endnegedge_regex.group(1) + "end"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)

            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            auto_reset_index = auto_reset_index + 1
            continue

        endposgedge_regex = re.search(RE_R_ENDPOSEDGE, line)

        if endposgedge_regex:
            remove_reset_val = 0
            print_line = endposgedge_regex.group(1) + "end"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)

            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            auto_reset_index = auto_reset_index + 1
            continue

        ########################################################################
        # Writing out Pkg2Assign outputs
        ########################################################################
        pkg2assign_regex = re.search(RE_PKG2ASSIGN, line)

        if pkg2assign_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            dbg(debug, json.dumps(pkg2assign_info[pkg2assign_index], indent=2))

            pkg2assign_list = pkg2assign_info[pkg2assign_index]
            for c_line in list(pkg2assign_list):
                out_file.write(c_line + "\n")

            pkg2assign_index = pkg2assign_index + 1
            continue

        ########################################################################
        # Writing out Assign2Pkg outputs
        ########################################################################
        assign2pkg_regex = re.search(RE_ASSIGN2PKG, line)

        if assign2pkg_regex:
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            dbg(debug, json.dumps(assign2pkg_info[assign2pkg_index], indent=2))

            assign2pkg_list = assign2pkg_info[assign2pkg_index]
            for c_line in list(assign2pkg_list):
                out_file.write(c_line + "\n")

            assign2pkg_index = assign2pkg_index + 1
            continue

        ########################################################################
        # Commenting out different & calls
        ########################################################################
        force_regex = re.search(RE_FORCE, line)
        beginskip_regex = re.search(RE_SKIP_BEGIN, line)
        endskip_regex = re.search(RE_SKIP_END, line)
        parser_off_regex = re.search(RE_PARSER_OFF, line)
        parser_on_regex = re.search(RE_PARSER_ON, line)
        skipifdefbegin_regex = re.search(RE_SKIP_IFDEF_BEGIN, line)
        skipifdefend_regex = re.search(RE_SKIP_IFDEF_END, line)

        if (
            force_regex
            or beginskip_regex
            or endskip_regex
            or parser_off_regex
            or parser_on_regex
            or skipifdefbegin_regex
            or skipifdefend_regex
        ):
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)
            continue

        ########################################################################
        # Stub Generation
        ########################################################################

        gendrivez_regex = re.search(RE_GENDRIVEZ, line)
        gendrive0_regex = re.search(RE_GENDRIVE0, line)
        gennoifdefdrive0_regex = re.search(RE_GENNOIFDEFDRIVE0, line)
        gendrive0andz_regex = re.search(RE_GENDRIVE0ANDZ, line)

        if gendrivez_regex:
            gendrive_space = gendrivez_regex.group(1)
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            if generate_stub:
                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrivez_regex.group(1)
                                + "assign "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrivez_regex.group(1)
                                + "assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)
                endmodule_found = 1
                break
            else:
                generate_stub_z = 1
                print_line = (
                    gendrivez_regex.group(1)
                    + "`ifdef "
                    + module_name.upper()
                    + "_DRIVE_Z"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrivez_regex.group(1)
                                + "  assign "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrivez_regex.group(1)
                                + "  assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrivez_regex.group(1) + "`else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                continue

        if gennoifdefdrive0_regex:
            gendrive_space = gennoifdefdrive0_regex.group(1)
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            generate_stub_0 = 0

            for c_port in ports:
                if ports[c_port]["dir"] == "output":
                    if c_port in stub_override_val:
                        print_line = (
                            gendrive_space
                            + "assign  "
                            + ports[c_port]["name"]
                            + " = "
                            + stub_override_val[c_port]
                            + ";"
                        )
                    else:
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrive_space
                                + "assign  "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'b0}};"
                            )
                        else:
                            print_line = (
                                gendrive_space
                                + "assign  "
                                + ports[c_port]["name"]
                                + " = 'd0;"
                            )

                    out_file.write(print_line + "\n")
                    dbg(debug, print_line)

            continue

        if gendrive0_regex:
            gendrive_space = gendrive0_regex.group(1)
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            if generate_stub:
                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0_regex.group(1)
                                + "assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)
                endmodule_found = 1
                break
            else:
                generate_stub_0 = 1
                print_line = (
                    gendrive0_regex.group(1)
                    + "`ifdef "
                    + module_name.upper()
                    + "_DRIVE_0"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0_regex.group(1)
                                + "  assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0_regex.group(1) + "`else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)
                continue

        if gendrive0andz_regex:
            gendrive_space = gendrive0andz_regex.group(1)
            ampersand_line = re.sub(r"&", r"//&", original_line, 1)
            out_file.write(ampersand_line + "\n")
            dbg(debug, ampersand_line)

            generate_stub_z = 1
            generate_stub_0 = 1

            if generate_stub:
                print_line = (
                    gendrive0andz_regex.group(1)
                    + "`ifdef "
                    + module_name.upper()
                    + "_DRIVE_0"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "  assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0andz_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0andz_regex.group(1)
                                    + "  assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_regex.group(1) + "`else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = (
                    gendrive0andz_regex.group(1)
                    + "  `ifdef "
                    + module_name.upper()
                    + "_DRIVE_Z"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_regex.group(1) + "  `endif"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = gendrive0andz_regex.group(1) + "`endif"
                out_file.write(print_line + "\n\n")
                dbg(debug, print_line)

                print_line = "\n\nendmodule"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                endmodule_found = 1
                break
            else:
                print_line = (
                    gendrive0andz_regex.group(1)
                    + "`ifdef "
                    + module_name.upper()
                    + "_DRIVE_0"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if c_port in stub_override_val:
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "  assign  "
                                + ports[c_port]["name"]
                                + " = "
                                + stub_override_val[c_port]
                                + ";"
                            )
                        else:
                            if parsing_format == "systemverilog":
                                print_line = (
                                    gendrive0andz_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = {$bits("
                                    + c_port
                                    + "){1'b0}};"
                                )
                            else:
                                print_line = (
                                    gendrive0andz_regex.group(1)
                                    + "assign  "
                                    + ports[c_port]["name"]
                                    + " = 'd0;"
                                )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_regex.group(1) + "`else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = (
                    gendrive0andz_regex.group(1)
                    + "  `ifdef "
                    + module_name.upper()
                    + "_DRIVE_Z"
                )
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                for c_port in ports:
                    if ports[c_port]["dir"] == "output":
                        if parsing_format == "systemverilog":
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = {$bits("
                                + c_port
                                + "){1'bz}};"
                            )
                        else:
                            print_line = (
                                gendrive0andz_regex.group(1)
                                + "    assign "
                                + ports[c_port]["name"]
                                + " = 'dZ;"
                            )

                        out_file.write(print_line + "\n")
                        dbg(debug, print_line)

                print_line = gendrive0andz_regex.group(1) + "  `else"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                continue

        ########################################################################
        # Check if endmodule declaration by user
        ########################################################################
        endmodule_regex = re.search(RE_END_MODULE_DECLARATION, line)

        if endmodule_regex:
            endmodule_found = 1
            generate_endmodule = 0
            if generate_stub_z and generate_stub_0:
                print_line = gendrive_space + "  `endif"
                out_file.write(print_line + "\n")
                dbg(debug, print_line)

                print_line = gendrive_space + "`endif"
                out_file.write(print_line + "\n\n")
                dbg(debug, print_line)
            elif generate_stub_z or generate_stub_0:
                print_line = gendrive_space + "`endif"
                out_file.write(print_line + "\n\n")
                dbg(debug, print_line)

            out_file.write(original_line + "\n")
            dbg(debug, original_line)
            continue

        ########################################################################
        # Print all other lines
        ########################################################################
        out_file.write(original_line + "\n")
        dbg(debug, original_line)
        prev_line = line

    if not endmodule_found:
        if generate_stub_z and generate_stub_0:
            print_line = gendrive_space + "  `endif"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)

            print_line = gendrive_space + "`endif"
            out_file.write(print_line + "\n\n")
            dbg(debug, print_line)
        elif generate_stub_z or generate_stub_0:
            print_line = gendrive_space + "`endif"
            out_file.write(print_line + "\n\n")
            dbg(debug, print_line)

        if generate_endmodule:
            print_line = "\n\nendmodule"
            out_file.write(print_line + "\n")
            dbg(debug, print_line)

    out_file.close()
    temp_file.close()

    # Adding the currently generated file to filelist
    filelist.append(output_file)

    # Generating filelist as <MODULE>.f
    if generate_filelist:
        unique_filelist = []
        filelist_set = set()
        for filename in filelist:
            filename = filename.strip()
            if filename.startswith("+incdir+") or os.path.exists(filename):
                if filename not in filelist_set:
                    filelist_set.add(filename)
                    unique_filelist.append(filename)

        with open(output_list, "w") as out_list:
            for c_file in unique_filelist:
                out_list.write(c_file + "\n")

    # Closing the debug dump file if debug is on
    if debug:
        dbg_file.close()
        print("  # Generated debug file " + debug_file + ".codegen")
        print("  # Generated debug file " + debug_file + ".parser")
        print("  # Generated debug file " + debug_file + ".write")
    else:
        if not found_error:
            if os.path.isfile(temporary_file):
                os.remove(temporary_file)

            if os.path.isfile(debug_file):
                os.remove(debug_file)
                os.remove(debug_file + ".codegen")
                os.remove(debug_file + ".parser")
        else:
            print("  # Generated expanded input .pv/psv file " + temporary_file)

            if debug:
                print("  # Generated debug file " + debug_file + ".codegen")
                print("  # Generated debug file " + debug_file + ".parser")
                print("  # Generated debug file " + debug_file + ".write")

    if found_error:
        os.rename(output_file, output_file + ".error")
        print(("  # Generated file " + output_file + ".error with Errors"))
        print("\nError: Please review the run log for errors\n")
        sys.exit(1)
    else:
        print(("  # Successfully generated file " + output_file + "\n"))
