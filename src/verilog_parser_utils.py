import re
import sys
import time

import anytree

from .regex import *

from verilog_syntax_check import (
    BranchNode,
    Error,
    Node,
    SyntaxData,
    TokenNode,
    VeribleVerilogSyntax,
)

# For Verible CST output Formatting
indent_level = 0


def indent():
    global indent_level
    indent_level += 1


def unindent():
    global indent_level
    indent_level -= 1


def get_indent_level():
    return indent_level


def indent_spaces():
    return " " * get_indent_level() * 2


# Verible CST navigation & processing
def get_source_text(node):
    token_nodes = list(node.iter_find_all(lambda n: isinstance(n, TokenNode)))
    # print(f"{indent_spaces()}token nodse: {token_nodes}")
    sorted_token_nodes = sorted(token_nodes, key=lambda n: n.start)
    # print(f"{indent_spaces()}sortedtoken nods: {sorted_token_nodes}")
    source_text = " ".join([n.text for n in sorted_token_nodes])
    source_text = re.sub(r"\s+::\s+", "::", source_text)
    # print(f"{indent_spaces()}Source text: '''{source_text}]'''\n")

    return source_text


def kExpressionList_func(node, mape, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kExpression_nodes = node.find_all({"tag": "kExpression"})
    for kExpression_node in kExpression_nodes:
        expression_str = get_source_text(kExpression_node)
        expression_str = re.sub(r"\s+", "", expression_str)
        parser.parse_conditions(expression_str)


kExpressionList = {
    "func": kExpressionList_func,
}


def kBlockingAssignmentStatement_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    parser.parse_assignments("assign", source_text)


kBlockingAssignmentStatement = {
    "func": kBlockingAssignmentStatement_func,
}


def kNonblockingAssignmentStatement_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    psv_assign_str = source_text
    # for line_key in parser.auto_reset_lines:
    #     line_source =  re.sub(r"\s*", "", source_text)
    #     if line_key in line_source or line_source in line_key:
    #         psv_assign_str = parser.auto_reset_lines[re.sub(r"\s*", "", line_key)]
    #         break

    if parser.always_for_loop_count > 0:
        for c_for_idx in parser.always_for_loops.keys():
            search_var = "\\b" + parser.always_for_loops[c_for_idx]["for_var"] + "\\b"
            replace_var = (
                str(parser.always_for_loops[c_for_idx]["end_val"])
                + ":"
                + str(parser.always_for_loops[c_for_idx]["start_val"])
            )
            psv_assign_str = re.sub(search_var, replace_var, psv_assign_str)

    parser.parse_assignments("ALWAYS_SEQ", psv_assign_str)


kNonblockingAssignmentStatement = {
    "func": kNonblockingAssignmentStatement_func,
}


def kProceduralContinuousAssignmentStatement_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    assign_regex = RE_ASSIGN.search(source_text)
    if assign_regex:
        parser.parse_assignments("assign", assign_regex.group(1))


# veilog.y:6816
kProceduralContinuousAssignmentStatement = {
    "func": kProceduralContinuousAssignmentStatement_func,
}


def kParenGroup_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kExpression_nodes = node.find_all({"tag": "kExpression"})
    for kExpression_node in kExpression_nodes:
        expression_str = get_source_text(kExpression_node)
        expression_str = re.sub(r"\s+", "", expression_str)
        parser.parse_conditions(expression_str)


kParenGroup = {
    "func": kParenGroup_func,
}

# verilog.y:3756 case_item
# kCaseItem will update with statement_item later
kCaseItem = {
    "kExpressionList": kExpressionList,
}

# kCaseItem will update with statement_item later
kDefaultItem = {}


def kCaseItemList_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:3791 case_items
kCaseItemList = {
    "kCaseItem": kCaseItem,
    "kDefaultItem": kDefaultItem,
    "func": kCaseItemList_func,
}

# verilog.y:3698 case_inside_item
# kCaseInsideItem will update with statement_item later
kCaseInsideItem = {
    "kExpressionList": kExpressionList,
}


def kCaseInsideItemList_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:3791 case_items
kCaseInsideItemList = {
    "kCaseInsideItem": kCaseInsideItem,
    "func": kCaseInsideItemList_func,
}


def kCaseStatement_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:6834 case_statement
kCaseStatement = {
    "kParenGroup": kParenGroup,
    "kCaseItemList": kCaseItemList,
    "kCaseInsideItemList": kCaseInsideItemList,
    "func": kCaseStatement_func,
}


def kIfHeader_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kExpression_nodes = node.find_all({"tag": "kExpression"})
    for kExpression_node in kExpression_nodes:
        expression_str = get_source_text(kExpression_node)
        expression_str = re.sub(r"\s+", "", expression_str)
        parser.parse_conditions(expression_str)


kIfHeader = {
    "func": kIfHeader_func,
}


def kIfClause_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:3174 block_item_or_statement_or_null_list_opt
# (-> block_item_or_statement_or_null -> statement_item)
# kBlockItemStatementList will update with statement_item later
kBlockItemStatementList = {}

kIfClause = {
    "kIfHeader": kIfHeader,
    "kIfBody": kBlockItemStatementList,
    "func": kIfClause_func,
}


def kElseClause_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kElseClause = {
    "kElseBody": kBlockItemStatementList,
    "func": kElseClause_func,
}


def kConditionalStatement_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:6855
# conditional_statement: unique_priority_opt TK_if expression_in_parens statement_or_null
# | unique_priority_opt TK_if expression_in_parens statement_or_null
#   TK_else statement_or_null
kConditionalStatement = {
    "kIfClause": kIfClause,
    "kElseClause": kElseClause,
    "func": kConditionalStatement_func,
}


def kNetVariableAssignment_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    if parser.always_for_loop_count > 0:
        for c_for_idx in parser.always_for_loops.keys():
            search_var = "\\b" + parser.always_for_loops[c_for_idx]["for_var"] + "\\b"
            replace_var = (
                str(parser.always_for_loops[c_for_idx]["end_val"])
                + ":"
                + str(parser.always_for_loops[c_for_idx]["start_val"])
            )
            source_text = re.sub(search_var, replace_var, source_text)

    parser.parse_assignments("assign", source_text)


# verilog.y:2356(assignment_statement_no_expr):5379(cont_assign):6818(procedural_continuous_assignment) TODO
kNetVariableAssignment = {
    "func": kNetVariableAssignment_func,
}


def kIncrementDecrementExpression_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:2430 TODO
kIncrementDecrementExpression = {
    "func": kIncrementDecrementExpression_func,
}


def kLoopHeader_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    for_regex = RE_FOR.search(source_text)

    if not for_regex:
        return

    for_extract_regex = RE_FOR_EXTRACT.search(for_regex.group(1))

    start_exp = for_extract_regex.group(1)
    end_exp = for_extract_regex.group(2)
    step_exp = for_extract_regex.group(3)

    # Handling int declaration part of for loop
    start_exp_int_regex = RE_FORLOOP_INT_EXTRACT.search(start_exp)

    if start_exp_int_regex:
        start_exp = start_exp_int_regex.group(1) + "=" + start_exp_int_regex.group(2)
        parser.integers.append(start_exp_int_regex.group(1))
        parser.dbg("# Storing integer variable " + start_exp_int_regex.group(1))

    # Handling integer declaration part of for loop
    start_exp_integer_regex = RE_FORLOOP_INTEGER_EXTRACT.search(start_exp)

    if start_exp_integer_regex:
        start_exp = (
            start_exp_integer_regex.group(1) + "=" + start_exp_integer_regex.group(2)
        )
        parser.integers.append(start_exp_integer_regex.group(1))
        parser.dbg("# Storing integer variable " + start_exp_integer_regex.group(1))

    start_exp = re.sub(r"\s+", "", start_exp)
    end_exp = re.sub(r"\s+", "", end_exp)
    step_exp = re.sub(r"\s+", "", step_exp)

    # Start Expression parsing
    start_exp_equal_regex = RE_EQUAL_EXTRACT.search(start_exp)

    if start_exp_equal_regex:
        for_var = start_exp_equal_regex.group(1)
        start_val_ret = parser.tickdef_param_getval(
            "TOP", start_exp_equal_regex.group(2), "", ""
        )
        if start_val_ret[0] == "STRING":
            print(
                "\nWarning: Unable to calculate the start value for the for loop in generate"
            )
        c_start_val = start_val_ret[1]

    # End Expression parsing
    end_exp_less_than_equal_regex = RE_LESS_THAN_EQUAL.search(end_exp)
    end_exp_less_than_regex = RE_LESS_THAN.search(end_exp)
    end_exp_greater_than_equal_regex = RE_GREATER_THAN_EQUAL.search(end_exp)
    end_exp_greater_than_regex = RE_GREATER_THAN.search(end_exp)

    # Step Expression parsing
    step_minus_minus_regex = RE_MINUS_MINUS.search(step_exp)
    step_plus_plus_regex = RE_PLUS_PLUS.search(step_exp)
    step_minus_number_regex = RE_MINUS_NUMBER.search(step_exp)
    step_plus_number_regex = RE_PLUS_NUMBER.search(step_exp)

    c_step_val = 1

    if step_minus_minus_regex:
        c_step_val = "1"
    elif step_plus_plus_regex:
        c_step_val = "1"
    elif step_minus_number_regex:
        c_step_val = step_minus_number_regex.group(3)
    elif step_plus_number_regex:
        c_step_val = step_plus_number_regex.group(3)

    if end_exp_less_than_equal_regex:
        c_end_val = end_exp_less_than_equal_regex.group(2)
    elif end_exp_less_than_regex:
        c_end_val = end_exp_less_than_regex.group(2) + "-" + str(c_step_val)
    elif end_exp_greater_than_equal_regex:
        c_end_val = end_exp_greater_than_equal_regex.group(2)
    elif end_exp_greater_than_regex:
        c_end_val = end_exp_greater_than_regex.group(2) + "+" + str(c_step_val)

    parser.always_for_loops[parser.always_for_loop_count] = {}
    parser.always_for_loops[parser.always_for_loop_count]["orig"] = source_text
    parser.always_for_loops[parser.always_for_loop_count]["for_var"] = for_var
    parser.always_for_loops[parser.always_for_loop_count]["start_val"] = c_start_val
    parser.always_for_loops[parser.always_for_loop_count]["end_val"] = c_end_val
    parser.always_for_loops[parser.always_for_loop_count]["step_val"] = c_step_val
    parser.always_for_loops[parser.always_for_loop_count]["count"] = (
        parser.always_for_loop_count
    )

    parser.dbg(
        "# FOR_LOOP: Var = "
        + for_var
        + "    BitDef: "
        + str(c_end_val)
        + ":"
        + str(c_start_val)
    )

    parser.always_for_loop_count = parser.always_for_loop_count + 1


kLoopHeader = {
    "func": kLoopHeader_func,
}


def kForLoopStatement_func(node, mape, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


def kForLoopStatement_post_func(node, mape, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    parser.always_for_loop_count = 0
    parser.always_for_loops.clear()


# verilog.y:2480 TODO
# loop_statement:TK_for '(' for_initialization_opt ';' expression_opt ';' for_step_opt ')' statement_or_null
# kForLoopStatement will update with statement_item later
kForLoopStatement = {
    "kLoopHeader": kLoopHeader,
    "func": kForLoopStatement_func,
    "post_func": kForLoopStatement_post_func,
}


def kEventControl_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kExpression_nodes = node.find_all({"tag": "kExpression"})
    for kExpression_node in kExpression_nodes:
        expression_str = get_source_text(kExpression_node)
        expression_str = re.sub(r"\s+", "", expression_str)
        parser.parse_conditions(expression_str)


# verilog.y:4188
kEventControl = {
    # "kEventExpression": kEventExpression,
    "func": kEventControl_func,
}

# verilog.y:6909 procedural_timing_control_statement: event_control statement_or_null
# kProceduralTimingControlStatement will update with statement_item later
kProceduralTimingControlStatement = {
    "kEventControl": kEventControl,
}

# verilog.y:6921 seq_block : begin block_item_or_statement_or_null_list_opt end
kSeqBlock = {
    "kBlockItemStatementList": kBlockItemStatementList,
}

kAlwaysStatement = {
    "kEventControl": kEventControl,
}

# verilog.y:6936 statement_item
statement_item = {
    "kBlockingAssignmentStatement": kBlockingAssignmentStatement,
    "kNonblockingAssignmentStatement": kNonblockingAssignmentStatement,
    # "kProceduralContinuousAssignmentStatement": kProceduralContinuousAssignmentStatement,
    "kCaseStatement": kCaseStatement,
    "kConditionalStatement": kConditionalStatement,
    "kNetVariableAssignment": kNetVariableAssignment,
    "kIncrementDecrementExpression": kIncrementDecrementExpression,
    "kForLoopStatement": kForLoopStatement,
    "kProceduralTimingControlStatement": kProceduralTimingControlStatement,
    "kSeqBlock": kSeqBlock,
    "kAlwaysStatement": kAlwaysStatement,  # 202307
}

# TODO: kBlockItemStatementList-> block_item_or_statement_or_null(verilog.y line 3151)
kBlockItemStatementList.update(statement_item)
kProceduralTimingControlStatement.update(statement_item)
kForLoopStatement.update(statement_item)
kCaseItem.update(statement_item)
kDefaultItem.update(statement_item)
kCaseInsideItem.update(statement_item)


def kPackageImportDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kScopePrefix_nodes = node.find_all({"tag": "kScopePrefix"})
    for kScopePrefix_node in kScopePrefix_nodes:
        import_package = kScopePrefix_node.find({"tag": "SymbolIdentifier"}).text
        import_file_name = import_package + ".sv"
        if import_package not in parser.packages:
            parser.load_import_or_include_file(
                "TOP", "IMPORT_EMBEDDED", import_file_name
            )
        else:
            parser.dbg(
                "### Skip importing previously imported package " + import_package
            )


kPackageImportDeclaration = {
    "func": kPackageImportDeclaration_func,
}


def kDataType_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kDataType = {
    "func": kDataType_func,
}


def kTypeDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    type_name = node.find({"tag": "SymbolIdentifier"}).text

    kDataType_node = node.find({"tag": "kDataType"})
    if kDataType_node:
        kPackedDimensions = get_source_text(
            kDataType_node.find({"tag": "kPackedDimensions"})
        )

        kEnumType_node = kDataType_node.find({"tag": "kEnumType"})
        kStructType_node = kDataType_node.find({"tag": "kStructType"})
        kUnionType_node = kDataType_node.find({"tag": "kUnionType"})

        if kEnumType_node:
            source_text = get_source_text(kEnumType_node)
            print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

            kPackedDimensions += get_source_text(
                kEnumType_node.find({"tag": "kPackedDimensions"})
            )

            kEnumNameList_node = kEnumType_node.find({"tag": "kEnumNameList"})
            if kEnumNameList_node:
                parser.enums_proc(
                    "TOP",
                    get_source_text(kEnumNameList_node),
                    parser.package_name,
                    parser.class_name,
                )

            parser.parse_reg_wire_logic(
                "TOP",
                "TYPEDEF",
                "logic",
                f"{kPackedDimensions} {type_name}".strip(),
                parser.package_name,
                parser.class_name,
            )

        elif kStructType_node:
            parser.parse_struct_union(
                "STRUCT", "TOP", source_text, parser.package_name, parser.class_name
            )

            source_text = get_source_text(kStructType_node)

            # print(f"{indent_spaces()}Source text: '''{source_text}'''\n")
        elif kUnionType_node:
            parser.parse_struct_union(
                "UNION", "TOP", source_text, parser.package_name, parser.class_name
            )

            source_text = get_source_text(kUnionType_node)
            # print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

        else:
            parser.parse_reg_wire_logic(
                "TOP",
                "TYPEDEF",
                "logic",
                f"{kPackedDimensions} {type_name}",
                parser.package_name,
                parser.class_name,
            )


# verilog.y:3627 type_declaration
kTypeDeclaration = {
    # "kDataType": kDataType,
    "func": kTypeDeclaration_func,
}


def kParamDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    parser.param_proc("TOP", source_text, "", "", "module_body")


# verilog.y:3484 any_param_declaration
kParamDeclaration = {
    "func": kParamDeclaration_func,
}


def binding_typedef(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kDataType_text = ""
    kDataType_node = node.find({"tag": "kDataType"})
    if kDataType_node:
        kDataType_text = get_source_text(kDataType_node)

    kGateInstanceRegisterVariableList_text = ""
    kGateInstanceRegisterVariableList_node = node.find(
        {"tag": "kGateInstanceRegisterVariableList"}
    )
    if kGateInstanceRegisterVariableList_node:
        kGateInstanceRegisterVariableList_text = get_source_text(
            kGateInstanceRegisterVariableList_node
        )

    temp_line = kDataType_text + " " + kGateInstanceRegisterVariableList_text
    temp_line = re.sub(r"\s+", " ", source_text)
    temp_line = re.sub(r"^\s*", "", temp_line)
    temp_line = re.sub(r"\s*;\s*$", "", temp_line)

    temp_line_split_list = [kDataType_text, kGateInstanceRegisterVariableList_text]

    typedef_ref_regex = RE_TYPEDEF_DOUBLE_COLON.search(temp_line_split_list[0])
    typedef_ref_regex_double = RE_TYPEDEF_DOUBLE_DOUBLE_COLON.search(
        temp_line_split_list[0]
    )

    found_in_typedef = ""

    if typedef_ref_regex_double:  # If a package name is associated
        typedef_package = typedef_ref_regex_double.group(1)
        typedef_class = typedef_ref_regex_double.group(2)
        typedef_name = typedef_ref_regex_double.group(3)
    elif typedef_ref_regex:  # If a package name is associated
        if typedef_ref_regex.group(1) in list(parser.classes):
            typedef_package = "default"
            typedef_class = typedef_ref_regex.group(1)
            typedef_name = typedef_ref_regex.group(2)
        else:
            typedef_package = typedef_ref_regex.group(1)
            typedef_class = "default"
            typedef_name = typedef_ref_regex.group(2)
    else:  # No package referred
        typedef_package = "default"
        typedef_class = "default"
        typedef_name = temp_line_split_list[0]
        kUnqualifiedId_node = kDataType_node.find({"tag": "kUnqualifiedId"})
        if kUnqualifiedId_node:
            typedef_name = get_source_text(kUnqualifiedId_node)

    if typedef_package not in parser.packages:
        parser.load_import_or_include_file(
            "TOP", "IMPORT_COMMANDLINE", typedef_package + ".sv"
        )

    if typedef_name in parser.typedef_logics[typedef_package][typedef_class]:
        found_in_typedef = "LOGICS"
    elif typedef_name in parser.typedef_structs[typedef_package][typedef_class]:
        found_in_typedef = "STRUCTS"
    elif typedef_name in parser.typedef_unions[typedef_package][typedef_class]:
        found_in_typedef = "UNIONS"

    if found_in_typedef != "":
        typedef_equal_regex = RE_EQUAL_EXTRACT_SPACE.search(temp_line)

        if typedef_equal_regex:
            temp_line = typedef_equal_regex.group(1)
            temp_line = re.sub(r"\s+$", "", temp_line)
            temp_line_split_list = temp_line.split(" ", 1)

        parser.binding_typedef("TOP", "MANUAL", temp_line)

        bitdef_begin_regex = RE_SQBRCT_BEGIN.search(temp_line_split_list[1])

        # Remove packed bitdef after typedef
        if bitdef_begin_regex:
            parser.update_typedef_regs("logic", "MANUAL", bitdef_begin_regex.group(2))
        else:
            parser.update_typedef_regs("logic", "MANUAL", temp_line_split_list[1])

        if typedef_equal_regex:
            parser.parse_assignments(
                "wiredassign",
                temp_line_split_list[1] + " = " + typedef_equal_regex.group(2),
            )


# veilog.y:3525 data_declaration_or_module_instantiation instantiation_base
def kDataDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kInstantiationBase_node = node.find({"tag": "kInstantiationBase"})
    if kInstantiationBase_node:
        kDataTypePrimitive_node = kInstantiationBase_node.find(
            {"tag": "kDataTypePrimitive"}
        )
        if kDataTypePrimitive_node:
            kDataTypePrimitive_text = kDataTypePrimitive_node.text
            others_text = ""
            kDataTypePrimitive_list = kDataTypePrimitive_text.split()
            if len(kDataTypePrimitive_list) > 1:
                kDataTypePrimitive_text = kDataTypePrimitive_list[0]
                others_text = " ".join(kDataTypePrimitive_list[1:])
            kPackedDimensions = get_source_text(
                kInstantiationBase_node.find({"tag": "kPackedDimensions"})
            )

            kGateInstanceRegisterVariableList_node = kInstantiationBase_node.find(
                {"tag": "kGateInstanceRegisterVariableList"}
            )
            if kGateInstanceRegisterVariableList_node:
                SymbolIdentifier_names = []
                kRegisterVariable_nodes = (
                    kGateInstanceRegisterVariableList_node.find_all(
                        {"tag": "kRegisterVariable"}
                    )
                )
                SymbolIdentifier_names = [
                    get_source_text(nd) for nd in kRegisterVariable_nodes
                ]

                if len(kRegisterVariable_nodes) > 0:
                    parser.parse_reg_wire_logic(
                        "TOP",
                        "MANUAL",
                        kDataTypePrimitive_text,
                        others_text
                        + " "
                        + kPackedDimensions
                        + " "
                        + ",".join(SymbolIdentifier_names),
                        "",
                        "",
                    )
        else:
            kDataType_node = kInstantiationBase_node.find({"tag": "kDataType"})
            if kDataType_node:
                kGateInstance_node = node.find({"tag": "kGateInstance"})
                if kGateInstance_node:
                    kGateInstance_text = get_source_text(kGateInstance_node)
                    # print(f"{indent_spaces()}Source text: '''{kGateInstance_text}'''\n")

                    manual_instance_line = get_source_text(node)
                    kUnqualifiedId_node = kDataType_node.find({"tag": "kUnqualifiedId"})
                    if kUnqualifiedId_node is not None:
                        for child in kUnqualifiedId_node.children:
                            if not isinstance(child, TokenNode):
                                continue

                            if child.tag == "SymbolIdentifier":
                                submod_name = child.text

                                for sn in [submod_name, submod_name.lower()]:
                                    submod_file_with_path = parser.find_manual_submod(
                                        parser.gen_dependencies, sn
                                    )
                                    if submod_file_with_path != 0:
                                        break

                                if submod_file_with_path != 0:
                                    parser.parse_manual_instance(
                                        manual_instance_line,
                                        submod_file_with_path,
                                        submod_name,
                                        submod_name,
                                    )
                                else:
                                    parser.dbg(
                                        "\nErrror: Unable to find the submodule "
                                        + submod_name
                                        + " in verilog/systemverilog format under following dirs"
                                    )
                                    parser.dbg("  List of search directories")
                                    print(
                                        "\nError: Unable to find the submodule "
                                        + submod_name
                                        + " in verilog/systemverilog format under following dirs"
                                    )
                                    print("  List of search directories")

                                    for dir in parser.incl_dirs:
                                        parser.dbg("    " + str(dir))
                                        print("    " + str(dir))
                                    sys.exit(1)
                            elif child.tag == "MacroIdentifier":
                                submod_name = parser.get_tick_defval(child.text[1:])
                else:
                    binding_typedef(node, map, parser)


kDataDeclaration = {
    "func": kDataDeclaration_func,
}


def kContinuousAssignmentStatement_func(node, map, parser):
    source_text = get_source_text(node)
    RE_LHS_RHS_WADDR = re.compile(
        r"assign\s+(?P<lhs_sig>w_addr_[0-9])\s*=\s*w_addr\s*(-\s*[0-9]+\s*)?;"
    )
    match = RE_LHS_RHS_WADDR.search(source_text)
    if match:
        lhs_sig = match.group("lhs_sig")
        rhs_sig = "w_addr"
        parser.match_lhs_rhs[lhs_sig] = rhs_sig

    RE_LHS_RHS_RADDR = re.compile(
        r"assign\s+(?P<lhs_sig>r_addr_[0-9])\s*=\s*bank_[0-9]_rea\s*\?\s*\(\s*r_addr"
    )
    match = RE_LHS_RHS_RADDR.search(source_text)
    if match:
        lhs_sig = match.group("lhs_sig")
        rhs_sig = "r_addr"
        parser.match_lhs_rhs[lhs_sig] = rhs_sig

    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    if parser.always_for_loop_count > 0:
        for c_for_idx in parser.always_for_loops.keys():
            search_var = "\\b" + parser.always_for_loops[c_for_idx]["for_var"] + "\\b"
            replace_var = (
                str(parser.always_for_loops[c_for_idx]["end_val"])
                + ":"
                + str(parser.always_for_loops[c_for_idx]["start_val"])
            )
            source_text = re.sub(search_var, replace_var, source_text)

    assign_regex = RE_ASSIGN.search(source_text)
    if assign_regex:
        parser.parse_assignments("assign", assign_regex.group(1))


# verilog.y:5676 continuous_assign:  TK_assign drive_strength_opt delay3_opt cont_assign_list ';'
kContinuousAssignmentStatement = {
    "func": kContinuousAssignmentStatement_func,
}


def kGenvarDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    SymbolIdentifier_nodes = node.find_all({"tag": "SymbolIdentifier"})
    for SymbolIdentifier_node in SymbolIdentifier_nodes:
        parser.genvars.append(SymbolIdentifier_node.text)


kGenvarDeclaration = {
    "func": kGenvarDeclaration_func,
}

# verilog.y:5736 always_construct : always_any statement
kAlwaysStatement.update(statement_item)


def kNetDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kPackedDimensions = ""
    kPackedDimensions_node = node.find({"tag": "kPackedDimensions"})
    if kPackedDimensions_node:
        kPackedDimensions = get_source_text(kPackedDimensions_node)

    kNetDeclarationAssignment_nodes = node.find_all(
        {"tag": "kNetDeclarationAssignment"}
    )
    for kNetDeclarationAssignment_node in kNetDeclarationAssignment_nodes:
        source_text = get_source_text(kNetDeclarationAssignment_node)

        if parser.always_for_loop_count > 0:
            for c_for_idx in parser.always_for_loops.keys():
                search_var = (
                    "\\b" + parser.always_for_loops[c_for_idx]["for_var"] + "\\b"
                )
                replace_var = (
                    str(parser.always_for_loops[c_for_idx]["end_val"])
                    + ":"
                    + str(parser.always_for_loops[c_for_idx]["start_val"])
                )
                source_text = re.sub(search_var, replace_var, source_text)

        line_split_list = source_text.split("=", 1)

        if parser.parsing_format == "verilog":
            parser.parse_reg_wire_logic(
                "TOP",
                "MANUAL",
                "wire",
                kPackedDimensions + " " + line_split_list[0],
                "",
                "",
            )
        else:
            parser.parse_reg_wire_logic(
                "TOP",
                "MANUAL",
                "logic",
                kPackedDimensions + " " + line_split_list[0],
                "",
                "",
            )
        parser.parse_assignments(
            "wiredassign",
            line_split_list[0] + kPackedDimensions + " = " + line_split_list[1],
        )

    kNetVariable_nodes = node.find_all({"tag": "kNetVariable"})
    for kNetVariable_node in kNetVariable_nodes:
        net_name = kNetVariable_node.find({"tag": "SymbolIdentifier"}).text
        if parser.parsing_format == "verilog":
            parser.parse_reg_wire_logic(
                "TOP",
                "MANUAL",
                "wire",
                kPackedDimensions + " " + net_name,
                "",
                "",
            )
        else:
            parser.parse_reg_wire_logic(
                "TOP",
                "MANUAL",
                "reg",
                kPackedDimensions + " " + net_name,
                "",
                "",
            )


# verilog.y:5552 net_declaration
kNetDeclaration = {
    "func": kNetDeclaration_func,
}

kGenerateItemList = {}


def kGenerateBlock_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kGenerateBlock = {
    "kGenerateItemList": kGenerateItemList,
    "func": kGenerateBlock_func,
}


def kLoopGenerateConstruct_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kLoopGenerateConstruct = {
    "kLoopHeader": kLoopHeader,
    "kGenerateBlock": kGenerateBlock,
    "func": kLoopGenerateConstruct_func,
}


def kGenerateItemList_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:6040 generate_item_list
# kGenerateItemList will update with kModuleItemList later
kGenerateItemList["kLoopGenerateConstruct"] = kLoopGenerateConstruct
kGenerateItemList["func"] = kGenerateItemList_func
kGenerateItemList.update(statement_item)
kGenerateItemList["kDataDeclaration"] = kDataDeclaration


def kGenerateRegion_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


# verilog.y:5671 generate_region
kGenerateRegion = {
    "kGenerateItemList": kGenerateItemList,
    "func": kGenerateRegion_func,
}


def kPreprocessorInclude_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    TK_StringLiteral_node = node.find({"tag": "TK_StringLiteral"})
    if TK_StringLiteral_node:
        include_file = TK_StringLiteral_node.text
        parser.load_import_or_include_file("TOP", "INCLUDE", include_file.strip('"'))


kPreprocessorInclude = {
    "func": kPreprocessorInclude_func,
}


def kGenerateIfHeader_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kExpression_nodes = node.find_all({"tag": "kExpression"})
    for kExpression_node in kExpression_nodes:
        expression_str = get_source_text(kExpression_node)
        expression_str = re.sub(r"\s+", "", expression_str)
        parser.parse_conditions(expression_str)


kGenerateIfHeader = {
    "func": kGenerateIfHeader_func,
}


def kGenerateIfClause_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kGenerateItemList_nodes = node.find_all({"tag": "kGenerateItemList"})
    for kGenerateItemList_node in kGenerateItemList_nodes:
        parser.sv_parser.traverse_veripy_nodes(
            kGenerateItemList_node, kGenerateItemList, parser
        )


kGenerateIfClause = {
    # "kGenerateIfHeader": kGenerateIfHeader, # TODO - old parser seems to ignore it
    # "kGenerateIfBody": kGenerateBlock,
    "func": kGenerateIfClause_func,
}


def kGenerateElseClause_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    kGenerateItemList_nodes = node.find_all({"tag": "kGenerateItemList"})
    for kGenerateItemList_node in kGenerateItemList_nodes:
        parser.sv_parser.traverse_veripy_nodes(
            kGenerateItemList_node, kGenerateItemList, parser
        )


kGenerateElseClause = {
    # "kGenerateElseBody": kGenerateBlock,
    "func": kGenerateElseClause_func,
}


def kConditionalGenerateConstruct_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kConditionalGenerateConstruct = {
    "kGenerateIfClause": kGenerateIfClause,
    "kGenerateElseClause": kGenerateElseClause,
    "func": kConditionalGenerateConstruct_func,
}

# verilog.y:5830 module_or_generate_item
# : parameter_override
# { $$ = std::move($1);}
# | gate_instantiation
# { $$ = std::move($1);}
# | data_declaration_or_module_instantiation
# { $$ = std::move($1);}
# | net_type_declaration
# { $$ = std::move($1);}
# | package_import_declaration
# { $$ = std::move($1);}
# | any_param_declaration
# { $$ = std::move($1);}
# | type_declaration
# { $$ = std::move($1);}
# | let_declaration
# { $$ = std::move($1);}
# / *includes
# module_instantiation, and most
# other
# instantiations * /
# | module_common_item
# { $$ = std::move($1);}
# ;

# verilog.y:5852 module_item, non_port_module_item(5915),
# module_or_generate_item (5830), module_common_item(5756)
# module_or_generate_item_declaration(5790)
kModuleItemList = {
    "kPackageImportDeclaration": kPackageImportDeclaration,  # 202307
    "kParamDeclaration": kParamDeclaration,  # 20230801
    "kTypeDeclaration": kTypeDeclaration,  # 20230809
    "kDataDeclaration": kDataDeclaration,  # 20230802 20230809
    "kGenerateRegion": kGenerateRegion,  # 20230808
    "kContinuousAssignmentStatement": kContinuousAssignmentStatement,  # 202307
    "kGenvarDeclaration": kGenvarDeclaration,  # 20230801
    "kAlwaysStatement": kAlwaysStatement,  # 202307
    "kNetDeclaration": kNetDeclaration,  # 20230802
    "kPreprocessorInclude": kPreprocessorInclude,
    "kConditionalGenerateConstruct": kConditionalGenerateConstruct,
    "kLoopGenerateConstruct": kLoopGenerateConstruct,
}
kGenerateItemList.update(kModuleItemList)


def kPackageImportList_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")


kPackageImportList = {
    "kPackageImportDeclaration": kPackageImportDeclaration,
    "func": kPackageImportList_func,
}


# verilog.y:5487 module_parameter_port
def kFormalParameterListDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    # kFormalParameterList_node = node.find({"tag": "kFormalParameterList"})
    # if kFormalParameterList_node:
    #     source_text = get_source_text(kFormalParameterList_node)
    #     parser.param_proc("TOP", source_text, "", "")


# verilog.y:5468 module_parameter_port_list_opt
kFormalParameterListDeclaration = {
    "func": kFormalParameterListDeclaration_func,
}

kPortDeclarationList = {}


def kModuleHeader_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    module_name = node.find({"tag": "SymbolIdentifier"}).text
    parser.module_name = module_name
    parser.module_found = 1

    kFormalParameterList_node = node.find({"tag": "kFormalParameterList"})
    if kFormalParameterList_node:
        source_text = get_source_text(kFormalParameterList_node)
        parser.param_proc("TOP", source_text, "", "", "module_header")

    kPortDeclarationList_node = node.find({"tag": "kPortDeclarationList"})
    if kPortDeclarationList_node is None:
        return

    parser.manual_ports = 1
    kPortDeclaration_nodes = kPortDeclarationList_node.find_all(
        {"tag": "kPortDeclaration"}
    )
    for kPortDeclaration_node in kPortDeclaration_nodes:
        source_text = get_source_text(kPortDeclaration_node)
        manual_input_regex = RE_DECLARE_INPUT.search(source_text)
        manual_output_regex = RE_DECLARE_OUTPUT.search(source_text)

        if manual_input_regex:  # all other input
            parser.parse_ios(
                "TOP",
                "MANUAL",
                "input",
                manual_input_regex.group(1),
            )
        elif manual_output_regex:  # all other input
            parser.parse_ios(
                "TOP",
                "MANUAL",
                "output",
                manual_output_regex.group(1),
            )


kModuleHeader = {
    "kPackageImportList": kPackageImportList,
    "kFormalParameterListDeclaration": kFormalParameterListDeclaration,
    "func": kModuleHeader_func,
}

# verilog.y:5403 module_or_interface_declaration
kModuleDeclaration = {
    "kModuleHeader": kModuleHeader,
    "kModuleItemList": kModuleItemList,
    "endmodule": None,
}

kPackageItemList = {
    "kParamDeclaration": kParamDeclaration,  # 20230801
    "kTypeDeclaration": kTypeDeclaration,  # 20230809
}


def kPackageDeclaration_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")

    package_name = node.find({"tag": "SymbolIdentifier"}).text

    if package_name not in parser.typedef_enums:
        parser.typedef_enums[package_name] = {}
        parser.typedef_enums[package_name]["default"] = {}

    if package_name not in parser.typedef_logics:
        parser.typedef_logics[package_name] = {}
        parser.typedef_logics[package_name]["default"] = {}

    if package_name not in parser.typedef_structs:
        parser.typedef_structs[package_name] = {}
        parser.typedef_structs[package_name]["default"] = {}

    if package_name not in parser.typedef_unions:
        parser.typedef_unions[package_name] = {}
        parser.typedef_unions[package_name]["default"] = {}

    parser.package_name = package_name
    if package_name not in parser.packages:
        parser.packages.append(package_name)


def kPackageDeclaration_post_func(node, map, parser):
    source_text = get_source_text(node)
    if parser.debug:
        print(f"{indent_spaces()}Source text: '''{source_text}'''\n")
    parser.package_name = "default"


kPackageDeclaration = {
    "kPackageItemList": kPackageItemList,
    "func": kPackageDeclaration_func,
    "post_func": kPackageDeclaration_post_func,
}

kDescriptionList = {
    "kModuleDeclaration": kModuleDeclaration,
    "kPreprocessorInclude": kPreprocessorInclude,
    "kPackageDeclaration": kPackageDeclaration,
}

vp_map = {
    "kDescriptionList": kDescriptionList,
}
