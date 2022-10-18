####################################################################################
#  Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#  The following information is considered proprietary and confidential to Facebook,
#  and may not be disclosed to any third party nor be used for any purpose other
#  than to full fill service obligations to Facebook
####################################################################################

################################################################################
# This is a block level makefile and block owner can append to the build
# variables. The user has to mention their top module name as MODULE_NAME.
# The user can append module specific information like directories and other
# spec files.
################################################################################

################################################################################
# Root directory to replace the hardcoded directory with ${ROOT} variable
# For demo, we are getting this variable from the enviroment.
################################################################################
#ROOT := $(shell pwd | sed 's/\/open_source\/.*//')


################################################################################
# Directory where Veripy scripts are kept 
################################################################################
VERIPY_PATH := ${ROOT}


################################################################################
# Directory where config files for build flow are kept
################################################################################
VERIPY_CFG_PATH := ${ROOT}


################################################################################
# Including the config.mk that has project level variables setup
################################################################################
include $(VERIPY_CFG_PATH)/config.mk


################################################################################
# Top level module name
################################################################################
MODULE = xdfil


################################################################################
# List of project wide directories to look for files
################################################################################
INCLUDE_DIRS += ./specs/


################################################################################
# List of directories to look for sub module psv or pv files
################################################################################
BUILD_SUB_DIRS += 


################################################################################
# Enables bottom up build
################################################################################
BUILD_SUBS = 0


################################################################################
# Any additional options user wants to add it in the local makefile
################################################################################
USER_OPTIONS +=


################################################################################
# List of module specific interface spec files
################################################################################
INTERFACE_SPECS = ./specs/interfaces.spec


################################################################################
# List of module specific interface definition files
################################################################################
INTERFACE_DEFS = ./specs/interfaces.def


################################################################################
# List of module specific module definition files
################################################################################
MODULE_DEFS = ./specs/module.def


################################################################################
# Any python scripts to be loaded through command-line
################################################################################
PYTHON_SCRIPTS +=


################################################################################
# Default format is systemverilog.
# Overriding project level Format with verilog
################################################################################
# RTL_FORMAT = "verilog"


################################################################################
# Including the common makefile for generic targets
################################################################################
include $(VERIPY_PATH)/common.mk
