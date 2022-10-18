$(RUN_DIR)/xdfil_lib: xdfil.psv ./specs/interfaces.spec ./specs/interfaces.def ./specs/module.def 
	$(VERIPY_LIB) xdfil.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/xdfil_lib


