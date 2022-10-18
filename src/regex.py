####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################
################################################################################
#                                                                              #
#     Author: Baheerathan Anandharengan                                        #
#     E-Mail: baheerathan@meta.com                                               #
#                                                                              #
#     Key Contributor: Dheepak Jayaraman                                       #
#     E-Mail: dheepak@meta.com                                                   #
#                                                                              #
################################################################################
import re

################################################################################
# All the regular expressions
################################################################################
RE_BLOCK_COMMENT_BEGIN_START = re.compile(r"^\s*\/\*")
RE_BLOCK_COMMENT_BEGIN = re.compile(r"\/\*")
RE_BLOCK_COMMENT_END = re.compile(r"\*\/\s*(.*)\s*")

## Do not use for performance reasons - use remove_single_line_comment() instead
# RE_BLOCK_COMMENT_SINGLE_LINE = re.compile(r"(.*)\/\*(.*)\*\/(.*)")
RE_SINGLE_COMMENT_BEGIN_START = re.compile(r"^\s*\/\/")
RE_SINGLE_LINE_COMMENT = re.compile(r"\/\/(.*)")
RE_EMPTY_LINE = re.compile(r"^\s*$")

RE_HASH_INCLUDE = re.compile(r"^\s*#include\s+[\"]{0,1}([A-Za-z0-9_\.]+)[\"]{0,1}\s*$")
RE_HASH_DEFINE = re.compile(r"^\s*#define\s+(.*)\s*$")
RE_HASH_UNDEF = re.compile(r"^\s*#undef\s+(\w*)\s*$")
RE_HASH_IFDEF = re.compile(r"^\s*#ifdef\s+(.*)\s*$")
RE_HASH_IFNDEF = re.compile(r"^\s*#ifndef\s+(.*)\s*$")
RE_HASH_ELIF = re.compile(r"^\s*#elif\s+(.*)\s*$")
RE_HASH_ELSE = re.compile(r"^\s*#else.*$")
RE_HASH_ENDIF = re.compile(r"^\s*#endif.*$")
RE_HASH_IFDEF_STR = re.compile(r"^\w*$")
RE_HASH_DEF = re.compile(r"^\s*(\w+)\s+(.+)$")
RE_HASH_DEF_WO_VAL = re.compile(r"^\s*(\w+)$")

RE_IMPORT_COLONS = re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)\s*::(.*)$")
RE_IMPORT_INMOD_SEMICOLON = re.compile(
    r"(.*)\s+import\s+([A-Za-z0-9_\.]+)\s*::\s*[\*\w]+\s*;(.*)$"
)
RE_IMPORT_INMOD_COMMA = re.compile(
    r"(.*)\s+import\s+([A-Za-z0-9_\.]+)\s*::\s*[\*\w]+\s*,(.*)$"
)
RE_IMPORT = re.compile(r"^\s*import\s+([A-Za-z0-9_\.]+)\s*[;]\s*$")
RE_PACKAGE = re.compile(r"^\s*package\s+([A-Za-z0-9_\.]+)\s*[;]\s*$")
RE_VIRTUAL_CLASS = re.compile(r"^\s*virtual\s+class\s+([A-Za-z0-9_\.]+)\s*[;]\s*$")
RE_CLASS = re.compile(r"^\s*class\s+([A-Za-z0-9_\.]+)\s*[;]\s*$")
RE_ENDCLASS = re.compile(r"^\s*endclass\s*$")
RE_TICK_INCLUDE = re.compile(r"^\s*`include\s+\"([A-Za-z0-9_\.]+)\"\s*$")
RE_TICK_DEFINE = re.compile(r"^\s*`define\s+(.*)$")
RE_TICK_UNDEF = re.compile(r"^\s*`undef\s+(\w*)\s*$")
RE_TICK_IFDEF = re.compile(r"^\s*`ifdef\s+(.*)$")
RE_TICK_IFNDEF = re.compile(r"^\s*`ifndef\s+(.*)$")
RE_TICK_ELSIF = re.compile(r"^\s*`elsif\s+(.*)$")
RE_TICK_ELSE = re.compile(r"^\s*`else.*$")
RE_TICK_ENDIF = re.compile(r"^\s*`endif.*$")
RE_TICK_IFDEF_STR = re.compile(r"^\w*$")
RE_TICK_DEF_WO_VAL = re.compile(r"^\s*(\w+)$")
RE_TICK_DEF = re.compile(r"^\s*(\w+)\s+(.+)$")
RE_HASH = re.compile(r"(.+)#(.+)")
RE_DOUBLE_HASH = re.compile(r"(\w+)#(\w+)#(\w+)")
RE_TRIPLE_HASH = re.compile(r"(.*)###(.*)")
RE_DOT = re.compile(r"(\w*)\.(.*)")
RE_TYPEDEF_DOUBLE_DOUBLE_COLON_BEFORE_BITDEF = re.compile(
    r"^(\w+)::(\w+)::(\w+)\s*\[(.*)"
)
RE_TYPEDEF_DOUBLE_COLON_BEFORE_BITDEF = re.compile(r"^(\w+)::(\w+)\s*\[(.*)")
RE_TYPEDEF_BEFORE_BITDEF = re.compile(r"^(\w+)\s*\[(.*)")
RE_TYPEDEF_DOUBLE_DOUBLE_COLON = re.compile(r"^(\w+)::(\w+)::(.*)")
RE_TYPEDEF_DOUBLE_COLON = re.compile(r"^(\w*)::(.*)")
RE_PORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON = re.compile(r"^(\w+)::(\w+)::(\w+)\b")
RE_PORT_WITH_TYPEDEF_DOUBLE_COLON = re.compile(r"^(\w*)::(\w+)\b")
RE_TYPEDEF_ENUM_EXTRACT = re.compile(r"^\s*typedef\s+enum\s+(.*)\s*\{(.*)\}\s+(.*)\s*")
RE_TYPEDEF_ENUM = re.compile(r"^\s*typedef\s+enum\s+(.*)")
RE_ENUM_IMPLICIT_RANGE = re.compile(r"(\w*)\[([0-9]*):([0-9]*)\]")
RE_ENUM_IMPLICIT_COUNT = re.compile(r"(\w*)\[([0-9]*)\]")
RE_TYPEDEF_LOGIC = re.compile(r"^\s*typedef\s+logic\b\s*(.*)")
RE_TYPEDEF_STRUCT_NOSPACE = re.compile(r"^\s*typedef\s+struct\b")
RE_TYPEDEF_STRUCT_CHECK = re.compile(r"^\s*typedef\s+struct\s+(.*)")
RE_TYPEDEF_STRUCT_PACKED_EXTRACT = re.compile(
    r"^\s*typedef\s+struct\s+(.*)\s*\{(.*)\}\s*([a-zA-Z_0-9]*)\s*;"
)
RE_TYPEDEF_UNION_PACKED_EXTRACT = re.compile(
    r"^\s*typedef\s+union\s+(.*)\s*\{(.*)\}\s*([a-zA-Z_0-9]*)\s*;"
)
RE_TYPEDEF_STRUCT_EXTRACT = re.compile(
    r"^\s*typedef\s+struct\s*\{(.*)\}\s*([a-zA-Z_0-9]*)\s*;"
)
RE_TYPEDEF_UNION_EXTRACT = re.compile(
    r"^\s*typedef\s+union\s*\{(.*)\}\s*([a-zA-Z_0-9]*)\s*;"
)
RE_TYPEDEF_UNION_CHECK = re.compile(r"^\s*typedef\s+union\s+(.*)")
RE_TYPEDEF_UNION_NOSPACE = re.compile(r"^\s*typedef\s+union\b")
RE_PACKED_ARRAY = re.compile(r"\]\s*\[")
RE_CLOSING_BRACE = re.compile(r"\}.*;")
RE_TYPEDEF_NO_BITDEF_NO_DEPTH = re.compile(r"\s*([\w:]+)\s+([\w,]+)\s*$")
RE_TYPEDEF_BITDEF_NO_DEPTH = re.compile(r"\s*([\w:]+)\s*\[(.*)\]\s*([\w,]+)\s*$")
RE_TYPEDEF_NO_BITDEF_DEPTH = re.compile(r"\s*([\w:]+)\s+([\w,]+)\s*\[(.*)\]\s*$")
RE_TYPEDEF_BITDEF_DEPTH = re.compile(
    r"\s*([\w:]+)\s*\[(.*)\]\s*([\w,]+)\s*\[(.*)\]\s*$"
)
RE_SUBPORT_WITH_TYPEDEF_DOUBLE_DOUBLE_COLON = re.compile(
    r"^(\w+)::(\w+)::(\w+)\s*\[(.*)"
)
RE_SUBPORT_WITH_TYPEDEF_DOUBLE_COLON = re.compile(r"^(\w+)::(\w+)\s*\[(.*)")
RE_PARAM = re.compile(r"^\s*parameter\s*")
RE_LOCALPARAM = re.compile(r"^\s*localparam\s*")
RE_PARAM_SPLIT = re.compile(r"(.*)=(.*)")
RE_HASH_SPLIT = re.compile(r"(.*)#(.*)")
RE_SEMICOLON = re.compile(r";")
RE_COLON = re.compile(r"(.*):(.*)")
RE_DOUBLE_COLON = re.compile(r"(.*)::(.*)")
RE_DOUBLE_DOUBLE_COLON = re.compile(r"(.*)::(.*)::(.*)")
RE_SPACE_BW = re.compile(r"(.+)\s+(.+)")
RE_OPEN_CURLY = re.compile(r"{")
RE_COMMA = re.compile(r",")
RE_IF_ITER_CHECK = re.compile(r"iter\s*=\s*\[(.*)\]\s*")
RE_IF_PREFIX_ITER_CHECK = re.compile(r"prefix_iter\s*=\s*\[(.*)\]\s*")
RE_IF_SUFFIX_ITER_CHECK = re.compile(r"suffix_iter\s*=\s*\[(.*)\]\s*")
RE_EQUAL_EXTRACT = re.compile(r"(.*)=(.*)")
RE_EQUAL_EXTRACT_SPACE = re.compile(r"(.*)\s*=\s*(.*)")
RE_CLOSE_SQBRCT_WITH_DOT = re.compile(r"(.*)\]\.(.*)")
RE_OPEN_SQBRCT = re.compile(r"\[")
RE_OPEN_SQBRCT_BITDEF = re.compile(r"(.*)\[(.*)")
RE_CLOSE_SQBRCT_END = re.compile(r"(.*)\]\s*$")
RE_EXTRACT_DEPTH = re.compile(r"(.*)\[(.*)\](.*)$")
RE_SQBRCT_BEGIN = re.compile(r"^\s*\[(.*)\]\s*(.*)$")
RE_CLOSE_SQBRCT = re.compile(r"\]")
RE_CLOSE_2D_SQBRCT = re.compile(r"\]\[")
RE_NUM_TICK = re.compile(r"'")
RE_DEFINE_TICK = re.compile(r"`")
RE_DEFINE_TICK_BEGIN = re.compile(r"^\s*`")
RE_DEFINE_TICK_EXTRACT = re.compile(r"^\s*`(\w+)")
RE_CONSTANT = re.compile(r"^[0-9]*$")
RE_RESET_VAL = re.compile(r"^(.*<)([s0-9A-Za-z'_]+)(=.*)$")
RE_MINUS1 = re.compile(r"-\s*1$")

RE_PYTHON_BLOCK_BEGIN = re.compile(
    r"^(\s*)&[Pp][Yy][Tt][Hh][Oo][Nn][Bb][Ee][Gg][Ii][Nn](\s*);*$"
)
RE_PYTHON_BLOCK_END = re.compile(r"^(\s*)&[Pp][Yy][Tt][Hh][Oo][Nn][Ee][Nn][Dd](\s*);*$")
RE_PYTHON_SINGLE_LINE = re.compile(r"^(\s*)&[Pp][Yy][Tt][Hh][Oo][Nn](\s+)(.*);*$")
RE_PYTHON_VARIABLE = re.compile(r"\$\${(.*?)}")
RE_HASH_VARIABLE_SYNTAX = re.compile(r"#{\w+}")
RE_HASH_VARIABLE = re.compile(r"#{(\w+)}")

RE_POST_PYTHON_BLOCK_BEGIN = re.compile(
    r"^(\s*)&[Pp][Yy][Tt][Hh][Oo][Nn][Pp][Oo][Ss][Tt][Bb][Ee][Gg][Ii][Nn](\s*)"
)
RE_POST_PYTHON_BLOCK_END = re.compile(
    r"^(\s*)&[Pp][Yy][Tt][Hh][Oo][Nn][Pp][Oo][Ss][Tt][Ee][Nn][Dd](\s*)"
)
RE_TICK_CHECK = re.compile(r"(.*)`$")
RE_TICK_DEF_CHECK_BITDEF = re.compile(r"\s*(.*)\s*:\s*(.*)\s*")

RE_MODULE_DECLARATION = re.compile(r"^\s*module\s+(\w*)\s*(.*)")
RE_MODULE_PARAM = re.compile(r"#\s*\(\s*parameter\s+(.*)\s*\)\s*\(\s*(.*)")
RE_MODULE_NOPARAM = re.compile(r"#\s*\(\s*(.*)\s*\)\s*\(\s*(.*)")
RE_END_MODULE_DECLARATION = re.compile(r"^\s*endmodule")
RE_FORCE = re.compile(r"^\s*&[Ff][Oo][Rr][Cc][Ee]\s+(.*)")
RE_FORCE_BIND = re.compile(r"^\s*[Bb][Ii][Nn][Dd]\s+(.*)\s*")
RE_FORCE_WIDTH = re.compile(r"^\s*[Ww][Ii][Dd][Tt][Hh]\s+(.*)\s*")
RE_WIDTH_SLASH = re.compile(r"\/(.*)\/\s+(.*)\s*")
RE_REGEX_SLASH = re.compile(r"^\/(.*)\/$")
RE_CONNECT_SLASH = re.compile(r"\/(.*)\/\s+\/(.*)\/")
RE_FORCE_INTERNAL = re.compile(r"^\s*[Ii][Nn][Tt][Ee][Rr][Nn][Aa][Ll]\s+(.*)\s*")
RE_FORCE_OTHERS = re.compile(r"^\s*(\w+)\s+(.*)")
RE_DECLARE_INPUT = re.compile(r"^\s*\binput\b\s+(.*)")
RE_DECLARE_OUTPUT = re.compile(r"^\s*\boutput\b\s+(.*)")
RE_DECLARE_INOUT = re.compile(r"^\s*\binout\b\s+(.*)")
RE_DECLARE_WIRE = re.compile(r"^\s*\bwire\b\s*(.*)")
RE_WIRE_ASSIGNMENT = re.compile(r"^\s*\bwire\b\s+(\w+)\s*=\s*(.*)")
RE_WIRE_ASSIGNMENT_BITDEF = re.compile(r"^\s*\bwire\b\s+\[.*\]\s+(\w+)\s*=\s*(.*)")
RE_DECLARE_REG = re.compile(r"^\s*\breg\b\s*(.*)")
RE_DECLARE_LOGIC = re.compile(r"^\s*\blogic\b\s*(.*)")
RE_DECLARE_SIGNED = re.compile(r"\s*\bsigned\b\s*(.*)")
RE_DECLARE_BITDEF = re.compile(r"\s*\[(.*)\]\s*(\w.*)")
RE_DECLARE_PACKED_BITDEF = re.compile(r"^\s*([\w:]+)\s*\[(.*)\]\s*(\w.*)")
RE_DECLARE_NAME = re.compile(r"\s*(\w+)\s*;")
RE_DECLARE_DEPTH = re.compile(r"\s*([\w:\s]*)\s*\[(.*)\]\s*[;]*\s*")
RE_ASSIGN = re.compile(r"^\s*\bassign\b\s*(.*)")
RE_ALWAYS = re.compile(r"^\s*\balways\b\s*(.*)")
RE_ALWAYS_FF = re.compile(r"^\s*\balways_ff\b\s*(.*)")
RE_ALWAYS_COMB = re.compile(r"^\s*\balways_comb\b\s*(.*)")
RE_OPEN_CURLY_BRACKET = re.compile(r"^\s*{")
RE_OPEN_WORD_CHAR = re.compile(r"^\s*\w")
RE_UNIQUE_CASE = re.compile(r"^\s*\bunique\s+case[zx]?\b(.*)")
RE_CASE = re.compile(r"^\s*\bcase\b(.*)")
RE_CASEZ = re.compile(r"^\s*\bcasez\b(.*)")
RE_CASEX = re.compile(r"^\s*\bcasex\b(.*)")
RE_ENDCASE = re.compile(r"^\s*\bendcase\b(.*)")
RE_CASE_EXPRESSION = re.compile(r"###")
RE_EMPTY_CASE_EXPRESSION = re.compile(r"###\s*;")
RE_IF = re.compile(r"^\s*\bif\b(.*)")
RE_ELSEIF = re.compile(r"^\s*\belse\s+if\b(.*)")
RE_ELSE = re.compile(r"^\s*\belse\b(.*)")
RE_BEGIN_BEGIN = re.compile(r"^\s*\bbegin\b(.*)\s*")
RE_A2Z_START = re.compile(r"^\s*[A-Za-z]")
RE_BEGIN_BEGIN_WITH_LABEL = re.compile(r"^\s*\bbegin\s*:(\w+)\b(.*)\s*")
RE_WITH_LABEL = re.compile(r"^\s*:\s*(\w+)\b(.*)\s*")
RE_BEGIN = re.compile(r"\bbegin\b(.*)\s*")
RE_BEGIN_NO_GROUP = re.compile(r"\bbegin\b")
RE_BEGIN_ONLY = re.compile(r"\bbegin\b\s*")
RE_END = re.compile(r"^\s*\bend\b\s*(.*)")
RE_END_ONLY = re.compile(r"^\s*\bend\b\s*")
RE_BEGIN_IN_BEGIN = re.compile(r"^\s*begin\b")
RE_END_IN_BEGIN = re.compile(r"^\s*end\b")
RE_IF_IN_BEGIN = re.compile(r"^\s*\bif\b")
RE_ELSEIF_IN_BEGIN = re.compile(r"^\s*\belse\s*if\b")
RE_ELSE_IN_BEGIN = re.compile(r"^\s*\belse\b")
RE_AMBERSAND_IN_BEGIN = re.compile(r"^\s*&")
RE_MANUAL_MODULE = re.compile(r"^\s*([\w`]+)\s+")
RE_MANUAL_MODULE_END = re.compile(r"^\s*([\w`]+)\s*$")
RE_POSEDGE = re.compile(r"\bposedge\b")
RE_NEGEDGE = re.compile(r"\bnegedge\b")
RE_LABEL_END = re.compile(r"^\s*:\s*\w+$")
RE_LABEL = re.compile(r"^\s*:\s*\w+\s+")
RE_TASK = re.compile(r"^\s*task\s+")
RE_SYS_TASK = re.compile(
    r"^\s*\$[fs]?(display|strobe|write|monitor|close|scan|read|seek|flush|eof|open|format|get|unget|rewind|tell|error|dump)",
    re.IGNORECASE,
)

RE_FUNCTION = re.compile(r"^\s*function\s+")
RE_FUNCTION_NAME1 = re.compile(r"\s+(\w*)\s*;")
RE_FUNCTION_NAME2 = re.compile(r"\s+(\w*)\s*\(")

RE_ENDFUNCTION = re.compile(r"^\s*endfunction")
RE_ENDTASK = re.compile(r"^\s*endtask")
RE_INT = re.compile(r"^\s*int\s+")
RE_INT_EXTRACT = re.compile(r"^\s*int\s+(.*);")
RE_INTEGER = re.compile(r"^\s*integer\s+")
RE_INTEGER_EXTRACT = re.compile(r"^\s*integer\s+(.*);")
RE_FORLOOP_INT_EXTRACT = re.compile(r"^\s*int\s+(\w+)\s*=\s*(.*)")
RE_FORLOOP_INTEGER_EXTRACT = re.compile(r"^\s*integer\s+(\w+)\s*=\s*(.*)")
RE_GENVAR = re.compile(r"^\s*genvar\s+")
RE_GENVAR_EXTRACT = re.compile(r"^\s*genvar\s+(.*);")
RE_GENERATE = re.compile(r"^(\s*)generate")
RE_GENERATE_FOR = re.compile(r"^\s*for\s*\(")
RE_GENERATE_FOR_EXTRACT = re.compile(r"^\s*for\s*\(\s*(.*)\s*;\s*(.*)\s*;\s*(.*)\s*\)")
RE_FOR = re.compile(r"^\s*for\b\s*(.*)")
RE_FOR_EXTRACT = re.compile(r"^\s*\(\s*(.*)\s*;\s*(.*)\s*;\s*(.*)\s*\)")
RE_ENDGENERATE = re.compile(r"^\s*endgenerate")
RE_ASSERT_PROPERTY = re.compile(r"^\s*assert\s+property")
RE_COMMENTED_SKIP_BEGIN = re.compile(
    r"^\s*\/\/\s*&[Bb][Ee][Gg][Ii][Nn][Ss][Kk][ii][Pp]"
)
RE_COMMENTED_SKIP_END = re.compile(r"^\s*\/\/\s*&[Ee][Nn][Dd][Ss][Kk][Ii][Pp]")
RE_SKIP_BEGIN = re.compile(r"^\s*&[Bb][Ee][Gg][Ii][Nn][Ss][Kk][ii][Pp]")
RE_SKIP_END = re.compile(r"^\s*&[Ee][Nn][Dd][Ss][Kk][Ii][Pp]")
RE_SKIP_IFDEF_BEGIN = re.compile(
    r"^\s*&[Bb][Ee][Gg][Ii][Nn][Ss][Kk][ii][Pp][Ii][Ff][Dd][Ee][Ff]"
)
RE_SKIP_IFDEF_END = re.compile(r"^\s*&[Ee][Nn][Dd][Ss][Kk][Ii][Pp][Ii][Ff][Dd][Ee][Ff]")
RE_PARSER_OFF = re.compile(r"^\s*&[Pp][Aa][Rr][Ss][Ee][Rr][Oo][Ff][Ff]")
RE_PARSER_ON = re.compile(r"^\s*&[Pp][Aa][Rr][Ss][Ee][Rr][Oo][Nn]")
RE_MINUS_MINUS = re.compile(r"^--")
RE_PLUS_PLUS = re.compile(r"^\+\+")
RE_MINUS_NUMBER = re.compile(r"(\w*)=(\w*)-(\d*)")
RE_PLUS_NUMBER = re.compile(r"(\w*)=(\w*)\+(\d)")
RE_LESS_THAN_EQUAL = re.compile(r"(.*)<=(.*)")
RE_LESS_THAN = re.compile(r"(.*)<(.*)")
RE_GREATER_THAN_EQUAL = re.compile(r"(.*)>=(.*)")
RE_GREATER_THAN = re.compile(r"(.*)>(.*)")

RE_DOLLAR_BITS_CHECK = re.compile(
    r"\s*(.*)\s*(\$bits\()([a-zA-Z0-9_\.:#]*)(\))\s*(.*)\s*"
)
RE_DOLLAR_BITS_EXTRACT = re.compile(r"(.*)(\$bits\(\w+\))(.*)")
RE_DOLLAR_CLOG2 = re.compile(r"\$clog2\s*\(")
RE_CLOG2 = re.compile(r"clog2\s*\(")

RE_NUMBERS = re.compile(r"^[0-9]*$")
RE_NUMBERS_ONLY = re.compile(r"^[0-9]+$")

RE_MODULE_DEF = re.compile(r"^\s*&[Mm][Oo][Dd][Uu][Ll][Ee][Dd][Ee][Ff]")
RE_MODULE_DEF_SPACE = re.compile(r"^(\s*)&[Mm][Oo][Dd][Uu][Ll][Ee][Dd][Ee][Ff]")
RE_MODULE_SPACE = re.compile(r"^(\s*)&[Mm][Oo][Dd][Uu][Ll][Ee]")
RE_MODULE_PARAMS = re.compile(r"^(\s*)&[Mm][Oo][Dd][Uu][Ll][Ee]\s*\((.*)\)\s*;")
RE_PORTS = re.compile(r"^(\s*)&[Pp][Oo][Rr][Tt][Ss]")
RE_REGS = re.compile(r"^(\s*)&[Rr][Ee][Gg][Ss]")
RE_LOGICS = re.compile(r"^(\s*)&[Ll][Oo][Gg][Ii][Cc][Ss]")
RE_WIRES = re.compile(r"^(\s*)&[Ww][Ii][Rr][Ee][Ss]")
RE_BINDINGS = re.compile(r"^(\s*)&[Bb][Ii][Nn][Dd][Ii][Nn][Gg][Ss]")
RE_PARAM_OVERRIDE = re.compile(r"^\s*&[Pp][Aa][Rr][Aa][Mm]\s+(.*)\s*;")
RE_BEGININSTANCE = re.compile(
    r"^(\s*)&[Bb][Ee][Gg][Ii][Nn][Ii][Nn][Ss][Tt][Aa][Nn][Cc][Ee]\s+(.*);"
)
RE_ENDINSTANCE = re.compile(r"^(\s*)&[Ee][Nn][Dd][Ii][Nn][Ss][Tt][Aa][Nn][Cc][Ee]\s*;")
RE_BUILD_COMMAND = re.compile(
    r"^\s*&[Bb][Uu][Ii][Ll][Dd][Cc][Oo][Mm][Mm][Aa][Nn][Dd]\s+(.*)\s*;"
)
RE_INCLUDE = re.compile(r"^\s*&[Ii][Nn][Cc][Ll][Uu][Dd][Ee]\s+(.*)\s*;")
RE_CONNECT = re.compile(r"^\s*&[Cc][Oo][Nn][Nn][Ee][Cc][Tt]\s+(.*)\s*;")
RE_NAME_BEGIN = re.compile(r"^\s*([A-Za-z0-9_`]*)\s+(.*)")
RE_NAME_BRACKET_BEGIN = re.compile(r"^\s*([A-Za-z0-9_]*)\s*\((.*)")
RE_BEGIN_SPACE = re.compile(r"^(\s*)(.*)")

RE_CLOCK = re.compile(r"^\s*&[Cc][Ll][Oo][Cc][Kk]\s+(.*)\s*;")
RE_ASYNCRESET = re.compile(r"^\s*&[Aa][Ss][Yy][Nn][Cc][Rr][Ee][Ss][Ee][Tt]\s+(.*)\s*;")
RE_SYNCRESET = re.compile(r"^\s*&[Ss][Yy][Nn][Cc][Rr][Ee][Ss][Ee][Tt]\s+(.*)\s*;")
RE_R_POSEDGE = re.compile(r"^(\s*)&[Pp][Oo][Ss][Ee][Dd][Gg][Ee]\s*;")
RE_R_ENDPOSEDGE = re.compile(r"^(\s*)&[Ee][Nn][Dd][Pp][Oo][Ss][Ee][Dd][Gg][Ee]\s*;")
RE_R_NEGEDGE = re.compile(r"^(\s*)&[Nn][Ee][Gg][Ee][Dd][Gg][Ee]\s*;")
RE_R_ENDNEGEDGE = re.compile(r"^(\s*)&[Ee][Nn][Dd][Nn][Ee][Gg][Ee][Dd][Gg][Ee]\s*;")

RE_FSM = re.compile(r"^(\s*)&[Ff][Ss][Mm]\s*;")
RE_ENDFSM = re.compile(r"^(\s*)&[Ee][Nn][Dd][Ff][Ss][Mm]\s*;")
RE_PIPE = re.compile(r"^(\s*)&[Pp][Ii][Pp][Ee]\s*\(\s*(.*)\s*\)\s*;")
RE_MEMGEN = re.compile(r"^(\s*)&[Mm][Ee][Mm][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;")
RE_MEMGEN_HLS = re.compile(
    r"^(\s*)&[Hh][Ll][Ss]_[Mm][Ee][Mm][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;"
)
RE_MEMGEN_ECC = re.compile(
    r"^(\s*)&[Ee][Cc][Cc]_[Mm][Ee][Mm][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;"
)
RE_CLOCKGEN = re.compile(
    r"^(\s*)&[Cc][Ll][Oo][Cc][Kk][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;"
)
RE_CLOCKGEN_V2 = re.compile(
    r"^(\s*)&[Cc][Ll][Oo][Cc][Kk][Gg][Ee][Nn]_[vV]2\s*\(\s*(.*)\s*\)\s*;"
)
RE_CLOCKRESETGEN = re.compile(
    r"^(\s*)&[Cc][Ll][Oo][Cc][Kk][Rr][Ee][Ss][Ee][Tt][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;"
)
RE_ARTCLOCKRESETGEN = re.compile(
    r"^(\s*)&[Aa][Rr][Tt][Cc][Ll][Oo][Cc][Kk][Rr][Ee][Ss][Ee][Tt][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;"
)
RE_SYNCGEN = re.compile(r"^(\s*)&[Ss][Yy][Nn][Cc][Gg][Ee][Nn]\s*\(\s*(.*)\s*\)\s*;")
RE_SYNCGEN3 = re.compile(r"^(\s*)&[Ss][Yy][Nn][Cc][Gg][Ee][Nn]3\s*\(\s*(.*)\s*\)\s*;")
RE_FB_ENFLOP = re.compile(r"^(\s*)&[Ff][Bb]_[Ee][Nn][Ff][Ll][Oo][Pp]\s*\(\s*(.*)\s*\)")
RE_FB_ENFLOP_RS = re.compile(
    r"^(\s*)&[Ff][Bb]_[Ee][Nn][Ff][Ll][Oo][Pp]_[Rr][Ss]\s*\(\s*(.*)\s*\)"
)
RE_FB_ENFLOP_RST = re.compile(
    r"^(\s*)&[Ff][Bb]_[Ee][Nn][Ff][Ll][Oo][Pp]_[Rr][Ss][Tt]\s*\(\s*(.*)\s*\)"
)

RE_STUBOUT = re.compile(r"^(\s*)&[Ss][Tt][Uu][Bb][Oo][Uu][Tt]\s+(.*)\s+(.*)\s*;")
RE_STUBOUT_VERILOG = re.compile(
    r"^(\s*)\/\/\s*&[Ss][Tt][Uu][Bb][Oo][Uu][Tt]\s+(.*)\s+(.*)\s*;"
)
RE_GENDRIVEZ = re.compile(r"^(\s*)&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee][Zz]\s*;")
RE_GENDRIVEZ_VERILOG = re.compile(
    r"^(\s*)\/\/\s*&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee][Zz]\s*;"
)
RE_GENDRIVE0 = re.compile(r"^(\s*)&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee]0\s*;")
RE_GENNOIFDEFDRIVE0 = re.compile(
    r"^(\s*)&[Gg][Ee][Nn][Nn][Oo][Ii][Ff][Dd][Ee][Ff][Dd][Rr][Ii][Vv][Ee]0\s*;"
)
RE_GENDRIVE0_VERILOG = re.compile(
    r"^(\s*)\/\/\s*&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee]0\s*;"
)
RE_GENDRIVE0ANDZ = re.compile(
    r"^(\s*)&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee]0[Aa][Nn][Dd][Zz]\s*;"
)
RE_GENDRIVE0ANDZ_VERILOG = re.compile(
    r"^(\s*)\/\/\s*&[Gg][Ee][Nn][Dd][Rr][Ii][Vv][Ee]0[Aa][Nn][Dd][Zz]\s*;"
)

RE_INFRA_ASIC_FPGA_ROOT = re.compile(r"^\$INFRA_ASIC_FPGA_ROOT")

RE_PKG2ASSIGN = re.compile(
    r"^(\s*)&[Pp][Kk][Gg]2[Aa][Ss][Ss][Ii][Gg][Nn]\s*\(\s*\"\s*([\w]+)\s*\"\s*,\s*\"\s*([\w:]+)\s*\"\s*,\s*\"\s*([\w]+)\s*\"\s*\)\s*;"
)
RE_ASSIGN2PKG = re.compile(
    r"^(\s*)&[Aa][Ss][Ss][Ii][Gg][Nn]2[Pp][Kk][Gg]\s*\(\s*\"\s*([\w]+)\s*\"\s*,\s*\"\s*([\w:]+)\s*\"\s*,\s*\"\s*([\w]+)\s*\"\s*\)\s*;"
)
RE_RESERVED = re.compile(r"[Rr][Ee][Ss][Ee][Rr][Vv][Ee][Dd]")
RE_TRANSLATE_OFF = re.compile(r"^\s*//\s*pragma\s+translate_off")
RE_TRANSLATE_ON = re.compile(r"^\s*//\s*pragma\s+translate_on")

MONSTER_REGEX_LIST = [
    RE_GENDRIVEZ_VERILOG,
    RE_GENDRIVE0_VERILOG,
    RE_GENDRIVE0ANDZ_VERILOG,
    RE_SKIP_BEGIN,
    RE_SKIP_END,
    RE_SKIP_IFDEF_BEGIN,
    RE_SKIP_IFDEF_END,
    RE_PARSER_OFF,
    RE_PARSER_ON,
    RE_TICK_IFDEF,
    RE_TICK_IFNDEF,
    RE_TICK_ELSIF,
    RE_TICK_ELSE,
    RE_TICK_ENDIF,
    RE_ASSERT_PROPERTY,
    RE_FUNCTION,
    RE_ENDFUNCTION,
    RE_GENERATE,
    RE_ENDGENERATE,
    RE_GENERATE_FOR,
    RE_GENVAR,
    RE_INTEGER,
    RE_INT,
    RE_TICK_DEFINE,
    RE_TICK_UNDEF,
    RE_MODULE_SPACE,
    RE_MODULE_PARAMS,
    RE_MODULE_DECLARATION,
    # RE_PARAM,
    RE_LOCALPARAM,
    RE_TICK_INCLUDE,
    RE_IMPORT,
    RE_R_POSEDGE,
    RE_R_NEGEDGE,
    RE_R_ENDNEGEDGE,
    RE_R_ENDPOSEDGE,
    RE_FORCE,
    # RE_DECLARE_INPUT,
    # RE_DECLARE_OUTPUT,
    RE_DECLARE_WIRE,
    RE_DECLARE_REG,
    RE_DECLARE_LOGIC,
    RE_ASSIGN,
    RE_ALWAYS,
    RE_ALWAYS_FF,
    RE_ALWAYS_COMB,
    RE_UNIQUE_CASE,
    RE_CASE,
    RE_CASEZ,
    RE_CASEX,
    RE_ENDCASE,
    RE_IF,
    RE_ELSEIF,
    RE_ELSE,
    RE_END,
    RE_BEGININSTANCE,
    RE_ENDINSTANCE,
    RE_BUILD_COMMAND,
    RE_INCLUDE,
    RE_PARAM_OVERRIDE,
    RE_CONNECT,
    RE_END_MODULE_DECLARATION,
]
ANY_MONSTER_REGEX = re.compile("|".join(x.pattern for x in MONSTER_REGEX_LIST))


# System verilog keywords to be used
sv_keywords = [
    "alias",
    "always",
    "always_comb",
    "always_ff",
    "always_latch",
    "and",
    "assert",
    "assign",
    "assume",
    "automatic",
    "before",
    "begin",
    "bind",
    "bins",
    "binsof",
    "bit",
    "break",
    "buf",
    "bufif0",
    "bufif1",
    "byte",
    "case",
    "casex",
    "casez",
    "cell",
    "chandle",
    "class",
    "clocking",
    "cmos",
    "config",
    "const",
    "constraint",
    "context",
    "continue",
    "cover",
    "covergroup",
    "coverpoint",
    "cross",
    "deassign",
    "default",
    "defparam",
    "design",
    "disable",
    "dist",
    "do",
    "edge",
    "else",
    "end",
    "endcase",
    "endclass",
    "endclocking",
    "endconfig",
    "endfunction",
    "endgenerate",
    "endgroup",
    "endinterface",
    "endmodule",
    "endpackage",
    "endprimitive",
    "endprogram",
    "endproperty",
    "endspecify",
    "endsequence",
    "endtable",
    "endtask",
    "enum",
    "event",
    "expect",
    "export",
    "extends",
    "extern",
    "final",
    "first_match",
    "for",
    "force",
    "foreach",
    "forever",
    "fork",
    "forkjoin",
    "function",
    "generate",
    "genvar",
    "highz0",
    "highz1",
    "if",
    "iff",
    "ifnone",
    "ignore_bins",
    "illegal_bins",
    "import",
    "incdir",
    "include",
    "initial",
    "inout",
    "input",
    "inside",
    "instance",
    "int",
    "integer",
    "interface",
    "intersect",
    "join",
    "join_any",
    "join_none",
    "large",
    "liblist",
    "library",
    "local",
    "localparam",
    "logic",
    "longint",
    "macromodule",
    "matches",
    "medium",
    "modport",
    "module",
    "nand",
    "negedge",
    "new",
    "nmos",
    "nor",
    "noshowcancelled",
    "not",
    "notif0",
    "notif1",
    "null",
    "or",
    "output",
    "package",
    "packed",
    "parameter",
    "pmos",
    "posedge",
    "primitive",
    "priority",
    "program",
    "property",
    "protected",
    "pull0",
    "pull1",
    "pulldown",
    "pullup",
    "pulsestyle_onevent",
    "pulsestyle_ondetect",
    "pure",
    "rand",
    "randc",
    "randcase",
    "randsequence",
    "rcmos",
    "real",
    # "realtime", "ref", "reg", "release", "repeat", "return", "rnmos", "rpmos",
    "realtime",
    "reg",
    "release",
    "repeat",
    "return",
    "rnmos",
    "rpmos",
    "rtran",
    "rtranif0",
    "rtranif1",
    "scalared",
    "sequence",
    "shortint",
    "shortreal",
    "showcancelled",
    "signed",
    "small",
    "solve",
    "specify",
    "specparam",
    "static",
    "string",
    "strong0",
    "strong1",
    "struct",
    "super",
    "supply0",
    "supply1",
    "table",
    "tagged",
    "task",
    "this",
    "throughout",
    "time",
    "timeprecision",
    "timeunit",
    "tran",
    "tranif0",
    "tranif1",
    "tri",
    "tri0",
    "tri1",
    "triand",
    "trior",
    "trireg",
    "type",
    "typedef",
    "union",
    "unique",
    "unsigned",
    "use",
    "uwire",
    "var",
    "vectored",
    "virtual",
    "void",
    "wait",
    "wait_order",
    "wand",
    "weak0",
    "weak1",
    "while",
    "wildcard",
    "wire",
    "with",
    "within",
    "wor",
    "xnor",
    "xor",
]
