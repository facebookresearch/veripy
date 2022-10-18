$(RUN_DIR)/generic_csa_lib: generic_csa.psv 
	$(VERIPY_LIB) generic_csa.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/generic_csa_lib


