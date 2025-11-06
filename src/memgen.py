####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################
################################################################################
#                                                                              #
#     Author: Dheepak Jayaraman                                                #
#     E-Mail: dheepak@meta.com                                                   #
#                                                                              #
#     Key Contributor: Baheerathan Anandharengan                               #
#     E-Mail: baheerathan@meta.com                                               #
#                                                                              #
################################################################################

#!/usr/bin/env python3
import json
import logging
import os
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from memgen_util import (
    addr_ports,
    bwe_ports,
    clog2,
    combinationSum,
    cs_ports,
    dec_to_bin,
    dec_to_bin_non_pow_two,
    dict_keys_str_to_int,
    din_ports,
    dout_ports,
    fb_chip_2_vendor_name,
    is_mersenne_prime,
    isPowerOfTwo,
    mem_mapping_file,
    mem_ports_file,
    memory_release_search_paths,
    nearest_2_pow,
    OrderedDict,
    re,
    str_to_list,
    SumTheList,
    valid_sram_types,
    valid_vendor_names,
    vendor_name_mapping,
    we_ports,
)

# from memgen_data import *
# from vendor import Vendor
# from userram import UserRam
# from memgenresult import MemgenResult


verbosity = 1
levels = [logging.WARNING, logging.INFO, logging.DEBUG]
level = levels[min(len(levels) - 1, verbosity)]  # capped to number of levels
logging.basicConfig(level=level, format="%(levelname)s %(message)s")


class Vendor:
    def __init__(self, name):
        self.name = name
        self.memory_release_dirctory = None
        self.mem_mapping_file = None
        self.mem_mapping = None
        self.mem_ports_file = None
        self.mem_ports = None
        self.fb_ports_2_phy_ports = None
        self.phy_ports_2_fb_ports = None

    def __str__(self):
        return f"""
    Vendor: {self.name}, Memory release directory: {self.memory_release_dirctory},
    Memory mapping file: {self.mem_mapping_file},
    Memory mapping: {self.mem_mapping},
    Memory ports file: {self.mem_ports_file},
    Memory ports: {self.mem_ports}
        """

    def self_check(self):
        rc = True

        logging.debug(f"Valid vendor names: {valid_vendor_names}")
        if self.name not in valid_vendor_names:
            logging.error(f"Invalid vendor set: {self.name}.")
            rc = False
        else:
            logging.debug(f"Vendor is set to {self.name}")

        logging.debug(self)
        return rc

    def load_memory_config(self, infra):
        for vendor in (self.name, "default"):
            path = memory_release_search_paths[vendor] % {
                "infra": infra,
                "vendor": self.name,
            }
            if os.path.exists(path):
                self.memory_release_dirctory = path
                break

        if self.memory_release_dirctory is None:
            logging.error(
                f"No memory release directory found: infra {infra} and vendor {self.name}."
            )
            return False
        else:
            logging.info(
                f"load vendor memory config from {self.memory_release_dirctory}"
            )

        rc = True
        mem_mapping_path = os.path.join(self.memory_release_dirctory, mem_mapping_file)
        if os.path.isfile(mem_mapping_path):
            self.mem_mapping_file = mem_mapping_path
            logging.debug(f"Loading Vendor mem_mapping {self.mem_mapping_file}.")
            with open(self.mem_mapping_file) as mem_mapping_json:
                mem_map = json.load(mem_mapping_json, object_pairs_hook=OrderedDict)
                output = dict_keys_str_to_int(mem_map)
                self.mem_mapping = OrderedDict(output)
        else:
            logging.error(f"Invalid mem_mapping.json file {mem_mapping_path}.")
            self.loadVendorJson = 1
            rc = False

        mem_ports_path = os.path.join(self.memory_release_dirctory, mem_ports_file)
        if os.path.isfile(mem_ports_path):
            self.mem_ports_file = mem_ports_path
            logging.debug(f"Loading Vendor mem_ports {self.mem_ports_file}.")
            with open(self.mem_ports_file) as mem_ports_json:
                self.mem_ports = json.load(mem_ports_json)
        else:
            logging.error(f"Invalid mem_port.json file {mem_ports_path}.")
            self.loadVendorJson = 1
            rc = False

        return rc

    def map_inout_ports(self, inports, outports):
        self.fb_ports_2_phy_ports = defaultdict(set)
        self.phy_ports_2_fb_ports = defaultdict(set)
        for phy_port, fb_port in tuple(inports.items()) + tuple(outports.items()):
            self.fb_ports_2_phy_ports[fb_port].add(phy_port)
            self.phy_ports_2_fb_ports[phy_port].add(fb_port)
        logging.info(f"FB ports 2 phy ports: {self.fb_ports_2_phy_ports}")
        logging.info(f"Phy ports 2 FB ports: {self.phy_ports_2_fb_ports}")


class UserRam:
    def __init__(self, prefix, width, depth, typ, pipeline, bitwrite, rst, wclk, rclk):
        self.prefix = prefix
        self.typ = typ
        self.width = width
        self.depth = depth
        self.pipeline = int(pipeline)
        self.bitWrite = int(bitwrite)
        self.rst = rst
        self.wclk = wclk
        self.rclk = rclk
        self.hls = 0
        self.ecc = 0
        self.ecc_width = 0
        self.addrSize = clog2(self.depth)
        self.vendor = None
        self.fitting = None

        self.sram_type = None
        self.module = None
        self.vf = None
        self.module_content = None

    def __str__(self):
        return f"""User Ram:
    Prefix: {self.prefix}, type: {self.typ}, depth: {self.depth}, 
    width: {self.width}, pipeline: {self.pipeline}, bit_write: {self.bitWrite}
    rst: {self.rst}, wclk: {self.wclk}, rclk: {self.rclk}, hls: {self.hls}
    ecc: {self.ecc}, ecc_width: {self.ecc_width}, addrSize: {self.addrSize}
    module: {self.module}
    verilog file: {self.vf}
    fitting: {self.fitting}
    vendor: {self.vendor}
    Module Content: {self.module_content}
        """

    def self_check(self):
        rc = True

        if self.typ.lower() not in valid_sram_types:
            logging.error(f"Sram type should be one of {valid_sram_types}")
            rc = False
        else:
            logging.debug(f"Sram type is set to {self.typ}")

        if self.width <= 0:
            logging.error(f"Memory width should be positive integer")
            rc = False
        else:
            logging.debug(f"Memory width is set to {self.width}")

        if self.depth <= 0:
            logging.error(f"Memory depth should be positive integer")
            rc = False
        else:
            logging.debug(f"Memory depth is set to {self.depth}")

        logging.debug(self)
        return rc

    def defineWrapperName(self):
        self.module = "mem_wrapper_" + self.prefix + "_" + self.typ + "_"
        self.module += str(self.depth) + "X" + str(self.width) + "_pipe_"
        self.module += str(self.pipeline) + "_bw_" + str(self.bitWrite)
        if self.hls:
            self.module += "_hls_" + str(self.hls)
        if self.ecc:
            self.module += "_ecc_" + str(self.ecc_width)
        self.vf = self.module + ".psv"

    def write_flop_version(self):
        if self.typ == "1f":
            self.module_content = "&BeginInstance fb_ram_1p_ff;\n"
        elif self.typ == "2f":
            self.module_content = "&BeginInstance fb_ram_2p_ff;\n"
        if self.ecc == 1:
            self.module_content += "  &Param DATA_WIDTH WIDTH_WITH_ECC;\n"
        else:
            self.module_content += "  &Param DATA_WIDTH WIDTH;\n"
        self.module_content += "  &Param ADDR_WIDTH ADDR_WIDTH;\n"
        if self.bitWrite == 0:
            self.module_content += "  &Connect bwe " + "'1" + ";" + "\n"
        if self.ecc == 1:
            self.module_content += "  &Connect din " + "din_with_ecc" + ";" + "\n"
        self.module_content += "  &Connect dout " + "dout_int" + ";" + "\n"
        self.module_content += "&EndInstance;\n"

    # def set_sram_type(self, vendor):
    #     if vendor == None:
    #         logging.error(f"Vendor isn't defined, can't determine sram type for user mmeory.")
    #         return
    #
    #     if self.typ == "1p" and self.bitWrite == 1:
    #         if vendor == "mrvl_n5":
    #            self.sram_type = 1111
    #         else:
    #            self.sram_type = 111
    #     elif self.typ == "1p" and self.bitWrite == 0:
    #         if vendor == "mrvl_n5":
    #            self.sram_type = 1110
    #         else:
    #            self.sram_type = 111
    #     elif self.typ == "2p" and self.bitWrite == 1:
    #         if vendor == "mrvl_n5":
    #            if self.wclk == self.rclk:
    #               self.sram_type = 2111
    #            else:
    #               self.sram_type = 21112
    #         else:
    #            self.sram_type = 211
    #     elif self.typ == "2p" and self.bitWrite == 0:
    #         if vendor == "mrvl_n5":
    #            if self.wclk == self.rclk:
    #               self.sram_type = 2110
    #            else:
    #               self.sram_type = 21102
    #         else:
    #            self.sram_type = 211
    #     else:
    #         print("Memory Type not supported \n")
    #
    #     logging.debug ("Memory Type " + str(self.sram_type))

    def ecc_print(self):
        if self.pipeline == 0:
            str_tmp = "dout_int"
        if self.pipeline == 1:
            str_tmp = "dout_pipe"

        str_ecc = """
localparam ECC_WIDTH = {0}; 
localparam WIDTH_WITH_ECC = WIDTH + ECC_WIDTH;
&logics;
assign din_with_ecc = {{ecc_chkbits,din}};

&BeginInstance fb_ecc_generate;
&Param DATA_WIDTH WIDTH;
&Param CHKBITS_WIDTH ECC_WIDTH;
&Connect in_data din;
&Connect out_chkbits ecc_chkbits[ECC_WIDTH-1:0];
&EndInstance;

assign dout_chkbits[ECC_WIDTH-1:0]  = {1}[WIDTH_WITH_ECC-1:WIDTH];
&BeginInstance fb_ecc_correct;
&Param DATA_WIDTH WIDTH;
&Param CHKBITS_WIDTH ECC_WIDTH;
&Connect in_data {1}[WIDTH-1:0];
&Connect in_chkbits dout_chkbits;
&Connect out_data dout;
&EndInstance;
""".format(self.ecc_width, str_tmp)

        if self.pipeline == 1:
            if self.typ == "1p":
                str_ecc += "&Clock clk;\n&AsyncReset reset_n;\n"
            if self.typ == "2p":
                str_ecc += "&Clock r_clk;\n&AsyncReset reset_n;\n"
            str_ecc += "&Posedge;\n    dout_pipe <0= dout_int;\n&Endposedge;\n"

        return str_ecc

    def print_beh_mem_xilinx(self, memWrapper):
        if self.ecc == 1:
            ecc_print = self.ecc_print()
            memWrapper.write(ecc_print)

        if self.ecc == 0:
            memWrapper.write("&logics;\n")

        if self.pipeline == 1:
            if (self.typ == "1p") or (self.typ == "1f"):
                memWrapper.write("&Clock clk;\n&AsyncReset reset_n;\n")
            if (self.typ == "2p") or (self.typ == "2f"):
                memWrapper.write("&Clock r_clk;\n&AsyncReset reset_n;\n")
            if self.ecc == 0:
                memWrapper.write("&Posedge;\n    dout <0= dout_int;\n&Endposedge;\n")
        else:
            if self.ecc == 0:
                memWrapper.write("assign dout = dout_int;\n")

        memWrapper.write("&Force width dout WIDTH;\n")
        if (self.typ == "1p") or (self.typ == "1f"):
            memWrapper.write("&BeginInstance fb_ram_1p_xilinx;\n")
        elif (self.typ == "2p") or (self.typ == "2f"):
            memWrapper.write("&BeginInstance fb_ram_2p_xilinx;\n")

        if self.ecc == 1:
            memWrapper.write("  &Param DATA_WIDTH WIDTH_WITH_ECC;\n")
        else:
            memWrapper.write("  &Param DATA_WIDTH WIDTH;\n")

        memWrapper.write("  &Param ADDR_WIDTH ADDR_WIDTH;\n")
        memWrapper.write("  &Param DEPTH DEPTH;\n")
        if self.bitWrite == 0:
            memWrapper.write("  &Connect bwe " + "'1" + ";" + "\n")
        if self.ecc == 1:
            memWrapper.write("  &Connect din " + "din_with_ecc" + ";" + "\n")
        memWrapper.write("  &Connect dout " + "dout_int" + ";" + "\n")
        memWrapper.write("  &EndInstance;\n")

    def print_beh_mem(self, memWrapper):
        if self.ecc == 1:
            ecc_print = self.ecc_print()
            memWrapper.write(ecc_print)

        if self.ecc == 0:
            memWrapper.write("&logics;\n")

        if self.pipeline == 1:
            if (self.typ == "1p") or (self.typ == "1f"):
                memWrapper.write("&Clock clk;\n&AsyncReset reset_n;\n")
            if (self.typ == "2p") or (self.typ == "2f"):
                memWrapper.write("&Clock r_clk;\n&AsyncReset reset_n;\n")
            if self.ecc == 0:
                memWrapper.write("&Posedge;\n    dout <0= dout_int;\n&Endposedge;\n")
        else:
            if self.ecc == 0:
                memWrapper.write("assign dout = dout_int;\n")

        memWrapper.write("&Force width dout WIDTH;\n")
        if (self.typ == "1p") or (self.typ == "1f"):
            memWrapper.write("&BeginInstance fb_ram_1p_beh;\n")
        elif (self.typ == "2p") or (self.typ == "2f"):
            memWrapper.write("&BeginInstance fb_ram_2p_beh;\n")

        if self.ecc == 1:
            memWrapper.write("  &Param DATA_WIDTH WIDTH_WITH_ECC;\n")
        else:
            memWrapper.write("  &Param DATA_WIDTH WIDTH;\n")

        memWrapper.write("  &Param ADDR_WIDTH ADDR_WIDTH;\n")
        if self.bitWrite == 0:
            memWrapper.write("  &Connect bwe " + "'1" + ";" + "\n")
        if self.ecc == 1:
            memWrapper.write("  &Connect din " + "din_with_ecc" + ";" + "\n")
        memWrapper.write("  &Connect dout " + "dout_int" + ";" + "\n")
        memWrapper.write("  &EndInstance;\n")

    def verilog_write_vendor(self, memWrapper):
        if self.vendor.name == "xilinx":
            memWrapper.write("`else // {\n\n")
        else:
            memWrapper.write("`elsif " + self.vendor.name + " // {\n\n")

        if self.vendor.mem_mapping != None and self.vendor.mem_ports != None:
            if self.ecc == 1:
                ecc_print = self.ecc_print()
                memWrapper.write(ecc_print)
            if self.ecc == 0:
                memWrapper.write("&logics;\n")
            if self.typ == "2p":
                if self.fitting is None or self.fitting.depth_iter == 1:
                    memWrapper.write("assign wea = we;\n")
                memWrapper.write("assign rea = re;\n")
                if self.bitWrite == 1:
                    memWrapper.write("assign bwea = bwe;\n")
            if self.fitting is None or self.fitting.depth_iter == 1:
                if self.pipeline == 1:
                    if (self.typ == "1p") or (self.typ == "1f"):
                        memWrapper.write("&Clock clk;\n&AsyncReset reset_n;\n")
                    if (self.typ == "2p") or (self.typ == "2f"):
                        memWrapper.write("&Clock r_clk;\n&AsyncReset reset_n;\n")
                    if self.ecc == 0:
                        memWrapper.write(
                            "&Posedge;\n    dout <0= dout_int;\n&Endposedge;\n"
                        )
                else:
                    if self.ecc == 0:
                        memWrapper.write("assign dout = dout_int;\n")
            memWrapper.write(self.module_content)
        else:
            if self.vendor.name == "xilinx":
                self.print_beh_mem_xilinx(memWrapper)
            else:
                self.print_beh_mem(memWrapper)

        memWrapper.write("// } " + self.vendor.name + " \n")
        memWrapper.write("`endif\n")

    def verilog_write(self):
        """Write a behavioral Verilog model."""
        logging.info(f"writing verilog file {self.vf}\n")
        with open(self.vf, "w") as memWrapper:
            memWrapper.write(
                "&Module(parameter WIDTH = {0}, DEPTH = {1}, ADDR_WIDTH = $clog2(DEPTH));\n\n".format(
                    self.width, self.depth
                ).format(self.addrSize)
            )
            memWrapper.write("`ifdef FB_BEH_MEM // {\n")
            self.print_beh_mem(memWrapper)
            memWrapper.write("// } FB_BEH_MEM\n")

            if self.vendor is not None:
                self.verilog_write_vendor(memWrapper)

        memWrapper.close()
        # self.module_content = None

    def return_sram_loop_2p(self, loop):
        # if user provides only loop int
        # if users provide list
        # if users provide string
        sram_instance = " u_" + self.prefix
        sramidx = ""
        content = ""
        for loopidx, loopvalue in enumerate(loop):
            if type(loopvalue) is int:
                sram_instance = " u_" + self.prefix + "_" + str(loopidx)
                sramidx = self.prefix + "_" + str(loopidx)
            elif type(loopvalue) is str:
                sramidx = loopvalue
                sram_instance = " u_" + loopvalue
            content += "&BeginInstance " + self.module + "{0};\n".format(sram_instance)
            content += "&BuildCommand --disable_tick_ifdefs;\n"
            content += "&Param DEPTH " + str(self.depth) + ";\n"
            content += "&Param WIDTH " + str(self.width) + ";\n"
            if self.hls:
                content += "&Connect r_addr " + "{0}_rd_r_addr;\n".format(sramidx)
                content += "&Connect re " + "{0}_rd_re;\n".format(sramidx)
                content += "&Connect dout " + "{0}_rd_dout;\n".format(sramidx)
                content += "&Connect w_addr " + "{0}_wr_w_addr;\n".format(sramidx)
                content += "&Connect din " + "{0}_wr_din;\n".format(sramidx)
                content += "&Connect we " + "{0}_wr_we;\n".format(sramidx)
                if self.bitWrite == 1:
                    content += "&Connect bwe " + "{0}_wr_bwe;\n".format(sramidx)
            else:
                content += "&Connect r_addr " + "{0}_r_addr;\n".format(sramidx)
                content += "&Connect re " + "{0}_re;\n".format(sramidx)
                content += "&Connect dout " + "{0}_dout;\n".format(sramidx)
                content += "&Connect w_addr " + "{0}_w_addr;\n".format(sramidx)
                content += "&Connect din " + "{0}_din;\n".format(sramidx)
                content += "&Connect we " + "{0}_we;\n".format(sramidx)
                if self.ecc == 1:
                    content += (
                        "&Connect out_err_detect "
                        + "{0}_out_err_detect;\n".format(sramidx)
                    )
                    content += (
                        "&Connect out_err_multiple "
                        + "{0}_out_err_multiple;\n".format(sramidx)
                    )

                if self.bitWrite == 1:
                    content += "&Connect bwe " + "{0}_bwe;\n".format(sramidx)

            if (self.typ == "2p") or (self.typ == "2f"):
                content += "&Connect r_clk " + self.rclk + ";" + "\n"
                content += "&Connect w_clk " + self.wclk + ";" + "\n"
            elif (self.typ == "1p") or (self.typ == "1f"):
                content += "&Connect clk " + self.wclk + ";" + "\n"

            content += "&Connect reset_n " + self.rst + ";" + "\n"
            content += "&EndInstance;" + "\n\n"
        return content

    def return_sram_loop_1p(self, loop):
        # if user provides only loop int
        # if users provide list
        # if users provide string
        sram_instance = " u_" + self.prefix
        sramidx = ""
        content = ""
        for loopidx, loopvalue in enumerate(loop):
            if type(loopvalue) is int:
                sram_instance = " u_" + self.prefix + "_" + str(loopidx)
                sramidx = self.prefix + "_" + str(loopidx)
            elif type(loopvalue) is str:
                sramidx = loopvalue
                sram_instance = " u_" + loopvalue
            content += "&BeginInstance " + self.module + "{0};\n".format(sram_instance)
            content += "&BuildCommand --disable_tick_ifdefs;\n"
            content += "&Param DEPTH " + str(self.depth) + ";\n"
            content += "&Param WIDTH " + str(self.width) + ";\n"
            content += "&Connect addr " + "{0}_addr;\n".format(sramidx)
            content += "&Connect cs " + "{0}_cs;\n".format(sramidx)
            content += "&Connect dout " + "{0}_dout;\n".format(sramidx)
            content += "&Connect din " + "{0}_din;\n".format(sramidx)
            if self.bitWrite == 1:
                content += "&Connect bwe " + "{0}_bwe;\n".format(sramidx)
            content += "&Connect we " + "{0}_we;\n".format(sramidx)
            content += "&Connect clk " + self.wclk + ";" + "\n"
            content += "&Connect reset_n " + self.rst + ";" + "\n"
            content += "&EndInstance;" + "\n\n"
        return content

    def return_sram_hls_2p(self):
        content = ""
        content = "&BeginInstance " + self.module + " u_" + self.module + ";\n"
        content += "&BuildCommand --disable_tick_ifdefs;\n"
        content += "&Param DEPTH " + str(self.depth) + ";\n"
        content += "&Param WIDTH " + str(self.width) + ";\n"
        if self.hls:
            content += "&Connect r_addr " + self.prefix + "_rd_r_addr;" + "\n"
            content += "&Connect re " + self.prefix + "_rd_re;" + "\n"
            content += "&Connect dout " + self.prefix + "_rd_dout;" + "\n"
            content += "&Connect w_addr " + self.prefix + "_wr_w_addr;" + "\n"
            content += "&Connect din " + self.prefix + "_wr_din;" + "\n"
            content += "&Connect we " + self.prefix + "_wr_we;" + "\n"
            if self.bitWrite == 1:
                content += "&Connect bwe " + self.prefix + "_wr_bwe;" + "\n"
        else:
            content += "&Connect r_addr " + self.prefix + "_r_addr;" + "\n"
            content += "&Connect re " + self.prefix + "_re;" + "\n"
            content += "&Connect dout " + self.prefix + "_dout;" + "\n"
            content += "&Connect w_addr " + self.prefix + "_w_addr;" + "\n"
            content += "&Connect din " + self.prefix + "_din;" + "\n"
            content += "&Connect we " + self.prefix + "_we;" + "\n"
            if self.ecc == 1:
                content += (
                    "&Connect out_err_detect " + self.prefix + "_out_err_detect;\n"
                )
                content += (
                    "&Connect out_err_multiple " + self.prefix + "_out_err_multiple;\n"
                )

            if self.bitWrite == 1:
                content += "&Connect bwe " + self.prefix + "_bwe;" + "\n"

        if (self.typ == "2p") or (self.typ == "2f"):
            content += "&Connect r_clk " + self.rclk + ";" + "\n"
            content += "&Connect w_clk " + self.wclk + ";" + "\n"
        elif (self.typ == "1p") or (self.typ == "1f"):
            content += "&Connect clk " + self.wclk + ";" + "\n"

        content += "&Connect reset_n " + self.rst + ";" + "\n"
        content += "&EndInstance;" + "\n"
        return content

    def return_sram(self):
        content = ""
        content = "&BeginInstance " + self.module + " u_" + self.module + ";\n"
        content += "&BuildCommand --disable_tick_ifdefs;\n"
        content += "&Param DEPTH " + str(self.depth) + ";\n"
        content += "&Param WIDTH " + str(self.width) + ";\n"
        content += "&Connect /^/ /" + self.prefix + "_/;" + "\n"

        if (self.typ == "2p") or (self.typ == "2f"):
            content += "&Connect r_clk " + self.rclk + ";" + "\n"
            content += "&Connect w_clk " + self.wclk + ";" + "\n"
        elif (self.typ == "1p") or (self.typ == "1f"):
            content += "&Connect clk " + self.wclk + ";" + "\n"
            if (self.vendor.name == "brcm_ccx_n7") and (self.typ != "1f"):
                content += "&Connect tm_sp_ram tm_sp_ram;" + "\n"
            if (self.vendor.name == "brcm_ccx_n5") and (self.typ != "1f"):
                content += "&Connect tm_sp_ram tm_sp_ram;" + "\n"

        content += "&Connect reset_n " + self.rst + ";" + "\n"
        content += "&EndInstance;" + "\n"
        return content

    def instantiate_module_instances(self, loop):
        content = ""
        if type(loop) is not list:
            return content

        # If loop cnt is greater than or equal to 1, includes hls
        if (len(loop) >= 1) and ((self.typ == "2p") or (self.typ == "2f")):
            content += self.return_sram_loop_2p(loop)
        # If loop cnt is greater than or equal to 1,
        # hls not needed. ports are same for 1p
        elif (len(loop) >= 1) and ((self.typ == "1p") or (self.typ == "1f")):
            content += self.return_sram_loop_1p(loop)
        # regular version no loop defined, includes hls
        elif (len(loop) == 0) and ((self.typ == "2p") or (self.typ == "2f")):
            content += self.return_sram_hls_2p()
        elif (len(loop) == 0) and ((self.typ == "1p") or (self.typ == "1f")):
            content += self.return_sram()
        else:
            logging.error("Generating the BeginInstance")
            logging.error(
                "Loop,Type,Hls:" + str(len(loop)) + str(self.typ) + str(self.hls)
            )

        return content


class MemgenResult:
    def __init__(
        self,
        sram_type,
        user_width,
        user_depth,
        ecc_width,
        pic_depth,
        depth_iter,
        depth_residue,
        pic_widths,
        width_iter,
        width_residue,
    ):
        self.sram_type = sram_type
        self.user_width = user_width
        self.user_depth = user_depth
        self.ecc_width = ecc_width
        self.pic_depth = pic_depth
        self.depth_iter = depth_iter
        self.depth_residue = depth_residue
        self.pic_widths = pic_widths
        self.width_iter = width_iter
        self.width_residue = width_residue

    def __str__(self):
        return f"""
memory_key: {self.sram_type}, user_width: {self.user_width}, user_depth: {self.user_depth}, ecc_width: {self.ecc_width},
pic_depth: {self.pic_depth}, depth_iter: {self.depth_iter}, depth_residue: {self.depth_residue}
pic_widths: {self.pic_widths}, width_iter: {self.width_iter}, width_residue: {self.width_residue}
"""


class memgen:
    def __init__(self):
        self.infra = os.environ.get("INFRA_ASIC_FPGA_ROOT", None)
        self.fb_chip = os.environ.get("FB_CHIP", None)
        self.vendor = None
        self.user_ram = None
        self.sram_type = None
        self.loop = []
        self.vendor_memories = None
        self.set_vendor()

    def __str__(self):
        return f"""
    INFRA_ASIC_FPGA_ROOT: {self.infra}
    FB_CHIP: {self.fb_chip}
    Loop: {self.loop}
    {self.vendor}
    {self.user_ram}
    SRAM Type: {self.sram_type}
        """

    def check_infra(self):
        rc = True
        if self.infra is None:
            logging.error("Missing Envir Variable INFRA_ASIC_FPGA_ROOT.")
            logging.error("Please set INFRA_ASIC_FPGA_ROOT \n or \n")
            logging.error(
                "Please do `set_chip tenjin or freya` and `ff switch <workspace>`\n"
            )
            rc = False
        else:
            logging.debug(f"Envir Variable INFRA_ASIC_FPGA_ROOT is set to {self.infra}")

        if self.fb_chip is None:
            logging.warning("Missing Envir Variable FB_CHIP.")
        else:
            logging.debug(f"Envir Variable FB_CHIP is set to {self.fb_chip}")

        if self.vendor != None:
            rc &= self.vendor.self_check()

        return rc

    def check_ram_info(self):
        if self.user_ram != None and self.user_ram.self_check():
            return True
        else:
            return False

    def set_vendor(self, vendor=None):
        if vendor is not None:
            for name in vendor_name_mapping:
                if name in vendor:
                    self.vendor = Vendor(vendor_name_mapping[name])
                    return True

        vendor = self.fb_chip
        if vendor is not None:
            for name in fb_chip_2_vendor_name:
                if name in vendor:
                    self.vendor = Vendor(fb_chip_2_vendor_name[name])
                    return True

        return True  # FIXME: Temporarily skipping the vendor check warnings

        logging.warning("No vendor set...")
        logging.warning(f"Vendor: {vendor}, FB_CHIP: {self.fb_chip}")
        logging.warning(f"Only {valid_vendor_names} is supported")
        return False

    def set_ram_info(
        self, prefix, width, depth, typ, pipeline, bitwrite, rst, wclk, rclk=""
    ):
        logging.info(
            "memory info - width:{} depth:{} type:{} pipeline:{}"
            " bit_write:{} rst:{} wclk:{}, rclk:{}".format(
                width, depth, typ, pipeline, bitwrite, rst, wclk, rclk
            )
        )
        self.user_ram = UserRam(
            prefix, width, depth, typ, pipeline, bitwrite, rst, wclk, rclk
        )

    def set_ecc(self, ecc_width):
        if self.user_ram:
            self.user_ram.ecc = 1
            self.user_ram.ecc_width = ecc_width
            logging.debug(f"\t\t ECC_RAM_WIDTH = {self.user_ram.ecc_width}")
        else:
            logging.error("Please set ram info before enabling ecc.")

    def set_hls(self):
        if self.user_ram:
            self.user_ram.hls = 1
            logging.debug(f"\t\t HLS = {self.user_ram.hls}")
        else:
            logging.error("Please set ram info before enabling hls.")

    def set_sram_type(self):
        if self.user_ram == None or self.vendor == None:
            logging.warning(
                f"Either user ram or vendor isn't defined, can't set sram type."
            )
            return False

        if self.user_ram.typ == "1p" and self.user_ram.bitWrite == 1:
            if self.vendor.name == "mrvl_n5":
                self.sram_type = 1111
            else:
                self.sram_type = 111
        elif self.user_ram.typ == "1p" and self.user_ram.bitWrite == 0:
            if self.vendor.name == "mrvl_n5":
                self.sram_type = 1110
            else:
                self.sram_type = 111
        elif self.user_ram.typ == "2p" and self.user_ram.bitWrite == 1:
            if self.vendor.name == "mrvl_n5":
                if self.user_ram.wclk == self.user_ram.rclk:
                    self.sram_type = 2111
                else:
                    self.sram_type = 21112
            else:
                self.sram_type = 211
        elif self.user_ram.typ == "2p" and self.user_ram.bitWrite == 0:
            if self.vendor.name == "mrvl_n5":
                if self.user_ram.wclk == self.user_ram.rclk:
                    self.sram_type = 2110
                else:
                    self.sram_type = 21102
            else:
                self.sram_type = 211
        else:
            logging.error("memory type not supported \n")

        logging.debug(f"memory type ....\t{self.sram_type}")
        return True

    def load_vendor_memory_config(self):
        if self.vendor is None:
            return False
        return self.vendor.load_memory_config(self.infra)

    def pick_min_iter_depth_keys(self, is_depth_power_of_2=False):
        import numpy as np

        # 1. Get all the depths available
        depth_keys = [
            depth
            for depth in self.vendor.mem_mapping[self.sram_type]
            if not is_depth_power_of_2 or isPowerOfTwo(depth)
        ]
        logging.debug("Depth:{}".format(depth_keys))
        # 2. Create a numpy array
        np_depth = np.array(depth_keys)
        # 3. Find the celing division
        # for example 8000/4096 = 2
        np_rem = -(self.user_ram.depth // -np_depth)
        logging.debug("\tRem: Depth:{}".format(np_rem))

        # 4. Locate which one has the lowest index
        # picked_depth = np_depth[np.argmin(np_rem, axis=0)]
        depths = np_depth[np.argsort(np_rem)]
        logging.debug("\targsort: Depth:{}".format(depths))

        return depths

    def pick_vendor_memory_widths(self, selected_depth, customized_widths=None):
        logging.debug(":: Estimating physical memory Width")
        selected_width = self.user_ram.width + self.user_ram.ecc_width
        type_dep_large_width_present = False
        pick_widths = []

        if customized_widths is None:
            type_dep_width_present = False
            # Step 2. Check if the width exists
            try:
                self.vendor.mem_mapping[self.sram_type][selected_depth][selected_width]
            except KeyError:
                type_dep_width_present = False
            else:
                type_dep_width_present = True
            # Step 2a. Width exist use it directly
            if type_dep_width_present:
                logging.debug(f"Selcted width from Json: {selected_width}")
                return [[selected_width]]
            # Step 2b. Width doesnt exist use a nearest bigger size
            # for example: 50 user given width, but 64 is available
            if not type_dep_width_present:
                logging.debug(
                    ":: width not available...for type:{} depth:{}".format(
                        self.sram_type, selected_depth
                    )
                )
                final_diff_width, final_width, diff_width = 10000, 0, 0

                for mem_keys, _mem_wid in self.vendor.mem_mapping[self.sram_type][
                    selected_depth
                ].items():
                    logging.debug(
                        f"selecting width : {mem_keys} argeted_width : {selected_width}"
                    )
                    if mem_keys > selected_width:
                        type_dep_large_width_present = True
                        diff_width = mem_keys - selected_width
                        logging.debug(f"diff_width : {diff_width}")
                        if diff_width < final_diff_width:
                            final_diff_width = diff_width
                            final_width = mem_keys
                            logging.debug(f"final_width : {final_width}")
                if type_dep_large_width_present:
                    logging.debug(f"select width : {final_width}")
                    logging.debug("-----------\n")
                    return [[final_width]]

        # Step 2c. bigger size doesnt exist, do a combination of smaller sizes
        # for example: 50 user given width, but 18 or 20 is available
        if not type_dep_large_width_present:
            logging.debug("MEMGEN...Have to do multiple combinations of a smaller size")
            if customized_widths is not None:
                widths_list = [customized_widths]
            else:
                widths_list = self.pick_vendor_widths(selected_depth)

            # list_keys = list(self.vendor.mem_mapping[self.sram_type][selected_depth].keys())
            logging.debug(f"Searching in widths - O(N*M) complexity: {widths_list}")
            for widths in widths_list:
                if len(widths) <= 8:
                    selected_phy_mem = combinationSum(widths, selected_width)
                else:
                    selected_phy_mem = SumTheList(widths, selected_width)
                pick_widths.append(selected_phy_mem)

        return pick_widths

    def pick_vendor_widths(self, selected_depth):
        widths_list = []
        width_dict = self.vendor.mem_mapping[self.sram_type][selected_depth]
        widths = width_dict.keys()
        if self.vendor.name == "mrvl_n5":
            widths_list = [
                [
                    width
                    for width in widths
                    for k, v in width_dict[width].items()
                    if "mrvl" in k
                ],
                [
                    width
                    for width in widths
                    for k, v in width_dict[width].items()
                    if "mrvl" not in k
                ],
            ]
        else:
            widths_list = [list(widths)]
        widths_list = [widths for widths in widths_list if len(widths) > 0]
        return widths_list

    def get_memory_depth_width(self, memory_name):
        RE_MEMORY_NAME = re.compile(r"\D+(\d+)[xX](\d+)\D+")
        memory_name_regex = RE_MEMORY_NAME.search(memory_name)

        width = depth = None
        if memory_name_regex:
            depth, width = memory_name_regex.group(1), memory_name_regex.group(2)

        return int(depth), int(width)

    def validate_vendor_memories(self, memory_names):
        logging.info(f"Validate vendor memories {memory_names}")
        depths = set()
        widths = set()
        for memory_name in memory_names:
            depth, width = self.get_memory_depth_width(memory_name)
            inports, outports, sel_phy_mem = self.get_vendor_memory_inout_ports(
                depth, width
            )
            if sel_phy_mem != memory_name:
                return None
            depths.add(depth)
            widths.add(width)

        if len(depths) > 1:
            return None
        else:
            return list(depths), list(widths)

    def fit_memory_module(self, is_depth_power_of_2=False):
        memory_dimensions = None
        if self.vendor_memories is not None and len(self.vendor_memories) > 0:
            memory_dimensions = self.validate_vendor_memories(self.vendor_memories)
        if memory_dimensions is not None:
            pic_depths = memory_dimensions[0]
        else:
            pic_depths = self.pick_min_iter_depth_keys(is_depth_power_of_2)

        tuple_list = []
        # depth_hash = {}
        for pic_depth in pic_depths:
            logging.debug(f"\t\tStarting...: {pic_depth}")
            depth_iter = -(self.user_ram.depth // -pic_depth)
            depth_residue = (depth_iter * pic_depth) - self.user_ram.depth
            logging.debug(
                "\t\tBANK:Selected Depth:{}, iter:{}".format(pic_depth, depth_iter)
            )

            # Calculate the best width possibility
            pic_widths_list = self.pick_vendor_memory_widths(
                pic_depth,
                memory_dimensions[1] if memory_dimensions is not None else None,
            )
            logging.debug("\t\tDepth Routine Width:{}".format(pic_widths_list))
            for pic_widths in pic_widths_list:
                # form a tuple of residue and No. of widths
                sort_key = (
                    (depth_iter, depth_residue, pic_depth),
                    (
                        len(pic_widths),
                        sum(pic_widths)
                        - (self.user_ram.width + self.user_ram.ecc_width),
                        tuple(pic_widths),
                    ),
                )
                # Form a small hash of all these depth and selected widths
                # depth_hash[sort_key] = (pic_depth, sel_phy_width)
                # build a tuple List
                tuple_list.append(sort_key)
            logging.debug(f"\t\tBANK: {tuple_list}\n")

        min_sort_key = min(tuple_list)
        (
            (depth_iter, depth_residue, pic_depth),
            (
                width_iter,
                width_residue,
                pic_widths,
            ),
        ) = min_sort_key
        result = MemgenResult(
            self.sram_type,
            self.user_ram.width + self.user_ram.ecc_width,
            self.user_ram.depth,
            self.user_ram.ecc_width,
            pic_depth,
            depth_iter,
            depth_residue,
            pic_widths,
            width_iter,
            width_residue,
        )
        logging.debug(f"Calculate vendor memory result: {result}")
        return result

    def print_depth_bank_cs(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        power_of_two = 0
        # selection logic calculation
        # user input 6000 (13 bits) - 3136 (12)
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        if isPowerOfTwo(pic_depth):
            power_of_two = 1
        # Write CS logic
        for i in range(0, depth_iter):
            if not power_of_two:
                if self.user_ram.typ == "1p":
                    phyMemA_str += "\nassign bank_" + str(i) + "_cs = cs &"
                    phyMemA_str += " (addr >= " + str((pic_depth * (i))) + " & "
                    if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                        phyMemA_str += (
                            " addr >= " + str((pic_depth * (i + 1) - 1)) + ");"
                        )
                    else:
                        phyMemA_str += " addr < " + str((self.user_ram.depth)) + ");"
                if self.user_ram.typ == "2p":
                    phyMemA_str += "\nassign bank_" + str(i) + "_wea = we &"
                    phyMemA_str += " (w_addr >= " + str((pic_depth * (i))) + " & "
                    if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                        phyMemA_str += "w_addr < " + str((pic_depth * (i + 1))) + ");"
                    else:
                        phyMemA_str += "w_addr < " + str((self.user_ram.depth)) + ");"
            else:
                if self.user_ram.typ == "1p":
                    phyMemA_str += "\nassign bank_" + str(i) + "_cs = cs &"
                    phyMemA_str += " (addr[" + str(clog2(self.user_ram.depth) - 1)
                if self.user_ram.typ == "2p":
                    phyMemA_str += "\nassign bank_" + str(i) + "_wea = we &"
                    phyMemA_str += " (w_addr[" + str(clog2(self.user_ram.depth) - 1)
                # calculate the address bits that need to be compared.
                if selection > 1:
                    phyMemA_str += (
                        ":" + str(clog2(self.user_ram.depth) - selection) + "] == "
                    )
                else:
                    phyMemA_str += "] == "
                phyMemA_str += dec_to_bin(i, bits) + ");"
        return phyMemA_str

    def print_depth_bank_read_en_pow_of_two(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        logging.debug(f"Selection: {selection}")
        # read en logic
        if self.user_ram.typ == "1p":
            phyMemA_str += "\nassign read_en = cs & ~we;"
            if selection > 1:
                phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"
            phyMemA_str += "\n&Clock clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            phyMemA_str += "\n  if (read_en)"
            phyMemA_str += "\n    addr_ff <0= addr[" + str(
                clog2(self.user_ram.depth) - 1
            )
            if selection > 1:
                phyMemA_str += ":" + str(clog2(self.user_ram.depth) - selection) + "];"
            else:
                phyMemA_str += "];"
        if self.user_ram.typ == "2p":
            if selection > 1:
                phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"
            phyMemA_str += "\n&Clock r_clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            phyMemA_str += "\n  if (re)"
            phyMemA_str += "\n    addr_ff <0= r_addr[" + str(
                clog2(self.user_ram.depth) - 1
            )
            if selection > 1:
                phyMemA_str += ":" + str(clog2(self.user_ram.depth) - selection) + "];"
            else:
                phyMemA_str += "];"

        phyMemA_str += "\n&EndPosedge;"
        return phyMemA_str

    def print_depth_bank_read_en(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        logging.debug(f"Selection: {selection}")
        # read en logic
        for i in range(0, depth_iter):
            if self.user_ram.typ == "1p":
                phyMemA_str += "\nassign bank_" + str(i) + "_cs = cs &"
                phyMemA_str += " (addr >= " + str((pic_depth * (i))) + " & "
                if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                    phyMemA_str += " addr >= " + str((pic_depth * (i + 1) - 1)) + ");"
                else:
                    phyMemA_str += " addr < " + str((self.user_ram.depth)) + ");"
            if self.user_ram.typ == "2p":
                phyMemA_str += "\nassign bank_" + str(i) + "_rea = re &"
                phyMemA_str += " (r_addr >= " + str((pic_depth * (i))) + " & "
                if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                    phyMemA_str += "r_addr < " + str((pic_depth * (i + 1))) + ");"
                else:
                    phyMemA_str += "r_addr < " + str((self.user_ram.depth)) + ");"
        bank_cs = ""
        for i in reversed(range(0, depth_iter)):
            if self.user_ram.typ == "1p":
                bank_cs += "bank_" + str(i) + "_cs"
            if self.user_ram.typ == "2p":
                bank_cs += "bank_" + str(i) + "_rea"
            if depth_iter - 1 <= i:
                bank_cs += ","
        if self.user_ram.typ == "1p":
            phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            phyMemA_str += "\n&Clock clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            phyMemA_str += "\n  if (read_en)"
            phyMemA_str += "\n    addr_ff <0= {" + bank_cs + "};"
        if self.user_ram.typ == "2p":
            phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            phyMemA_str += "\n&Clock r_clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            phyMemA_str += "\n  if (re)"
            phyMemA_str += "\n    addr_ff <0= {" + bank_cs + "};"
        phyMemA_str += "\n&EndPosedge;"
        return phyMemA_str

    def print_depth_bank_addr(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        logging.debug(f"Selection: {selection}")
        # read en logic
        for i in range(0, depth_iter):
            if self.user_ram.typ == "1p":
                phyMemA_str += "\nassign addr_" + str(i) + " = (cs & ~we) ? (addr "
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += "): '0;"
            if self.user_ram.typ == "2p":
                phyMemA_str += "\nassign w_addr_" + str(i) + " = w_addr"
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += ";"
                phyMemA_str += (
                    "\nassign r_addr_"
                    + str(i)
                    + " = bank_"
                    + str(i)
                    + "_rea ? (r_addr "
                )
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += "): '0;"
        return phyMemA_str

    def print_depth_bank_case(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        nearest = nearest_2_pow(depth_iter)
        phyMemA_str += "\nalways_comb begin\n  case (addr_ff)"
        if isPowerOfTwo(pic_depth):
            for i in range(0, depth_iter):
                phyMemA_str += "\n      " + dec_to_bin(i, bits)
                phyMemA_str += ": dout_int = bank_" + str(i) + "_dout_int;"
            # check if have enumerated all combinations
            # otherwise add a default case.
            if nearest != depth_iter:
                phyMemA_str += "\n       default: dout_int = '0;"
        else:
            for i in range(0, depth_iter + 1):
                if (i != 0) or (is_mersenne_prime(i)):
                    # logging.debug("Converting to 2 power: " + str(i) + " iter:" + str(depth_iter))
                    phyMemA_str += "\n    " + dec_to_bin_non_pow_two(i, depth_iter)
                    phyMemA_str += ": dout_int = bank_" + str(i - 1) + "_dout_int;"
            phyMemA_str += "\n    default: dout_int = '0;"
        phyMemA_str += "\n  endcase\nend\n"
        if self.user_ram.pipeline == 1:
            if self.user_ram.typ == "1p":
                phyMemA_str += "&Clock clk;\n&AsyncReset reset_n;\n"
            if self.user_ram.typ == "2p":
                phyMemA_str += "&Clock r_clk;\n&AsyncReset reset_n;\n"
            if self.user_ram.ecc == 0:
                phyMemA_str += "&Posedge;\n    dout <0= dout_int;\n&Endposedge;\n"
        else:
            if self.user_ram.ecc == 0:
                phyMemA_str += "\nassign dout = dout_int;\n"
        return phyMemA_str

    def select_phy_mem_frm_lst(self, lst_phy_mem):
        selected = ""
        if self.user_ram.bitWrite == 0:
            for element in lst_phy_mem:
                if "W1H" not in element:
                    logging.debug(f"NO BWE:\t\t{element}")
                    selected = element
        else:
            for element in lst_phy_mem:
                logging.debug(f"BWE:\t\t{element}")
                if "W1H" in element:
                    selected = element
        #  this case is needed if there is no memory with the right BWE config
        # pick the first one and move on
        if not selected:
            for element in lst_phy_mem:
                selected = element

        logging.debug(f"Selected:\t\t{selected}")
        return selected

    def get_vendor_memory_inout_ports(self, pic_depth, pic_width):
        inports = outports = sel_phy_mem = memory_compiler = None
        memories = self.vendor.mem_mapping[self.sram_type]

        if pic_depth not in memories or pic_width not in memories[pic_depth]:
            return inports, outports, sel_phy_mem

        lst_sel_phy_mem = memories[pic_depth][pic_width]
        # select one memory from the list of memories
        # for now just pick one. later use the power data to pick the efficient one
        if isinstance(lst_sel_phy_mem, dict):
            for k, v in lst_sel_phy_mem.items():
                logging.debug(f"compiler name : {k}")
                for onemem in v.keys():
                    sel_phy_mem = onemem
                    memory_compiler = k
        elif isinstance(lst_sel_phy_mem, list):
            sel_phy_mem = self.select_phy_mem_frm_lst(lst_sel_phy_mem)
        else:
            sel_phy_mem = lst_sel_phy_mem

        logging.info(f"use ....\t{sel_phy_mem}")
        logging.debug(f"use ....\t{memory_compiler}")

        _typ = _de = _wi = None
        if self.vendor.name == "mrvl_n5":
            _typ = str(self.sram_type)
            if (_typ == "2110") and memory_compiler == "ts05p0g42p11sacrl128s":
                _typ += "2"
        else:
            config = re.findall(r"(\D\D+\d\d\d\D\D+)(\d+)X(\d+)", sel_phy_mem)
            for _typ, _de, _wi in config:
                pass

        logging.debug("\tdepth {} + width {} + Type {}".format(_de, _wi, _typ))

        if _typ in self.vendor.mem_ports.keys():
            inports = self.vendor.mem_ports[_typ]["input"]
            outports = self.vendor.mem_ports[_typ]["output"]
            # self.vendor.map_inout_ports(inports, outports)
        else:
            logging.error("Error: missing port info for physical memory type " + _typ)

        return inports, outports, sel_phy_mem

    def print_bwe(
        self,
        phy_mem_bwe,
        ports,
        values,
        iter_width,
        min_iter_width,
        max_iter_width,
        blank_width,
        user_width,
    ):
        phyMemA_str = ""
        if self.user_ram.bitWrite == 0:
            if phy_mem_bwe:
                phyMemA_str += "&Connect " + str(ports) + " " + "'1" + " ;\n"
            else:
                return ""
        elif (self.user_ram.bitWrite == 1) and (phy_mem_bwe == 0):
            logging.error(
                "USER requested Bit write enable but physical memory doesnt have it."
            )
            return ""
        elif self.user_ram.bitWrite == 1:
            if iter_width < user_width:
                str_width_cal = (
                    str(values)
                    + "["
                    + str(max_iter_width)
                    + ":"
                    + str(min_iter_width)
                    + "]"
                )
            else:
                str_width_cal = (
                    "{"
                    + "{"
                    + str(blank_width)
                    + "{1'b0}},"
                    + str(values)
                    + "["
                    + str(user_width - 1)
                    + ":"
                    + str(min_iter_width)
                    + "]}"
                )

            phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal + " ;\n"
        return phyMemA_str

    def print_addr(self, pic_depth, user_depth, ports, values):
        # Address size calculation

        phyMemA_str = ""
        str_depth_cal = ""
        phy_addrSize = 0
        user_addrSize = 0
        residue = 0
        # TODO Fill in this.
        phy_addrSize = clog2(pic_depth)
        user_addrSize = clog2(user_depth)
        residue = phy_addrSize - user_addrSize
        if user_addrSize < phy_addrSize:
            str_depth_cal = (
                "{"
                + "{"
                + str(residue)
                + "{1'b0}},"
                + str(values)
                + "["
                + str(user_addrSize - 1)
                + ":0]}"
            )
        else:
            if "ra" == ports or "wa" == ports:
                str_depth_cal = str(values)
            else:
                str_depth_cal = str(values) + "[" + str(phy_addrSize - 1) + ":0]"

        phyMemA_str += "&Connect " + str(ports) + " " + str_depth_cal + " ;\n"
        return phyMemA_str

    def print_din(
        self,
        ports,
        values,
        min_iter_width,
        max_iter_width,
        blank_width,
        iter_width,
        user_width,
    ):
        phyMemA_str = ""

        if self.user_ram.ecc == 1:
            values = f"{values}_with_ecc"

        if iter_width < user_width:
            str_width_cal = (
                str(values)
                + "["
                + str(max_iter_width)
                + ":"
                + str(min_iter_width)
                + "]"
            )
        else:
            str_width_cal = (
                "{"
                + "{"
                + str(blank_width)
                + "{1'b0}},"
                + str(values)
                + "["
                + str(user_width - 1)
                + ":"
                + str(min_iter_width)
                + "]}"
            )
        phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal + " ;\n"
        return phyMemA_str

    def print_dout(
        self,
        ports,
        values,
        iter_width,
        min_iter_width,
        max_iter_width,
        iterator,
        phy_mem_cnt,
        user_width,
    ):
        phyMemA_str = ""
        if values != "":
            if iterator != None and iterator >= 0:
                values = "bank_" + str(iterator) + "_" + values

            if iter_width < user_width:
                str_width_cal_op = (
                    str(values)
                    + "["
                    + str(max_iter_width)
                    + ":"
                    + str(min_iter_width)
                    + "]"
                )
            else:
                str_width_cal_op = (
                    "{sram_dout_tie_"
                    + (str(iterator) + "_" if iterator != None else "")
                    + str(phy_mem_cnt)
                    + ","
                    + str(values)
                    + "["
                    + str(user_width - 1)
                    + ":"
                    + str(min_iter_width)
                    + "]}"
                )
            phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal_op + " ;\n"
        else:
            phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
        return phyMemA_str

    def print_vendor_memory_banks(self, result, cur_depth, iterator):
        logging.debug(f"Iterating Memory Depth: {result.pic_depth}")

        phyMemA_str = ""
        power_of_two = True if isPowerOfTwo(result.pic_depth) else False
        phy_mem_cnt = 0
        min_iter_width = 0
        max_iter_width = 0
        blank_width = 0
        user_width = self.user_ram.width + self.user_ram.ecc_width

        for pic_width in result.pic_widths:
            logging.debug(f"Iterating Memory Width: {pic_width}")

            inports, outports, sel_phy_mem = self.get_vendor_memory_inout_ports(
                result.pic_depth, pic_width
            )
            if inports is None or outports is None:
                return phyMemA_str

            iter_width = max_iter_width + pic_width - 1
            if iter_width < user_width:
                max_iter_width += pic_width - 1
            else:
                blank_width = min_iter_width + pic_width - user_width
            if iter_width >= user_width:
                phyMemA_str += (
                    "wire ["
                    + str(blank_width - 1)
                    + ":0] sram_dout_tie_"
                    + (str(iterator) + "_" if iterator != None else "")
                    + str(phy_mem_cnt)
                    + ";\n"
                )

            # Check if physical memory has bit write enable
            phy_mem_bwe = 0
            iso_pin = 0
            if "W1H" in sel_phy_mem or re.search(r"b\dw1", sel_phy_mem):
                phy_mem_bwe = 1
            if re.search(r"b\dw1", sel_phy_mem):
                phy_mem_bwe = 1
            if bool(re.search(".*SRF.*S$", sel_phy_mem)):
                iso_pin = 1

            # Every thing is clear, let's push it to the variable and print it.
            phyMemA_str += "\n&BeginInstance " + sel_phy_mem + " "
            phyMemA_str += (
                self.user_ram.module
                + "_phy_inst_"
                + (str(iterator) + "_" if iterator != None else "")
                + str(phy_mem_cnt)
                + " ;\n"
            )

            for ports, values in inports.items():
                if ports in bwe_ports:
                    phyMemA_str += self.print_bwe(
                        phy_mem_bwe,
                        ports,
                        values,
                        iter_width,
                        min_iter_width,
                        max_iter_width,
                        blank_width,
                        user_width,
                    )
                elif ports in addr_ports:
                    if (iter_width >= 0) & (power_of_two == 0):
                        values = values + (
                            "_" + str(iterator) if iterator != None else ""
                        )
                    phyMemA_str += self.print_addr(
                        result.pic_depth, self.user_ram.depth, ports, values
                    )
                elif ports in din_ports:
                    phyMemA_str += self.print_din(
                        ports,
                        values,
                        min_iter_width,
                        max_iter_width,
                        blank_width,
                        iter_width,
                        user_width,
                    )
                elif ports in we_ports:
                    if iterator != None and self.user_ram.typ == "2p":
                        str_we = "bank_" + str(iterator) + "_we"
                        values = values.replace("we", str_we)
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
                elif ports in cs_ports:
                    if iterator != None:
                        str_cs = (
                            "bank_"
                            + (str(iterator) + "_" if iterator != None else "")
                            + "cs"
                        )
                        values = values.replace("cs", str_cs)
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
                elif ("iso" == ports) and (iso_pin):
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
                else:
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
            # output ports
            for ports, values in outports.items():
                # print ("OUTPUT: " + str(ports) + " val:" +str(values))
                if ports in dout_ports:
                    phyMemA_str += self.print_dout(
                        ports,
                        values,
                        iter_width,
                        min_iter_width,
                        max_iter_width,
                        iterator,
                        phy_mem_cnt,
                        user_width,
                    )
                else:
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"

            phyMemA_str += "&EndInstance;\n\n\n"
            phy_mem_cnt += 1
            min_iter_width = max_iter_width + 1
            max_iter_width += 1
        return phyMemA_str

    def print_memory_module(self, result):
        logging.info(f"Generate content for module {self.user_ram.module}")
        self.user_ram.module_content = ""
        nearest = nearest_2_pow(result.depth_iter)
        bits = clog2(nearest)

        if bits > 0:
            self.user_ram.module_content += self.print_depth_bank_cs(
                result.pic_depth, result.depth_iter, bits
            )
            if isPowerOfTwo(result.pic_depth):
                self.user_ram.module_content += (
                    self.print_depth_bank_read_en_pow_of_two(
                        result.pic_depth, result.depth_iter, bits
                    )
                )
            else:
                self.user_ram.module_content += self.print_depth_bank_read_en(
                    result.pic_depth, result.depth_iter, bits
                )
                self.user_ram.module_content += self.print_depth_bank_addr(
                    result.pic_depth, result.depth_iter, bits
                )
            self.user_ram.module_content += self.print_depth_bank_case(
                result.pic_depth, result.depth_iter, bits
            )

        tot_depth = result.user_depth
        i = 0
        while tot_depth > 0:
            if tot_depth >= result.pic_depth:
                cur_depth = result.pic_depth
            else:
                cur_depth = tot_depth

            logging.debug(
                "Widths:{} cur_depth:{}, pic_depth:{}, Iter:{} ".format(
                    result.pic_widths, cur_depth, result.pic_depth, i
                )
            )
            iterator = i if result.depth_iter > 1 else None
            self.user_ram.module_content += self.print_vendor_memory_banks(
                result, cur_depth, iterator
            )
            i += 1
            tot_depth -= result.pic_depth

    def write_flop_version(self):
        self.user_ram.write_flop_version()

    def set_phy_info(self):
        if not self.check_infra():
            logging.error("Please correct the setting error(s) before retrying.")
            sys.exit(1)

        if not self.check_ram_info():
            logging.error("Please set the ram info before generating memory.")
            sys.exit(1)

        self.user_ram.defineWrapperName()

        if self.load_vendor_memory_config():
            if (self.user_ram.typ == "1f") or (self.user_ram.typ == "2f"):
                self.write_flop_version()
                self.user_ram.vendor = self.vendor
            else:
                self.set_sram_type()
                result = self.fit_memory_module()
                self.user_ram.fitting = result
                self.user_ram.vendor = self.vendor
                self.print_memory_module(result)
        else:
            logging.warning("No Vendor Memory info loaded...\n")

    def verilog_write(self):
        self.user_ram.verilog_write()

    def returnWrapperName(self):
        return self.user_ram.module

    def clear_ram_info(self):
        self.user_ram = None
        self.loop = []
        self.vendor_memories = None

    def set_loop(self, loop):
        # Step 1. Detect if it is passed as integer 20 or "20"
        if type(loop) is int:
            self.loop = list(range(loop))
        # Step 2. Detect if it is str
        elif type(loop) is str:
            # check if there is , then convert it to list
            if "," in loop:
                self.loop = str_to_list(loop)
            # check if it is interger
            elif loop.isdigit():
                self.loop = list(range(int(loop)))
            else:
                self.loop = str_to_list(loop)
        else:
            logging.error(
                f"Invalid type is specified with the loop: {loop}, use the default (1)."
            )
            self.loop = [1]

    def returnInstance(
        self,
    ):
        if self.user_ram is None:
            logging.error(f"User ram isn't set, no instance content will be generated.")
            return

        return self.user_ram.instantiate_module_instances(self.loop)

    def set_vendor_memories(self, vendor_memories):
        self.vendor_memories = vendor_memories


if __name__ == "__main__":
    ram = memgen()
    ram.set_ram_info("memgen", 72, 1024, "2p", 0, 0, "reset_n", "clk", "clk")
    ram.set_vendor_memories(
        [
            "saculs0g4u2p1024x72m2b2w0c1p1d0r1rm4rw00e10zh0h0ms0mg0_wrapper",
            "sasuls0g4e2p1024x158m4b2w0c1p1d0r1rm4rw00e10zh0h0ms0mg0_wrapper",
        ]
    )
    ram.set_phy_info()
    ram.verilog_write()

    # ram = memgen()
    # ram.set_ram_info("enc_dma_metw_ram", 96, 256, "1p", 1, 0, "xcoder_enc_dma_rams_reset_n", "xcoder_enc_dma_rams_clk")
    # ram.set_ecc(calculate_ecc_width(96))
    # ram.set_phy_info()
    # ram.verilog_write()
    # s = ram.returnInstance()
    # print(s)

    # ram = memgen()
    # ram.set_ram_info("fb_nic", 512,  2048, "2p", 1, 0, "reset_n", "clk", "clk")
    # ram.set_ecc(calculate_ecc_width(512))
    # ram.set_phy_info()
    # ram.verilog_write()
    # ll = "pbuf"
    # ram.set_loop(ll)
    # s = ram.returnInstance()
    # print(s)

    # ram = memgen()
    # ram.set_ram_info("fb_nic", 64, 1024, "2p", 1, 0, "reset_n", "clk", "clk")
    # ram.set_ecc(calculate_ecc_width(64))
    # ram.set_phy_info()
    # ram.verilog_write()

    # ram = memgen()
    # ram.set_ram_info("fb_nic",280,  38, "2p", 0, 0, "reset_n", "clk", "clk")
    # ram.set_ecc(calculate_ecc_width(280))
    # ram.set_phy_info()
    # ram.verilog_write()
    # ll = "aa,ab,cc"
    # ram.set_loop(ll)
    # s = ram.returnInstance()
    # print(s)

    # ram = memgen()
    # ram.set_ram_info("scl_hs_luma_coeff_reg_set_1rw", 400, 8, "1f", 0, 0, "scl_reset_n", "scl_clk")
    # ram.set_hls()
    # ram.set_phy_info()
    # ram.verilog_write()

    # ram = memgen()
    # ram.set_ram_info("xcoder_qm_msssim_l0_top_nbr", 512, 6240,  "2p", 0, 0, "reset_n",
    #                  "clk", "clk")
    # ram.set_hls()
    # ram.set_phy_info()
    # ram.verilog_write()
    # ram.set_loop("xcoder_qm_msssim_l0_top_nbr")
    # s = ram.returnInstance()
    # print(s)

    # ram = memgen()
    # ram.set_ram_info("hs_coeff_reg_set_loop", 160, 8, "1f", 0, 0, "reset_n", "clk")
    # ram.set_hls()
    # ram.set_phy_info()
    # ram.verilog_write()

    # print(ram)
