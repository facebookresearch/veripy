####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

import logging
import math
import os
import re
from collections import OrderedDict
from itertools import combinations_with_replacement


ASIC_VENDORS = os.environ.get("ASIC_VENDORS", "").split() + [
    "brcm_apd_n2",
    "brcm_apd_n3",
    "brcm_apd_n3p",
    "mrvl_n3",
]

bwe_ports = ["bwe", "bwea", "BW", "BWA", "WEMA", "wema", "WEM", "wem"]
we_ports = ["we", "wea", "web", "WE", "WEA", "WEB", "MEA", "MEB", "RE"]
cs_ports = ["cs", "mea", "meb", "CS", "ME"]
din_ports = ["D", "DA", "din", "dina", "CDI", "CE", "MASK"]
dout_ports = ["QP", "QPB", "doutb", "dout", "Q", "QB"]
one_bit_ports = ["QVLD", "QHIT", "QPV"]
addr_ports = ["A", "ra", "wa", "AA", "AB", "ADR", "ADRA", "ADRB", "adda", "addb", "add"]
# depth_partition_ports = ["RHL", "QHR", "RVLD"]
depth_partition_ports = ["RHL", "QHR"]
# depth_partition_input_ports = ["RVLD"]
depth_partition_input_ports = []
cam_spl_in_ports = ["VWE", "SWE", "DINV", "VBE"]
cam_spl_out_ports = ["QV"]

memory_release_search_paths = [
    "%(infra)s/ip/mtia/%(chip)s/third_party/memories/%(vendor)s",
    "%(infra)s/ip/mnic/%(chip)s/third_party/memories/%(vendor)s",
    "%(infra)s/soc/mtia/%(chip)s/third_party/memories/%(vendor)s",
    "%(infra)s/ip/%(chip)s/third_party/memories/%(vendor)s",
    "%(infra)s/ip/mtia/%(chip)s/third_party/memories/custom/%(vendor)s",
    "%(infra)s/ip/mnic/%(chip)s/third_party/memories/custom/%(vendor)s",
    "%(infra)s/soc/mtia/%(chip)s/third_party/memories/custom/%(vendor)s",
]

mem_mapping_file = "mem_mapping.json"
mem_vendor_mapping_file = "mem_vendor_mapping.json"
mem_ports_file = "mem_ports.json"

valid_sram_types = ("1p", "2p", "1f", "2f")


def calculate_ecc_width(width, num_ecc):
    if num_ecc == 0:
        num_ecc = 1

    min_dw = width / num_ecc
    num_max_dw = width % num_ecc
    max_dw = (min_dw + 1) if (num_max_dw > 0) else min_dw
    min_ecc = 5 if (min_dw < 12) else (clog2(min_dw + clog2(min_dw) + 1) + 1)
    max_ecc = 5 if (max_dw < 12) else (clog2(max_dw + clog2(max_dw) + 1) + 1)

    ecc_width = (num_ecc - num_max_dw) * min_ecc + num_max_dw * max_ecc
    return ecc_width


def dict_keys_str_to_int(d):
    new = OrderedDict()
    for k, v in d.items():
        if isinstance(v, dict):
            v = dict_keys_str_to_int(v)
        if re.search("\D", k):
            new[k] = v
        else:
            new[int(k)] = v
    return new


def get_change(current, previous):
    if current == previous:
        return 100.0
    try:
        return (abs(current - previous) / previous) * 100.0
    except ZeroDivisionError:
        return 0


def SumTheList(thelist, target):
    arr = []
    residue = 0
    selected = []
    phy_mem_list = []
    max_list_len = -(target // -max(thelist))
    thelist.sort(reverse=True)

    if len(thelist) >= 16:
        thelist = thelist[:: -(len(thelist) // -10)]

    count = 0
    reserved_phy_mem_list = None
    if max_list_len > len(thelist):
        count = max_list_len - len(thelist)
        reserved_phy_mem_list = [max(thelist)] * count
        target -= max(thelist) * count

    if len(thelist) > 0:
        # Step 1. Iterate all possible widths
        for r in range(1, -(target // -max(thelist)) + 1):
            # this will return all possible combinations in steps
            arr = list(combinations_with_replacement(thelist, r))
            # logging.debug("Array:" + str(arr))
            # Iterate array
            for item in arr:
                if sum(item) == target:
                    selected.append(item[::-1])
                elif sum(item) > target:
                    residue = get_change(
                        max(thelist) * count + sum(item), max(thelist) * count + target
                    )
                    if residue <= 15:
                        selected.append(item[::-1])
            if selected:
                logging.debug("Selected:" + str(selected))
                # below gives the best result but it is too late
                # to change the memory configuration at this point of the project
                # for Now just pick the one with min and move on
                # selected.sort(key = lambda x: x[0] - x[1],reverse=True)
                logging.debug("Sorted Selected:" + str(selected))
                phy_mem_list = min(selected, key=lambda i: (len(i), sum(i)))
                # minLength = len(phy_mem_list)
                logging.debug("Equal: chosen" + str(phy_mem_list))
                selected = []
                if phy_mem_list:
                    if reserved_phy_mem_list is not None:
                        phy_mem_list = (*phy_mem_list, *reserved_phy_mem_list)
                    return phy_mem_list

    logging.debug(
        f"MEMGEN: No summed widths from the widths list {thelist} found to be Equal or Greater than {target}"
    )
    return phy_mem_list


def combinationSum(candidates, target):
    def dfs(candidates, target, start, curr, ans, great):
        if target == 0:
            ans.append(curr[:])
            return
        for i in range(start, len(candidates)):
            if candidates[i] > target:
                curr.append(candidates[i])
                great.append(curr[:])
                curr.pop()
                return
            curr.append(candidates[i])
            dfs(candidates, target - candidates[i], i, curr, ans, great)
            curr.pop()

    ans = []
    great = []
    candidates.sort()
    dfs(candidates, target, 0, [], ans, great)
    selected = ans + great

    return min(selected, key=lambda i: len(i))


def nearest_2_pow(N):
    nearest = int(pow(2, math.ceil(math.log(N) / math.log(2))))
    return nearest


def clog2(depth):
    addrSize = 0
    shifter = 1
    r"""Return the ceiling log base two of an integer """
    if depth < 1:
        raise ValueError("expected depth >= 1")
        addrSize, shifter = 0, 1
    while depth > shifter:
        shifter <<= 1
        addrSize += 1

    return addrSize


def Log2(x):
    if x == 0:
        return False

    return math.log10(x) / math.log10(2)


# if x is power of 2
def isPowerOfTwo(n):
    return math.ceil(Log2(n)) == math.floor(Log2(n))

    # Function to return the binary
    # equivalent of decimal value N


def dec_to_bin(N, bits):
    # To store the binary number
    B_Number = 0
    cnt = 0
    while N != 0:
        rem = N % 2
        c = pow(10, cnt)
        B_Number += rem * c
        N //= 2
        # Count used to store exponent value
        cnt += 1
    # print ("S: "+ str(str(bits)) +"\'b" + str(B_Number).zfill(bits))
    st_b_number = str(str(bits)) + "'b" + str(B_Number).zfill(bits)
    return st_b_number


# Function to return the binary
# equivalent of decimal value N
def dec_to_bin_non_pow_two(N, bits):
    # To store the binary number
    B_Number = 0
    cnt = 0
    while N != 0:
        rem = N % 2
        c = pow(10, cnt)
        B_Number += rem * c
        N //= 2
        # Count used to store exponent value
        cnt += 1
    # print ("S: "+ str(str(bits)) +"\'b" + str(B_Number).zfill(bits))
    st_b_number = str(str(bits)) + "'b" + str(B_Number).zfill(bits)
    return st_b_number


def is_mersenne_prime(n):
    binary = -~n & n < all(n % i for i in range(2, n)) < n
    return binary


def str_to_list(myString):
    # if it is string format process it and return it
    if myString and myString.strip():
        myString = re.sub(r"\s", r"", myString)
        myString = re.sub(r"\[|\]", "", myString)
        if myString and myString.strip():
            str_list = myString.split(",")
            return str_list
    return None


def dec_to_one_hot_bin(i, bits):
    if i < 1:
        return str(bits) + "'b" + "0" * bits
    one_hot_value = 2 ** (i - 1)
    binary_str = str(bits) + "'b" + format(one_hot_value, f"0{bits}b")
    return binary_str
