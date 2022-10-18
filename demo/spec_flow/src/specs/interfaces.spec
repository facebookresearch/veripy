####################################################################################
#  Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#  The following information is considered proprietary and confidential to Facebook,
#  and may not be disclosed to any third party nor be used for any purpose other
#  than to full fill service obligations to Facebook
####################################################################################

DVS:
    ARGS:
        - <PACKAGE>
    INPUTS:
        - <PREFIX><INTERFACE_NAME_LC>_valid
        - <PACKAGE> <PREFIX><INTERFACE_NAME_LC>_data
    OUTPUTS:
        - <PREFIX><INTERFACE_NAME_LC>_stall

DV:
    ARGS:
        - <PACKAGE>
    INPUTS:
        - input           <INTERFACE_NAME_LC>_valid
        - input <PACKAGE> <INTERFACE_NAME_LC>_data

DPRAMRW:
    ARGS:
        - <DATAWIDTH>
        - <ADDRWIDTH>
    INPUTS:
        - <INTERFACE_NAME_LC>_ren
        - <ADDRWIDTH> <INTERFACE_NAME_LC>_raddr
        - <INTERFACE_NAME_LC>_wen
        - <ADDRWIDTH> <INTERFACE_NAME_LC>_waddr
        - <DATAWIDTH> <INTERFACE_NAME_LC>_wdata
    OUTPUTS:
        - <DATAWIDTH> <INTERFACE_NAME_LC>_rdata


DPRAMRD:
    ARGS:
        - <DATAWIDTH>
        - <ADDRWIDTH>
    INPUTS:
        - <INTERFACE_NAME_LC>_ren
        - <ADDRWIDTH> <INTERFACE_NAME_LC>_raddr
    OUTPUTS:
        - <DATAWIDTH> <INTERFACE_NAME_LC>_rdata

DPRAMWR:
    ARGS:
        - <DATAWIDTH>
        - <ADDRWIDTH>
    INPUTS:
        - <INTERFACE_NAME_LC>_wen
        - <ADDRWIDTH> <INTERFACE_NAME_LC>_waddr
        - <DATAWIDTH> <INTERFACE_NAME_LC>_wdata

SPRAMRW:
    ARGS:
        - <DATAWIDTH>
        - <ADDRWIDTH>
    INPUTS:
        - <INTERFACE_NAME_LC>_csn
        - <INTERFACE_NAME_LC>_rw
        - <ADDRWIDTH> <INTERFACE_NAME_LC>_addr
        - <DATAWIDTH> <INTERFACE_NAME_LC>_wdata
    OUTPUTS:
        - <DATAWIDTH> <INTERFACE_NAME_LC>_rdata
