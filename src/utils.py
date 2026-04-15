####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

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


################################################################################
# Function to print a debug string in a debug dump file
################################################################################
def dbg(debug, dbg_info):
    first = 1

    if debug:
        if type(dbg_info) is list:
            for curr_str in dbg_info:
                if first:
                    first = 0
                    # dbg_file.write(str(curr_str))
                # else:
                # dbg_file.write(", " + str(curr_str))
        # else:
        # dbg_file.write(str(dbg_info))

        # dbg_file.write("\n")

    return


################################################################################
# Function to print a debug string in a debug dump file
################################################################################
def find_in_files(filename):
    global files

    for c_file in files:
        file_search_regex = filename + "$"
        RE_SEARCH_FILE_REGEX = re.compile(file_search_regex)
        search_file_regex = re.search(RE_SEARCH_FILE_REGEX, c_file)

        if search_file_regex:
            return c_file
    return


################################################################################
# Function to Indent based on column width
################################################################################
def indent_array(array, separator, empty_char):
    indented_array = []
    indent_size = []

    for c_line in array:
        c_line_split = c_line.split(separator)
        index = 0

        for col in c_line_split:
            col_len = len(col)

            try:
                indent_size[index]
            except IndexError:
                indent_size.append(0)

            if indent_size[index] < col_len:
                indent_size[index] = col_len

            index = index + 1

    for c_line in array:
        c_line_split = c_line.split(separator)

        indented_line = ""
        index = 0

        for col in c_line_split:
            col_len = len(col)

            if col == empty_char:
                col = " "

            space_dup = indent_size[index] - col_len
            col += " " * space_dup

            col = col + "  "

            indented_line = indented_line + col

            index = index + 1

        # Removing end of line spaces
        indented_line = re.sub(r"\s*$", r"", indented_line)
        indented_array.append(indented_line)

    return indented_array


def indent_dict(mydict, separator, empty_char):
    indented_dict = {}
    indent_size = []

    for c_port in mydict:
        c_line = mydict[c_port]
        c_line_split = c_line.split(separator)
        index = 0

        for col in c_line_split:
            col_len = len(col)

            try:
                indent_size[index]
            except IndexError:
                indent_size.append(0)

            if indent_size[index] < col_len:
                indent_size[index] = col_len

            index = index + 1

    for c_port in mydict:
        c_line = mydict[c_port]
        c_line_split = c_line.split(separator)

        indented_line = ""
        index = 0

        for col in c_line_split:
            col_len = len(col)

            if col == empty_char:
                col = " "

            space_dup = indent_size[index] - col_len
            col += " " * space_dup

            col = col + "  "

            indented_line = indented_line + col

            index = index + 1

        # Removing end of line spaces
        indented_line = re.sub(r"\s*$", r"", indented_line)
        indented_dict[c_port] = indented_line

    return indented_dict


def set_vendor():
    if "FB_CHIP" in os.environ:
        vendor = os.environ["FB_CHIP"]
    else:
        logging.error("Missing Envr Variable FB_CHIP.")
    if "freya" in vendor:
        vendor = "brcm_apd_n7"
        return vendor
    elif "tenjin" in vendor:
        vendor = "brcm_ccx_n7"
        return vendor
    elif "fujin" in vendor:
        vendor = "brcm_ccx_n5"
        return vendor
    elif "terminus_gen1" in vendor:
        vendor = "mrvl_n5"
        return vendor
    elif "terminus" in vendor:
        vendor = "xilinx"
        return vendor
    elif "artemis" in vendor:
        vendor = "brcm_apd_n5"
        return vendor
    elif "athena" in vendor:
        vendor = "brcm_apd_n3"
        return vendor
    elif "voyager" in vendor:
        vendor = "mrvl_n5"
        return vendor
    else:
        logging.error(
            "Error in vendor name. envr variable FB_CHIP doesnt have freya/tenjin/terminus/terminus_gen1/fujin/artemis2.0"
        )
        sys.exit(1)


### Perf Improvement over using RE_BLOCK_COMMENT_SINGLE_LINE
def remove_single_line_comment(line):
    beg_idx = line.find("/*")
    if beg_idx >= 0:
        end_idx = line.find("*/", beg_idx)
        if beg_idx < end_idx:
            return line[:beg_idx] + " " + line[end_idx + 2 :]
    return line


################################################################################
# Sort and Unique a list
################################################################################
def sort_uniq(sequence):
    return (x[0] for x in itertools.groupby(sorted(sequence)))


################################################################################
# recursively traverse list
################################################################################


def nonblank_lines(f):
    for l in f:
        line = l.rstrip()
        line = line.strip()
        line = line.replace("\r", "")
        line = line.replace("\n", "")
        if line:
            yield line


def check_path(line: str, filename: str) -> None:
    matches = re.search(r"\$\{?([A-Za-z_]+)\}?", line)
    if matches:
        envvar_name = matches.group(1)
        logging.error(
            "%s",
            f"{envvar_name} could not be expanded ({line})\n   referenced by {filename}",
        )
        sys.exit(1)
    if not os.path.exists(line):
        logging.error("%s", f"Missing {line}\n.   referenced by {filename}")
        sys.exit(1)


def recursive_filelist(filename: str) -> Set[str]:
    filelist = list()
    lineList = list()
    with open(filename) as filep:
        for c_file in nonblank_lines(filep):
            lline = c_file.rstrip("\n")
            lineList.append(lline)
    filep.close
    # lineList = [line.rstrip('\n') for line in open(filename)]
    for line in lineList:
        line = line.rstrip()
        line = os.path.expandvars(line)
        if re.search("^-f ", line):
            data = re.sub(r"-f ", r"", line)
            check_path(data, filename)
            a = recursive_filelist(data)
            filelist.extend(a)
        elif re.search("filelist.txt$", line):
            data = re.sub(r"-f ", r"", line)
            check_path(data, filename)
            a = recursive_filelist(data)
            filelist.extend(a)
        elif line.startswith("+incdir+"):
            incdir = line[8:]
            expanded_incdir = os.path.expandvars(incdir)
            check_path(expanded_incdir, filename)
            if os.path.isdir(expanded_incdir):
                incdir_files = os.listdir(expanded_incdir)
            else:
                print(f"Could not find {expanded_incdir}")
                sys.exit(1)
            filelist.extend(
                [
                    os.path.join(incdir, f)
                    for f in incdir_files
                    if f.endswith((".svh", ".vh"))
                ]
            )
        else:
            filelist.append(line)

    return filelist
