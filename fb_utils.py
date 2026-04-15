####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

#!/usr/local/bin/asicpy


import argparse
import glob
import importlib
import os
import re
import subprocess
import sys
from collections import OrderedDict
from math import ceil, log
from typing import Callable

import oyaml as yaml


def log2(inp):
    return int(ceil(log(float(inp), 2)))


def find_reg_address_window(instance, regs_dir="", regs_package=""):
    try:
        import fb_defaults
    except ImportError:
        print(
            "Please run 'buck run //scripts/build:set_defaults -- -p <fb_inference or your project>' to set your project default.\n"
        )
        return (-1, -1)
    import fb_projects

    project = fb_defaults.fb_project_name
    ips = fb_projects.projects_hash[project]["ip"]
    instances = fb_projects.projects_hash[project]["instance"]

    base_address = instances[instance]["reg_base_address"]
    if "reg_upper_bound" in ips[instances[instance]["type"]]:
        reg_upper_bound = (
            ips[instances[instance]["type"]]["reg_upper_bound"] + base_address
        )
    else:
        reg_path = os.path.join(fb_defaults.root_dir, regs_dir)
        sys.path.append(reg_path)
        m_name = regs_package
        m = importlib.import_module(m_name)
        last_i = 0
        registers = m.registers["registers"]
        for i in registers:
            reg_array = m.registers["registers"][i]["meta"]["array"]
            if (i + reg_array) > last_i:
                last_i = i + reg_array
        reg_upper_bound = base_address + last_i * m.registers["bytes_per_reg"]
    return (base_address, reg_upper_bound)


def convert_to_hash(text):
    return yaml.load(text, Loader=yaml.FullLoader)


def convert_to_yaml(d):
    return yaml.dump(d)


class CustomOrderedDict(OrderedDict):
    """
    a custom OrderedDict class that supports object-like dot notation
    perserving the ordering information in OrderedDict objects
    """

    def __getattr__(self, k):
        # this method is called when using the d.key notation
        # it returns the d[key] unless key does not exist
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        try:
            self.__getattribute__(k)
        except AttributeError:
            # OrderedDict uses "_OrderedDict__root" and "_OrderedDict__map"
            # still need them to be real attributes, but route other setattr
            # to d[key]=v assignment
            if k in ["_OrderedDict__root", "_OrderedDict__map"]:
                self.__dict__[k] = v
            else:
                self[k] = v

    def __delattr__(self, k):
        # first tries to delete the attribute if it exists (as attribute)
        # otherwise execute as 'del d[key]'
        try:
            object.__getattribute__(self, k)
        except AttributeError:
            try:
                del self[k]
            except KeyError:
                raise AttributeError(k)
        else:
            super(CustomOrderedDict, self).__delattr__(k)


def _gen_custom_ordereddict_obj(d):
    # recursively converting the nested OrderedDict to CustomOrderedDict
    if isinstance(d, dict):  # OrderedDict is child class of dict
        return CustomOrderedDict(
            (k, _gen_custom_ordereddict_obj(v)) for k, v in d.items()
        )
    elif isinstance(d, (list, tuple)):
        return type(d)(_gen_custom_ordereddict_obj(v) for v in d)
    else:
        return d


def convert_to_classobject(aOrderedDict):
    # returns an object of the CustomOrderedDict class
    return _gen_custom_ordereddict_obj(aOrderedDict)


def add_reserved_fields(
    fields: OrderedDict,
    enums: OrderedDict,
    aligned_lsb: Callable,
    in_isa: Callable,
) -> OrderedDict:
    aligned_fields = OrderedDict()

    field_lsb = 0
    rsvd_idx = 0
    for field in fields:
        if field != "rest" and in_isa(field) and field_lsb < aligned_lsb(field):
            aligned_fields[f"reserved_{rsvd_idx}"] = {
                "width": aligned_lsb(field) - field_lsb
            }
            field_lsb = aligned_lsb(field)
            rsvd_idx += 1

        aligned_fields[field] = fields[field]
        width = (
            fields[field]["width"]
            if "width" in fields[field]
            else enums[fields[field]["enum"]]["width"]
        )
        field_lsb += width

    return aligned_fields


def convert_to_pktgen_dict(interfaces, enums=None, aligned_lsb=None, in_isa=None):
    if enums is None:
        enums = {}
    pktgen_dict = {}
    for interface in interfaces:
        # print("LOG interface {}".format(interface))
        if "commands" in interfaces[interface]:
            commands = interfaces[interface]["commands"]
            pktgen_dict[interface] = {}
            pktgen_dict[interface]["fields"] = {}
            pktgen_dict[interface]["packets"] = {}
            pktgen_dict[interface]["width"] = 0
            pktgen_dict[interface]["description"] = interfaces[interface].get(
                "text", ""
            )
            for command in commands:
                # add reserved fields to the custom_instr structs only.
                if aligned_lsb is not None and "iid" not in commands[command]["fields"]:
                    commands[command]["fields"] = add_reserved_fields(
                        commands[command]["fields"], enums, aligned_lsb, in_isa
                    )
                command_name = commands[command]["name"].upper()
                pktgen_dict[interface]["packets"][command_name] = {}
                pktgen_dict[interface]["packets"][command_name]["description"] = (
                    commands[command].get("text", "")
                )
                pktgen_dict[interface]["packets"][command_name]["fields"] = {}
                pktgen_dict[interface]["packets"][command_name]["width"] = 0
                lsb = 0
                for field in commands[command]["fields"]:
                    FIELD = field.upper()
                    pktgen_dict[interface]["packets"][command_name]["fields"][
                        FIELD
                    ] = {}
                    if "enum" in commands[command]["fields"][field]:
                        width = enums[commands[command]["fields"][field]["enum"]][
                            "width"
                        ]
                        pktgen_dict[interface]["packets"][command_name]["fields"][
                            FIELD
                        ]["enums"] = enums[commands[command]["fields"][field]["enum"]][
                            "values"
                        ]
                    else:
                        width = commands[command]["fields"][field]["width"]
                        pktgen_dict[interface]["packets"][command_name]["fields"][
                            FIELD
                        ]["enums"] = {}
                    text = commands[command]["fields"][field].get("text", "")
                    msb = lsb + width - 1
                    pktgen_dict[interface]["packets"][command_name]["fields"][FIELD][
                        "lsb"
                    ] = lsb
                    pktgen_dict[interface]["packets"][command_name]["fields"][FIELD][
                        "msb"
                    ] = msb
                    pktgen_dict[interface]["packets"][command_name]["fields"][FIELD][
                        "description"
                    ] = text
                    pktgen_dict[interface]["packets"][command_name]["width"] += width
                    lsb += width
                if (
                    pktgen_dict[interface]["packets"][command_name]["width"]
                    > pktgen_dict[interface]["width"]
                ):
                    pktgen_dict[interface]["width"] = pktgen_dict[interface]["packets"][
                        command_name
                    ]["width"]
        else:
            pktgen_dict[interface] = {}
            pktgen_dict[interface]["fields"] = {}
            pktgen_dict[interface]["packets"] = {}
            pktgen_dict[interface]["width"] = 0
            pktgen_dict[interface]["description"] = interfaces[interface].get(
                "text", ""
            )
            lsb = 0
            valid_interface = True
            if "fields" in interfaces[interface]:
                for field in interfaces[interface]["fields"]:
                    FIELD = field.upper()
                    pktgen_dict[interface]["fields"][FIELD] = {}
                    if "enum" in interfaces[interface]["fields"][field]:
                        # Default enums are a single word. This is how they are defined in the dictionary. But for some use
                        # cases like sub module level interfaces, we might have a mix of enum packages (local pkg file and fb_inference_pkg). In
                        # these cases, the enum name will have the package name in it (like xx::yy). So we have to remove the package name
                        # to get the enum information.
                        try:
                            width = enums[
                                interfaces[interface]["fields"][field]["enum"]
                            ]["width"]
                            pktgen_dict[interface]["fields"][FIELD]["enums"] = enums[
                                interfaces[interface]["fields"][field]["enum"]
                            ]["values"]
                        except KeyError:
                            enum_name = interfaces[interface]["fields"][field]["enum"]
                            enum_name = enum_name.split("::")
                            enum_name = enum_name[-1]
                            width = enums[enum_name]["width"]
                            pktgen_dict[interface]["fields"][FIELD]["enums"] = enums[
                                enum_name
                            ]["values"]
                    elif "width" in interfaces[interface]["fields"][field]:
                        width = interfaces[interface]["fields"][field]["width"]
                        pktgen_dict[interface]["fields"][FIELD]["enums"] = {}
                    else:
                        valid_interface = False
                        break
                    text = interfaces[interface]["fields"][field].get("text", "")
                    msb = (
                        lsb
                        + width
                        - 1
                        - interfaces[interface]["fields"][field].get("lsb", 0)
                    )
                    pktgen_dict[interface]["fields"][FIELD]["lsb"] = lsb
                    pktgen_dict[interface]["fields"][FIELD]["msb"] = msb
                    pktgen_dict[interface]["fields"][FIELD]["description"] = text
                    pktgen_dict[interface]["width"] += width
                    lsb += width
            if not valid_interface:
                pktgen_dict.pop(interface)
            else:
                if pktgen_dict[interface]["width"] > pktgen_dict[interface]["width"]:
                    pktgen_dict[interface]["width"] = pktgen_dict[interface]["width"]
    return pktgen_dict


def convert_to_csrgen_dict(registers, enums=None, offset=0, prefix=""):
    if enums is None:
        enums = {}
    csrgen_dict = {}
    block_name = registers["block_name"]
    csrgen_dict[block_name] = {}
    registers_registers_sorted = sorted(registers["registers"])
    for i in registers_registers_sorted:
        reg_name = registers["registers"][i]["name"]
        REG_NAME = prefix.upper() + reg_name.upper()
        csrgen_dict[block_name][REG_NAME] = {}
        csrgen_dict[block_name][REG_NAME]["fields"] = {}
        csrgen_dict[block_name][REG_NAME]["address"] = offset + i
        csrgen_dict[block_name][REG_NAME]["block_offset"] = offset
        csrgen_dict[block_name][REG_NAME]["description"] = registers["registers"][
            i
        ].get("text", "")
        csrgen_dict[block_name][REG_NAME]["read_mask"] = 0xFFFFFFFF
        csrgen_dict[block_name][REG_NAME]["reset"] = 0
        csrgen_dict[block_name][REG_NAME]["type"] = "rw"
        csrgen_dict[block_name][REG_NAME]["target"] = registers["registers"][i].get(
            "target", ""
        )
        csrgen_dict[block_name][REG_NAME]["array"] = registers["registers"][i].get(
            "array", 0
        )
        for f in registers["registers"][i]["fields"]:
            F = f.upper()
            csrgen_dict[block_name][REG_NAME]["fields"][F] = {}
            csrgen_dict[block_name][REG_NAME]["fields"][F]["comments"] = registers[
                "registers"
            ][i]["fields"][f].get("text", "")
            lsb = registers["registers"][i]["fields"][f]["lsb"]
            msb = lsb + registers["registers"][i]["fields"][f]["calculated_width"] - 1
            csrgen_dict[block_name][REG_NAME]["fields"][F]["range"] = {
                "lsb": lsb,
                "msb": msb,
            }
            csrgen_dict[block_name][REG_NAME]["fields"][F]["prods"] = {}
            csrgen_dict[block_name][REG_NAME]["fields"][F]["enums"] = {}
            csrgen_dict[block_name][REG_NAME]["fields"][F]["rval"] = registers[
                "registers"
            ][i]["fields"][f].get(
                "reset", registers["registers"][i]["fields"][f].get("value", 0)
            )
            if "::" in str(csrgen_dict[block_name][REG_NAME]["fields"][F]["rval"]):
                dummy_list = csrgen_dict[block_name][REG_NAME]["fields"][F][
                    "rval"
                ].split("::")
                reset_enum = dummy_list[-1]
                try:
                    csrgen_dict[block_name][REG_NAME]["fields"][F]["rval"] = enums[
                        registers["registers"][i]["fields"][f]["enum"]
                    ]["values"][reset_enum]
                except Exception:
                    dummy_list = reset_enum.split("_E_")
                    reset_enum = dummy_list[-1]
                    reset_enum_name = f"{dummy_list[0]}_e"
                    csrgen_dict[block_name][REG_NAME]["fields"][F]["rval"] = enums[
                        reset_enum_name
                    ]["values"][reset_enum]
            if "enum" in registers["registers"][i]["fields"][f]:
                if registers["registers"][i]["fields"][f]["enum"] in enums:
                    for v in enums[registers["registers"][i]["fields"][f]["enum"]][
                        "values"
                    ]:
                        csrgen_dict[block_name][REG_NAME]["fields"][F]["enums"][v] = (
                            enums[registers["registers"][i]["fields"][f]["enum"]][
                                "values"
                            ][v]
                        )
            if "auto_enum" in registers["registers"][i]["fields"][f]:
                csrgen_dict[block_name][REG_NAME]["fields"][F]["enums"] = registers[
                    "registers"
                ][i]["fields"][f]["auto_enum"]
    return csrgen_dict


def get_args():
    parser = argparse.ArgumentParser(
        description="Performs various functions.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    requiredNamed = parser.add_argument_group("required named arguments")

    requiredNamed.add_argument(
        "--function",
        "-f",
        metavar="<function>",
        type=str,
        required=True,
        help="function to perform.",
    )

    parser.add_argument(
        "--targets",
        nargs="*",
        help="targets to perform the function on.",
    )

    parser.add_argument(
        "--ext",
        nargs="*",
        default=[],
        type=str,
        help="which extensions to list [--function read_file_list]. ",
    )

    parser.add_argument(
        "--search_pattern",
        nargs="*",
        default=[],
        type=str,
        help="search string for the file names [--function read_file_list]. ",
    )

    parser.add_argument(
        "--get_all_files",
        action="store_true",
        help="gets all files from the output directory [--function read_file_list]. ",
    )

    parser.add_argument(
        "--output_directory",
        "-o",
        action="store_true",
        help="only print the directory.",
    )

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    (args) = get_args()
    if args.function == "read_file_list":
        files = []
        buck_root = (
            subprocess.check_output(["/usr/local/bin/buck", "root"])
            .decode("utf-8")
            .rstrip("\n")
        )
        buck_root_re = re.compile("(.*)buck-out(.*)$")

        for target in args.targets:
            outputs = subprocess.check_output(
                ["/usr/local/bin/buck", "build", target, "--deep", "--show-full-output"]
            )
            output_dir = outputs.decode("utf-8").split()[1]
            files_count = len(files)
            with open("{}/{}".format(output_dir, "filelist.txt"), "r") as file_list:
                files = files + file_list.readlines()
            if (len(files) == files_count) or (args.get_all_files):
                files = files + list(
                    set(glob.glob(f"{output_dir}/*"))
                    - set(glob.glob(f"{output_dir}/filelist.txt"))
                )
        sv_list = []
        svh_list = []
        pkg_list = []
        rest_list = []
        all_list = []
        ext_list = []
        files_list = []
        sv_pkg_re = re.compile(".*_pkg.sv$")
        svh_re = re.compile(".*.svh$")
        sv_re = re.compile(".*.sv$")
        files_re = re.compile("-f .*$")

        for f in files:
            buck_root_reg = re.search(buck_root_re, f)
            if buck_root_reg:
                f = buck_root + "/buck-out" + buck_root_reg.group(2)
            name, ext = os.path.splitext(os.path.basename(f))
            search_matched = True if len(args.search_pattern) == 0 else False
            for search in args.search_pattern:
                if search in name:
                    search_matched = True
            if not search_matched:
                continue
            ext = ext.rstrip()
            bn = os.path.basename(f)
            if args.output_directory:
                all_list.append(os.path.dirname(f).rstrip("\n"))
            else:
                all_list.append(f.rstrip("\n"))
            if ext in args.ext:
                ext_list.append(f.rstrip("\n"))
            if sv_pkg_re.match(f):
                pkg_list.append(f.rstrip("\n"))
            elif sv_re.match(f):
                sv_list.append(f.rstrip("\n"))
            elif svh_re.match(f):
                svh_file = f.rstrip("\n")
                svh_dir = os.path.dirname(svh_file)
                svh_list.append(f"+incdir+{svh_dir}")
            elif ext in args.ext:
                rest_list.append(f.rstrip("\n"))

            if files_re.match(f) and ("file_list" in args.ext):
                files_list.append(f.rstrip("\n"))

        svh_list = list(dict.fromkeys(svh_list))
        if ".sv" in args.ext or ".svh" in args.ext:
            all_files = pkg_list + sv_list + svh_list + files_list + rest_list
        elif len(args.ext) > 0:
            all_files = ext_list
        else:
            all_files = list(dict.fromkeys(all_list))
        print(" ".join(all_files))
