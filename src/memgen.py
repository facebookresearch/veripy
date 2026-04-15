####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

#!/usr/bin/env python3
import json
import logging
import os
import re
import sys
from collections import defaultdict, OrderedDict

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from memgen_util import (
    addr_ports,
    ASIC_VENDORS,
    bwe_ports,
    calculate_ecc_width,
    cam_spl_in_ports,
    cam_spl_out_ports,
    clog2,
    combinationSum,
    cs_ports,
    dec_to_bin,
    dec_to_one_hot_bin,
    depth_partition_input_ports,
    depth_partition_ports,
    dict_keys_str_to_int,
    din_ports,
    dout_ports,
    is_mersenne_prime,
    isPowerOfTwo,
    mem_mapping_file,
    mem_ports_file,
    mem_vendor_mapping_file,
    memory_release_search_paths,
    nearest_2_pow,
    one_bit_ports,
    str_to_list,
    SumTheList,
    valid_sram_types,
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
        self.mem_vendor_mapping = None

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

        logging.debug(f"Valid vendor names: {ASIC_VENDORS}")
        if self.name not in ASIC_VENDORS:
            logging.error(f"Invalid vendor set: {self.name}.")
            rc = False
        else:
            logging.debug(f"Vendor is set to {self.name}")

        logging.debug(self)
        return rc

    def load_memory_config(self, infra, chip):
        rc = True
        for memory_release_search_path in memory_release_search_paths:
            path = memory_release_search_path % {
                "infra": infra,
                "chip": chip,
                "vendor": self.name,
            }

            mem_mapping_path = os.path.join(path, mem_mapping_file)
            if os.path.isfile(mem_mapping_path):
                self.mem_mapping_file = mem_mapping_path
                self.memory_release_dirctory = path
                logging.info(
                    f"load vendor memory config from {self.memory_release_dirctory}"
                )
                logging.debug(f"Loading memory mapping {self.mem_mapping_file}.")
                with open(self.mem_mapping_file) as mem_mapping_json:
                    mem_map = json.load(mem_mapping_json, object_pairs_hook=OrderedDict)
                    output = dict_keys_str_to_int(mem_map)
                    self.mem_mapping = OrderedDict(output)

                mem_vendor_mapping_path = os.path.join(path, mem_vendor_mapping_file)
                if os.path.isfile(mem_vendor_mapping_path):
                    logging.debug(
                        f"Loading Vendor memory mapping {mem_vendor_mapping_path}."
                    )
                    with open(mem_vendor_mapping_path) as mem_vendor_mapping_json:
                        mem_vendor_map = json.load(
                            mem_vendor_mapping_json, object_pairs_hook=OrderedDict
                        )
                        output = dict_keys_str_to_int(mem_vendor_map)
                        self.mem_vendor_mapping = OrderedDict(output)

                break

        if self.memory_release_dirctory is None:
            logging.error(
                f"No memory release directory found. infra: {infra} and vendor: {self.name}."
            )
            return False

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
        self.num_ecc_syndromes = 0
        self.enable_error_injection = False
        self.addrSize = clog2(self.depth)
        self.vendor = None
        self.fitting = None
        self.port_prefix = None

        self.sram_type = None
        self.module = None
        self.vf = None
        self.module_content = None
        self.dv_api = False
        self.phyMem_inst = {}
        self.mem_array = ""
        self.use_2cyc_memory = False

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

    def write_flop_version(self, fb_chip):
        if self.typ == "1f":
            self.module_content = "&BeginInstance fb_ram_1p_ff;\n"
        elif self.typ == "2f":
            self.module_content = "&BeginInstance fb_ram_2p_ff;\n"
        if self.ecc == 1:
            self.module_content += "  &Param DATA_WIDTH WIDTH_WITH_ECC;\n"
        else:
            self.module_content += "  &Param DATA_WIDTH WIDTH;\n"
        self.module_content += "  &Param DEPTH DEPTH;\n"
        if self.bitWrite == 0:
            self.module_content += "  &Connect bwe " + "'1" + ";" + "\n"
        if self.ecc == 1:
            self.module_content += "  &Connect din " + "din_with_ecc" + ";" + "\n"
        self.module_content += "  &Connect dout " + "dout_int" + ";" + "\n"
        self.module_content += "&EndInstance;\n"

    def print_flopstage_instantiation(self, num_latency, clk, reset, din, dout, is_ecc):
        width = "WIDTH_WITH_ECC" if is_ecc else "WIDTH"
        return f"""
&BeginInstance fb_flopstage;
&Param   N                  {num_latency};
&Param   SKID                0;
&Param   WIDTH               {width};
&Connect clk                 {clk};
&Connect reset_n             {reset};
&Connect out                 {dout};
&Connect out_valid           ;          // spyglass disable W287b
&Connect out_ready           1'b1;      //spyglass disable W240
&Connect in                  {din};
&Connect in_valid            1'b1;      //spyglass disable W240
&Connect in_ready            ;          // spyglass disable W287b
&EndInstance;\n
"""

    def fb_delay_re_print(self):
        clk = "r_clk" if self.typ == "2p" else "clk"
        re = "re" if self.typ == "2p" else "cs && ~we"
        latency = 2 if self.use_2cyc_memory else 1
        str_delay = f"""
assign re_in = {re};
// align re with dout
logic [{latency}:0] re_in_array;
assign re_in_array[0] = re_in;

always_ff @(posedge {clk} or negedge reset_n) begin
   if (~reset_n) begin
       re_in_array[{latency}:1] <= '0;
   end else begin
       re_in_array[{latency}:1] <= re_in_array[{latency}-1:0];
   end
end // always_ff @ (posedge {clk} or negedge reset_n)

assign re_aligned = re_in_array[{latency}];
"""
        return str_delay

    def fb_delay_print(self):
        clk = "r_clk" if self.typ == "2p" else "clk"
        re = "re" if self.typ == "2p" else "cs && ~we"
        latency = 2 if self.use_2cyc_memory else 1
        pipe = self.pipeline

        str_delay = self.fb_delay_re_print()

        if pipe == 0:
            str_delay += f"""
// optional pipe for dout
assign re_pipe = re_aligned;
assign dout_pipe = dout_int;
"""
        else:
            str_delay += f"""

// optional pipe for dout
logic [{pipe}:0] re_aligned_valid_array;
logic [{pipe}:0][WIDTH_WITH_ECC-1:0] dout_int_array;

assign re_aligned_valid_array[0] = re_aligned;

always_ff @(posedge {clk} or negedge reset_n) begin
  if (~reset_n) begin
      re_aligned_valid_array[{pipe}:1] <= '0;
  end else begin
      re_aligned_valid_array[{pipe}:1] <= re_aligned_valid_array[{pipe}-1:0];
  end
end // always_ff @ (posedge {clk} or negedge reset_n)

assign re_pipe = re_aligned_valid_array[{pipe}];

assign dout_int_array[0]         = dout_int;

always_ff @(posedge {clk} or negedge reset_n) begin
  if (~reset_n) begin
      dout_int_array[{pipe}:1]         <= '0;
  end else begin
      for (int i=1; i<{pipe}+1; i++) begin
          if (re_aligned_valid_array[i-1]) begin
              dout_int_array[i] <= dout_int_array[i-1];
          end
      end
  end
end
assign dout_pipe = dout_int_array[{pipe}];
"""

        return str_delay

    def ecc_print(self):
        str_tmp = "dout_pipe"

        str_ecc = f"""
localparam ECC_WIDTH = {self.ecc_width};
localparam WIDTH_WITH_ECC = WIDTH + ECC_WIDTH;
&logics;
assign din_with_ecc = {{ecc_chkbits,din}};

&BeginInstance fb_ecc_generate;
&Param DATA_WIDTH WIDTH;
&Param CHKBITS_WIDTH ECC_WIDTH;
&Connect in_data din;
&Connect out_chkbits ecc_chkbits[ECC_WIDTH-1:0];
&EndInstance;
"""

        str_ecc += self.fb_delay_print()

        str_ecc += f"""
assign dout_chkbits[ECC_WIDTH-1:0]  = {str_tmp}[WIDTH_WITH_ECC-1:WIDTH];
&BeginInstance fb_ecc_correct;
&Param DATA_WIDTH WIDTH;
&Param CHKBITS_WIDTH ECC_WIDTH;
&Connect in_data {str_tmp}[WIDTH-1:0];
&Connect in_chkbits dout_chkbits;
&Connect out_data dout;
&Connect out_err_detect out_err_detect_int;
&Connect out_err_multiple out_err_multiple_int;
&EndInstance;\n
"""

        str_ecc += "assign out_err_detect = re_pipe && out_err_detect_int;\n"
        str_ecc += "assign out_err_multiple = re_pipe && out_err_multiple_int;\n\n"

        return str_ecc

    def multi_ecc_print(self):
        r_clk = "clk"
        w_clk = "clk"
        wr_valid = "cs & we"
        if self.typ == "2p":
            r_clk = "r_clk"
            w_clk = "w_clk"
            wr_valid = "we"
        str_tmp = "dout_pipe"

        if not self.enable_error_injection:
            str_err_inj_tied_0 = "&Connect in_err_inj_1b 1'b0;\n&Connect in_err_inj_2b 1'b0;\n&Connect ecc_gen_state ; // spyglass disable W287b\n"
        else:
            str_err_inj_tied_0 = ""

        str_ecc = f"""
localparam ECC_WIDTH = {self.ecc_width};
localparam WIDTH_WITH_ECC = WIDTH + ECC_WIDTH;
&logics;
assign din_with_ecc = {{ecc_chkbits,ecc_data}};
assign in_valid = {wr_valid};

&BeginInstance fb_multi_ecc_generate;
&Param DATA_WIDTH WIDTH;
&Param NUM_ECC {self.num_ecc_syndromes};
&Connect clk {w_clk};
&Connect in_data din;
&Connect in_poison '0;
&Connect out_data ecc_data;
&Connect out_chkbits ecc_chkbits;
{str_err_inj_tied_0}&EndInstance;
"""

        str_ecc += self.fb_delay_print()
        str_ecc += f"""
assign dout_chkbits[ECC_WIDTH-1:0]  = {str_tmp}[WIDTH_WITH_ECC-1:WIDTH];
&BeginInstance fb_multi_ecc_correct;
&Param DATA_WIDTH WIDTH;
&Param NUM_ECC {self.num_ecc_syndromes};
&Connect clk {r_clk};
&Connect in_data {str_tmp}[WIDTH-1:0];
&Connect in_valid 1'b0;
&Connect in_chkbits dout_chkbits;
&Connect in_err_inj_1b 1'b0;
&Connect in_err_inj_2b 1'b0;
&Connect out_chkbits ; // spyglass disable W287b
&Connect out_data dout;
&Connect out_poison ; // spyglass disable W287b
&Connect ecc_state ; // spyglass disable W287b
&Connect out_err_detect out_err_detect_int;
&Connect out_err_multiple out_err_multiple_int;
&EndInstance;\n
"""

        str_ecc += "assign out_err_detect = re_pipe && out_err_detect_int;\n"
        str_ecc += "assign out_err_multiple = re_pipe && out_err_multiple_int;\n\n"

        return str_ecc

    def print_beh_mem_xilinx(self, memWrapper, fb_chip):
        if self.ecc == 1:
            ecc_print = self.ecc_print()
            memWrapper.write(ecc_print)

        if self.ecc == 0:
            memWrapper.write("&logics;\n")
            clk = "clk" if self.typ == "1p" else "r_clk"
            if self.pipeline > 0:
                if self.pipeline == 1:
                    memWrapper.write(f"&Clock {clk};\n&AsyncReset reset_n;\n")
                    memWrapper.write(
                        "&Posedge;\n    dout <0= dout_int;\n&Endposedge;\n"
                    )
                else:
                    memWrapper.write(
                        self.print_flopstage_instantiation(
                            self.pipeline, clk, "reset_n", "dout_int", "dout", False
                        )
                    )
            else:
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

        memWrapper.write("  &Param DEPTH DEPTH;\n")
        if self.bitWrite == 0:
            memWrapper.write("  &Connect bwe " + "'1" + ";" + "\n")
        if self.ecc == 1:
            memWrapper.write("  &Connect din " + "din_with_ecc" + ";" + "\n")
        memWrapper.write("  &Connect dout " + "dout_int" + ";" + "\n")
        memWrapper.write("  &EndInstance;\n")

    def print_beh_cam(self, memWrapper, fb_chip):
        if self.ecc == 0:
            memWrapper.write("&logics;\n")

        doutv_conn = "doutv_int_beh"

        beh_cam_str = """
    fb_tcam_1p_beh # (
      .WIDTH (WIDTH),
      .DEPTH (DEPTH),
      .RD_LATENCY (CAM_RD_LATENCY)
    ) u_cam_i (
      .clk       (clk),
      .add       (addr),
      .cs        (cs),
      .ce        (ce),
      .re        (re),
      .we        (we),
      .swe       (swe),
      .vwe       (vwe),
      .din       (din),
      .dinv      (dinv),
      .dinm      (dinm),
      .reset_n   (reset_n),
      .dout      (dout_int),
      .doutv     ({0}),
      .matchout  (matchout)
    );
""".format(
            doutv_conn,
        )

        memWrapper.write(beh_cam_str)

        if self.ecc == 0:
            clk = "clk"  # CAM is always 1p
            if self.pipeline > 0:
                if self.pipeline == 1:
                    ecc_0_pipe_1_str = self.fb_delay_re_print()

                    ecc_0_pipe_1_str += f"""
always_ff @(posedge {clk} or negedge reset_n) begin
  if (~reset_n) begin
      dout[WIDTH-1:0] <= '0;
  end else begin
      if (re_aligned) begin
          dout[WIDTH-1:0] <= dout_int;
      end
  end
end // always_ff @ (posedge {clk} or negedge reset_n)

                    """
                    memWrapper.write(ecc_0_pipe_1_str)

                    # Handle doutv with verilog preprocessor style (CAM-specific)
                    memWrapper.write(f"&Clock {clk};\n&AsyncReset reset_n;\n")
                    memWrapper.write(
                        "&Posedge;\n    doutv <0= |doutv_int_beh;\n&Endposedge;\n"
                    )
                else:
                    # pipeline > 1
                    memWrapper.write(
                        self.print_flopstage_instantiation(
                            self.pipeline, clk, "reset_n", "dout_int", "dout", False
                        )
                    )
                    memWrapper.write(
                        self.print_flopstage_instantiation(
                            self.pipeline,
                            clk,
                            "reset_n",
                            "|doutv_int_beh",
                            "doutv",
                            False,
                        )
                    )
            else:
                # pipeline == 0
                memWrapper.write("assign dout[WIDTH-1:0] = dout_int;\n")
                memWrapper.write("assign doutv = |doutv_int_beh;\n")

    def print_beh_mem(self, memWrapper, fb_chip):
        if self.ecc == 0:
            clk = "clk" if self.typ == "1p" else "r_clk"
            memWrapper.write("&logics;\n")
            if self.pipeline > 0:
                if self.pipeline == 1:
                    ecc_0_pipe_1_str = self.fb_delay_re_print()

                    ecc_0_pipe_1_str += f"""
always_ff @(posedge {clk} or negedge reset_n) begin
  if (~reset_n) begin
      dout <= '0;
  end else begin
      if (re_aligned) begin
          dout <= dout_int;
      end
  end
end // always_ff @ (posedge {clk} or negedge reset_n)

                    """
                    memWrapper.write(ecc_0_pipe_1_str)
                else:
                    memWrapper.write(
                        self.print_flopstage_instantiation(
                            self.pipeline, clk, "reset_n", "dout_int", "dout", False
                        )
                    )
            else:
                memWrapper.write("assign dout = dout_int;\n")

            if self.fitting is None or self.fitting.depth_iter == 1:
                if self.pipeline == 1:
                    if (self.typ == "1p") or (self.typ == "1f"):
                        memWrapper.write("&Clock clk;\n&AsyncReset reset_n;\n")
                    if (self.typ == "2p") or (self.typ == "2f"):
                        memWrapper.write("&Clock r_clk;\n&AsyncReset reset_n;\n")

        memWrapper.write("&Force width dout WIDTH;\n")
        if (self.typ == "1p") or (self.typ == "1f"):
            memWrapper.write("&BeginInstance fb_ram_1p_beh;\n")
        elif (self.typ == "2p") or (self.typ == "2f"):
            memWrapper.write("&BeginInstance fb_ram_2p_beh;\n")

        if self.ecc == 1:
            memWrapper.write("  &Param DATA_WIDTH WIDTH_WITH_ECC;\n")
        else:
            memWrapper.write("  &Param DATA_WIDTH WIDTH;\n")

        memWrapper.write("  &Param DEPTH DEPTH;\n")
        if self.use_2cyc_memory:
            memWrapper.write("  &Param LATENCY 2;\n")

        if self.bitWrite == 0:
            memWrapper.write("  &Connect bwe " + "'1" + ";" + "\n")
        if self.ecc == 1:
            memWrapper.write("  &Connect din " + "din_with_ecc" + ";" + "\n")
        memWrapper.write("  &Connect dout " + "dout_int" + ";" + "\n")
        memWrapper.write("  &EndInstance;\n")

    def verilog_write_vendor(self, memWrapper, fb_chip, is_cam_memory):
        if self.vendor.name == "xilinx":
            memWrapper.write("`else // {\n\n")
        else:
            memWrapper.write("`elsif " + self.vendor.name + " // {\n\n")

        if self.vendor.mem_mapping != None and self.vendor.mem_ports != None:
            if self.ecc == 1:
                if self.num_ecc_syndromes > 0 or self.enable_error_injection:
                    ecc_print = self.multi_ecc_print()
                else:
                    ecc_print = self.ecc_print()
                memWrapper.write(ecc_print)

            if self.ecc == 0:
                memWrapper.write("&logics;\n")

            if self.typ == "2p":
                bits = clog2(nearest_2_pow(self.fitting.depth_iter))
                if not isPowerOfTwo(self.fitting.pic_depth) and bits > 0:
                    bits += 1
                if bits == 0:
                    memWrapper.write("logic wea; assign wea = we;\n")
                if (
                    self.vendor.name != "mrvl_n3"
                    or isPowerOfTwo(self.depth)
                    or self.fitting.depth_iter == 1
                ):
                    memWrapper.write("assign rea = re;\n")
                if self.bitWrite == 1 and ("brcm" not in self.vendor.name):
                    memWrapper.write("assign bwea = bwe;\n")

            if self.ecc == 0:
                clk = "clk" if self.typ == "1p" else "r_clk"
                if self.pipeline > 0:
                    if self.pipeline == 1:
                        ecc_0_pipe_1_str = self.fb_delay_re_print()

                        ecc_0_pipe_1_str += f"""
always_ff @(posedge {clk} or negedge reset_n) begin
  if (~reset_n) begin
      dout <= '0;
  end else begin
      if (re_aligned) begin
          dout <= dout_int;
      end
  end
end // always_ff @ (posedge {clk} or negedge reset_n)
                        """
                        memWrapper.write(ecc_0_pipe_1_str)

                        if is_cam_memory:
                            memWrapper.write(f"&Clock {clk};\n&AsyncReset reset_n;\n")
                            memWrapper.write(
                                "&Posedge;\n    doutv <0= |doutv_int;\n&Endposedge;\n"
                            )
                    else:
                        memWrapper.write(
                            self.print_flopstage_instantiation(
                                self.pipeline, clk, "reset_n", "dout_int", "dout", False
                            )
                        )
                        if is_cam_memory:
                            memWrapper.write(
                                self.print_flopstage_instantiation(
                                    self.pipeline,
                                    clk,
                                    "reset_n",
                                    "|doutv_int",
                                    "doutv",
                                    False,
                                )
                            )
                else:
                    memWrapper.write("assign dout = dout_int;\n")
                    if is_cam_memory:
                        memWrapper.write("assign doutv = |doutv_int;\n")

                if self.fitting is None or self.fitting.depth_iter == 1:
                    if self.pipeline == 1:
                        if (self.typ == "1p") or (self.typ == "1f"):
                            memWrapper.write("&Clock clk;\n&AsyncReset reset_n;\n")
                        if (self.typ == "2p") or (self.typ == "2f"):
                            memWrapper.write("&Clock r_clk;\n&AsyncReset reset_n;\n")

            memWrapper.write(self.module_content)
        else:
            if self.vendor.name == "xilinx":
                self.print_beh_mem_xilinx(memWrapper, fb_chip)
            else:
                self.print_beh_mem(memWrapper, fb_chip)

        memWrapper.write("// } " + self.vendor.name + " \n")

    def set_mem_array(self):
        if "brcm_ccx" in self.vendor.name:
            self.mem_array = ".array"
        elif "brcm_apd" in self.vendor.name:
            self.mem_array = ".u_mem"

    def dv_api_print_get_write(
        self, beh_mem_type, vendor_write_decls, vendor_write, memgen
    ):
        if memgen.cam_memory:
            dv_api_str = """
    `ifdef MEM_DV_API
    //synopsys pragma translate_off
    localparam DATA_WIDTH = {0};
    localparam MAX_ADDR = {1};

    task automatic backdoorWrite;
        input [ADDR_WIDTH:0] addr_in;
        input [DATA_WIDTH-1:0] wdata;
        output success;
{5}        begin
            if(addr_in >= MAX_ADDR) begin
                success = 0;
            end else begin
                `ifdef FB_BEH_MEM{2}
                `elsif {3}
{4}				`endif
                success = 1;
            end
        end
    endtask : backdoorWrite
    """.format(
                self.ecc_width + self.width,
                self.depth,
                "",
                self.vendor.name,
                vendor_write,
                vendor_write_decls,
            )
        else:
            dv_api_str = """
    `ifdef MEM_DV_API
    //synopsys pragma translate_off
    localparam DATA_WIDTH = {0};
    localparam MAX_ADDR = {1};

    task automatic backdoorWrite;
        input [ADDR_WIDTH:0] addr_in;
        input [DATA_WIDTH-1:0] wdata;
        output success;
{5}        begin
            if(addr_in >= MAX_ADDR) begin
                success = 0;
            end else begin
                `ifdef FB_BEH_MEM
                {2}.mem[addr_in]  = wdata[DATA_WIDTH-1:0];
                `elsif {3}
{4}				`endif
                success = 1;
            end
        end
    endtask : backdoorWrite
    """.format(
                self.ecc_width + self.width,
                self.depth,
                beh_mem_type,
                self.vendor.name,
                vendor_write,
                vendor_write_decls,
            )
        return dv_api_str

    def dv_api_print_get_read(
        self, beh_mem_type, vendor_read_decls, vendor_read, memgen
    ):
        if memgen.cam_memory:
            dv_api_str = """
    task  automatic backdoorRead;
        input  [ADDR_WIDTH:0] addr_in;
        output [DATA_WIDTH-1:0] rdata;
        output success;
{3}        begin
            if(addr_in >= MAX_ADDR) begin
                success = 0;
             end else begin
                `ifdef FB_BEH_MEM{0}
                `elsif {1}
{2}				`endif
                success = 1;
            end
        end
    endtask : backdoorRead
    """.format("", self.vendor.name, vendor_read, vendor_read_decls)
        else:
            dv_api_str = """
    task  automatic backdoorRead;
        input  [ADDR_WIDTH:0] addr_in;
        output [DATA_WIDTH-1:0] rdata;
        output success;
{3}        begin
            if(addr_in >= MAX_ADDR) begin
                success = 0;
             end else begin
                `ifdef FB_BEH_MEM
                rdata[DATA_WIDTH-1:0] = {0}.mem[addr_in];
                `elsif {1}
{2}				`endif
                success = 1;
            end
        end
    endtask : backdoorRead
    """.format(beh_mem_type, self.vendor.name, vendor_read, vendor_read_decls)
        return dv_api_str

    def dv_api_print_get_init(
        self,
        beh_mem_type,
        mem_init_decls,
        mem_inst_init_0,
        mem_inst_init_1,
        mem_inst_init_2,
        memgen,
    ):
        if memgen.cam_memory:
            dv_api_str = """
    task automatic backdoorInit;
        input [4:0] data_type;
        output 		success;
        reg [DATA_WIDTH-1:0] init_data;
{5}        //data_type
        //0: init all 'h0
        //1: init all 'h1
        //2: init all random
        begin
            if(data_type == 0) begin
                success		= 1;
                `ifdef FB_BEH_MEM{0}
                `elsif {1}
                // repeat the following for all mem instances. No addr/data split check needed here since init data is 0 for all instances
{2}				`endif
            end else if(data_type == 1) begin
                success		= 1;
                `ifdef FB_BEH_MEM{0}
                `elsif {1}
                // repeat the following for all mem instances. No addr/data split check needed here since init data is 1 for all instances
{3}				`endif
            end else if(data_type == 2) begin
                success		= 1;
                `ifdef FB_BEH_MEM{0}
                `elsif {1}
{4}				`endif
            end else begin
                success 	= 0;
                $display("%m: data_type %0d is not supported in init_mem\\n", data_type);
            end
        end
    endtask : backdoorInit
    //synopsys pragma translate_on
    `endif // MEM_DV_API
                """.format(
                "",
                self.vendor.name,
                mem_inst_init_0,
                mem_inst_init_1,
                mem_inst_init_2,
                mem_init_decls,
            )
        else:
            dv_api_str = """
    task automatic backdoorInit;
        input [4:0] data_type;
        output 		success;
        reg [DATA_WIDTH-1:0] init_data;
{5}        //data_type
        //0: init all 'h0
        //1: init all 'h1
        //2: init all random
        begin
            if(data_type == 0) begin
                success		= 1;
                `ifdef FB_BEH_MEM
                foreach ({0}.mem[addr_in]) begin
                    {0}.mem[addr_in] = 'h0;
                end
                `elsif {1}
                // repeat the following for all mem instances. No addr/data split check needed here since init data is 0 for all instances
{2}				`endif
            end else if(data_type == 1) begin
                success		= 1;
                `ifdef FB_BEH_MEM
                foreach ({0}.mem[addr_in]) begin
                    {0}.mem[addr_in] = 'h1;
                end
                `elsif {1}
                // repeat the following for all mem instances. No addr/data split check needed here since init data is 1 for all instances
{3}				`endif
            end else if(data_type == 2) begin
                success		= 1;
                `ifdef FB_BEH_MEM
                foreach ({0}.mem[addr_in]) begin
                    std::randomize(init_data);
                    {0}.mem[addr_in] = init_data;
                end
                `elsif {1}
{4}				`endif
            end else begin
                success 	= 0;
                $display("%m: data_type %0d is not supported in init_mem\\n", data_type);
            end
        end
    endtask : backdoorInit
    //synopsys pragma translate_on
    `endif // MEM_DV_API
    """.format(
                beh_mem_type,
                self.vendor.name,
                mem_inst_init_0,
                mem_inst_init_1,
                mem_inst_init_2,
                mem_init_decls,
            )

        return dv_api_str

    def dv_api_get_vendor(self, memgen):
        indent_cnt = 16
        vendor_write_decls = []
        vendor_write = []
        vendor_read_decls = []
        vendor_read = []
        mem_init_decls = []
        mem_inst_init_0 = ""
        mem_inst_init_1 = ""
        mem_inst_init_2 = ""

        if self.vendor.name.startswith("brcm") and memgen.cam_memory:
            vendor_write_decls.extend(["input [1:0] validbits;", "input ynx;"])
            vendor_read_decls.extend(["input [1:0] validbits;", "input ynx;"])
            mem_init_decls.extend(
                [
                    "input [ADDR_WIDTH:0] addr_in;",
                    "input [1:0] validbits;",
                    "input ynx;",
                ]
            )

        curr_start_addr = 0
        for bank_index, bank in self.phyMem_inst.items():
            user_addr_bits = clog2(self.depth)

            indent_cnt += 2
            if len(self.phyMem_inst) > 1:
                pick_addr_bits = clog2(bank["depth"])
                selection = user_addr_bits - pick_addr_bits
                if bank_index == 0:
                    if_clause = f"{' ' * indent_cnt}if(addr_in >= {curr_start_addr} & addr_in < {curr_start_addr + bank['depth']})"
                    vendor_write.append(if_clause)
                    vendor_read.append(if_clause)
                elif bank_index == len(self.phyMem_inst) - 1:
                    vendor_write.append(f"{' ' * indent_cnt}else")
                    vendor_read.append(f"{' ' * indent_cnt}else")
                else:
                    elsif_clause = f"{' ' * indent_cnt}else if(addr_in >= {curr_start_addr} & addr_in < {curr_start_addr + bank['depth']})"
                    vendor_write.append(elsif_clause)
                    vendor_read.append(elsif_clause)

                vendor_write.append(f"{' ' * indent_cnt}begin")
                vendor_read.append(f"{' ' * indent_cnt}begin")

            indent_cnt += 2
            for bank_width in bank["insts"]:
                inst_ref = bank_width["inst_ref"]
                max_width = bank_width["max_width"]
                min_width = bank_width["min_width"]
                if self.vendor.name.startswith("brcm") and memgen.cam_memory:
                    mem_inst_init_0 += (
                        f"{' ' * indent_cnt}{inst_ref}.tf_fill_mem('h0, validbits);\n"
                    )
                    mem_inst_init_1 += (
                        f"{' ' * indent_cnt}{inst_ref}.tf_fill_mem(1, validbits);\n"
                    )
                    mem_inst_init_2 += f"""{" " * indent_cnt}for (int tk_addr = 0; tk_addr < DEPTH; tk_addr = tk_addr +1) begin
{" " * indent_cnt}  std::randomize(init_data);
{" " * indent_cnt}{inst_ref}.tf_put_word(tk_addr, init_data[{max_width}:{min_width}], ynx, validbits);
{" " * indent_cnt}end
"""
                    vendor_write.append(
                        f"{' ' * indent_cnt}{inst_ref}.tf_put_word(addr_in, wdata[{max_width}:{min_width}], ynx, validbits);"
                    )
                    vendor_read.append(
                        f"{' ' * indent_cnt}{inst_ref}.tf_get_word(rdata[{max_width}:{min_width}], validbits, addr_in, ynx);"
                    )
                else:
                    mem_inst_init_0 += (
                        f"{' ' * indent_cnt}{inst_ref}.tf_fill_mem('h0);\n"
                    )
                    mem_inst_init_1 += f"{' ' * indent_cnt}{inst_ref}.tf_fill_mem(1);\n"
                    mem_inst_init_2 += f"""{" " * indent_cnt}foreach ({inst_ref}.array[addr_in]) begin
{" " * indent_cnt}  std::randomize(init_data);
{" " * indent_cnt}{inst_ref}.tf_put_word(addr_in, init_data[{max_width}:{min_width}]);
{" " * indent_cnt}end
"""
                    offset_str = f" - {curr_start_addr}" if curr_start_addr > 0 else ""
                    vendor_write.append(
                        f"{' ' * indent_cnt}{inst_ref}.tf_put_word(addr_in{offset_str}, wdata[{max_width}:{min_width}]);"
                    )
                    vendor_read.append(
                        f"{' ' * indent_cnt}{inst_ref}.tf_get_word(rdata[{max_width}:{min_width}], addr_in{offset_str});"
                    )
            indent_cnt -= 2

            if len(self.phyMem_inst) > 1:
                vendor_write.append(f"{' ' * indent_cnt}end")
                vendor_read.append(f"{' ' * indent_cnt}end")
            indent_cnt -= 2

            curr_start_addr += bank["depth"]

        return (
            (
                "".join([f"        {l}\n" for l in vendor_write_decls]),
                "".join([l + "\n" for l in vendor_write]),
            ),
            (
                "".join([f"        {l}\n" for l in vendor_read_decls]),
                "".join([l + "\n" for l in vendor_read]),
            ),
            (
                "".join([f"        {l}\n" for l in mem_init_decls]),
                mem_inst_init_0,
                mem_inst_init_1,
                mem_inst_init_2,
            ),
        )

    def dv_api_print(self, memgen):
        vendor_write = ""
        vendor_read = ""
        beh_mem_type = ""
        mem_inst_init_0 = ""
        mem_inst_init_1 = ""
        mem_inst_init_2 = ""
        inst = ""

        dv_api_str = ""

        if memgen.cam_memory:
            beh_mem_type = "u_cam_i"
        elif self.typ == "1p" or self.typ == "1f":
            beh_mem_type = "u_fb_ram_1p_beh"
        elif self.typ == "2p" or self.typ == "2f":
            beh_mem_type = "u_fb_ram_2p_beh"

        if self.typ == "1f":
            self.phyMem_inst.append(
                {
                    "inst_ref": "u_fb_ram_1f_ff",
                    "max_width": "DATA_WIDTH-1",
                    "min_width": "0",
                }
            )
        if self.typ == "2f":
            self.phyMem_inst.append(
                {
                    "inst_ref": "u_fb_ram_2f_ff",
                    "max_width": "DATA_WIDTH-1",
                    "min_width": "0",
                }
            )

        (
            (vendor_write_decls, vendor_write),
            (vendor_read_decls, vendor_read),
            (mem_init_decls, mem_inst_init_0, mem_inst_init_1, mem_inst_init_2),
        ) = self.dv_api_get_vendor(memgen)

        if (
            beh_mem_type != ""
            and vendor_write != ""
            and vendor_read != ""
            and mem_inst_init_0 != ""
            and mem_inst_init_1 != ""
            and mem_inst_init_2 != ""
        ):
            dv_api_str = self.dv_api_print_get_write(
                beh_mem_type, vendor_write_decls, vendor_write, memgen
            )
            dv_api_str += self.dv_api_print_get_read(
                beh_mem_type, vendor_read_decls, vendor_read, memgen
            )
            dv_api_str += self.dv_api_print_get_init(
                beh_mem_type,
                mem_init_decls,
                mem_inst_init_0,
                mem_inst_init_1,
                mem_inst_init_2,
                memgen,
            )

        return dv_api_str

    def verilog_write(self, memgen):
        """Write a behavioral Verilog model."""
        logging.info(f"writing verilog file {self.vf}\n")
        with open(self.vf, "w") as memWrapper:
            memWrapper.write(
                "&Module(parameter WIDTH = {0}, DEPTH = {1}, ADDR_WIDTH = $clog2(DEPTH)".format(
                    self.width, self.depth
                ).format(self.addrSize)
            )
            if memgen.cam_memory:
                memWrapper.write(", CAM_RD_LATENCY = 1);\n\n")
            else:
                memWrapper.write(");\n")

            if self.vendor.name == "mrvl_n3" or (
                (self.vendor.name == "brcm_apd_n3" or self.vendor.name == "brcm_apd_n2")
                and memgen.beh_wrapper_only
            ):
                memWrapper.write("&Force input CORE_MEM_RST;\n")
                if memgen.cam_memory:
                    memWrapper.write("&Force input logic blksel;\n")
                if self.vendor.name == "mrvl_n3":
                    memWrapper.write(
                        "logic CORE_MEM_RST_unused; //spyglass disable W528\n"
                    )
                    memWrapper.write(
                        "assign CORE_MEM_RST_unused = CORE_MEM_RST; //spyglass disable W528\n"
                    )

            memWrapper.write("\n`ifdef FB_BEH_MEM // {\n")
            if self.ecc == 1:
                if self.num_ecc_syndromes > 0 or self.enable_error_injection:
                    ecc_print = self.multi_ecc_print()
                else:
                    ecc_print = self.ecc_print()
                memWrapper.write(ecc_print)

            if memgen.cam_memory:
                self.print_beh_cam(memWrapper, memgen.fb_chip)
            else:
                self.print_beh_mem(memWrapper, memgen.fb_chip)
            memWrapper.write("// } FB_BEH_MEM\n")

            if not memgen.beh_wrapper_only:
                if self.vendor is not None:
                    self.verilog_write_vendor(
                        memWrapper, memgen.fb_chip, memgen.cam_memory
                    )

            memWrapper.write("`endif\n")

            if self.dv_api:
                memWrapper.write(self.dv_api_print(memgen))

        memWrapper.close()
        # self.module_content = None

    def return_sram_loop_2p(self, loop):
        port_prefix = self.port_prefix if self.port_prefix is not None else self.prefix
        # if user provides only loop int
        # if users provide list
        # if users provide string
        sram_instance = " u_" + self.prefix
        sramidx = ""
        content = ""
        for loopidx, loopvalue in enumerate(loop):
            if type(loopvalue) is int:
                sram_instance = " u_" + self.prefix + "_" + str(loopidx)
                sramidx = port_prefix + "_" + str(loopidx)
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
                    if self.num_ecc_syndromes > 0 or self.enable_error_injection:
                        content += f"&Connect ecc_gen_state {sramidx}_ecc_gen_state;\n"

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
        port_prefix = self.port_prefix if self.port_prefix is not None else self.prefix
        # if user provides only loop int
        # if users provide list
        # if users provide string
        sram_instance = " u_" + self.prefix
        sramidx = ""
        content = ""
        for loopidx, loopvalue in enumerate(loop):
            if type(loopvalue) is int:
                sram_instance = " u_" + self.prefix + "_" + str(loopidx)
                sramidx = port_prefix + "_" + str(loopidx)
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
        port_prefix = self.port_prefix if self.port_prefix is not None else self.prefix
        content = ""
        content = "&BeginInstance " + self.module + " u_" + self.module + ";\n"
        content += "&BuildCommand --disable_tick_ifdefs;\n"
        content += "&Param DEPTH " + str(self.depth) + ";\n"
        content += "&Param WIDTH " + str(self.width) + ";\n"
        if self.hls:
            content += "&Connect r_addr " + port_prefix + "_rd_r_addr;" + "\n"
            content += "&Connect re " + port_prefix + "_rd_re;" + "\n"
            content += "&Connect dout " + port_prefix + "_rd_dout;" + "\n"
            content += "&Connect w_addr " + port_prefix + "_wr_w_addr;" + "\n"
            content += "&Connect din " + port_prefix + "_wr_din;" + "\n"
            content += "&Connect we " + port_prefix + "_wr_we;" + "\n"
            if self.bitWrite == 1:
                content += "&Connect bwe " + port_prefix + "_wr_bwe;" + "\n"
        else:
            content += "&Connect r_addr " + port_prefix + "_r_addr;" + "\n"
            content += "&Connect re " + port_prefix + "_re;" + "\n"
            content += "&Connect dout " + port_prefix + "_dout;" + "\n"
            content += "&Connect w_addr " + port_prefix + "_w_addr;" + "\n"
            content += "&Connect din " + port_prefix + "_din;" + "\n"
            content += "&Connect we " + port_prefix + "_we;" + "\n"
            if self.ecc == 1:
                content += (
                    "&Connect out_err_detect " + port_prefix + "_out_err_detect;\n"
                )
                content += (
                    "&Connect out_err_multiple " + port_prefix + "_out_err_multiple;\n"
                )
                if self.num_ecc_syndromes > 0 or self.enable_error_injection:
                    content += f"&Connect ecc_gen_state {port_prefix}_ecc_gen_state;\n"

            if self.bitWrite == 1:
                content += "&Connect bwe " + port_prefix + "_bwe;" + "\n"

        if (self.typ == "2p") or (self.typ == "2f"):
            content += "&Connect r_clk " + self.rclk + ";" + "\n"
            content += "&Connect w_clk " + self.wclk + ";" + "\n"
        elif (self.typ == "1p") or (self.typ == "1f"):
            content += "&Connect clk " + self.wclk + ";" + "\n"

        content += "&Connect reset_n " + self.rst + ";" + "\n"
        content += "&EndInstance;" + "\n"
        return content

    def return_sram(self, memgen):
        port_prefix = self.port_prefix if self.port_prefix is not None else self.prefix
        content = ""
        content = "&BeginInstance " + self.module + " u_" + self.module + ";\n"
        content += "&BuildCommand --disable_tick_ifdefs;\n"
        content += "&Param DEPTH " + str(self.depth) + ";\n"
        content += "&Param WIDTH " + str(self.width) + ";\n"
        if memgen.cam_memory:
            content += "&Param CAM_RD_LATENCY CAM_RD_LATENCY;\n"

        content += "&Connect /^/ /" + port_prefix + "_/;" + "\n"

        if (self.typ == "2p") or (self.typ == "2f"):
            content += "&Connect r_clk " + self.rclk + ";" + "\n"
            content += "&Connect w_clk " + self.wclk + ";" + "\n"
        elif (self.typ == "1p") or (self.typ == "1f"):
            content += "&Connect clk " + self.wclk + ";" + "\n"
            if (self.vendor.name == "brcm_ccx_n7") and (self.typ != "1f"):
                content += "&Connect tm_sp_ram tm_sp_ram;" + "\n"

        content += "&Connect reset_n " + self.rst + ";" + "\n"
        content += "&EndInstance;" + "\n"
        return content

    def instantiate_module_instances(self, memgen):
        content = ""
        if type(memgen.loop) is not list:
            return content

        # If loop cnt is greater than or equal to 1, includes hls
        if (len(memgen.loop) >= 1) and ((self.typ == "2p") or (self.typ == "2f")):
            content += self.return_sram_loop_2p(memgen.loop)
        # If loop cnt is greater than or equal to 1,
        # hls not needed. ports are same for 1p
        elif (len(memgen.loop) >= 1) and ((self.typ == "1p") or (self.typ == "1f")):
            content += self.return_sram_loop_1p(memgen.loop)
        # regular version no loop defined, includes hls
        elif (len(memgen.loop) == 0) and ((self.typ == "2p") or (self.typ == "2f")):
            content += self.return_sram_hls_2p()
        elif (len(memgen.loop) == 0) and ((self.typ == "1p") or (self.typ == "1f")):
            content += self.return_sram(memgen)
        else:
            logging.error("Generating the BeginInstance")
            logging.error(
                "Loop,Type,Hls:" + str(len(memgen.loop)) + str(self.typ) + str(self.hls)
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
        sel_phy_mem,
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
        self.sel_phy_mem = sel_phy_mem

    def __str__(self):
        return f"""
memory_key: {self.sram_type}, user_width: {self.user_width}, user_depth: {self.user_depth}, ecc_width: {self.ecc_width},
pic_depth: {self.pic_depth}, depth_iter: {self.depth_iter}, depth_residue: {self.depth_residue}
pic_widths: {self.pic_widths}, width_iter: {self.width_iter}, width_residue: {self.width_residue}, sel_phy_mem: {self.sel_phy_mem}
"""


class memgen:
    def __init__(self):
        self.infra = os.environ.get("INFRA_ASIC_FPGA_ROOT", None)
        # self.fb_chip = os.environ.get("FB_CHIP", None)
        self.fb_chip = None
        self.vendor = None
        self.user_ram = None
        self.sram_type = None
        self.loop = []
        self.vendor_memories = None
        self.beh_wrapper_only = False
        self.internal_use = False
        self.no_wrapper_instantiation = False
        self.cam_memory = False
        self.num_ecc_syndromes = 0
        self.enable_error_injection = False
        self.vendor_tiling = None
        self.force_internal_signals = []

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
            logging.error("Please do `set_chip <chip> ` and `ff switch <workspace>`\n")
            rc = False
        else:
            logging.debug(f"Envir Variable INFRA_ASIC_FPGA_ROOT is set to {self.infra}")

        if self.fb_chip is None:
            logging.error("Missing Envir Variable FB_CHIP.")
            rc = False
        else:
            logging.debug(f"Envir Variable FB_CHIP is set to {self.fb_chip}")

        if self.vendor is None:
            logging.error(f"Missing Envir Variable FB_CHIP.")
            rc = False
        else:
            rc &= self.vendor.self_check()

        return rc

    def check_ram_info(self):
        if self.user_ram != None and self.user_ram.self_check():
            self.user_ram.vendor = self.vendor
            return True
        else:
            return False

    def set_vendor(self, vendor=None):
        if vendor is None:
            vendor = os.environ.get("ASIC_VENDOR", None)

        if vendor == "brcm":
            vendor = "brcm_apd_n3"

        if vendor is not None:
            self.vendor = Vendor(vendor)
            return True

        return False

    def set_ram_info(
        self, prefix, width, depth, typ, pipeline, bitwrite, rst, wclk, rclk=None
    ):
        if self.memgen_line is not None:
            logging.info(f"Memgen - memgen call: {self.memgen_line}")
        logging.info(
            "memory info - width:{} depth:{} type:{} pipeline:{}"
            " bit_write:{} rst:{} wclk:{}, rclk:{}".format(
                width, depth, typ, pipeline, bitwrite, rst, wclk, rclk
            )
        )
        self.user_ram = UserRam(
            prefix, width, depth, typ, pipeline, bitwrite, rst, wclk, rclk
        )
        if self.vendor:
            self.user_ram.vendor = self.vendor

    def set_ecc(self):
        if self.user_ram:
            self.user_ram.ecc = 1
            self.user_ram.enable_error_injection = self.enable_error_injection
            if self.user_ram.enable_error_injection and self.num_ecc_syndromes == 0:
                self.user_ram.num_ecc_syndromes = 1
            else:
                self.user_ram.num_ecc_syndromes = self.num_ecc_syndromes
            self.user_ram.ecc_width = calculate_ecc_width(
                self.user_ram.width, self.user_ram.num_ecc_syndromes
            )
            logging.debug(f"\t\t ECC_RAM_WIDTH = {self.user_ram.ecc_width}")
        else:
            logging.error("Please set ram info before enabling ecc.")

    def set_dv_api(self, dv_api):
        if self.user_ram:
            self.user_ram.dv_api = dv_api
            logging.debug(f"\t\t dv_api = {self.user_ram.dv_api}")
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

        if self.cam_memory:
            self.sram_type = 311
        elif self.user_ram.typ == "1p" and self.user_ram.bitWrite == 1:
            if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
                self.sram_type = 1111
            else:
                self.sram_type = 111
        elif self.user_ram.typ == "1p" and self.user_ram.bitWrite == 0:
            if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
                self.sram_type = 1110
            else:
                self.sram_type = 111
        elif self.user_ram.typ == "2p" and self.user_ram.bitWrite == 1:
            if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
                if self.user_ram.wclk == self.user_ram.rclk:
                    self.sram_type = 2111
                else:
                    self.sram_type = 21112
            else:
                self.sram_type = 211
        elif self.user_ram.typ == "2p" and self.user_ram.bitWrite == 0:
            if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
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
        return self.vendor.load_memory_config(self.infra, self.fb_chip)

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
        # depths = np_depth[np.argmin(np_rem, axis=0)]
        depths = np_depth[np.argsort(np_rem)]
        small_deps = sorted([d for d in depths if d < self.user_ram.depth])
        large_deps = sorted([d for d in depths if d >= self.user_ram.depth])
        # if len(large_deps) == 0:
        #     depths = small_deps
        # else:
        #     depths = large_deps[0:5] + small_deps[:5]
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
                _mem_wid = self.vendor.mem_mapping[self.sram_type][selected_depth][
                    selected_width
                ]
            except KeyError:
                type_dep_width_present = False
            else:
                for vendor_memory in _mem_wid:
                    if (
                        self.vendor.name == "mrvl_n5"
                        or self.vendor.name == "mrvl_n3"
                        or self.is_vendor_memory_compatible(vendor_memory)
                    ):
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
                        for vendor_memory in _mem_wid:
                            if (
                                self.vendor.name != "mrvl_n5"
                                and self.vendor.name != "mrvl_n3"
                            ):
                                if not self.is_vendor_memory_compatible(vendor_memory):
                                    continue

                            type_dep_large_width_present = True
                            diff_width = mem_keys - selected_width
                            logging.debug(f"diff_width : {diff_width}")
                            if diff_width < final_diff_width:
                                final_diff_width = diff_width
                                final_width = mem_keys
                                logging.debug(f"final_width : {final_width}")
                            break
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

            if len(widths_list) > 0:
                # list_keys = list(self.vendor.mem_mapping[self.sram_type][selected_depth].keys())
                logging.debug(f"Searching in widths - O(N*M) complexity: {widths_list}")
                for widths in widths_list:
                    if len(widths) <= 8 and selected_width / max(widths) < 10:
                        selected_phy_mem = combinationSum(widths, selected_width)
                        logging.debug(
                            f"Use combinationSum - widths: {widths}, selected_witdh: {selected_width}, selected_phy_mem: {selected_phy_mem}"
                        )
                    else:
                        selected_phy_mem = SumTheList(widths, selected_width)
                        logging.debug(
                            f"Use SumTheList - widths: {widths}, selected_witdh: {selected_width}, selected_phy_mem: {selected_phy_mem}"
                        )
                    if len(selected_phy_mem) > 0:
                        pick_widths.append(selected_phy_mem)

        return pick_widths

    def is_pipeline_vendor_memory(self, vendor_memory):
        if vendor_memory is None or (
            not re.match(r"^M[235]PSP111HD.*", vendor_memory)
            and not re.match(r"^PM[235]PSP111HD.*", vendor_memory)
            and not re.match(r"^M[235]\D+\d\d\dHC\d+X\d+.*Q", vendor_memory)
            and not re.match(r"^marvell2p", vendor_memory)
        ):
            return False
        else:
            return True

    def is_vendor_memory_compatible(self, vendor_memory):
        if not self.is_vendor_memory_bwe_compatible(vendor_memory):
            return False

        if not self.is_vendor_memory_clk_compatible(vendor_memory):
            return False

        if self.user_ram.use_2cyc_memory:
            if self.is_pipeline_vendor_memory(vendor_memory):
                return True
        elif not self.is_pipeline_vendor_memory(vendor_memory):
            return True
        return False

    def is_vendor_memory_bwe_compatible(self, vendor_memory):
        if bool("W1H" in vendor_memory or re.search(r"b\dw1", vendor_memory)) == bool(
            self.user_ram.bitWrite
        ):
            return True
        else:
            return False

    def is_vendor_memory_clk_compatible(self, vendor_memory):
        if (self.user_ram.wclk is not None and self.user_ram.rclk is not None) and (
            self.user_ram.wclk == self.user_ram.rclk
        ):
            return True

        if self.user_ram.wclk is not None and self.user_ram.rclk is not None:
            is_user_ram_dual_clk = True
        else:
            is_user_ram_dual_clk = False

        is_vendor_memory_dual_clk = True
        _typ, _de, _wi = re.search(
            r"(\D\D+\d\d\d\D\D+)(\d+)X(\d+)", vendor_memory
        ).groups()
        if (
            _typ in self.vendor.mem_ports.keys()
            and "CK" in self.vendor.mem_ports[_typ]["input"]
        ):
            is_vendor_memory_dual_clk = False

        return is_user_ram_dual_clk == is_vendor_memory_dual_clk

    def pick_vendor_widths(self, selected_depth):
        widths_list = []
        width_dict = self.vendor.mem_mapping[self.sram_type][selected_depth]
        widths = width_dict.keys()
        if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
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
            matched_widths = []
            for width in widths:
                vendor_memories = self.vendor.mem_mapping[self.sram_type][
                    selected_depth
                ][width]
                for vendor_memory in vendor_memories:
                    if self.is_vendor_memory_compatible(vendor_memory):
                        matched_widths.append(width)
                        break

            widths_list = [list(matched_widths)]
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
            if self.is_pipeline_vendor_memory(memory_name):
                self.user_ram.use_2cyc_memory = True

            depth, width = self.get_memory_depth_width(memory_name)
            found_phy_mem = False
            while found_phy_mem == False:
                inports, outports, sel_phy_mem = self.get_vendor_memory_inout_ports(
                    depth, width, memory_name
                )
                if sel_phy_mem == memory_name:
                    found_phy_mem = True
            if found_phy_mem:
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
            if len(pic_widths_list) == 0:
                continue

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

        if len(tuple_list) == 0:
            return None

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
            None if self.vendor_memories is None else self.vendor_memories[0],
        )
        logging.info(f"Memgen: result picked by memgen - {result}")
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
                    self.force_internal_signals.append(f"bank_{i}_cs")
                    phyMemA_str += "\nassign bank_" + str(i) + "_cs = cs &"
                    phyMemA_str += " (addr >= " + str((pic_depth * (i))) + " & "
                    if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                        phyMemA_str += (
                            " addr <= " + str((pic_depth * (i + 1) - 1)) + ");"
                        )
                    else:
                        phyMemA_str += " addr < " + str((self.user_ram.depth)) + ");"
                if self.user_ram.typ == "2p":
                    self.force_internal_signals.append(f"bank_{i}_wea")
                    phyMemA_str += "\nassign bank_" + str(i) + "_wea = we &"
                    phyMemA_str += " (w_addr >= " + str((pic_depth * (i))) + " & "
                    if (pic_depth * (i + 1) - 1) < self.user_ram.depth:
                        phyMemA_str += "w_addr < " + str((pic_depth * (i + 1))) + ");"
                    else:
                        phyMemA_str += "w_addr < " + str((self.user_ram.depth)) + ");"
            else:
                if self.user_ram.typ == "1p":
                    self.force_internal_signals.append(f"bank_{i}_cs")
                    phyMemA_str += "\nassign bank_" + str(i) + "_cs = cs &"
                    if self.cam_memory:
                        if self.vendor.name.startswith("brcm"):
                            phyMemA_str += " ((addr[" + str(clog2(self.user_ram.depth))
                        else:
                            phyMemA_str += " ((addr[" + str(
                                clog2(self.user_ram.depth) - 1
                            )
                    else:
                        phyMemA_str += " (addr[" + str(clog2(self.user_ram.depth) - 1)

                if self.user_ram.typ == "2p":
                    self.force_internal_signals.append(f"bank_{i}_wea")
                    phyMemA_str += "\nassign bank_" + str(i) + "_wea = we &"
                    if self.cam_memory and self.vendor.name.startswith("brcm"):
                        phyMemA_str += " ((w_addr[" + str(clog2(self.user_ram.depth))
                    else:
                        phyMemA_str += " (w_addr[" + str(clog2(self.user_ram.depth) - 1)
                # calculate the address bits that need to be compared.
                if selection > 1:
                    if self.cam_memory and self.vendor.name.startswith("brcm"):
                        phyMemA_str += (
                            ":"
                            + str(clog2(self.user_ram.depth) - selection + 1)
                            + "] == "
                        )
                    else:
                        phyMemA_str += (
                            ":" + str(clog2(self.user_ram.depth) - selection) + "] == "
                        )
                else:
                    phyMemA_str += "] == "
                if self.cam_memory:
                    phyMemA_str += dec_to_bin(i, bits) + ") || ce);"
                else:
                    phyMemA_str += dec_to_bin(i, bits) + ");"
        return phyMemA_str

    def print_depth_bank_read_en_pow_of_two(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        logging.debug(f"Selection: {selection}")

        lhs = clog2(self.user_ram.depth) - 1
        rhs = clog2(self.user_ram.depth) - selection
        if self.cam_memory and (
            self.vendor.name.startswith("brcm") or self.vendor.name.startswith("mrvl")
        ):
            lhs = clog2(self.user_ram.depth)
            rhs = clog2(self.user_ram.depth) - selection + 1

        # read en logic
        if self.user_ram.typ == "1p":
            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += "\nreg [1:0] addr_ff;"
                else:
                    phyMemA_str += "\nreg [1:0] [" + str(bits - 1) + ":0] addr_ff;"
            elif selection > 1:
                phyMemA_str += "\nreg [" + str(bits - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"

            phyMemA_str += "\n&Clock clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            if selection == 0 or (
                not self.user_ram.use_2cyc_memory
                and not (self.cam_memory and self.vendor.name.startswith("mrvl"))
            ):
                phyMemA_str += "\n  if (~we)"

            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += (
                        "\n    addr_ff <0= {addr_ff[0], addr[" + str(lhs) + "]};"
                    )
                else:
                    phyMemA_str += (
                        "\n    addr_ff <0= {addr_ff[0], addr["
                        + str(lhs)
                        + ":"
                        + str(rhs)
                        + "]};"
                    )
            elif selection > 1:
                phyMemA_str += (
                    "\n    addr_ff <0= addr[" + str(lhs) + ":" + str(rhs) + "];"
                )
            else:
                phyMemA_str += "\n    addr_ff <0= addr[" + str(lhs) + "];"

            phyMemA_str += "\n&EndPosedge;"

        if self.user_ram.typ == "2p":
            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += "\nreg [1:0] addr_ff;"
                else:
                    phyMemA_str += "\nreg [1:0] [" + str(bits - 1) + ":0] addr_ff;"
            elif selection > 1:
                phyMemA_str += "\nreg [" + str(bits - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"

            phyMemA_str += "\n&Clock r_clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            if selection == 0 or (
                not self.user_ram.use_2cyc_memory
                and not (self.cam_memory and self.vendor.name.startswith("mrvl"))
            ):
                phyMemA_str += "\n  if (re)"

            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += (
                        "\n    addr_ff <0= {addr_ff[0], r_addr[" + str(lhs) + "]};"
                    )
                else:
                    phyMemA_str += (
                        "\n    addr_ff <0= {addr_ff[0], r_addr["
                        + str(lhs)
                        + ":"
                        + str(rhs)
                        + "]};"
                    )
            elif selection > 1:
                phyMemA_str += (
                    "\n    addr_ff <0= r_addr[" + str(lhs) + ":" + str(rhs) + "];"
                )
            else:
                phyMemA_str += "\n    addr_ff <0= r_addr[" + str(lhs) + "];"

            phyMemA_str += "\n&EndPosedge;"

        return phyMemA_str

    def print_depth_bank_read_en(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = bits
        logging.debug(f"Selection: {selection}")
        # read en logic
        for i in range(0, depth_iter):
            if self.user_ram.typ == "2p":
                self.force_internal_signals.append(f"bank_{i}_rea")
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
            if i > 0:
                bank_cs += ","

        lhs = clog2(self.user_ram.depth) - 1
        rhs = clog2(self.user_ram.depth) - selection
        if self.cam_memory and self.vendor.name.startswith("brcm"):
            lhs = clog2(self.user_ram.depth)
            rhs = clog2(self.user_ram.depth) - selection + 1

        if self.user_ram.typ == "1p":
            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += "\nreg [1:0] addr_ff;"
                else:
                    phyMemA_str += (
                        "\nreg [1:0] [" + str(depth_iter - 1) + ":0] addr_ff;"
                    )
            elif selection > 1:
                phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"

            phyMemA_str += "\n&Clock clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            if selection == 0 or (
                not self.user_ram.use_2cyc_memory
                and not (self.cam_memory and self.vendor.name.startswith("mrvl"))
            ):
                phyMemA_str += "\n  if (~we)"

            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                phyMemA_str += "\n    addr_ff <0= {addr_ff[0], " + bank_cs + "};"
            else:
                phyMemA_str += "\n    addr_ff <0= {" + bank_cs + "};"

        if self.user_ram.typ == "2p":
            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                if selection == 1:
                    phyMemA_str += "\nreg [1:0] addr_ff;"
                else:
                    phyMemA_str += (
                        "\nreg [1:0] [" + str(depth_iter - 1) + ":0] addr_ff;"
                    )
            elif selection > 1:
                phyMemA_str += "\nreg [" + str(depth_iter - 1) + ":0] addr_ff;"
            else:
                phyMemA_str += "\nreg  addr_ff;"

            phyMemA_str += "\n&Clock r_clk;\n&AsyncReset reset_n;"
            phyMemA_str += "\n&Posedge;"
            if selection == 0 or (
                not self.user_ram.use_2cyc_memory
                and not (self.cam_memory and self.vendor.name.startswith("mrvl"))
            ):
                phyMemA_str += "\n  if (re)"

            if (
                self.user_ram.use_2cyc_memory
                or (self.cam_memory and self.vendor.name.startswith("mrvl"))
                and selection > 0
            ):
                phyMemA_str += "\n    addr_ff <0= {addr_ff[0], " + bank_cs + "};"
            else:
                phyMemA_str += "\n    addr_ff <0= {" + bank_cs + "};"

        phyMemA_str += "\n&EndPosedge;"
        return phyMemA_str

    def print_depth_bank_addr(self, pic_depth, depth_iter, bits):
        phyMemA_str = ""
        selection = clog2(self.user_ram.depth) - clog2(pic_depth)
        logging.debug(f"Selection: {selection}")
        addr_bitdef = f"[{clog2(self.user_ram.depth) - 1}:0]"
        # read en logic
        for i in range(0, depth_iter):
            if self.user_ram.typ == "1p":
                phyMemA_str += (
                    "\nassign addr_"
                    + str(i)
                    + addr_bitdef
                    + " = bank_"
                    + str(i)
                    + "_cs ? (addr "
                )
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += "): '0;"
                self.force_internal_signals.append(f"addr_{i}")
            if self.user_ram.typ == "2p":
                phyMemA_str += "\nassign w_addr_" + str(i) + addr_bitdef + " = w_addr"
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += ";"
                self.force_internal_signals.append(f"w_addr_{i}")
                phyMemA_str += (
                    "\nassign r_addr_"
                    + str(i)
                    + addr_bitdef
                    + " = bank_"
                    + str(i)
                    + "_rea ? (r_addr "
                )
                if i > 0:
                    phyMemA_str += " - " + str((pic_depth * (i)))
                phyMemA_str += "): '0;"
                self.force_internal_signals.append(f"r_addr_{i}")
        return phyMemA_str

    def print_depth_bank_assign(self, pn, width_iter):
        lvalue = pn
        bank_sigs = [f"bank_{pn}_{i}" for i in range(width_iter)]
        rvalue = " & ".join(bank_sigs)
        return f"assign {lvalue} = {rvalue};\n"

    def print_one_bit_assign(self, pn, depth_iter, width_iter):
        phyMemA_str = ""
        if width_iter > 1:
            pn_depth_banks = []
            for i in range(depth_iter):
                # lvalue = f"bank_{i}_{pn}"
                rvalue = " & ".join([f"bank_{i}_{pn}_{j}" for j in range(width_iter)])
                # phyMemA_str += f"assign {lvalue} = {rvalue};\n"
                pn_depth_banks.append(f"({rvalue})")
            lvalue = pn
            # rvalue = " | ".join([f"bank_{i}_{pn}" for i in range(depth_iter)])
            rvalue = " |\n".join(pn_depth_banks)
            phyMemA_str += f"assign {lvalue} = {rvalue};\n"
        else:
            lvalue = pn
            rvalue = " | ".join(
                [
                    f"bank_{i}_{pn}_{j}"
                    for i in range(depth_iter)
                    for j in range(width_iter)
                ]
            )
            phyMemA_str += f"assign {lvalue} = {rvalue};\n"

        return phyMemA_str

    def print_depth_bank_width_and(self, pn, depth_iter, width_iter):
        """Generate intermediate signals for each depth bank by ANDing across width banks"""
        phyMemA_str = ""
        for i in range(depth_iter):
            lvalue = f"bank_{i}_{pn}"
            rvalue = " & ".join([f"bank_{i}_{pn}_{j}" for j in range(width_iter)])
            phyMemA_str += f"assign {lvalue} = {rvalue};\n"
            self.force_internal_signals.append(f"bank_{i}_{pn}")
        return phyMemA_str

    def print_depth_bank_case(self, pic_depth, depth_iter, bits, pn):
        width = str(self.user_ram.width - 1)
        phyMemA_str = ""
        nearest = nearest_2_pow(depth_iter)
        selection = bits

        if selection > 0 and (
            (self.cam_memory and self.vendor.name.startswith("mrvl"))
            or self.user_ram.use_2cyc_memory
        ):
            phyMemA_str += "\nalways_comb begin\n  case (addr_ff[1])"
        else:
            phyMemA_str += "\nalways_comb begin\n  case (addr_ff)"

        if isPowerOfTwo(pic_depth):
            has_default = False
            for i in range(0, depth_iter):
                if i < depth_iter - 1:
                    phyMemA_str += "\n      " + dec_to_bin(i, bits)
                else:
                    phyMemA_str += "\n      default"
                    has_default = True
                phyMemA_str += ": " + pn + "_int = bank_" + str(i) + "_" + pn + "_int;"
                self.force_internal_signals.append(f"bank_{i}_{pn}_int")
            # check if have enumerated all combinations
            # otherwise add a default case.
            if has_default == False and nearest != depth_iter:
                phyMemA_str += "\n       default: " + pn + "_int = '0;"
        else:
            for i in range(0, depth_iter + 1):
                if (i != 0) or (is_mersenne_prime(i)):
                    # logging.debug("Converting to 2 power: " + str(i) + " iter:" + str(depth_iter))
                    phyMemA_str += "\n    " + dec_to_one_hot_bin(i, depth_iter)
                    phyMemA_str += (
                        ": " + pn + "_int = bank_" + str(i - 1) + "_" + pn + "_int;"
                    )
                    self.force_internal_signals.append(f"bank_{i - 1}_{pn}_int")
            phyMemA_str += "\n    default: " + pn + "_int = '0;"
        phyMemA_str += "\n  endcase\nend\n"
        return phyMemA_str

    def select_phy_mem_frm_lst(self, lst_phy_mem):
        selected = None
        matched_phy_mem = []

        for element in lst_phy_mem:
            if (
                (self.user_ram.use_2cyc_memory)
                and not self.is_pipeline_vendor_memory(element)
            ) or (
                (not self.user_ram.use_2cyc_memory)
                and self.is_pipeline_vendor_memory(element)
            ):
                continue
            if self.is_vendor_memory_clk_compatible(element):
                matched_phy_mem.append(element)

        if self.user_ram.bitWrite == 0:
            for element in matched_phy_mem:
                if "W1H" not in element:
                    logging.debug(f"NO BWE:\t\t{element}")
                    selected = element
        else:
            for element in matched_phy_mem:
                logging.debug(f"BWE:\t\t{element}")
                if "W1H" in element:
                    selected = element
        #  this case is needed if there is no memory with the right BWE config
        # pick the first one and move on
        if not selected:
            for element in matched_phy_mem:
                selected = element

        logging.debug(f"Selected:\t\t{selected}")
        return selected

    def get_vendor_memory_inout_ports(self, pic_depth, pic_width, sel_phy_mem=None):
        inports = outports = memory_compiler = None
        memories = self.vendor.mem_mapping[self.sram_type]

        if sel_phy_mem is None:
            if pic_depth not in memories or pic_width not in memories[pic_depth]:
                logging.warning(
                    f"No vendor memory found for width {pic_width}, depth: {pic_depth}."
                )
                return inports, outports, sel_phy_mem

            lst_sel_phy_mem = memories[pic_depth][pic_width]
            # select one memory from the list of memories
            # for now just pick one. later use the power data to pick the efficient one
            if isinstance(lst_sel_phy_mem, dict):
                for k, v in lst_sel_phy_mem.items():
                    logging.debug(f"compiler name : {k}")
                    for onemem in v.keys():
                        if (
                            self.vendor.name != "mrvl_n5"
                            and self.vendor.name != "mrvl_n3"
                        ):
                            if not self.is_vendor_memory_clk_compatible(onemem):
                                continue

                        sel_phy_mem = onemem
                        memory_compiler = k
                        break
            elif isinstance(lst_sel_phy_mem, list):
                sel_phy_mem = self.select_phy_mem_frm_lst(lst_sel_phy_mem)
            else:
                sel_phy_mem = lst_sel_phy_mem

            # if re.match(r"^M3PSP111HD.*", sel_phy_mem):
            #     self.user_ram.piped_vendor_memory = True

            logging.info(f"use ....\t{sel_phy_mem}")
            logging.debug(f"use ....\t{memory_compiler}")

        if sel_phy_mem is None:
            logging.warning(
                f"No vendor memory found for width {pic_width}, depth: {pic_depth}."
            )
            return inports, outports, sel_phy_mem

        _typ = _de = _wi = None
        if self.vendor.name == "mrvl_n5" or self.vendor.name == "mrvl_n3":
            if memory_compiler is None:
                lst_sel_phy_mem = memories[pic_depth][pic_width]
                if isinstance(lst_sel_phy_mem, dict):
                    for k, _ in lst_sel_phy_mem.items():
                        logging.debug(f"compiler name : {k}")
                        memory_compiler = k

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
            if "pipelined" in inports and "non-pipelined" in inports:
                if self.is_pipeline_vendor_memory(sel_phy_mem):
                    inports.update(inports["pipelined"])
                else:
                    inports.update(inports["non-pipelined"])
                del inports["pipelined"]
                del inports["non-pipelined"]
            if "pipelined" in outports and "non-pipelined" in outports:
                if self.is_pipeline_vendor_memory(sel_phy_mem):
                    outports.update(outports["pipelined"])
                else:
                    outports.update(outports["non-pipelined"])
                del outports["pipelined"]
                del outports["non-pipelined"]
        else:
            logging.error("Error: missing port info for physical memory type " + _typ)

        if memory_compiler in [
            "mrvl_n3_sram1a_1rw",
            "mrvl_n3_sram1u_1rw",
            "mrvl_n3_sram2q1pl_1r1rw",
        ]:
            inports["DS"] = "'0"
            inports["SD"] = "'0"

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
                if self.cam_memory and (
                    self.vendor.name.startswith("brcm")
                    or self.vendor.name.startswith("mrvl")
                ):
                    str_depth_cal = str(values) + "[" + str(phy_addrSize) + ":1]"
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
        tie_off = "{1'b1}" if ports == "MASK" else "{1'b0}"
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
                + tie_off
                + "},"
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

            str_width_cal_op = values
            if min_iter_width is not None and max_iter_width is not None:
                if iter_width < user_width:
                    str_width_cal_op = (
                        str(values)
                        + "["
                        + str(max_iter_width)
                        + ":"
                        + str(min_iter_width)
                        + "] ;"
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
                        + "]} ;     //spyglass disable W528"
                    )
            phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal_op + "\n"
        else:
            phyMemA_str += (
                "&Connect "
                + str(ports)
                + " "
                + str(values)
                + " ; // spyglass disable W287b\n"
            )
        return phyMemA_str

    def depth_input_ports(
        self,
        ports,
        values,
        min_iter_depth,
        max_iter_depth,
        iterator,
    ):
        phyMemA_str = ""
        if values != "":
            str_width_cal_op = values
            if min_iter_depth is not None and max_iter_depth is not None:
                str_width_cal_op = (
                    str(values)
                    + "["
                    + str(max_iter_depth)
                    + ":"
                    + str(min_iter_depth)
                    + "]"
                )
            phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal_op + " ;\n"
        else:
            phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
        return phyMemA_str

    def depth_bank_ports(
        self,
        ports,
        values,
        min_iter_depth,
        max_iter_depth,
        iterator,
    ):
        phyMemA_str = ""
        if values != "":
            if iterator != None and iterator >= 0:
                values = "bank_" + values + "_" + str(iterator)

            str_width_cal_op = values
            if min_iter_depth is not None and max_iter_depth is not None:
                str_width_cal_op = (
                    str(values)
                    + "["
                    + str(max_iter_depth)
                    + ":"
                    + str(min_iter_depth)
                    + "]"
                )
            phyMemA_str += "&Connect " + str(ports) + " " + str_width_cal_op + " ;\n"
        else:
            phyMemA_str += (
                "&Connect "
                + str(ports)
                + " "
                + str(values)
                + " ; // spyglass disable W287b\n"
            )
        return phyMemA_str

    def depth_bank_one_bit_ports(
        self,
        ports,
        values,
        depth_iter,
        width_iter,
    ):
        phyMemA_str = ""
        if values != "":
            if depth_iter != None and width_iter != None:
                values = (
                    "bank_" + str(depth_iter) + "_" + values + "_" + str(width_iter)
                )
            phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
        else:
            phyMemA_str += (
                "&Connect "
                + str(ports)
                + " "
                + str(values)
                + " ; // spyglass disable W287b\n"
            )
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
        self.user_ram.phyMem_inst[(0 if iterator is None else iterator)] = {
            "depth": result.pic_depth,
            "insts": [],
        }

        for pic_width in result.pic_widths:
            logging.debug(f"Iterating Memory Width: {pic_width}")

            inports, outports, sel_phy_mem = self.get_vendor_memory_inout_ports(
                result.pic_depth, pic_width, result.sel_phy_mem
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

            # Check for value of CBLKS if BRCM TCAM
            tcam_rblks = 1
            tcam_cblks = 1
            if self.vendor.name.startswith("brcm") and self.cam_memory:
                tcam_phy_info = re.search(r"(\d)(\d)VT", sel_phy_mem)
                if tcam_phy_info:
                    tcam_rblks = tcam_phy_info.group(1)
                    tcam_cblks = tcam_phy_info.group(2)

            # Every thing is clear, let's push it to the variable and print it.
            phyMemA_str += "\n&BeginInstance " + sel_phy_mem + " "
            phy_Mem_inst_str = (
                self.user_ram.module
                + "_phy_inst_"
                + (str(iterator) + "_" if iterator != None else "")
                + str(phy_mem_cnt)
            )
            phyMemA_str += phy_Mem_inst_str + " ;\n"

            dft_ref = self.user_ram.mem_array
            if "EBG" in sel_phy_mem:
                dft_ref = ".mem7_ebgio.u_mem"

            self.user_ram.phyMem_inst[(0 if iterator is None else iterator)][
                "insts"
            ].append(
                {
                    "depth_iterator": 0 if iterator is None else iterator,
                    "width_iterator": phy_mem_cnt,
                    "depth": result.pic_depth,
                    "width": pic_width,
                    "inst_ref": phy_Mem_inst_str + dft_ref,
                    "max_width": str(max_iter_width),
                    "min_width": str(min_iter_width),
                }
                if iter_width < user_width
                else {
                    "depth_iterator": 0 if iterator is None else iterator,
                    "width_iterator": phy_mem_cnt,
                    "depth": result.pic_depth,
                    "width": pic_width,
                    "inst_ref": phy_Mem_inst_str + dft_ref,
                    "max_width": str(user_width - 1),
                    "min_width": str(min_iter_width),
                }
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
                    local_mem_width = (
                        "wdata[" + str(user_width - 1) + ":" + str(min_iter_width) + "]"
                    )
                elif ports in cam_spl_in_ports:
                    phyMemA_str += (
                        "&Connect "
                        + str(ports)
                        + " "
                        + "{"
                        + str(tcam_cblks)
                        + "{"
                        + str(values)
                        + "}"
                        + "};\n"
                    )
                elif ports in we_ports:
                    if iterator != None:
                        if self.user_ram.typ == "2p" and (
                            ports != "MEB" or not isPowerOfTwo(result.user_depth)
                        ):
                            str_we = f"bank_{str(iterator)}_{values}"
                            values = str_we
                        elif self.cam_memory:
                            str_we = f"bank_{str(iterator)}_{values}"
                            values = str_we

                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
                elif ports in cs_ports:
                    if iterator != None:
                        if not self.cam_memory:  # T235716598
                            str_cs = (
                                "bank_"
                                + (str(iterator) + "_" if iterator != None else "")
                                + "cs"
                            )
                            values = values.replace("cs", str_cs)
                    phyMemA_str += "&Connect " + str(ports) + " " + str(values) + " ;\n"
                elif ports in depth_partition_input_ports:
                    depth_iterator = 0 if iterator is None else iterator
                    min_iter_depth = depth_iterator * cur_depth
                    max_iter_depth = min_iter_depth + cur_depth - 1
                    phyMemA_str += self.depth_input_ports(
                        ports,
                        values,
                        min_iter_depth,
                        max_iter_depth,
                        phy_mem_cnt,
                    )
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
                elif ports in depth_partition_ports:
                    depth_iterator = 0 if iterator is None else iterator
                    min_iter_depth = depth_iterator * cur_depth
                    max_iter_depth = min_iter_depth + cur_depth - 1
                    phyMemA_str += self.depth_bank_ports(
                        ports,
                        values,
                        min_iter_depth,
                        max_iter_depth,
                        phy_mem_cnt,
                    )
                elif ports in one_bit_ports:
                    depth_iterator = 0 if iterator is None else iterator
                    phyMemA_str += self.depth_bank_one_bit_ports(
                        ports,
                        values,
                        depth_iterator,
                        phy_mem_cnt,
                    )
                elif ports in cam_spl_out_ports:
                    depth_iterator = 0 if iterator is None else iterator
                    phyMemA_str += (
                        "&Connect "
                        + str(ports)
                        + " bank_"
                        + str(depth_iterator)
                        + "_"
                        + str(values)
                        + "_"
                        + str(phy_mem_cnt)
                        + "["
                        + str(tcam_cblks)
                        + "-1:0];\n"
                    )
                else:
                    if values != "":
                        phyMemA_str += (
                            "&Connect " + str(ports) + " " + str(values) + " ;\n"
                        )
                    else:
                        phyMemA_str += (
                            "&Connect "
                            + str(ports)
                            + " "
                            + str(values)
                            + " ; // spyglass disable W287b\n"
                        )

            phyMemA_str += "&EndInstance;\n\n\n"
            phy_mem_cnt += 1
            min_iter_width = max_iter_width + 1
            max_iter_width += 1
        return phyMemA_str, tcam_rblks, tcam_cblks

    def print_memory_module(self, result):
        logging.info(f"Generate content for module {self.user_ram.module}")
        self.user_ram.module_content = ""
        nearest = nearest_2_pow(result.depth_iter)
        bits = clog2(nearest)
        if not isPowerOfTwo(result.pic_depth) and bits > 0:
            bits += 1

        if bits > 0:
            if self.cam_memory:
                for sig in ["we", "re"]:
                    for i in range(0, result.depth_iter):
                        self.force_internal_signals.append(f"bank_{i}_{sig}")
                        if self.vendor.name.startswith(
                            "brcm"
                        ) or self.vendor.name.startswith("mrvl"):
                            assign_str1 = f"\nassign bank_{str(i)}_{sig} = ((addr[{clog2(self.user_ram.depth)}"
                        else:
                            assign_str1 = f"\nassign bank_{str(i)}_{sig} = ((addr[{clog2(self.user_ram.depth) - 1}"
                        self.user_ram.module_content += assign_str1
                        if bits > 1:
                            if self.vendor.name.startswith(
                                "brcm"
                            ) or self.vendor.name.startswith("mrvl"):
                                assign_str2 = f":{str(clog2(self.user_ram.depth) - bits + 1)}] == {dec_to_bin(i, bits)}) && {sig});"
                            else:
                                assign_str2 = f":{str(clog2(self.user_ram.depth) - bits)}] == {dec_to_bin(i, bits)}) && {sig});"
                        else:
                            assign_str2 = f"] == {dec_to_bin(i, bits)}) && {sig});"
                        self.user_ram.module_content += assign_str2
            else:
                self.user_ram.module_content += self.print_depth_bank_cs(
                    result.pic_depth, result.depth_iter, bits
                )

            if isPowerOfTwo(result.pic_depth) and (
                self.fb_chip == "trantor" or isPowerOfTwo(result.user_depth)
            ):
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
                result.pic_depth, result.depth_iter, bits, "dout"
            )
            if self.cam_memory:
                self.user_ram.module_content += self.print_depth_bank_case(
                    result.pic_depth, result.depth_iter, bits, "doutv"
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
            print_vendor_memory_banks_module_content, tcam_rblks, tcam_cblks = (
                self.print_vendor_memory_banks(result, cur_depth, iterator)
            )
            self.user_ram.module_content += print_vendor_memory_banks_module_content
            i += 1
            tot_depth -= result.pic_depth

        for force_internal_signal in self.force_internal_signals:
            self.user_ram.module_content += (
                f"&Force internal {force_internal_signal};\n"
            )
        if self.cam_memory:
            self.user_ram.module_content += (
                f"&Force logic [" + str(tcam_cblks) + f"-1:0] doutv_int;\n"
            )
            self.user_ram.module_content += self.print_depth_bank_assign(
                "matchout", result.width_iter
            )

            if bits == 0:
                # No case statement, so generate final assignment directly
                self.user_ram.module_content += self.print_one_bit_assign(
                    "doutv_int", result.depth_iter, result.width_iter
                )
            else:
                # Case statement will follow, so just create intermediate signals
                self.user_ram.module_content += self.print_depth_bank_width_and(
                    "doutv_int", result.depth_iter, result.width_iter
                )
                # print_depth_bank_width_and adds bank_{i}_doutv_int to force_internal_signals,
                # which would emit &Force internal (no width) - causing VPP to declare 1-bit.
                # Remove those entries and emit explicit width-specified &Force logic instead.
                for i in range(result.depth_iter):
                    sig_name = f"bank_{i}_doutv_int"
                    if sig_name in self.force_internal_signals:
                        self.force_internal_signals.remove(sig_name)
                    self.user_ram.module_content += (
                        f"&Force logic [{tcam_cblks}-1:0] {sig_name};\n"
                    )
            # if self.vendor.name == "mrvl_n3":
            #    self.user_ram.module_content += self.print_one_bit_assign(
            #        "hit", result.depth_iter, result.width_iter
            #    )

    def write_flop_version(self):
        self.user_ram.write_flop_version(self.fb_chip)

    def get_memory_tiling_result(self, memory_tiling):
        memory_name = memory_tiling["inst_name"]
        depth_iter = memory_tiling["depth"]
        width_iter = memory_tiling["width"]
        pic_depth, pic_width = self.get_memory_depth_width(memory_name)

        total_width = self.user_ram.width + self.user_ram.ecc_width
        if (
            total_width > pic_width * width_iter
            or self.user_ram.depth > pic_depth * depth_iter
            or (width_iter > 1 and pic_width >= total_width)
            or (depth_iter > 1 and pic_depth >= self.user_ram.depth)
        ):
            logging.error(
                f"Can't apply vendor tiling {memory_tiling} to sram specification, use memgen legacy flow instead.\n"
            )
            return None

        if self.user_ram.use_2cyc_memory != self.is_pipeline_vendor_memory(memory_name):
            logging.error(
                f"""memgen_call: use_2cyc_memory={self.user_ram.use_2cyc_memory}, vendor_tiling: use_2cyc_memory={self.is_pipeline_vendor_memory(memory_name)}\n"""
                """The read cycle in memgen call and the physical memory in vendor tiling are mismatched\n"""
            )
            logging.error("Please correct the vendor mapping error(s) before retrying.")
            sys.exit(1)
            return None

        if (
            not self.cam_memory
            and self.vendor.name != "mrvl_n5"
            and self.vendor.name != "mrvl_n3"
        ):
            match = re.search(r"\D\D+(\d\d\d)\D\D+(\d+)X(\d+)", memory_name)
            if match:
                _typ = int(match.group(1))
                if _typ != self.sram_type:
                    if _typ != self.sram_type:
                        logging.error(
                            f"Mismatched port type in memgen() call for tiling vendor memory {memory_name}.\n"
                        )
                        return None

        depth_residue = (depth_iter * pic_depth) - self.user_ram.depth
        width_residue = (
            (width_iter * pic_width) - self.user_ram.width - self.user_ram.ecc_width
        )

        result = MemgenResult(
            self.sram_type,
            self.user_ram.width + self.user_ram.ecc_width,
            self.user_ram.depth,
            self.user_ram.ecc_width,
            pic_depth,
            depth_iter,
            depth_residue,
            width_iter * (pic_width,),
            width_iter,
            width_residue,
            memory_name,
        )
        logging.info(f"Memgen: result picked from vendor tiling - {result}")
        return result

    def set_phy_info(self, fitting):
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
                self.user_ram.set_mem_array()
            else:
                self.set_sram_type()
                self.user_ram.vendor = self.vendor
                self.user_ram.set_mem_array()

                if fitting:
                    result = None
                    if self.vendor_tiling is not None:
                        result = self.get_tilting_result(
                            {
                                "inst_name": self.vendor_tiling[0],
                                "depth": self.vendor_tiling[1],
                                "width": self.vendor_tiling[2],
                            }
                        )
                    elif (
                        self.vendor.mem_vendor_mapping is not None
                        and self.user_ram.prefix in self.vendor.mem_vendor_mapping
                    ):
                        result = self.get_mem_vendor_mapping_by_prefix(
                            self.user_ram.prefix
                        )

                    if result is None:
                        result = self.fit_memory_module()
                    # result = self.fit_memory_module()
                    if result is None:
                        logging.error(
                            f"No vendor memories selected for memory width: {self.user_ram.width} "
                            f"depth:{self.user_ram.depth} type:{self.user_ram.typ} pipeline:{self.user_ram.pipeline}"
                            f" bit_write:{self.user_ram.bitWrite}"
                        )
                        sys.exit(1)

                    self.user_ram.fitting = result
                    self.print_memory_module(result)
        else:
            logging.warning("No Vendor Memory info loaded...\n")

    def verilog_write(self):
        self.user_ram.verilog_write(self)

    def returnWrapperName(self):
        return self.user_ram.module

    def clear_ram_info(self, beh_wrapper_only):
        self.user_ram = None
        self.loop = []
        self.vendor_memories = None
        self.beh_wrapper_only = beh_wrapper_only
        self.internal_use = False
        self.cam_memory = False
        self.num_ecc_syndromes = 0
        self.enable_error_injection = False
        self.vendor_tiling = None
        self.force_internal_signals = []

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

        return self.user_ram.instantiate_module_instances(self)

    def set_vendor_memories(self, vendor_memories):
        self.vendor_memories = vendor_memories

    def set_beh_wrapper_only(self, beh_wrapper_only):
        self.beh_wrapper_only = beh_wrapper_only

    def set_internal_use(self, internal_use):
        self.internal_use = internal_use

    def set_no_wrapper_instantiation(self, no_wrapper_instantiation):
        self.no_wrapper_instantiation = no_wrapper_instantiation

    def add_vendor_memory_release_search_paths(self, memory_release_search_path):
        memory_release_search_paths.append(memory_release_search_path)

    def set_cam_memory(self, cam_memory):
        self.cam_memory = cam_memory

    def get_mem_vendor_mapping_by_prefix(self, prefix):
        if prefix not in self.vendor.mem_vendor_mapping:
            return None

        return self.get_memory_tiling_result(
            dict(self.vendor.mem_vendor_mapping[prefix])
        )


if __name__ == "__main__":
    ram = memgen()
    ram.set_ram_info(
        "memgen", 586, 586, "2p", 1, 0, "reset_n", "clk", "clk", port_prefix="abc"
    )
    # ram.set_vendor_memories(
    #     [
    #         "M3PSP111HD8192X144R20822VTLPEBRCW1H20OLD_wrapper",
    #         "PM3PSP111HD8192X144R20822VTLPEBRCW1H20OLD_wrapper",
    #         "M3PSP111HD8192X288R20823VTLPEBRCW1H20OLD_wrapper",
    #     ]
    # )
    ram.set_vendor()
    ram.fb_chip = os.environ.get("FB_CHIP", None)

    ram.set_phy_info()
    ram.set_dv_api(True)
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
