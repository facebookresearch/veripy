$(RUN_DIR)/pyramid_gen_0_lib: pyramid_gen_0.psv $(RUN_DIR)/clk_gate_lib $(RUN_DIR)/reset_sync_lib $(RUN_DIR)/down_scale_lib 
	$(VERIPY_LIB) pyramid_gen_0.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/pyramid_gen_0_lib


$(RUN_DIR)/clk_gate_lib: clk_gate.psv 
	$(VERIPY_LIB) clk_gate.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/clk_gate_lib


$(RUN_DIR)/reset_sync_lib: reset_sync.psv 
	$(VERIPY_LIB) reset_sync.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) 
	touch $(RUN_DIR)/reset_sync_lib


$(RUN_DIR)/down_scale_lib: down_scale.psv $(RUN_DIR)/dsx2_lib 
	$(VERIPY_LIB) down_scale.psv $(FORMAT_OPTION) $(INCLUDE_OPTION) $(INTERFACE_SPEC_OPTION)                         $(INTERFACE_DEF_OPTION) $(MODULE_DEF_OPTION) $(FILES_OPTION)                         $(LIST_OPTION) $(VERILOG_INCLUDE_FILES_OPTION)                         $(HASH_DEFINE_FILES_OPTION) $(HASH_DEFINE_VARS_OPTION)                         $(PARSE_GENERATE_OPTION) --destination $(DEST_DIR) $(USER_OPTIONS)                         $(ADDITIONAL_OPTIONS) --hash_define_vars ENABLE 
	touch $(RUN_DIR)/down_scale_lib


$(RUN_DIR)/dsx2_lib: 
ifeq ($(BUILD_SUBS),1)
	make -C $(ROOT)/demo/pyramid_gen_0/dsx2/src Build
endif
	touch $(RUN_DIR)/dsx2_lib


