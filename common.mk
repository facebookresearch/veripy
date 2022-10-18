####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

################################################################################
# This is a common.mk file which will be inlcluded in all the veripy makefiles #
# This file needs to be in a common place for a project.
################################################################################

################################################################################
# Generate module extention based on verilog or systemverilog
################################################################################
ifeq ($(RTL_FORMAT),"verilog")
  MODULE_EXT = $(MODULE).pv
else
  MODULE_EXT = $(MODULE).psv
endif


################################################################################
# Adding the dest_dir for BUILS_SUB_DIRS list to add it to INCLUDE_DIRS
# for veripy to look for submodule files
################################################################################
DEST_INCL_DIRS = $(subst src,$(TARGET),$(BUILD_SUB_DIRS))

INCLUDE_DIRS += $(DEST_INCL_DIRS)


################################################################################
# Create $(RUN_DIR) directory if does not exist
################################################################################
ifeq ($(wildcard $(RUN_DIR)),)
$(shell mkdir $(RUN_DIR))
endif


################################################################################
# Create the DEST_DIR if does not exist
################################################################################
ifeq ($(wildcard $(DEST_DIR)),)
$(shell mkdir -p $(DEST_DIR))
endif


################################################################################
# --format option for veripy run command
################################################################################
ifneq ($(RTL_FORMAT),)
FORMAT_OPTION = --format $(RTL_FORMAT)
else
FORMAT_OPTION = # Intentionally left blank here
endif


################################################################################
# Expanding INCLUDE_DIRS to veripy --include option
################################################################################
ifneq ($(INCLUDE_DIRS),)
INCLUDE_OPTION = --include $(INCLUDE_DIRS)
endif


################################################################################
# --include option for build have additional directories to look for .psv/.pv files
################################################################################
BUILD_ALL_DIRS = $(BUILD_SUB_DIRS)
BUILD_ALL_DIRS += $(INCLUDE_DIRS)

ifneq ($(BUILD_ALL_DIRS),)
BUILD_INCLUDE_OPTION = --include $(BUILD_ALL_DIRS)
endif


################################################################################
# --verilog_include_files option for loading define or param files
################################################################################
VERILOG_INCLUDE_FILES_OPTION = # Intentionally left blank here

ifneq ($(VERILOG_INCLUDE_FILES),)
VERILOG_INCLUDE_FILES_OPTION = --verilog_define_files $(VERILOG_INCLUDE_FILES)
endif


################################################################################
# --hash_define_files option for loading define or param files
################################################################################
HASH_DEFINE_FILES_OPTION = # Intentionally left blank here

ifneq ($(HASH_DEFINE_FILES),)
HASH_DEFINE_FILES_OPTION = --hash_define_files $(HASH_DEFINE_FILES)
endif


################################################################################
# --hash_define_vars option for loading #define variables
################################################################################
HASH_DEFINE_VARS_OPTION = # Intentionally left blank here

ifneq ($(HASH_DEFINE_VARS),)
HASH_DEFINE_VARS_OPTION = --hash_define_vars $(HASH_DEFINE_VARS)
endif


################################################################################
# Expanding INTERFACE_SPECS to veripy --interface_spec option
################################################################################
ifneq ($(INTERFACE_SPECS),)
INTERFACE_SPEC_OPTION = --interface_spec $(INTERFACE_SPECS)
endif


################################################################################
# Expanding INTERFACE_DEFS to veripy --interface_spec option
################################################################################
ifneq ($(INTERFACE_DEFS),)
INTERFACE_DEF_OPTION = --interface_def $(INTERFACE_DEFS)
endif


################################################################################
# Expanding MODULE_DEFS to veripy --module_def option
################################################################################
ifneq ($(MODULE_DEFS),)
MODULE_DEF_OPTION = --module_def $(MODULE_DEFS)
endif


################################################################################
# Pass the root path option to veripy_build.py to replace with $(ROOT)
################################################################################
VERIPY_ROOT_PATH_OPTION = --root_path ${ROOT}/


################################################################################
# veripy script path option for veripy_build.py
################################################################################
VERIPY_PATH_OPTION = --veripy_path $(VERIPY_SCRIPT)


################################################################################
# veripy script path option for veripy_build.py
################################################################################
VERIPY_BUILD_UPDATE_INC_OPTION = --update_inc

################################################################################
# USER_OPTIONS contect to be added as target_args in TARGETS
################################################################################
BUILD_USER_OPTIONS = # Intentionally left blank here
ifneq ($(USER_OPTIONS),)
BUILD_USER_OPTIONS = --user_options "$(USER_OPTIONS) $(ADDITIONAL_OPTIONS)"
endif

ifneq ($(ADDITIONAL_OPTIONS),)
BUILD_USER_OPTIONS = --user_options "$(USER_OPTIONS) $(ADDITIONAL_OPTIONS)"
endif

################################################################################
# SUBDIRS Dictionary File location
# Use flag USE_DICT=1 in your make command to reuse dictionary files
# Use flag USE_DICT=2 in your make command to not use dictionary file
################################################################################
ifeq ($(USE_DICT),1)
SUBDIRS_DICT_JSON := "/tmp/${USER}_subdirs_dict.json"
SUBDIRS_DICT_JSON_OPTION = --build_subdirs_dict "$(SUBDIRS_DICT_JSON)"
USE_PREV_DICT_OPTION = --use_prev_dict
SUBDIRS_DICT_MSG = "\nUsing dictionary file: $(SUBDIRS_DICT_JSON)\n"
else ifeq ($(USE_DICT),0)
SUBDIRS_DICT_JSON_OPTION = # Intentionally left blank here
USE_PREV_DICT_OPTION = # Intentionally left blank here
SUBDIRS_DICT_MSG = "\nNot using dictionary file\n"
DEL_DICT_FILE := $(shell rm -rf /tmp/${USER}*_subdirs_dict.json) # This variable is not used, and is only here to delete the dictionary file
else
TIMESTAMP := $(shell /bin/date "+%d%m%Y_%H%M%S")
SUBDIRS_DICT_JSON := "/tmp/${USER}_$(TIMESTAMP)_subdirs_dict.json"
SUBDIRS_DICT_JSON_OPTION = --build_subdirs_dict "$(SUBDIRS_DICT_JSON)"
USE_PREV_DICT_OPTION = # Intentionally left blank here
SUBDIRS_DICT_MSG = "\nUsing dictionary file: $(SUBDIRS_DICT_JSON)\n"
endif

################################################################################
# Profiling variable
# Use flag PROF=1 in your make command to enable profiling
################################################################################
ifeq ($(PROF),1)
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PROFILING_MODULE = $(MODULE)
PROFILING_OPTION = --profiling $(ROOT_DIR)/$(PROFILING_MODULE).profile
PROF_SAVED = 1
else ifeq ($(PROF_SAVED),1)
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
PROFILING_MODULE = $(MODULE)
PROFILING_OPTION = --profiling $(ROOT_DIR)/$(PROFILING_MODULE).profile
PROF_SAVED = 1
else
ROOT_DIR :=
PROFILING_MODULE =
PROFILING_OPTION =
PROF_SAVED =
endif

################################################################################
## dest_dir variable
## pass dest directory
################################################################################

DEST_DIR_OPTION = --targetdir $(DEST_DIR)

################################################################################
# Target to generate buck TARGETS file
################################################################################
TARGETS targets: DEL_PROF SUB_TARGETS $(ADDITIONAL_DEPENDENCIES)
	@echo -e $(SUBDIRS_DICT_MSG)
	$(VERIPY_BUILD_SCRIPT) $(MODULE_EXT) $(FORMAT_OPTION) \
            $(SUBDIRS_DICT_JSON_OPTION) \
            $(USE_PREV_DICT_OPTION) \
            $(BUILD_INCLUDE_OPTION) \
            $(INTERFACE_SPEC_OPTION) \
            $(INTERFACE_DEF_OPTION) \
            $(MODULE_DEF_OPTION) \
            $(VERIPY_ROOT_PATH_OPTION) \
            $(VERIPY_PATH_OPTION) \
            $(BUILD_ADDITIONAL_OPTIONS) \
            $(VERILOG_INCLUDE_FILES_OPTION) \
            $(HASH_DEFINE_FILES_OPTION) \
            $(HASH_DEFINE_VARS_OPTION) \
            $(BUILD_USER_OPTIONS) \
            $(USER_OPTIONS) \
            $(PROFILING_OPTION) \
	    $(DEST_DIR_OPTION)
	@mv TARGETS.new ${PWD}/../TARGETS
	@echo "### Generated ../TARGETS successfully ###"

SUB_TARGETS sub_targets:
ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)
	@for dir in $(BUILD_SUB_DIRS); do cd $$dir && echo "DIRECTORY= $$dir" && $(MAKE) TARGETS SUBDIRS_DICT_JSON=$(SUBDIRS_DICT_JSON) USE_PREV_DICT_OPTION=$(USE_PREV_DICT_OPTION) ROOT_DIR=$(ROOT_DIR) PROFILING_MODULE=$(PROFILING_MODULE) PROF_SAVED=$(PROF_SAVED) PROF=0 || exit 1; done
endif
endif

DEL_DICT del_dict:
	if [ -f "/tmp/${USER}*_subdirs_dict.json" ] ; then \
	  rm /tmp/${USER}*_subdirs_dict.json; \
	fi

DEL_PROF del_prof:
ifeq ($(PROF),1)
	if [ -f "$(ROOT_DIR)/$(PROFILING_MODULE).profile" ] ; then \
	  rm $(ROOT_DIR)/$(PROFILING_MODULE).profile; \
	fi
endif

################################################################################
# Target to generate buck MAKEINC file
################################################################################
MAKEINC makeinc: SUB_MAKEINC $(ADDITIONAL_DEPENDENCIES)
	$(VERIPY_BUILD_SCRIPT) $(MODULE_EXT) $(FORMAT_OPTION) \
            $(BUILD_INCLUDE_OPTION) \
            $(INTERFACE_SPEC_OPTION) \
            $(INTERFACE_DEF_OPTION) \
            $(MODULE_DEF_OPTION) \
            $(VERIPY_ROOT_PATH_OPTION) \
            $(VERIPY_PATH_OPTION) \
            $(VERIPY_BUILD_UPDATE_INC_OPTION) \
            $(BUILD_ADDITIONAL_OPTIONS) \
            $(VERILOG_INCLUDE_FILES_OPTION) \
            $(HASH_DEFINE_FILES_OPTION) \
            $(HASH_DEFINE_VARS_OPTION) \
            $(BUILD_USER_OPTIONS) \
            $(USER_OPTIONS) \
	    $(DEST_DIR_OPTION)
	@mv makefile.inc.new makefile.inc
	@echo "### Generated makefile.inc successfully ###"


SUB_MAKEINC sub_makeinc:
ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)
	for dir in $(BUILD_SUB_DIRS); do cd $$dir && $(MAKE) MAKEINC || exit 1; done
endif
endif


################################################################################
# Build command for the top module
####################################m ############################################
Build build: makefile.inc $(RUN_DIR)/$(MODULE)_lib $(ADDITIONAL_DEPENDENCIES) SUB_BUILD


SUB_BUILD sub_build:
ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)
	for dir in $(BUILD_SUB_DIRS); do cd $$dir && make Build || exit 1; done
endif
endif

################################################################################
# Buck build target from the src directory
################################################################################
BUCK_TARGET = $(shell pwd | sed -E 's/\/src//' | sed -E 's/.*\/fbcode\//\/\//')

Buck buck:
	buck build -v 5 $(BUCK_TARGET)
	gen_filelist -i ../$(TARGET)/filelist.txt -m rel -b $(MODULE) -o ../$(TARGET)/

nvBuck nvbuck:
	buck build $(BUCK_TARGET)
	gen_filelist -i ../$(TARGET)/filelist.txt -m rel -b $(MODULE) -o ../$(TARGET)/

################################################################################
# Filelist generation using gen_filelist for each block
################################################################################
gen_filelist GEN_FILELIST: SUB_GEN_FILELIST ../$(TARGET)/$(MODULE).f


../$(TARGET)/$(MODULE).f: ../$(TARGET)/filelist.txt
	gen_filelist -i ../$(TARGET)/filelist.txt -m rel -b $(MODULE) -o ../$(TARGET)/


SUB_GEN_FILELIST sub_gen_filelist:
ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)
	for dir in $(BUILD_SUB_DIRS); do cd $$dir && make gen_filelist || exit 1; done
endif
endif


################################################################################
# Clean the dependancies touched files
################################################################################
Clean clean: DEL_DICT
ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)
	for dir in $(BUILD_SUB_DIRS); do cd $$dir && $(MAKE) Clean || exit 1; done
endif
endif
	rm -r -f *_lib $(RUN_DIR)/*_lib *.expanded *.debug


################################################################################
# Include the makefile.inc only if it exists
################################################################################
ifneq ($(wildcard ./makefile.inc),)
include makefile.inc
endif


