$(RUN_DIR)/booth_mult_pp_lib: booth_mult_pp.psv 
	$(VERIPY_LIB) booth_mult_pp.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/booth_mult_pp_lib


