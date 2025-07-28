####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################
################################################################################
#                                                                              #
#     Author: Baheerathan Anandharengan                                        #
#     E-Mail: baheerathan@meta.com                                             #
#                                                                              #
#     Key Contributor: Dheepak Jayaraman                                       #
#     E-Mail: dheepak@meta.com                                                 #
#                                                                              #
#     Additional Contributor: Yunqing Chen                                     #
#     E-Mail: yqchen@meta.com                                                  #
#                                                                              #
################################################################################

import io
import os
import os.path
import re
import sys
from src.utils import *
from src.regex import *

from src.memgen import memgen


class codegen:
    """
    Class to do the code generation part.
    Parse #ifdef and work on only enabled code
    Expand embedded python code output
    Run plugin and generate code
    """

    def __init__(
        self,
        in_file,
        rm_code,
        incl_dirs,
        files,
        debug_en,
        debug_file,
        gen_dependencies,
        cmdline,
        py_ns,
    ):
        """
        Constructor
        """

        self.in_file = in_file
        self.remove_code = rm_code
        self.incl_dirs = incl_dirs
        self.files = files
        self.debug = debug_en
        self.debug_file = debug_file + ".codegen"
        self.gen_dependencies = gen_dependencies
        self.parsing_format = cmdline.format
        self.debug_print = 0

        self.hash_define_vars = []
        self.hash_define_files = []
        self.hash_defines = {}
        self.hash_ifdef_en = 1
        self.hash_ifdef_arr = []
        self.hash_decisions = []
        self.hash_types = []
        self.hash_served = []
        self.hash_curr_decision = 1
        self.hash_curr_type = ""
        self.hash_curr_served = 0
        self.last_hash_loc = 0

        self.line_no = 0
        self.in_lines = []

        self.clock = "clk"
        self.async_reset = "arst_n"
        self.sync_reset = "rst_n"
        self.reset_type = "ASYNC"

        # Output variables
        self.stub_override_val = {}
        self.functions_list = {}
        self.lines = []
        self.debug_info = []
        self.found_error = 0
        self.header_files = []

        self.gen_dependencies

        self.py_ns = py_ns
        vars(self).update(py_ns)

        if self.debug:
            self.dbg_file = open(self.debug_file, "w")

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
                    print("")
            else:
                self.dbg_file.write(str(dbg_info))

                if self.debug_print:
                    print(str(dbg_info))

            self.dbg_file.write("\n")

        return

    def get_hash_defval(self, hash_def):
        """
        Function to get the value of a #define. This can be called in a embedded
        python script.
        """

        if hash_def in self.hash_defines:
            hash_defval = self.hash_defines[hash_def]["val"]
        else:
            self.dbg("        Error: Unable to find the #define " + hash_def + "\n")
            print("        Error: Unable to find the #define " + hash_def + "\n")
            sys.exit(1)

        return hash_defval

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

    def hash_def_getval(self, hash_def_exp):
        """
        Function to calculate value for a #define and return its type
        Type can be numerical, string
        """

        hash_def_info = []
        hash_def_exp_split = self.split_on_word_boundary(hash_def_exp)

        hash_eval_string = ""
        for hash_split in hash_def_exp_split:
            if hash_split in self.hash_defines:
                hash_eval_string = hash_eval_string + str(
                    self.hash_defines[hash_split]["val"]
                )
            else:
                hash_eval_string = hash_eval_string + hash_split

        try:
            hash_eval_string_val = eval(hash_eval_string)
        except (SyntaxError, NameError, TypeError, ZeroDivisionError):
            hash_eval_string_val = ""

        check_val = isinstance(hash_eval_string_val, int)

        if check_val:
            hash_def_info.append("NUMBER")
        else:
            hash_def_info.append("STRING")
            hash_eval_string_val = hash_def_exp

        hash_def_info.append(hash_eval_string_val)

        return hash_def_info

    def hash_def_proc(self, hash_def_in):
        """
        Function parses the #define and updates the hash table with value and type
        """

        # Removing = if its passed through command line
        hash_def_in = re.sub(r"=", r" ", hash_def_in.rstrip())

        # Removing single line comment at the end of #define
        hash_def_in = re.sub(r"\s*\/\/.*", r"", hash_def_in)

        # Removing multiple space to single and no space at the end
        hash_def_in = re.sub(r"\s+", r" ", hash_def_in)
        hash_def_in = re.sub(r"\s*$", r"", hash_def_in)

        hash_def_val_ret = []

        hash_def_regex = RE_HASH_DEF.search(hash_def_in)

        hash_def_wo_val_regex = RE_HASH_DEF_WO_VAL.search(hash_def_in)

        # If there is no values or expression for a define, it's value will be assigned as 1
        if hash_def_wo_val_regex:
            if hash_def_wo_val_regex.group(1) in self.hash_defines:
                print(
                    "\nWarning: The following #define already defined\n"
                    + hash_def_wo_val_regex.group(0)
                )
            else:
                self.hash_defines[hash_def_wo_val_regex.group(1)] = {}

            self.hash_defines[hash_def_wo_val_regex.group(1)]["type"] = "NUMBER"
            self.hash_defines[hash_def_wo_val_regex.group(1)]["val"] = 1
            self.hash_defines[hash_def_wo_val_regex.group(1)]["exp"] = 1

            self.dbg("#define " + hash_def_in)
            self.dbg(
                "   TYPE: "
                + self.hash_defines[hash_def_wo_val_regex.group(1)]["type"]
                + " :: VALUE: "
                + str(self.hash_defines[hash_def_wo_val_regex.group(1)]["val"])
            )
        else:
            if hash_def_regex:
                if hash_def_regex.group(1) in self.hash_defines:
                    print(
                        "\nWarning: The following #define already defined\n"
                        + hash_def_regex.group(0)
                    )
                else:
                    self.hash_defines[hash_def_regex.group(1)] = {}

                hash_def_val_ret = self.hash_def_getval(hash_def_regex.group(2))
                self.hash_defines[hash_def_regex.group(1)]["type"] = hash_def_val_ret[0]
                self.hash_defines[hash_def_regex.group(1)]["val"] = hash_def_val_ret[1]
                self.hash_defines[hash_def_regex.group(1)]["exp"] = (
                    hash_def_regex.group(2)
                )

                self.dbg("#define " + hash_def_in)
                self.dbg(
                    "   TYPE: "
                    + self.hash_defines[hash_def_regex.group(1)]["type"]
                    + " :: VALUE: "
                    + str(self.hash_defines[hash_def_regex.group(1)]["val"])
                )
            else:
                self.dbg("\nError: Unable to get value for #define\n")
                self.dbg(hash_def_in)
                print("\nError: Unable to get value for #define\n")
                print(hash_def_in)
                self.found_error = 1

        return

    def hash_ifdef_proc(self, hash_ifdef_type, hash_ifdef_str):
        """
        Function to process #ifdef and it returns current ifdef status
        to skip the code or parse it
        """

        last_hash_decision = 0
        popped_hash_decision = 0
        popped_hash_type = ""
        popped_hash_served = 0

        if hash_ifdef_type == "ifdef":
            hash_level = len(self.hash_decisions)
            self.dbg(
                "\n### HASH LEVEL: "
                + str(hash_level)
                + ", "
                + hash_ifdef_type
                + ", "
                + hash_ifdef_str
            )
        else:
            hash_level = len(self.hash_decisions) - 1
            self.dbg(
                "\n### HASH LEVEL: "
                + str(hash_level)
                + ", "
                + hash_ifdef_type
                + ", "
                + hash_ifdef_str
            )

        hash_ifdef_str_regex = RE_HASH_IFDEF_STR.search(hash_ifdef_str)

        if hash_ifdef_type == "else":
            # Pop the last ifdef/elif of the same level
            if len(self.hash_decisions) > 0:
                self.dbg(
                    "# HASH: Popping previous construct "
                    + popped_hash_type
                    + " for else"
                )
                popped_hash_decision = self.hash_decisions.pop()
                popped_hash_type = self.hash_types.pop()
                popped_hash_served = self.hash_served.pop()
                self.dbg(
                    "  Type: "
                    + popped_hash_type
                    + ",  Decision: "
                    + str(popped_hash_decision)
                    + ",  Served: "
                    + str(popped_hash_served)
                )

            if len(self.hash_decisions) > 0:
                self.last_hash_loc = len(self.hash_decisions) - 1
                last_hash_decision = self.hash_decisions[self.last_hash_loc]
            else:
                last_hash_decision = 1

            # if the current hash ifdef/elif already served, then else will be disabled
            if self.hash_curr_served:
                self.hash_curr_decision = 0
                self.hash_decisions.append(0)
                self.hash_types.append("else")
                self.hash_served.append(1)
            else:
                if last_hash_decision:
                    self.hash_curr_decision = 1
                    self.hash_decisions.append(1)
                    self.hash_types.append("else")
                    self.hash_served.append(1)
                else:
                    self.hash_curr_decision = 0
                    self.hash_decisions.append(0)
                    self.hash_types.append("else")
                    self.hash_served.append(1)

            self.dbg("# HASH: Pushing current construct else")
            if len(self.hash_decisions) > 0:
                self.dbg(self.hash_types)
                self.dbg(self.hash_decisions)
                self.dbg(self.hash_served)
        elif hash_ifdef_type == "endif":
            if len(self.hash_decisions) > 0:
                self.dbg(
                    "# HASH: Popping previous construct "
                    + popped_hash_type
                    + " for endif"
                )
                popped_hash_decision = self.hash_decisions.pop()
                popped_hash_type = self.hash_types.pop()
                popped_hash_served = self.hash_served.pop()
                self.dbg(
                    "  Type: "
                    + popped_hash_type
                    + ",  Decision: "
                    + str(popped_hash_decision)
                    + ",  Served: "
                    + str(popped_hash_served)
                )

                if len(self.hash_decisions) > 0:
                    self.last_hash_loc = len(self.hash_decisions) - 1
                    self.hash_curr_decision = self.hash_decisions[self.last_hash_loc]
                    self.hash_curr_type = self.hash_types[self.last_hash_loc]
                    self.hash_curr_served = self.hash_served[self.last_hash_loc]
                else:
                    # Out of all the ifdef and hence its enabled
                    self.hash_curr_decision = 1
                    self.hash_curr_type = ""
                    self.hash_curr_served = 0

            else:
                self.dbg(
                    "\nError: There is no pending #ifdef/#elif in the buffer, but reaching #endif at line "
                    + str(self.line_no)
                )
                print(
                    "\nError: There is no pending #ifdef/#elif in the buffer, but reaching #endif at line "
                    + str(self.line_no)
                )
                sys.exit(1)
        else:  # ifdef / ifndef / elif
            # for all other ifdef, ifndef, elif to process hash_ifdef_str evaluation
            # TODO: For elif, if ifdef is already served, then no need to evaluate the expression
            if len(self.hash_decisions) > 0:
                self.last_hash_loc = len(self.hash_decisions) - 1
                last_hash_decision = self.hash_decisions[self.last_hash_loc]
            else:
                last_hash_decision = 1

            if (
                (hash_ifdef_type == "elif" and self.hash_curr_served == 0)
                or hash_ifdef_type == "ifdef"
                or hash_ifdef_type == "ifndef"
            ):
                # Need to pop previous elif or ifdef or ifndef for elif case
                if hash_ifdef_type == "elif":
                    self.dbg(
                        "# HASH: Popping previous construct "
                        + popped_hash_type
                        + " for elif"
                    )
                    popped_hash_decision = self.hash_decisions.pop()
                    popped_hash_type = self.hash_types.pop()
                    popped_hash_served = self.hash_served.pop()
                    self.dbg(
                        "  Type: "
                        + popped_hash_type
                        + ",  Decision: "
                        + str(popped_hash_decision)
                        + ",  Served: "
                        + str(popped_hash_served)
                    )

                if hash_ifdef_str_regex:  # Check if this is without expression
                    # TODO: Need to add tick check here
                    if (
                        hash_ifdef_str in self.hash_defines
                    ):  # define is present in the hash database
                        if hash_ifdef_type == "ifndef":
                            self.hash_curr_decision = 0
                            self.hash_curr_type = hash_ifdef_type
                            self.hash_curr_served = 0
                        else:
                            # Current decision is set only if previous decision is 1
                            if last_hash_decision:
                                self.hash_curr_decision = 1
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1
                            else:
                                self.hash_curr_decision = 0
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1

                        self.hash_decisions.append(self.hash_curr_decision)
                        self.hash_types.append(self.hash_curr_type)
                        self.hash_served.append(self.hash_curr_served)
                    else:
                        if hash_ifdef_type == "ifndef":
                            if last_hash_decision:
                                self.hash_curr_decision = 1
                                self.hash_curr_served = 1
                                self.hash_curr_type = hash_ifdef_type
                            else:
                                self.hash_curr_decision = 0
                                self.hash_curr_served = 1
                                self.hash_curr_type = hash_ifdef_type
                        else:
                            self.hash_curr_decision = 0
                            self.hash_curr_served = 0
                            self.hash_curr_type = hash_ifdef_type

                        self.hash_decisions.append(self.hash_curr_decision)
                        self.hash_types.append(self.hash_curr_type)
                        self.hash_served.append(self.hash_curr_served)

                    self.dbg("# HASH: Pushing current construct " + self.hash_curr_type)
                    if len(self.hash_decisions) > 0:
                        self.dbg(self.hash_types)
                        self.dbg(self.hash_decisions)
                        self.dbg(self.hash_served)
                else:
                    # If ifdef has an expression, then we need to get the result of expression
                    # TODO: Need to add tick check here
                    ifdef_exp_val = self.hash_def_getval(hash_ifdef_str)

                    if hash_ifdef_type == "ifndef":
                        if ifdef_exp_val[1]:
                            self.hash_curr_decision = 0
                            self.hash_curr_type = hash_ifdef_type
                            self.hash_curr_served = 0
                        else:
                            if last_hash_decision:
                                self.hash_curr_decision = 1
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1
                            else:
                                self.hash_curr_decision = 0
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1

                        self.hash_decisions.append(self.hash_curr_decision)
                        self.hash_types.append(self.hash_curr_type)
                        self.hash_served.append(self.hash_curr_served)
                    else:
                        if ifdef_exp_val[1]:
                            if last_hash_decision:
                                self.hash_curr_decision = 1
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1
                            else:
                                self.hash_curr_decision = 0
                                self.hash_curr_type = hash_ifdef_type
                                self.hash_curr_served = 1
                        else:
                            self.hash_curr_decision = 0
                            self.hash_curr_type = hash_ifdef_type
                            self.hash_curr_served = 0

                        self.hash_decisions.append(self.hash_curr_decision)
                        self.hash_types.append(self.hash_curr_type)
                        self.hash_served.append(self.hash_curr_served)

                    self.dbg("# HASH: Pushing current construct " + self.hash_curr_type)
                    if len(self.hash_decisions) > 0:
                        self.dbg(self.hash_types)
                        self.dbg(self.hash_decisions)
                        self.dbg(self.hash_served)
            else:
                self.hash_curr_decision = 0

        self.dbg("# HASH: DECISION: " + str(self.hash_curr_decision))

        return self.hash_curr_decision

    def load_hash_include_file(self, hash_inc_file):
        """
        Function to parse an #include file
        """

        hash_inc_file_path = hash_inc_file
        found_hash_inc_file = 0

        if os.path.isfile(hash_inc_file):  # if the file exists
            found_hash_inc_file = 1
        else:
            for dir in self.incl_dirs:
                if not found_hash_inc_file:
                    hash_inc_file_path = str(dir) + "/" + str(hash_inc_file)
                    if os.path.isfile(hash_inc_file_path):
                        found_hash_inc_file = 1
                        hash_inc_file = hash_inc_file_path

        if not found_hash_inc_file:
            hash_inc_file_path_int = self.find_in_files(hash_inc_file)

            if hash_inc_file_path_int is not None:
                found_hash_inc_file = 1
                hash_inc_file_path = hash_inc_file_path_int

        if not found_hash_inc_file:
            self.dbg("\nError: Unable to find the #include file " + hash_inc_file)
            self.dbg("  List of search directories")
            print("\nError: Unable to find the #include file " + hash_inc_file)
            print("  List of search directories")
            self.found_error = 1

            for dir in self.incl_dirs:
                self.dbg("    " + str(dir))
                print("    " + str(dir))
            sys.exit(1)
        else:
            hash_inc_file_path = re.sub(r"\/\/", r"/", hash_inc_file_path)

            # TODO: if gen_dependencies:
            # dependencies['include_files'].append(hash_inc_file_path)

            self.dbg(
                "\n################################################################################"
            )
            self.dbg("### Loading #include file " + hash_inc_file_path + " ###")
            self.dbg(
                "################################################################################"
            )
            print("    - Loading #include file " + hash_inc_file_path)
            hash_incl_data = open(hash_inc_file_path, "r")
            self.header_files.append(hash_inc_file_path)
            m_line_no = 0
            m_hash_ifdef_en = 1
            m_block_comment = 0

            for hash_incl_line in hash_incl_data:
                m_line_no = m_line_no + 1

                # if the whole line is commented from the beginning
                m_single_comment_begin_start_regex = (
                    RE_SINGLE_COMMENT_BEGIN_START.search(hash_incl_line)
                )
                if m_single_comment_begin_start_regex:
                    continue

                # Removing single line comment at the end of a line
                hash_incl_line = re.sub(r"\s*\/\/.*", r"", hash_incl_line)

                # Removing block comment in a single line
                hash_incl_line = remove_single_line_comment(hash_incl_line)

                # Removing multiple space to single and no space at the end
                hash_incl_line = re.sub(r"\s+", r" ", hash_incl_line)
                hash_incl_line = re.sub(r"\s*$", r"", hash_incl_line)

                m_block_comment_begin_start_regex = RE_BLOCK_COMMENT_BEGIN_START.search(
                    hash_incl_line
                )
                m_block_comment_begin_regex = RE_BLOCK_COMMENT_BEGIN.search(
                    hash_incl_line
                )
                m_block_comment_end_regex = RE_BLOCK_COMMENT_END.search(hash_incl_line)

                if m_block_comment_end_regex:
                    m_block_comment = 0
                    continue

                if m_block_comment:
                    continue

                if m_block_comment_begin_start_regex:
                    m_block_comment = 1
                    continue
                elif m_block_comment_begin_regex:
                    m_block_comment = 1

                m_hash_ifdef_regex = RE_HASH_IFDEF.search(hash_incl_line)
                m_hash_ifndef_regex = RE_HASH_IFNDEF.search(hash_incl_line)
                m_hash_elif_regex = RE_HASH_ELIF.search(hash_incl_line)
                m_hash_else_regex = RE_HASH_ELSE.search(hash_incl_line)
                m_hash_endif_regex = RE_HASH_ENDIF.search(hash_incl_line)

                if m_hash_ifdef_regex:
                    m_hash_ifdef_en = self.hash_ifdef_proc(
                        "ifdef", m_hash_ifdef_regex.group(1)
                    )
                    continue
                elif m_hash_ifndef_regex:
                    m_hash_ifdef_en = self.hash_ifdef_proc(
                        "ifndef", m_hash_ifndef_regex.group(1)
                    )
                    continue
                elif m_hash_elif_regex:
                    m_hash_ifdef_en = self.hash_ifdef_proc(
                        "elif", m_hash_elif_regex.group(1)
                    )
                    continue
                elif m_hash_else_regex:
                    m_hash_ifdef_en = self.hash_ifdef_proc("else", "")
                    continue
                elif m_hash_endif_regex:
                    m_hash_ifdef_en = self.hash_ifdef_proc("endif", "")
                    continue

                if not m_hash_ifdef_en:  # If hash disables the code
                    continue
                else:  # if m_hash_ifdef_en:
                    ################################################################################
                    # #define processing
                    ################################################################################
                    m_hash_define_regex = RE_HASH_DEFINE.search(hash_incl_line)

                    if m_hash_define_regex:
                        self.hash_def_proc(m_hash_define_regex.group(1))
                        continue

                    ################################################################################
                    # #undef processing
                    ################################################################################
                    m_hash_undef_regex = RE_HASH_UNDEF.search(hash_incl_line)

                    if m_hash_undef_regex:
                        self.dbg(hash_incl_line)
                        if m_hash_undef_regex.group(1) not in self.hash_defines:
                            print(
                                "\nWarning: Unabed to find #define to undef\n"
                                + m_hash_undef_regex.group(0)
                                + "\n"
                            )
                        else:
                            del self.hash_defines[m_hash_undef_regex.group(1)]
                            self.dbg(
                                "  # Removed #define "
                                + m_hash_undef_regex.group(1)
                                + " for undef"
                            )

                        continue

                    ################################################################################
                    # Recursive #include processing
                    ################################################################################
                    m_hash_include_regex = RE_HASH_INCLUDE.search(hash_incl_line)

                    if m_hash_include_regex:
                        self.load_hash_include_file(m_hash_include_regex.group(1))
                        continue

            hash_incl_data.close()

        return

    def generate_code(self, module_name):
        """
        Main code generation function
        """

        doing_python = 0
        begin_python_space = ""
        block_comment = 0
        code_block = ""
        comment_indent = ""
        gather_fsm_data = 0
        codegen_skip = 0

        ram = memgen()
        ram_hls = memgen()
        ram_ecc = memgen()

        input_file = open(self.in_file, "r")
        self.in_lines = input_file.readlines()

        for line in self.in_lines:
            original_line = line
            self.line_no = self.line_no + 1

            ################################################################################
            # Gathering Stub output overriding vals from verilog files that are commented
            ################################################################################
            stubout_verilog_regex = RE_STUBOUT_VERILOG.search(line)

            if stubout_verilog_regex:
                self.stub_override_val[stubout_verilog_regex.group(2)] = (
                    stubout_verilog_regex.group(3)
                )

                if self.hash_ifdef_en:
                    self.lines.append(original_line)

                print(
                    "      # Overriding output value for "
                    + stubout_verilog_regex.group(2)
                    + " as "
                    + stubout_verilog_regex.group(3)
                )
                continue

            ################################################################################
            # if the whole line is commented from the beginning
            ################################################################################
            single_comment_begin_start_regex = RE_SINGLE_COMMENT_BEGIN_START.search(
                line
            )
            if single_comment_begin_start_regex:
                if self.hash_ifdef_en:
                    self.lines.append(original_line)

                continue

            ################################################################################
            # &BeginSkip and &EndSkip for codegen and parsing skip
            ################################################################################
            begin_skip_regex = RE_SKIP_BEGIN.search(line)
            end_skip_regex = RE_SKIP_END.search(line)

            if begin_skip_regex:
                codegen_skip = 1
                print("    - Turning Off Code Generator at line " + str(self.line_no))

                if self.hash_ifdef_en:
                    self.lines.append(original_line)

                continue
            elif end_skip_regex:
                codegen_skip = 0
                print("    - Turning On Code Generator at line " + str(self.line_no))

                if self.hash_ifdef_en:
                    self.lines.append(original_line)

                continue

            if codegen_skip:
                if self.hash_ifdef_en:
                    self.lines.append(original_line)

                continue

            ################################################################################
            # Gathering Stub output overriding vals
            ################################################################################
            stubout_regex = RE_STUBOUT.search(line)

            if stubout_regex:
                self.stub_override_val[stubout_regex.group(2)] = stubout_regex.group(3)
                print(
                    "      # Overriding output value for "
                    + stubout_regex.group(2)
                    + " as "
                    + stubout_regex.group(3)
                )
                ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                self.dbg(ampersand_line)
                self.lines.append(ampersand_line)
                continue

            ################################################################################
            # Block comment check
            ################################################################################
            block_comment_begin_start_regex = RE_BLOCK_COMMENT_BEGIN_START.search(line)
            block_comment_begin_regex = RE_BLOCK_COMMENT_BEGIN.search(line)
            block_comment_end_regex = RE_BLOCK_COMMENT_END.search(line)

            if block_comment_end_regex:
                block_comment = 0
                self.lines.append(original_line)
                continue

            if block_comment:
                self.lines.append(original_line)
                continue

            if block_comment_begin_start_regex:
                block_comment = 1
                self.lines.append(original_line)
                continue
            elif block_comment_begin_regex:
                block_comment = 1

            hash_ifdef_regex = RE_HASH_IFDEF.search(line)
            hash_ifndef_regex = RE_HASH_IFNDEF.search(line)
            hash_elif_regex = RE_HASH_ELIF.search(line)
            hash_else_regex = RE_HASH_ELSE.search(line)
            hash_endif_regex = RE_HASH_ENDIF.search(line)

            if hash_ifdef_regex:
                self.hash_ifdef_en = self.hash_ifdef_proc(
                    "ifdef", hash_ifdef_regex.group(1)
                )

                if not self.remove_code:
                    self.lines.append("// " + original_line)
                continue
            elif hash_ifndef_regex:
                self.hash_ifdef_en = self.hash_ifdef_proc(
                    "ifndef", hash_ifndef_regex.group(1)
                )

                if not self.remove_code:
                    self.lines.append("// " + original_line)
                continue
            elif hash_elif_regex:
                self.hash_ifdef_en = self.hash_ifdef_proc(
                    "elif", hash_elif_regex.group(1)
                )

                if not self.remove_code:
                    self.lines.append("// " + original_line)
                continue
            elif hash_else_regex:
                self.hash_ifdef_en = self.hash_ifdef_proc("else", "")

                if not self.remove_code:
                    self.lines.append("// " + original_line)
                continue
            elif hash_endif_regex:
                self.hash_ifdef_en = self.hash_ifdef_proc("endif", "")

                if not self.remove_code:
                    self.lines.append("// " + original_line)
                continue

            if not self.hash_ifdef_en:  # If hash disables the code
                if not self.remove_code:
                    self.lines.append("// " + original_line)
                    self.dbg("// " + original_line)
                continue
            else:  # if self.hash_ifdef_en:
                ################################################################################
                # Replace all the #define variables #{<VAR>} with values
                ################################################################################
                hash_var_replacement_regex = RE_HASH_VARIABLE.search(original_line)

                if hash_var_replacement_regex:
                    hash_list = RE_HASH_VARIABLE.findall(original_line)

                    for c_hash in hash_list:
                        c_hash_val = self.get_hash_defval(c_hash)
                        original_line = re.sub(
                            RE_HASH_VARIABLE_SYNTAX, str(c_hash_val), original_line, 1
                        )
                        line = re.sub(RE_HASH_VARIABLE_SYNTAX, str(c_hash_val), line, 1)

                ################################################################################
                # #define processing
                ################################################################################
                hash_define_regex = RE_HASH_DEFINE.search(line)

                if hash_define_regex:
                    self.hash_def_proc(hash_define_regex.group(1))
                    self.lines.append("// " + original_line)
                    continue

                ################################################################################
                # #undef processing
                ################################################################################
                hash_undef_regex = RE_HASH_UNDEF.search(line)

                if hash_undef_regex:
                    self.dbg(original_line)
                    if hash_undef_regex.group(1) not in self.hash_defines:
                        print(
                            "\nWarning: Unable to find #define to undef\n"
                            + hash_undef_regex.group(0)
                            + "\n"
                        )
                    else:
                        del self.hash_defines[hash_undef_regex.group(1)]
                        self.dbg(
                            "  # Removed #define "
                            + hash_undef_regex.group(1)
                            + " for undef"
                        )

                    continue

                ################################################################################
                # #include processing
                ################################################################################
                hash_include_regex = RE_HASH_INCLUDE.search(line)

                if hash_include_regex:
                    self.lines.append("// " + original_line)
                    self.load_hash_include_file(hash_include_regex.group(1))

                    continue

                ################################################################################
                # Embedded python script processing
                ################################################################################
                python_begin_regex = RE_PYTHON_BLOCK_BEGIN.search(line)
                python_end_regex = RE_PYTHON_BLOCK_END.search(line)
                single_python_regex = RE_PYTHON_SINGLE_LINE.search(line)
                variable_replacement_regex = RE_PYTHON_VARIABLE.search(line)

                if not doing_python and python_begin_regex:
                    begin_python_space = python_begin_regex.group(1)
                    doing_python = 1
                    code_block = ""
                    print(
                        "    - Executing embedded python code at line "
                        + str(self.line_no)
                    )

                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    comment_indent = python_begin_regex.group(1)
                    # auto_indent = comment_indent
                    continue
                elif doing_python and python_end_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    doing_python = 0

                    stdout_ = sys.stdout  # Keep track of the previous value.
                    stream = io.StringIO()
                    sys.stdout = stream

                    try:
                        exec(code_block)
                    except Exception:
                        print("Error in code:\n" + code_block + "\n")
                        self.found_error = 1
                        raise

                    sys.stdout = stdout_  # restore the previous stdout.
                    exec_data = stream.getvalue()
                    exec_data = stream.getvalue()
                    exec_data = re.sub(r"[\n]+$", r"", exec_data)
                    exec_data = re.sub(r"[\n]+", r"\n", exec_data)
                    exec_data_array = exec_data.split("\n")
                    stream.close()

                    # Inserting generated code for codegen parsing
                    c_line_no = 0
                    for c_line in exec_data_array:
                        exec_data_array[c_line_no] = (
                            begin_python_space + exec_data_array[c_line_no]
                        )
                        c_line_no = c_line_no + 1

                    self.in_lines[self.line_no : self.line_no] = exec_data_array

                    # for c_exec_line in exec_data_array:
                    # self.lines.append(begin_python_space + c_exec_line)

                    continue
                elif doing_python:
                    dum = re.sub(r"^(" + comment_indent + r")", r"", original_line)
                    code_block += dum
                    self.lines.append("// " + original_line)

                    continue
                elif not doing_python and single_python_regex:
                    begin_python_space = single_python_regex.group(1)
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    stdout_ = sys.stdout  # Keep track of the previous value.
                    stream = io.StringIO()
                    sys.stdout = stream

                    try:
                        exec(single_python_regex.group(3))

                    except Exception:
                        print(
                            "Error in Single Python Code:\n"
                            + single_python_regex.group(3)
                            + "\n"
                        )
                        self.found_error = 1
                        raise

                    sys.stdout = stdout_  # restore the previous stdout.
                    exec_data = stream.getvalue()
                    exec_data = re.sub(r"[\n]+$", r"", exec_data)
                    exec_data = re.sub(r"[\n]+", r"\n", exec_data)
                    exec_data_array = exec_data.split("\n")
                    stream.close()

                    # Inserting generated code for codegen parsing
                    c_line_no = 0
                    for c_line in exec_data_array:
                        exec_data_array[c_line_no] = (
                            begin_python_space + exec_data_array[c_line_no]
                        )
                        c_line_no = c_line_no + 1

                    self.in_lines[self.line_no : self.line_no] = exec_data_array

                    # for c_exec_line in exec_data_array:
                    # self.lines.append(begin_python_space + c_exec_line)

                    continue
                elif variable_replacement_regex:
                    my_replace = lambda m, g=globals(), l=locals(): str(
                        eval(m.group(1), g, l)
                    )
                    original_line = re.sub(
                        RE_PYTHON_VARIABLE, my_replace, original_line
                    )
                    line = re.sub(RE_PYTHON_VARIABLE, my_replace, line)

                ################################################################
                # &FSM Plugin
                ################################################################
                fsm_regex = RE_FSM.search(line)
                endfsm_regex = RE_ENDFSM.search(line)

                if fsm_regex and not gather_fsm_data:
                    fsm_begin_space = fsm_regex.group(1)
                    self.lines.append("// " + original_line)
                    gather_fsm_data = 1
                    fsm_data = ""
                    continue

                if gather_fsm_data:
                    if endfsm_regex:
                        ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                        self.lines.append(ampersand_line)
                        gather_fsm_data = 0

                        fsm_output = self.fsm(fsm_data)
                        fsm_output_list = re.split(r"\n", fsm_output)

                        for c_fsm_line in fsm_output_list:
                            self.lines.append(fsm_begin_space + c_fsm_line)

                        continue
                    else:
                        self.lines.append("// " + original_line)
                        fsm_data = fsm_data + original_line
                        continue

                ################################################################################
                # &fb_enflop / &fb_enflop_rs / &fb_enflop_rst Plugins
                ################################################################################
                fb_enflop_regex = RE_FB_ENFLOP.search(line)
                fb_enflop_rs_regex = RE_FB_ENFLOP_RS.search(line)
                fb_enflop_rst_regex = RE_FB_ENFLOP_RST.search(line)

                if fb_enflop_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    flop_begin_space = fb_enflop_regex.group(1)

                    flop_output = self.flop("fb_enflop", fb_enflop_regex.group(2))
                    flop_output = re.sub(r"[\n]+", r"\n", flop_output)
                    flop_output_list = re.split(r"\n", flop_output)

                    for c_flop_line in flop_output_list:
                        if c_flop_line != "":
                            self.lines.append(flop_begin_space + c_flop_line)

                    continue

                if fb_enflop_rs_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    flop_begin_space = fb_enflop_rs_regex.group(1)

                    flop_output = self.flop("fb_enflop_rs", fb_enflop_rs_regex.group(2))

                    flop_output_list = re.split(r"\n", flop_output)

                    for c_flop_line in flop_output_list:
                        if c_flop_line != "":
                            self.lines.append(flop_begin_space + c_flop_line)

                    continue

                if fb_enflop_rst_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    flop_begin_space = fb_enflop_rst_regex.group(1)

                    flop_output = self.flop(
                        "fb_enflop_rst", fb_enflop_rst_regex.group(2)
                    )

                    flop_output_list = re.split(r"\n", flop_output)

                    for c_flop_line in flop_output_list:
                        if c_flop_line != "":
                            self.lines.append(flop_begin_space + c_flop_line)

                    continue

                ################################################################################
                # &Pipe Plugin
                ################################################################################
                pipe_regex = RE_PIPE.search(line)

                if pipe_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    pipe_begin_space = pipe_regex.group(1)
                    pipe_data = pipe_regex.group(2)

                    pipe_output = self.pipe(pipe_data)

                    pipe_output_list = re.split(r"\n", pipe_output)

                    for c_pipe_line in pipe_output_list:
                        self.lines.append(pipe_begin_space + c_pipe_line)

                    continue

                ################################################################################
                # &MemGen Plugin
                ################################################################################
                memgen_regex = RE_MEMGEN.search(line)
                hls_memgen_regex = RE_MEMGEN_HLS.search(line)
                ecc_memgen_regex = RE_MEMGEN_ECC.search(line)

                if memgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    memgen_begin_space = memgen_regex.group(1)
                    memgen_data = memgen_regex.group(2)
                    memgen_data_split = re.split(
                        r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", memgen_data
                    )
                    memgen_data_split = [i.replace('"', "") for i in memgen_data_split]
                    memgen_data_split = [i.replace(" ", "") for i in memgen_data_split]
                    ram_prefix = str(memgen_data_split[0])
                    ram_width = int(memgen_data_split[1])
                    ram_depth = int(memgen_data_split[2])
                    ram_type = str(memgen_data_split[3])
                    ram_pipe_en = int(memgen_data_split[4])
                    ram_bitwrite_en = int(memgen_data_split[5])
                    ram_rst = str(memgen_data_split[6])
                    ram_list = None

                    if (
                        ram_type == "2P"
                        or ram_type == "2p"
                        or ram_type == "2F"
                        or ram_type == "2f"
                    ):
                        ram_wclk = str(memgen_data_split[7])
                        ram_rclk = str(memgen_data_split[8])
                        if len(memgen_data_split) > 9:
                            ram_list = memgen_data_split[9]
                    elif (
                        ram_type == "1P"
                        or ram_type == "1p"
                        or ram_type == "1F"
                        or ram_type == "1f"
                    ):
                        ram_wclk = str(memgen_data_split[7])
                        ram_rclk = str(memgen_data_split[7])
                        if len(memgen_data_split) > 8:
                            ram_list = memgen_data_split[8]
                    else:
                        self.dbg("\nError: SRAM Type passed in incorrect " + ram_type)
                        print("\nError: SRAM Type passed in incorrect " + ram_type)

                    ram.set_ram_info(
                        ram_prefix,
                        ram_width,
                        ram_depth,
                        ram_type,
                        ram_pipe_en,
                        ram_bitwrite_en,
                        ram_rst,
                        ram_wclk,
                        ram_rclk,
                    )
                    ram.set_phy_info()
                    if ram_list:
                        ram.set_loop(ram_list)

                    # Generate ram wrapper module only in build mode
                    if self.gen_dependencies:
                        ram.verilog_write()

                    ram_wrapper_name = ram.returnWrapperName()

                    ram_inst_data = ram.returnInstance()

                    ram.clear_ram_info()

                    memgen_output_list = re.split(r"\n", ram_inst_data)

                    # Appending the instance commands
                    for c_memgen_line in memgen_output_list:
                        self.lines.append(memgen_begin_space + c_memgen_line)

                    continue

                ################################################################################
                # &HlsMemGen Plugin
                ################################################################################
                if hls_memgen_regex:
                    hls_ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(hls_ampersand_line)
                    hls_memgen_begin_space = hls_memgen_regex.group(1)
                    hls_memgen_data = hls_memgen_regex.group(2)
                    hls_memgen_data_split = re.split(
                        r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", hls_memgen_data
                    )
                    hls_memgen_data_split = [
                        i.replace('"', "") for i in hls_memgen_data_split
                    ]
                    hls_memgen_data_split = [
                        i.replace(" ", "") for i in hls_memgen_data_split
                    ]

                    ram_prefix = str(hls_memgen_data_split[0])
                    ram_width = int(hls_memgen_data_split[1])
                    ram_depth = int(hls_memgen_data_split[2])
                    ram_type = str(hls_memgen_data_split[3])
                    ram_pipe_en = int(hls_memgen_data_split[4])
                    ram_bitwrite_en = int(hls_memgen_data_split[5])
                    ram_rst = str(hls_memgen_data_split[6])
                    ram_list = None

                    if (
                        ram_type == "2P"
                        or ram_type == "2p"
                        or ram_type == "2F"
                        or ram_type == "2f"
                    ):
                        ram_wclk = str(hls_memgen_data_split[7])
                        ram_rclk = str(hls_memgen_data_split[8])
                        if len(hls_memgen_data_split) > 9:
                            ram_list = hls_memgen_data_split[9]
                    elif (
                        ram_type == "1P"
                        or ram_type == "1p"
                        or ram_type == "1F"
                        or ram_type == "1f"
                    ):
                        ram_wclk = str(hls_memgen_data_split[7])
                        ram_rclk = str(hls_memgen_data_split[7])
                        if len(hls_memgen_data_split) > 8:
                            ram_list = hls_memgen_data_split[8]
                    else:
                        self.dbg(
                            "\nError: HLS SRAM Type passed in incorrect " + ram_type
                        )
                        print(
                            ("\nError: HLS SRAM Type passed in incorrect " + ram_type)
                        )

                    ram_hls.set_ram_info(
                        ram_prefix,
                        ram_width,
                        ram_depth,
                        ram_type,
                        ram_pipe_en,
                        ram_bitwrite_en,
                        ram_rst,
                        ram_wclk,
                        ram_rclk,
                    )
                    ram_hls.set_hls()
                    ram_hls.set_phy_info()
                    if ram_list:
                        ram_hls.set_loop(ram_list)

                    # Generate ram wrapper module only in build mode
                    if self.gen_dependencies:
                        ram_hls.verilog_write()

                    hls_ram_wrapper_name = ram_hls.returnWrapperName()

                    hls_ram_inst_data = ram_hls.returnInstance()
                    ram_hls.clear_ram_info()

                    hls_memgen_output_list = re.split(r"\n", hls_ram_inst_data)

                    # Appending the instance commands
                    for hls_c_memgen_line in hls_memgen_output_list:
                        self.lines.append(hls_memgen_begin_space + hls_c_memgen_line)

                    continue

                ################################################################################
                # &ECCMemGen Plugin
                ################################################################################
                if ecc_memgen_regex:
                    ecc_ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ecc_ampersand_line)
                    ecc_memgen_begin_space = ecc_memgen_regex.group(1)
                    ecc_memgen_data = ecc_memgen_regex.group(2)
                    ecc_memgen_data_split = re.split(
                        r",(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)", ecc_memgen_data
                    )
                    ecc_memgen_data_split = [
                        i.replace('"', "") for i in ecc_memgen_data_split
                    ]
                    ecc_memgen_data_split = [
                        i.replace(" ", "") for i in ecc_memgen_data_split
                    ]

                    ram_prefix = str(ecc_memgen_data_split[0])
                    ram_width = int(ecc_memgen_data_split[1])
                    ram_depth = int(ecc_memgen_data_split[2])
                    ram_type = str(ecc_memgen_data_split[3])
                    ram_pipe_en = int(ecc_memgen_data_split[4])
                    ram_bitwrite_en = int(ecc_memgen_data_split[5])
                    ram_rst = str(ecc_memgen_data_split[6])
                    ram_list = None

                    if ram_type == "2P" or ram_type == "2p":
                        ram_wclk = str(ecc_memgen_data_split[7])
                        ram_rclk = str(ecc_memgen_data_split[8])
                        if len(ecc_memgen_data_split) > 9:
                            ram_list = ecc_memgen_data_split[9]
                    elif ram_type == "1P" or ram_type == "1p":
                        ram_wclk = str(ecc_memgen_data_split[7])
                        ram_rclk = str(ecc_memgen_data_split[7])
                        if len(ecc_memgen_data_split) > 8:
                            ram_list = ecc_memgen_data_split[8]
                    else:
                        self.dbg(
                            "\nError: ECC SRAM Type passed in incorrect " + ram_type
                        )
                        print("\nError: ECC SRAM Type passed in incorrect " + ram_type)
                    if ram_bitwrite_en == 1:
                        self.dbg(
                            "\nError: ECC SRAM Type passed in incorrect "
                            + ram_bitwrite_en
                        )
                        print(
                            "\nError: ECC SRAM Type passed in incorrect "
                            + ram_bitwrite_en
                        )
                        ram_bitwrite_en = 0
                    ####
                    # Calculation on Width and Depth for ECC
                    # for example: 128 X 320 - 2(128 X 160)
                    # Depth remain same - 128
                    # 320 - 2^(r-1) >= r+w
                    ####
                    ecc_ram_width = calculate_ecc_width(ram_width)
                    ram_ecc.set_ram_info(
                        ram_prefix,
                        ram_width,
                        ram_depth,
                        ram_type,
                        ram_pipe_en,
                        ram_bitwrite_en,
                        ram_rst,
                        ram_wclk,
                        ram_rclk,
                    )
                    ram_ecc.set_ecc(ecc_ram_width)
                    ram_ecc.set_phy_info()
                    if ram_list:
                        ram_ecc.set_loop(ram_list)

                    # Generate ram wrapper module only in build mode
                    if self.gen_dependencies:
                        ram_ecc.verilog_write()

                    ecc_ram_wrapper_name = ram_ecc.returnWrapperName()

                    ecc_ram_inst_data = ram_ecc.returnInstance()
                    ram_ecc.clear_ram_info()

                    ecc_memgen_output_list = re.split(r"\n", ecc_ram_inst_data)

                    # Appending the instance commands
                    for ecc_c_memgen_line in ecc_memgen_output_list:
                        self.lines.append(ecc_memgen_begin_space + ecc_c_memgen_line)

                    continue

                ################################################################################
                # &ClockGen Plugin
                ################################################################################
                clockgen_regex = RE_CLOCKGEN.search(line)

                if clockgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    clkgen_begin_space = clockgen_regex.group(1)
                    # Fetch the first argument of the &ClockGen and use it as input clock
                    clkgen_inclk = clockgen_regex.group(2).split(",", 1)[0].strip()
                    # Fetch the second argument of the &ClockGen and strip "double quotes" and whitespaces
                    clkgen_outclk_list = (
                        clockgen_regex.group(2)
                        .split(",", 1)[1]
                        .replace('"', "")
                        .strip()
                    )
                    # Only expand to CG instances if the gated output clock list is not empty.
                    if clkgen_outclk_list:
                        for clkgen_outclk in clkgen_outclk_list.split(","):
                            clkgen_outclk = clkgen_outclk.strip()
                            clkgen_str = (
                                """
&BeginInstance fb_cgc_ovrd  u_{1}_clkgate;
&Connect free_running_clk_i     {0};
&Connect enable_i               {1}_clken;
&Connect override_en_i          {1}_clken_ovrd;
&Connect test_enable_i          1'b0;
&Connect gated_clk_o            {1}_clk;
&EndInstance;
"""
                            ).format(clkgen_inclk, clkgen_outclk)
                            ### Dump out line by line keeping USER's indentation

                            clk_output_list = re.split(r"\n", clkgen_str)

                            for clkgen_line in clk_output_list:
                                self.lines.append(clkgen_begin_space + clkgen_line)

                    continue

                clockgen_v2_regex = RE_CLOCKGEN_V2.search(line)

                if clockgen_v2_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)
                    clkgen_begin_space = clockgen_v2_regex.group(1)
                    # Fetch the first argument of the &ClockGen and use it as input clock
                    clkgen_inclk = clockgen_v2_regex.group(2).split(",", 1)[0].strip()
                    # Fetch the second argument of the &ClockGen and strip "double quotes" and whitespaces
                    clkgen_outclk_list = (
                        clockgen_v2_regex.group(2)
                        .split(",", 1)[1]
                        .replace('"', "")
                        .strip()
                    )
                    # Only expand to CG instances if the gated output clock list is not empty.
                    if clkgen_outclk_list:
                        for clkgen_outclk in clkgen_outclk_list.split(","):
                            clkgen_outclk = clkgen_outclk.strip()
                            clkgen_str = (
                                """
&BeginInstance fb_cgc_ovrd_en_dis  u_{1}_clkgate;
&Connect free_running_clk_i     {0};
&Connect enable_i               {1}_clken;
&Connect override_en_i          {1}_clken_ovrd_en;
&Connect override_dis_i         {1}_clken_ovrd_dis;
&Connect test_enable_i          1'b0;
&Connect gated_clk_o            {1}_clk;
&EndInstance;
"""
                            ).format(clkgen_inclk, clkgen_outclk)
                            ### Dump out line by line keeping USER's indentation

                            clk_output_list = re.split(r"\n", clkgen_str)

                            for clkgen_line in clk_output_list:
                                self.lines.append(clkgen_begin_space + clkgen_line)

                    continue

                ################################################################################
                # &SyncGen Plugin
                # &SyncGen("<Prefix>", "<CLK>", "<RST>", "<DATAIN>", "<DATAOUT", "<TEST_ENABLE>");
                # <TEST_ENABLE> is optional and connect test_enable
                ################################################################################
                syncgen_regex = RE_SYNCGEN.search(line)

                if syncgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    syncgen_begin_space = syncgen_regex.group(1)

                    # Removing " and space if any by user
                    syncgen_args = re.sub(r'[\s"]', r"", syncgen_regex.group(2))
                    syncgen_args_list = syncgen_args.split(",")

                    if len(syncgen_args_list) < 5:
                        print("Error: &SyncGen plugin arguments missing")
                        print(original_line)
                        sys.exit(1)

                    # Extracting args
                    syncgen_prefix = syncgen_args_list[0]
                    syncgen_clk = syncgen_args_list[1]
                    syncgen_rst = syncgen_args_list[2]
                    syncgen_datain = syncgen_args_list[3]
                    syncgen_dataout = syncgen_args_list[4]

                    if len(syncgen_args_list) > 5:
                        syncgen_test_enable = syncgen_args_list[5]
                    else:
                        syncgen_test_enable = "test_enable"

                    syncgen_str = (
                        """
&BeginInstance fb_sync2  u_{0}_fb_sync2;
&Connect clk_i          {1};
&Connect reset_n_i      {2};
&Connect data_i         {3};
&Connect sync_data_o    {4};
&Connect test_enable_i  {5};
&EndInstance;
"""
                    ).format(
                        syncgen_prefix,
                        syncgen_clk,
                        syncgen_rst,
                        syncgen_datain,
                        syncgen_dataout,
                        syncgen_test_enable,
                    )

                    syncgen_output_list = re.split(r"\n", syncgen_str)

                    for syncgen_line in syncgen_output_list:
                        self.lines.append(syncgen_begin_space + syncgen_line)

                    continue

                ################################################################################
                # &SyncGen3 Plugin
                # &SyncGen3("<Prefix>", "<CLK>", "<RST>", "<DATAIN>", "<DATAOUT", "<TEST_ENABLE>");
                # <TEST_ENABLE> is optional and connect test_enable
                ################################################################################
                syncgen_regex = RE_SYNCGEN3.search(line)

                if syncgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    syncgen_begin_space = syncgen_regex.group(1)

                    # Removing " and space if any by user
                    syncgen_args = re.sub(r'[\s"]', r"", syncgen_regex.group(2))
                    syncgen_args_list = syncgen_args.split(",")

                    if len(syncgen_args_list) < 5:
                        print("Error: &SyncGen plugin arguments missing")
                        print(original_line)
                        sys.exit(1)

                    # Extracting args
                    syncgen_prefix = syncgen_args_list[0]
                    syncgen_clk = syncgen_args_list[1]
                    syncgen_rst = syncgen_args_list[2]
                    syncgen_datain = syncgen_args_list[3]
                    syncgen_dataout = syncgen_args_list[4]

                    if len(syncgen_args_list) > 5:
                        syncgen_test_enable = syncgen_args_list[5]
                    else:
                        syncgen_test_enable = "test_enable"

                    syncgen_str = (
                        """
                        &BeginInstance fb_sync3  u_{0}_fb_sync3;
                        &Connect clk_i          {1};
                        &Connect reset_n_i      {2};
                        &Connect data_i         {3};
                        &Connect sync_data_o    {4};
                        &Connect test_enable_i  {5};
                        &EndInstance;
                        """
                    ).format(
                        syncgen_prefix,
                        syncgen_clk,
                        syncgen_rst,
                        syncgen_datain,
                        syncgen_dataout,
                        syncgen_test_enable,
                    )

                    syncgen_output_list = re.split(r"\n", syncgen_str)

                    for syncgen_line in syncgen_output_list:
                        self.lines.append(syncgen_begin_space + syncgen_line)

                    continue

                ################################################################################
                # &ClockResetGen Plugin instantiates clock and reset syncronizer from free
                # running clock and power on reset.
                # &ClockResetGen(<source_clk>, <reset_in>, "<outclk_prefix>")
                # outclk_prefix can be one or more separated by ,
                ################################################################################
                clockresetgen_regex = RE_CLOCKRESETGEN.search(line)

                if clockresetgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    clockresetgen_begin_space = clockresetgen_regex.group(1)
                    clockresetgen_args = re.sub(
                        r'[\s"]', r"", clockresetgen_regex.group(2)
                    )
                    clockresetgen_args_list = clockresetgen_args.split(",")

                    # Removing " if any by user
                    clkgen_inclk = clockresetgen_args_list[0]

                    # Extracting clock_in
                    clkgen_inrst = clockresetgen_args_list[1]

                    # Removing first two args
                    del clockresetgen_args_list[0:2]

                    # Only expand to CG instances if the gated output clock list is not empty.
                    if clockresetgen_args_list:
                        for clkgen_outclk in clockresetgen_args_list:
                            clkgen_outclk = clkgen_outclk.strip()
                            clkgen_str = (
                                """
&BeginInstance fb_clkrst u_{0}_fb_clkrst_unit;
"""
                            ).format(clkgen_outclk)

                            clkgen_str += (
                                """
&Connect free_running_clk_i {0};
&Connect wait_cycles_i 4'd15;
&Connect power_on_reset_n_i {1};
&Connect sw_rst_n_i {2}_sw_reset_n;
&Connect ip_clk_enable_i {2}_clken;
&Connect test_enable_i test_enable;
&Connect clk_o {2}_clk;
&Connect rst_n_o {2}_reset_n;
&EndInstance;
"""
                            ).format(clkgen_inclk, clkgen_inrst, clkgen_outclk)

                            clk_output_list = re.split(r"\n", clkgen_str)

                            for clkgen_line in clk_output_list:
                                self.lines.append(
                                    clockresetgen_begin_space + clkgen_line
                                )

                    continue

                ################################################################################
                # &ArtClockResetGen Plugin instantiates clock and reset syncronizer from free
                # running clock and power on reset.
                # &ArtClockResetGen(<source_clk>, <reset_in>, "<outclk_prefix>")
                # outclk_prefix can be one or more separated by ,
                ################################################################################

                artclockresetgen_regex = RE_ARTCLOCKRESETGEN.search(line)

                if artclockresetgen_regex:
                    ampersand_line = re.sub(r"&", r"//&", original_line, 1)
                    self.lines.append(ampersand_line)

                    artclockresetgen_begin_space = artclockresetgen_regex.group(1)
                    artclockresetgen_args = re.sub(
                        r'[\s"]', r"", artclockresetgen_regex.group(2)
                    )
                    artclockresetgen_args_list = artclockresetgen_args.split(",")

                    # Removing " if any by user
                    artclkgen_inclk = artclockresetgen_args_list[0]

                    # Extracting clock_in
                    artclkgen_inrst = artclockresetgen_args_list[1]

                    # Removing first two args
                    del artclockresetgen_args_list[0:2]

                    # Only expand to CG instances if the gated output clock list is not empty.
                    if artclockresetgen_args_list:
                        for artclkgen_outclk in artclockresetgen_args_list:
                            artclkgen_outclk = artclkgen_outclk.strip()
                            artclkgen_str = (
                                """
&BeginInstance fb_clkrst u_{0}_fb_clkrst_unit;
"""
                            ).format(artclkgen_outclk)

                            artclkgen_str += (
                                """
&Connect free_running_clk_i {0};
&Connect wait_cycles_i 5'hf;
&Connect power_on_reset_n_i {1};
&Connect sw_rst_n_i {2}_sw_reset_n;
&Connect ip_clk_enable_i {2}_clken;
&Connect test_enable_i test_enable;
&Connect clk_o {2}_clk;
&Connect rst_n_o {2}_reset_n;
&EndInstance;
"""
                            ).format(artclkgen_inclk, artclkgen_inrst, artclkgen_outclk)

                            clk_output_list = re.split(r"\n", artclkgen_str)

                            for artclkgen_line in clk_output_list:
                                self.lines.append(
                                    artclockresetgen_begin_space + artclkgen_line
                                )

                    continue

                ################################################################################
                # &Posedge, &Negedge, &Clock, &SyncReset and &Asyncreset
                ################################################################################
                clock_regex = RE_CLOCK.search(line)

                if clock_regex:
                    self.clock = clock_regex.group(1)
                    self.lines.append(original_line)
                    continue

                asyncreset_regex = RE_ASYNCRESET.search(line)

                if asyncreset_regex:
                    self.async_reset = asyncreset_regex.group(1)
                    self.reset_type = "ASYNC"
                    self.lines.append(original_line)
                    continue

                syncreset_regex = RE_SYNCRESET.search(line)

                if syncreset_regex:
                    self.sync_reset = syncreset_regex.group(1)
                    self.reset_type = "SYNC"
                    self.lines.append(original_line)
                    continue

                posedge_regex = RE_R_POSEDGE.search(line)

                if posedge_regex:
                    self.lines.append(original_line)

                    if self.parsing_format == "systemverilog":
                        if self.reset_type == "ASYNC":
                            self.lines.append(
                                posedge_regex.group(1)
                                + "always_ff @ (posedge "
                                + self.clock
                                + " or negedge "
                                + self.async_reset
                                + ") begin"
                            )
                        else:
                            self.lines.append(
                                posedge_regex.group(1)
                                + "always_ff @ (posedge "
                                + self.clock
                                + ") begin"
                            )
                    else:
                        if self.reset_type == "ASYNC":
                            self.lines.append(
                                posedge_regex.group(1)
                                + "always @ (posedge "
                                + self.clock
                                + " or negedge "
                                + self.async_reset
                                + ") begin"
                            )
                        else:
                            self.lines.append(
                                posedge_regex.group(1)
                                + "always @ (posedge "
                                + self.clock
                                + ") begin"
                            )

                    continue

                negedge_regex = RE_R_NEGEDGE.search(line)

                if negedge_regex:
                    self.lines.append(original_line)

                    if self.parsing_format == "systemverilog":
                        if self.reset_type == "ASYNC":
                            self.lines.append(
                                negedge_regex.group(1)
                                + "always_ff @ (negedge "
                                + self.clock
                                + " or negedge "
                                + self.async_reset
                                + ") begin"
                            )
                        else:
                            self.lines.append(
                                negedge_regex.group(1)
                                + "always_ff @ (negedge "
                                + self.clock
                                + ") begin"
                            )
                    else:
                        if self.reset_type == "ASYNC":
                            self.lines.append(
                                negedge_regex.group(1)
                                + "always @ (negedge "
                                + self.clock
                                + " or negedge "
                                + self.async_reset
                                + ") begin"
                            )
                        else:
                            self.lines.append(
                                negedge_regex.group(1)
                                + "always @ (negedge "
                                + self.clock
                                + ") begin"
                            )

                    continue

                endnegedge_regex = RE_R_ENDNEGEDGE.search(line)

                if endnegedge_regex:
                    self.lines.append(endnegedge_regex.group(1) + "  end")

                    self.lines.append(original_line)
                    continue

                endposgedge_regex = RE_R_ENDPOSEDGE.search(line)

                if endposgedge_regex:
                    self.lines.append(endposgedge_regex.group(1) + "  end")

                    self.lines.append(original_line)
                    continue

                ################################################################################
                # Gather the list of functions in the input file
                ################################################################################
                function_regex = RE_FUNCTION.search(line)

                if function_regex:
                    function_name1_regex = RE_FUNCTION_NAME1.search(line)
                    function_name2_regex = RE_FUNCTION_NAME2.search(line)
                    if function_name1_regex:
                        try:
                            package_name
                            function_name = (
                                package_name + "::" + function_name1_regex.group(1)
                            )
                        except NameError:
                            function_name = function_name1_regex.group(1)

                        self.dbg(
                            "\n### Skipping function "
                            + function_name
                            + " at "
                            + str(self.line_no)
                        )
                        self.functions_list[function_name] = {}
                        self.functions_list[function_name]["name"] = function_name

                        self.lines.append(original_line)
                        continue
                    elif function_name2_regex:
                        try:
                            package_name
                            function_name = (
                                package_name + "::" + function_name2_regex.group(1)
                            )
                        except NameError:
                            function_name = function_name2_regex.group(1)

                        self.dbg(
                            "\n### Skipping function "
                            + function_name
                            + " at "
                            + str(self.line_no)
                        )
                        self.functions_list[function_name] = {}
                        self.functions_list[function_name]["name"] = function_name

                        self.lines.append(original_line)
                        continue
                    else:
                        self.dbg(
                            "\nError: Unable to find function name. Might be due to missing ;"
                        )
                        self.dbg(original_line + "\n")
                        print(
                            "\nError: Unable to find function name. Might be due to missing ;"
                        )
                        print(line + "\n")
                        self.found_error = 1

            self.lines.append(original_line)

        if self.debug:
            self.dbg_file.close()

        input_file.close()

    def fsm(self, inp_str):
        """
        FSM plugin code generation
        """

        result = re.split(r"FSM_REG|FSM_INIT|FSM_DEFAULT|FSM_STATES", inp_str)
        reg = result[1]
        init = result[2]
        default = result[3]
        state = result[4]

        reg_l = []
        init_l = ""
        default_l = ""
        st_l = []
        st_idx = -1
        st_con = {}

        str_rst = ""
        str_reg = ""
        clken = ""
        ostr = "\n"

        regs = re.split(r"\n", reg)
        reg_idx = -1
        for line in regs:
            line = line.rstrip()
            match = re.search(r"\<\-\s*(\S+)$", line)

            if match:
                clken = match.group(1)

            match = re.search(r"\s*(\S+)\s*\<\s*(\S+)\s*=\s*(\S+)\s*\;", line)

            if match:
                reg_idx += 1
                str_rst += " " * 9 + match.group(1) + " <= " + match.group(2) + ";"
                if reg_idx > 0:
                    str_reg += " " * 9 + match.group(1) + " <= " + match.group(3) + ";"
                else:
                    str_reg_c = match.group(1)
                    str_reg_n = match.group(3)

        inits = re.split(r"\n", init)

        for line in inits:
            line = line.rstrip()
            match = re.search(r"\s*(\S+)\s*=\s*(\S+)\s*\;", line)

            if match:
                init_l += " " * 6 + match.group(1) + " = " + match.group(2) + ";\n"

        defaults = re.split(r"\n", default)
        for line in defaults:
            line = line.rstrip()
            match = re.search(r"\s*(\S+)\s*=\s*(\S+)\s*\;", line)

            if match:
                default_l += " " * 12 + match.group(1) + " = " + match.group(2) + ";\n"

        states = re.split(r"\n", state)
        tmp_assign = ""
        ext_assign = 1
        for line in states:
            line = line.rstrip()
            match = re.search(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\:", line)

            if match:
                ext_assign = 1
                if st_idx >= 0:
                    st_con[st_idx].append(tmp_assign)
                tmp_assign = ""
                st_l.append(match.group(1))
                st_idx += 1
                st_con[st_idx] = []
                ext_assign = 1

            else:
                match = re.search(r"\s*(\S+)\s*\<\-\s*(.+);", line)

                if match:
                    ext_assign = 0
                    st_con[st_idx].append(tmp_assign)
                    tmp_assign = ""
                    st_con[st_idx].append(match.group(1))
                    st_con[st_idx].append(match.group(2))
                else:
                    match = re.search(r"(.+);", line.lstrip())
                    if match:
                        if ext_assign:
                            tmp_assign += " " * 12
                        else:
                            tmp_assign += " " * 15
                        tmp_assign += match.group(1) + ";\n"
        st_con[st_idx].append(tmp_assign)

        log2_w = (
            6
            if (st_idx >= 32)
            else (
                5
                if (st_idx >= 16)
                else (
                    4
                    if (st_idx >= 8)
                    else 3
                    if (st_idx >= 4)
                    else 2
                    if (st_idx >= 2)
                    else 1
                )
            )
        )
        log2_ex = st_idx == (1 << log2_w)

        for idx in range(0, st_idx + 1):
            state_name = st_l[idx]
            ostr += (
                "   localparam "
                + state_name
                + " = "
                + str(log2_w)
                + "'d"
                + str(idx)
                + ";\n"
            )

        ostr += "\n   always @(posedge clk or negedge rst ) begin\n"
        ostr += "      if (! rst ) begin\n"
        ostr += str_rst
        ostr += "\n      end"

        if (clken == "1") or (clken == "1'b1") or (clken == ""):
            ostr += " else begin\n"
        else:
            ostr += " else if ( " + clken + " ) begin\n"

        ostr += str_reg
        ostr += (
            " " * 9
            + str_reg_c
            + "["
            + str(log2_w - 1)
            + ":0] <= "
            + str_reg_n
            + "["
            + str(log2_w - 1)
            + ":0];"
        )
        ostr += "\n      end\n   end\n\n"

        ostr += "   always @(*) begin\n"
        ostr += init_l + "\n"
        ostr += "      case (" + str_reg_c + ")\n"

        for idx in range(0, st_idx + 1):
            ostr += " " * 9 + st_l[idx] + " : begin\n"
            ostr += st_con[idx][0]

            for tran in range(1, len(st_con[idx]), 3):
                state_togo = st_con[idx][tran]
                state_cond = st_con[idx][tran + 1]

                if (state_cond == "1") or (state_cond == "1'b1") or (state_cond == ""):
                    ostr += " " * 12 + "end else begin\n"
                else:
                    ostr += (
                        " " * 12 + "end else if (" + state_cond + ") begin\n"
                        if (tran > 1)
                        else " " * 12 + "if (" + state_cond + " )begin\n"
                    )

                ostr += " " * 15 + str_reg_n + " = " + state_togo + ";\n"
                ostr += st_con[idx][tran + 2]

            ostr += " " * 12 + "end\n"
            ostr += " " * 9 + "end\n\n"
        if log2_ex != 0:
            ostr += "         default: begin\n"
            ostr += default_l
            ostr += "         end\n"
        ostr += "      endcase\n"
        ostr += "   end\n\n"
        ostr = ostr.replace(" clk ", " " + self.clock + " ")
        ostr = ostr.replace(" rst )", " " + self.async_reset + " )")
        return ostr

    def pipe(self, inp_str):
        """
        Pipe plugin code generation
        """

        arg_list = inp_str.split(",")
        pipe_type = arg_list[0].strip()
        pipe_width = arg_list[1].strip()

        match = re.match(r"\d+", pipe_width)
        match2 = re.match(r"(`)?(\w+)", pipe_width)
        if match:
            data_width = str((int(pipe_width) - 1)) + " :0"
        elif match2:
            width_str = match2.group(2)
            if match2.group(1) is None:
                width_pref = ""
            else:
                width_pref = match2.group(1)
            data_width = "{0}{1}-1:0".format(width_pref, width_str)
        else:
            data_width = pipe_width + " -1 :0"

        inp_name = arg_list[2].strip()
        outp_name = arg_list[3].strip()

        sr_str = """

assign set_skid_valid = inp_valid & !skid_valid & outp_stall;
assign clr_skid_valid = skid_valid & !outp_stall;
assign skid_valid_nxt = set_skid_valid? 1'b1 : clr_skid_valid? 1'b0 : skid_valid;

always_ff @ (posedge clk or negedge rst ) begin
    if ( !rst ) begin
        skid_valid <= 1'b0;
    end
    else begin
        skid_valid <= skid_valid_nxt;
    end
end

assign inp_stall = skid_valid;

always_ff @(posedge clk or negedge rst ) begin
    if ( !rst ) begin
        skid_data <= '0;
    end
    else if ( set_skid_valid ) begin
        skid_data[WIDTH] <= inp_data[WIDTH];
    end
end

assign outp_valid = skid_valid ? 1'b1 : inp_valid;
assign outp_data[WIDTH] = skid_valid ? skid_data : inp_data;

"""
        sv_str = """

assign inp_stall = (outp_valid & outp_stall);

always_ff @(posedge clk or negedge rst ) begin
    if (!rst ) begin
        outp_data <= '0;
    end
    else if ( inp_valid & !inp_stall ) begin
        outp_data[WIDTH] <= inp_data[WIDTH];
    end
end

always_ff @(posedge clk or negedge rst ) begin
    if ( !rst ) begin
        outp_valid <= 1'b0;
    end
    else if ( !inp_stall ) begin
        outp_valid <= inp_valid;
    end
end

"""

        if pipe_type == "ss":
            outp_str = sr_str
        elif pipe_type == "sv":
            outp_str = sv_str
        elif pipe_type == "svs":
            outp_str = sv_str.replace("outp_", "pipe_") + sr_str.replace(
                "inp_", "pipe_"
            )
        elif pipe_type == "ssv":
            outp_str = sr_str.replace("outp_", "pipe_") + sv_str.replace(
                "inp_", "pipe_"
            )
        else:
            print("pipe type syntax error" + inp_str)

        outp_str = outp_str.replace("inp_", inp_name + "_")
        outp_str = outp_str.replace("outp_", outp_name + "_")
        outp_str = outp_str.replace("pipe_", inp_name + "_pipe_")
        outp_str = outp_str.replace("skid_", inp_name + "_skid_")
        outp_str = outp_str.replace("WIDTH", data_width)
        outp_str = outp_str.replace(" clk ", " " + self.clock + " ")
        outp_str = outp_str.replace("rst )", self.async_reset + " )")
        return outp_str

    def flop(self, flop_type, flop_string):
        """
        Flop code generation
        """

        flop_string = re.sub(r"\s*,\s*", r",", flop_string)
        flop_string = re.sub(r"^\s*", r"", flop_string)
        flop_string = re.sub(r"\s*$", r"", flop_string)

        flop_args = flop_string.split(",")

        fb_enflop = """
always_ff @(posedge <clk>) begin
    if (<en>) begin <q> <= <d>; end
end
"""
        fb_enflop_rs = """
always_ff @(posedge <clk> or negedge <rst>) begin
    if (~<rst>) begin <q> <= <rs_value>; end
    else if (<en>) begin <q> <= <d>; end
end
"""
        fb_enflop_rst = """
always_ff @(posedge <clk> or negedge <rst>) begin
    if (~<rst>) begin <q> <= '0; end
    else if (<en>) begin <q> <= <d>; end
end
"""

        if flop_type == "fb_enflop":
            c_flop = fb_enflop
            c_flop = re.sub(r"<clk>", flop_args[0], c_flop)
            c_flop = re.sub(r"<en>", flop_args[1], c_flop)
            c_flop = re.sub(r"<d>", flop_args[2], c_flop)
            c_flop = re.sub(r"<q>", flop_args[3], c_flop)
        elif flop_type == "fb_enflop_rs":
            c_flop = fb_enflop_rs
            c_flop = re.sub(r"<clk>", flop_args[0], c_flop)
            c_flop = re.sub(r"<rst>", flop_args[1], c_flop)
            c_flop = re.sub(r"<rs_value>", flop_args[2], c_flop)
            c_flop = re.sub(r"<en>", flop_args[3], c_flop)
            c_flop = re.sub(r"<d>", flop_args[4], c_flop)
            c_flop = re.sub(r"<q>", flop_args[5], c_flop)
        else:
            c_flop = fb_enflop_rst
            c_flop = re.sub(r"<clk>", flop_args[0], c_flop)
            c_flop = re.sub(r"<rst>", flop_args[1], c_flop)
            c_flop = re.sub(r"<en>", flop_args[2], c_flop)
            c_flop = re.sub(r"<d>", flop_args[3], c_flop)
            c_flop = re.sub(r"<q>", flop_args[4], c_flop)

        return c_flop
