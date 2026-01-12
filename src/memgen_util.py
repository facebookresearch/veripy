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
import logging
import math
import re
from collections import OrderedDict
from itertools import combinations_with_replacement

vendor_name_mapping = {
    "ccx": "brcm_ccx_n7",
    "ccx_n5": "brcm_apd_n5",
    "apd": "brcm_apd_n7",
    "terminus_gen1": "mrvl_n5",
    "terminus": "xilinx",
    "mt5": "mrvl_n5",
}

fb_chip_2_vendor_name = {
    "freya": "brcm_apd_n7",
    "artemis": "brcm_apd_n5",
    "tenjin": "brcm_ccx_n7",
    "fujin": "brcm_ccx_n5",
    "terminus_gen1": "mrvl_n5",
    "terminus": "xilinx",
}

valid_vendor_names = set(
    list(vendor_name_mapping.values()) + list(fb_chip_2_vendor_name.values())
)

bwe_ports = ["bwe", "bwea", "BW", "BWA", "WEMA", "wema", "WEM", "wem"]
we_ports = ["we", "wea", "web", "WE", "WEA", "WEB"]
cs_ports = ["cs", "mea", "mebCS"]
din_ports = ["D", "DA", "din", "dina"]
dout_ports = ["QP", "QPB", "doutb", "dout", "Q", "QB"]
addr_ports = ["A", "ra", "wa", "AA", "AB", "adda", "addb", "add"]

memory_release_search_paths = {
    "brcm_apd_n5": "%(infra)s/ip/fb_inference_gen2/third_party/memories/%(vendor)s",
    "brcm_ccx_n5": "%(infra)s/ip/xcoder2_0/third_party/memories/%(vendor)s",
    "mrvl_n5": "%(infra)s/ip/fb_nic_gen1/third_party/memories/%(vendor)s",
    "default": "%(infra)s/third_party/memories/%(vendor)s",
}

mem_mapping_file = "mem_mapping.json"
mem_ports_file = "mem_ports.json"

valid_sram_types = ("1p", "2p", "1f", "2f")


def calculate_ecc_width(width):
    # for example: 128 X 320 - 2(128 X 160)
    # Depth remain same - 128
    # 320 - 2^(r-1) >= r+w
    for i in range(1, 20):
        # print ("calculating LHS:" +str(2**(i-1)))
        # print ("calculating RHS:" +str(i + width))
        if 2 ** (i - 1) >= (i + width):
            # print ("Iterating:" +str(i))
            # print ("Iterating:" +str(width))
            value = i + width
            return i


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
    phy_mem_list = 0
    if len(thelist) > 0:
        # Step 1. Iterate all possible widths
        for r in range(0, len(thelist) + 1):
            # this will return all possible combinations in steps
            arr = list(combinations_with_replacement(thelist, r))
            # logging.debug("Array:" + str(arr))
            # Iterate array
            for item in arr:
                if sum(item) == target:
                    selected.append(item)
                elif sum(item) > target:
                    residue = get_change(sum(item), target)
                    if residue <= 15:
                        selected.append(item)
            if selected:
                logging.debug("Selected:" + str(selected))
                # below gives the best result but it is too late
                # to change the memory configuration at this point of the project
                # for Now just pick the one with min and move on
                # selected.sort(key = lambda x: x[0] - x[1],reverse=True)
                logging.debug("Sorted Selected:" + str(selected))
                phy_mem_list = min(selected, key=lambda i: len(i))
                # minLength = len(phy_mem_list)
                logging.debug("Equal: choosen" + str(phy_mem_list))
                selected = []
                if phy_mem_list:
                    return phy_mem_list

    logging.error("MEMGEN: No width found to be Equal or Greater than " + str(target))
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
