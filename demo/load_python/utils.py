####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

#!/usr/bin/env python3

num_inputs = 16


def inst_syncfifo(prefix, clk, rst, width, depth):
    print("&BeginInstance fb_fifo u_" + prefix + "_fb_fifo;")
    print("&Param DEPTH " + str(width) + ";")
    print("&Param WIDTH " + str(depth) + ";")
    print("&Connect /^/ /" + prefix + "_/;")
    print("&Connect clk " + clk + ";")
    print("&Connect rst_n " + rst + ";")
    print("&EndInstance;")
