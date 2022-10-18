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
MODULE = pyramid_gen_0


################################################################################
# List of project wide directories to look for files
################################################################################
INCLUDE_DIRS += $(VERIPY_PATH)/demo/pyramid_gen_0/incl \
                $(VERIPY_PATH)/demo/pyramid_gen_0/header \
                $(VERIPY_PATH)/demo/pyramid_gen_0/libs \
		$(VERIPY_PATH)/demo/pyramid_gen_0/dsx2/rtl_bc7 \
		$(VERIPY_PATH)/demo/pyramid_gen_0/dsx2/rtl_b \
		$(VERIPY_PATH)/demo/pyramid_gen_0/rtl_b \
		$(VERIPY_PATH)/demo/pyramid_gen_0/rtl_bc7


################################################################################
# List of directories to look for sub module psv or pv files
################################################################################
BUILD_SUB_DIRS += $(VERIPY_PATH)/demo/pyramid_gen_0/dsx2/src \
                  $(VERIPY_PATH)/demo/pyramid_gen_0/common/generic_csa/src \
                  $(VERIPY_PATH)/demo/pyramid_gen_0/common/booth_mult_pp/src \


################################################################################
# Enables sub-block build for hierarchical bottom up build
################################################################################
BUILD_SUBS = 1


################################################################################
# Any additional options user wants to add it in the local makefile
################################################################################
USER_OPTIONS +=


################################################################################
# List of module specific interface definition files
################################################################################
INTERFACE_SPECS +=


################################################################################
# List of module specific interface definition files
################################################################################
INTERFACE_DEFS +=


################################################################################
# List of module specific module definition files
################################################################################
MODULE_DEFS +=


################################################################################
# Default format is systemverilog.
# Overriding project level Format with verilog
################################################################################
# RTL_FORMAT = "verilog"


################################################################################
# Including the common makefile for generic targets
################################################################################
include $(VERIPY_CFG_PATH)/common.mk
