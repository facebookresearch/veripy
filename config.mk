####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

################################################################################
# This is a config file for the Veripy Build Make flow. Please do not update   #
# this file without discussing the flow owner.                                 #
################################################################################

################################################################################
# Veripy Scripty Path
################################################################################
VERIPY_SCRIPT = ${VERIPY_PATH}/veripy.py


################################################################################
# Veripy script Lib
################################################################################
VERIPY_LIB = $(VERIPY_SCRIPT)


################################################################################
# Veripy Build script path
################################################################################
VERIPY_BUILD_SCRIPT = ${VERIPY_PATH}/veripy_build.py


################################################################################
# Veripy Build script Lib
################################################################################
VERIPY_BUILD_LIB = $(VERIPY_BUILD_SCRIPT)


################################################################################
# List of project wide interface spec files
################################################################################
INTERFACE_SPECS = 


################################################################################
# List of project wide interface definition files
################################################################################
INTERFACE_DEFS = 


################################################################################
# List of project wide module definition files
################################################################################
MODULE_DEFS = 


################################################################################
# List of project level pythin scripts to be loaded
################################################################################
PYTHON_SCRIPTS =


###############################################m#################################
# Top level module name is derived from directory name
################################################################################
MODULE = top

################################################################################
# Target directory name where generated RTL files will be stored
################################################################################
TARGET = rtl


################################################################################
# Destination Directory where generated *.sv / *.v stored
################################################################################
DEST_DIR = ../$(TARGET)


################################################################################
# List of project wide directories to look for files
################################################################################
INCLUDE_DIRS = 


################################################################################
# List of project wide directories to look for files
################################################################################
BUILD_SUB_DIRS =


################################################################################
# List of verilog define or parameter files to be loaded for this block
################################################################################
VERILOG_INCLUDE_FILES =


################################################################################
# List of hash define files to be loaded for this block
################################################################################
HASH_DEFINE_FILES =


################################################################################
# Hash define vars to be passed as command line
################################################################################
HASH_DEFINE_VARS =


################################################################################
# Default Format is System Verilog
################################################################################
RTL_FORMAT = systemverilog


################################################################################
# Additional project level command line options
################################################################################
ADDITIONAL_OPTIONS = --sort_ports --ungroup_ports


################################################################################
# Additional project level command line options
################################################################################
BUILD_ADDITIONAL_OPTIONS =


################################################################################
# Any additional options user wants to add it in the local makefile
################################################################################
USER_OPTIONS =


################################################################################
# Prefix to be added to generated files and also search sub modules with prefix
################################################################################
PREFIX =


################################################################################
# Enables sub-block build for hierarchical bottom up build
################################################################################
BUILD_SUBS = 1


################################################################################
# List of additional dependencies for the build
################################################################################
ADDITIONAL_DEPENDENCIES =


################################################################################
# Option to not to delete the filelist for the submodule files
################################################################################
DELETE_SUB_FILELISTS = 1


################################################################################
# Running directory name where all the temp files are created
################################################################################
RUN_DIR = tmp
