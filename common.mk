####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################

################################################################################
# This is a common.mk file which will be inlcluded in all the veripy makefiles #
################################################################################

# DO NOT REMOVE THE NEXT LINE! This is needed to pick up the eda env
SHELL=/usr/bin/bash

USE_OPEN_SOURCE_VERIPY ?= 0
ifeq ($(USE_OPEN_SOURCE_VERIPY),1)
    export PATH := $(INFRA_ASIC_FPGA_ROOT)/common/tools/veripy/open_source:$(PATH)
endif

################################################################################
# Generate module extention based on verilog or systemverilog
################################################################################
ifeq ($(RTL_FORMAT),"verilog")
  MODULE_EXT = $(MODULE).pv
  TARGET_MODULE_EXT = $(MODULE).v
else
  MODULE_EXT = $(MODULE).psv
  TARGET_MODULE_EXT = $(MODULE).sv
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
# Expanding INCLUDE_FILELISTS to veripy --flist option
################################################################################
ifneq ($(INCLUDE_LISTS),)
FILELIST_OPTION = --flist $(INCLUDE_LISTS)
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
VERIPY_ROOT_PATH_OPTION = --root_path ${INFRA_ASIC_FPGA_ROOT}/../


################################################################################
# veripy script path option for veripy_build.py
################################################################################
VERIPY_PATH_OPTION = --veripy_path $(VERIPY_SCRIPT)


################################################################################
# veripy script path option for veripy_build.py
################################################################################
VERIPY_BUILD_UPDATE_INC_OPTION = --update_inc

################################################################################
# USER_OPTIONS contect to be added as target_args in BUCK
################################################################################
BUILD_USER_OPTIONS = # Intentionally left blank here
ifneq ($(USER_OPTIONS),)
BUILD_USER_OPTIONS = --user_options "$(USER_OPTIONS) $(ADDITIONAL_OPTIONS)"
endif

ifneq ($(ADDITIONAL_OPTIONS),)
BUILD_USER_OPTIONS = --user_options "$(USER_OPTIONS) $(ADDITIONAL_OPTIONS)"
endif

################################################################################
# PRUNE_DEPS option that only keeps dependencies actually used
################################################################################
ifeq ($(PRUNE_DEPS),1)
PRUNE_DEPS_OPTION = --prune_deps
else
PRUNE_DEPS_OPTION = # Default is blank
endif

################################################################################
# PRUNE_DEP_TARGET option to prune dependencies (PRUNE_DEPS=1) for specified targets.
################################################################################
ifneq ($(PRUNE_DEP_TARGET),)
PRUNE_DEP_TARGET_OPTION = --prune_dep_target $(PRUNE_DEP_TARGET)
else
PRUNE_DEP_TARGET_OPTION = # Default is blank
endif

################################################################################
# CONFIG_FILE option to define configuration for specified targets.
################################################################################
ifneq ($(CONFIG_FILE),)
CONFIG_FILE_OPTION = --config_file $(CONFIG_FILE)
else
CONFIG_FILE_OPTION = # Default is blank
endif

################################################################################
# VENDOR_CODE_OPTION specifies ASIC_VENDOR_CODE that veripy_build actually used
################################################################################
ifneq ($(VENDOR_CODE),)
VENDOR_CODE_OPTION = --asic_vendor_code $(VENDOR_CODE)
else
VENDOR_CODE_OPTION = # Default is blank
endif

################################################################################
# APPEND_TO_TARGETS_OPTION to append generated targets to existing BUCK file
################################################################################
ifeq ($(APPEND_TO_TARGETS),1)
APPEND_TO_TARGETS_OPTION = --append_to_targets
else
APPEND_TO_TARGETS_OPTION = # Default is blank
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
# Target to build veripy libs
################################################################################
VERIPY veripy: $(VERIPY_SCRIPT)
	if [ ! -f "$(VERIPY_LIB)" ] || [ ! -f "${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy" ] || [ "$$(cat ${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy)" != "$$(cat $(VERIPY_SCRIPT) | md5sum)" ]; then \
	    # buck build //infra_asic_fpga/common/tools/veripy2.0:veripy; \
	    cat $(VERIPY_SCRIPT) | md5sum > ${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy; \
	fi


################################################################################
# Target to build veripy_build libs
################################################################################
VERIPY_BUILD veripy_build: $(VERIPY_BUILD_SCRIPT)
	if [ ! -f "$(VERIPY_BUILD_LIB)" ] || [ ! -f "${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy_build" ] || [ "$$(cat ${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy_build)" != "$$(cat $(VERIPY_BUILD_SCRIPT) | md5sum)" ]; then \
	    # buck build //infra_asic_fpga/common/tools/veripy2.0:veripy_build; \
	    cat $(VERIPY_BUILD_SCRIPT) | md5sum > ${INFRA_ASIC_FPGA_ROOT}/common/tools/veripy2.0/.veripy_build; \
	fi

# VERIPY_BIN:=veripy.py
# VERIPY_BUILD_LIB:=veripy_build.py

ifeq ($(BUILD_SUBS),1)
ifneq ($(BUILD_SUB_DIRS),)

print_subdirs:
	@echo -e "\n### $(shell pwd) has BUILD_SUB_DIRS: $(BUILD_SUB_DIRS)\n"

$(BUILD_SUB_DIRS):
	$(MAKE) --directory=$@ $(MAKECMDGOALS)

targets clean clean_makeinc clean_targets gen_filelist verilog_lint lint synth register: print_subdirs $(BUILD_SUB_DIRS)

.PHONY: print_subdirs $(BUILD_SUB_DIRS)

endif
endif

################################################################################
# Mixed .sv/.psv file support: Symlink vanilla .sv files to rtl_b/
################################################################################
# Identify .sv files (vanilla SystemVerilog, no veripy processing needed)
SV_FILES := $(wildcard *.sv)

# Symlink .sv files to rtl_b/ before veripy_build runs
.PHONY: symlink_sv_files
symlink_sv_files:
ifneq ($(SV_FILES),)
	@echo "=== Symlinking vanilla .sv files to rtl_b/ ==="
	@mkdir -p ../rtl_$(BUCK_CHIP)
	@for sv_file in $(SV_FILES); do \
		echo "  Symlinking $$sv_file -> ../rtl_$(BUCK_CHIP)/$$sv_file"; \
		ln -sf ../src/$$sv_file ../rtl_$(BUCK_CHIP)/$$sv_file; \
	done
endif

################################################################################
# Target to generate buck BUCK file
################################################################################
make_targets:
	@echo -e "\n### Make targets $(MODULE)  ($(shell pwd)) ...\n"
.PHONY: make_targets

TARGETS targets: symlink_sv_files make_targets DEL_PROF $(ADDITIONAL_DEPENDENCIES)
	@echo -e $(SUBDIRS_DICT_MSG)
	@echo -e $(VERIPY_BUILD_SCRIPT)
	@set -o pipefail; $(VERIPY_BUILD_SCRIPT) $(MODULE_EXT) $(FORMAT_OPTION) $(SUBDIRS_DICT_JSON_OPTION) $(USE_PREV_DICT_OPTION) $(BUILD_INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION) $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(VERIPY_ROOT_PATH_OPTION) $(VERIPY_PATH_OPTION) $(BUILD_ADDITIONAL_OPTIONS) $(VERILOG_INCLUDE_FILES_OPTION)$(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION) $(BUILD_USER_OPTIONS) $(USER_OPTIONS) $(PRUNE_DEPS_OPTION) $(PRUNE_DEP_TARGET_OPTION) $(PROFILING_OPTION) $(FILELIST_OPTION) $(VENDOR_CODE_OPTION) $(APPEND_TO_TARGETS_OPTION) $(CONFIG_FILE_OPTION) $(DEST_DIR_OPTION) 2>&1 | tee tmp/make_targets_${MODULE}.log

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
# Target to generate buck makefile.inc file
################################################################################
make_makeinc_module:
	@echo -e "\n### Make makeinc is deprecated, use make targets instead ..."
.PHONY: make_makeinc_module

MAKEINC makeinc: make_makeinc_module


################################################################################
# Builducommand for the top module
####################################m ############################################
make_build_module:
	@echo -e "\n### Make build is deprecated, use make buck2 instead ..."
.PHONY: make_build_module

Build build: make_build_module

################################################################################
# Buck build target from the src directory
################################################################################
ifneq ($(BUCK_CHIP),)
BUCK_TARGET =  $(shell pwd | sed -E 's/\/src/:/' | sed -E 's/.*\/fbcode\//\/\//')rtl_$(BUCK_CHIP)_$(ASIC_VENDOR_CODE)_f_list
else
BUCK_TARGET = $(shell pwd | sed -E 's/\/src/:/' | sed -E 's/.*\/fbcode\//\/\//')
endif

BUCK_LIB_GEN ?= 1
BUCK_CHIPLET_LIB_GEN ?= 0
BUCK_VERBOSE ?= 5
Buck buck:
	@set -o pipefail; buck build -v $(BUCK_VERBOSE) $(BUCK_TARGET) 2>&1 | tee tmp/make_buck_${MODULE}.log
ifeq ($(BUCK_CHIPLET_LIB_GEN),1)
	import-filelists --upload-volumettes
else ifeq ($(BUCK_LIB_GEN),1)
	import-all-filelists
endif

nvBuck nvbuck:
	buck2 build $(BUCK_TARGET)

Buck2 buck2:
	@set -o pipefail; buck2 build -v $(BUCK_VERBOSE) $(BUCK_TARGET) 2>&1 | tee tmp/make_buck2_${MODULE}.log
ifeq ($(BUCK_CHIPLET_LIB_GEN),1)
	import-filelists --upload-volumettes
else ifeq ($(BUCK_LIB_GEN),1)
	import-all-filelists
endif

################################################################################
# Target to build vcs
################################################################################
BUILD_HOME      = $(shell pwd)/tmp

VCS vcs:
	mkdir -p ${BUILD_HOME}
	gen_filelist -i ../$(TARGET)/filelist.txt -m dv -o ${BUILD_HOME}/$(MODULE).f
	$(eval vcs_define = +define+NOTBV +define+FCOV_disable +define+DURGA_BEH_MEM +define+DURGA_BEH_MEM_INIT_0 +define+DURGA_BEH_CKG +define+DURGA_BEH_MODE +define+DURGA_BEH_CGC +define+DURGA_BEH_SIM +define+FB_BEH_MEM +define+FB_BEH_MEM_INIT_0 +define+FB_BEH_CKG +define+FB_BEH_MODE +define+FB_BEH_CGC +define+FB_BEH_SIM)
	cd ${BUILD_HOME} && vcs $(VCS_ERROPTS) +error+2500 -Xkeyopt=tbopt -ntb_opts uvm-ieee -Mupdate=1 -kdb -full64 -licqueue -lca -sverilog -f ${BUILD_HOME}/$(MODULE).f $(vcs_define) $(VCS_DEFINE) -top $(MODULE) -override_timescale=1ns/1ps
	rm -rf verdi_config_file

VCS_CLEAN vcs_clean:
	rm -rf ${BUILD_HOME}

################################################################################
# Filelist generation using gen_filelist for each block
################################################################################
gen_filelist GEN_FILELIST: ../$(TARGET)/$(MODULE).f


../$(TARGET)/$(MODULE).f: ../$(TARGET)/filelist.txt
	@set -o pipefail; gen_filelist -i ../$(TARGET)/filelist.txt -m rel -b $(MODULE) -o ../$(TARGET)/ 2>&1 | tee tmp/make_gen_filelist_${MODULE}.log

################################################################################
# Verilog lint using verilog_syntax_check.py for each block
################################################################################
VERILOG_SYNTAX_CHECK_SCRIPT = $(shell which verilog_syntax_check.py)

verilog_lint VERILOG_LINT: ../$(TARGET)/$(MODULE)_syntax_errors

../$(TARGET)/$(MODULE)_syntax_errors: ../$(TARGET)/$(MODULE).f
	$(VERILOG_SYNTAX_CHECK_SCRIPT) -i ../$(TARGET)/$(MODULE).f -o ../$(TARGET)/$(MODULE)_syntax_errors

################################################################################
# flows_make wrapper targets (lint, synth)
#
# These invoke the flows_make infrastructure from the design src/ directory,
# so you don't have to cd into common/flows_make and run make_flow manually.
#
# Usage:
#   make lint                              # RTL lint (SpyGlass) for current module
#   make lint TAG=my_run NC_JOB_MEM=100G   # custom tag and memory
#
#   make synth                             # synthesis import/elab stage
#   make synth BLOCK=sub_module            # synth a sub-module
#   make synth SYNTH_STAGE=syn_fc_initial_opto  # run through initial_opto
################################################################################
MAKE_FLOW_SCRIPT = $(INFRA_ASIC_FPGA_ROOT)/common/flows_make/scripts/make_flow.bash
BLOCK ?= $(MODULE)
NC_JOB_MEM ?= 50G
NC_JOB_CLASS ?=

# Synthesis-specific
SYNTH_STAGE ?= syn_fc
SYNTH_JOB_MEM ?= 500G

# Build the extra args string
_FLOW_EXTRA_ARGS = CONTINUE_ON_ERROR=1
ifneq ($(NC_JOB_CLASS),)
_FLOW_EXTRA_ARGS += NC_JOB_CLASS=$(NC_JOB_CLASS)
endif

lint LINT spyglass SPYGLASS:
	bash -c '\
		cd $(INFRA_ASIC_FPGA_ROOT)/common/flows_make && \
		source ./scripts/make_flow.bash && \
		make_flow rtl_lint \
			DESIGN_NAME=$(MODULE) \
			TAG=$(MODULE)_lint_$(shell date +%Y%m%d_%H%M%S) \
			NC_JOB_MEM=$(NC_JOB_MEM) \
			$(_FLOW_EXTRA_ARGS)'

synth SYNTH:
	bash -c '\
		cd $(INFRA_ASIC_FPGA_ROOT)/common/flows_make && \
		source ./scripts/make_flow.bash && \
		make_flow $(SYNTH_STAGE) \
			DESIGN_NAME=$(MODULE) \
			BLOCK=$(BLOCK) \
			TAG=$(BLOCK)_synth_$(shell date +%Y%m%d_%H%M%S) \
			NC_JOB_MEM=$(SYNTH_JOB_MEM) \
			$(_FLOW_EXTRA_ARGS)'

register REGISTER:
	$(MAKE) -C $(INFRA_ASIC_FPGA_ROOT)/common/flows_make create_design_list UPDATE_DESIGN_LIST=1

################################################################################
# Clean the dependancies touched files
################################################################################
make_clean_module:
	@echo -e "\n### Make clean $(MODULE) ($(shell pwd)) ..."
make_clean_makeinc:
	@echo -e "\n### Make clean_makeinc $(MODULE) ($(shell pwd)) ..."
make_clean_targets:
	@echo -e "\n### Make clean_targets $(MODULE) ($(shell pwd)) ..."
.PHONY: make_clean_module make_clean_makeinc make_clean_targets

Clean clean: make_clean_module DEL_DICT
	rm -r -f *.expanded* *.debug $(CLEAN_TARGETS)

Clean_makeinc clean_makeinc: make_clean_makeinc
	rm -r -f makefile.inc

Clean_targets clean_targets: make_clean_targets
	rm -r -f ../BUCK

################################################################################
# Run 'make clean 2>&1 | tee make_clean_$(MODULE).log' to create make_clean_$(MODULE).log
################################################################################
ifneq ($(wildcard make_clean_$(MODULE).log),)
make_clean_hierarchy_json:
	gen_module_hierarchy.py make_clean_$(MODULE).log
endif

################################################################################
# Run 'make makeinc 2>&1 | tee make_makeinc_$(MODULE).log' to create make_makeinc_$(MODULE).log
################################################################################
ifneq ($(wildcard make_makeinc_$(MODULE).log),)
make_makeinc_hierarchy_json:
	gen_module_hierarchy.py make_makeinc_$(MODULE).log
endif

################################################################################
# Run 'make targets 2>&1 | tee make_targets_$(MODULE).log' to create maketargets_$(MODULE).log
################################################################################
ifneq ($(wildcard make_targets_$(MODULE).log),)
make_targets_hierarchy_json:
	gen_module_hierarchy.py make_targets_$(MODULE).log
endif

################################################################################
# Include the makefile.inc only if it exists (make makeinc & make build are deprecated)
################################################################################
# ifneq ($(wildcard ./makefile.inc),)
# include makefile.inc
# endif
