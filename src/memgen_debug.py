#!/usr/bin/env python3
"""
Wrapper script for debugging single memory generation cases with memgen.py
"""

import os
import sys

from memgen import memgen
# Uncomment if using ECC:
# from ecc_lib import calculate_ecc_width


# Add your custom memory case here
def debug_my_custom_memory():
    """YOUR CUSTOM MEMORY CASE - Modify parameters as needed"""
    ram = memgen()
    ram.memgen_line = None  # Initialize memgen_line attribute
    ram.set_ram_info(
        prefix="mem",
        width=576,  # Change this
        depth=8192,  # Change this
        typ="1p",  # "1p", "2p", or "1f"
        pipeline=2,
        bitwrite=1,
        rst="reset_n",
        wclk="clk",
        rclk="clk",
    )

    # Optional: Set vendor-specific memories
    # ram.set_vendor_memories([
    #     "M3PSP111HD8192X144R20822VTLPEBRCW1H20OLD_wrapper",
    #     "PM3PSP111HD8192X144R20822VTLPEBRCW1H20OLD_wrapper",
    # ])

    ram.set_vendor()
    ram.fb_chip = os.environ.get("FB_CHIP", None)
    ram.set_phy_info(fitting=True)
    ram.set_dv_api(True)
    ram.verilog_write()

    # Optional: Get instance string
    # instance_str = ram.returnInstance()
    # print(instance_str)

    print("\n=== Custom Memory Case Complete ===")


def debug_qp_cache_tcam():
    """qp_cache_tcam - CAM/TCAM memory test case"""
    ram = memgen()
    ram.memgen_line = None  # Initialize memgen_line attribute
    ram.set_ram_info(
        prefix="qp_cache_tcam",
        width=152,
        depth=128,
        typ="1p",
        pipeline=0,
        bitwrite=0,
        rst="reset_n",
        wclk="clk",
        rclk="clk",
    )

    # Set CAM/TCAM memory flag
    ram.cam_memory = 1

    ram.set_vendor()
    ram.fb_chip = os.environ.get("FB_CHIP", None)
    ram.set_phy_info(fitting=True)
    ram.set_dv_api(True)
    ram.verilog_write()

    print("\n=== qp_cache_tcam Test Complete ===")


if __name__ == "__main__":
    debug_qp_cache_tcam()
