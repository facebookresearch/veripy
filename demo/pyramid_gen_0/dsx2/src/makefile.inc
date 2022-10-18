$(RUN_DIR)/dsx2_lib: dsx2.psv $(RUN_DIR)/ds2_function_lib 
	$(VERIPY_LIB) dsx2.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/dsx2_lib


$(RUN_DIR)/ds2_function_lib: ds2_function.psv $(RUN_DIR)/generic_csa_lib $(RUN_DIR)/booth_mult_pp_lib 
	$(VERIPY_LIB) ds2_function.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/ds2_function_lib


$(RUN_DIR)/generic_csa_lib: 
ifeq ($(BUILD_SUBS),1)
	make -C $(ROOT)/demo/pyramid_gen_0/common/generic_csa/src Build
endif
	touch $(RUN_DIR)/generic_csa_lib


$(RUN_DIR)/booth_mult_pp_lib: 
ifeq ($(BUILD_SUBS),1)
	make -C $(ROOT)/demo/pyramid_gen_0/common/booth_mult_pp/src Build
endif
	touch $(RUN_DIR)/booth_mult_pp_lib


