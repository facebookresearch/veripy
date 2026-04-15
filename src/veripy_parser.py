import json
import os
import re
import sys
import time

import anytree
from pyparsing import (
    alphanums,
    alphas,
    CaselessKeyword,
    CaselessLiteral,
    Char,
    col,
    Combine,
    cppStyleComment,
    dblQuotedString,
    dblSlashComment,
    delimitedList,
    Empty,
    empty,
    FollowedBy,
    Forward,
    Group,
    Keyword,
    line,
    lineEnd,
    lineno,
    Literal,
    nums,
    oneOf,
    OneOrMore,
    Optional,
    ParseException,
    ParserElement,
    ParseResults,
    printables,
    Regex,
    restOfLine,
    SkipTo,
    StringEnd,
    Suppress,
    Word,
    ZeroOrMore,
)

from .regex import RE_ASSIGN2PKG, RE_COMMA, RE_PKG2ASSIGN, RE_RESET_VAL
from .spec_flow import spec_flow

g_psv_parser = None


def get_result_text(tokens):
    result_text = []
    if not isinstance(tokens, (list, ParseResults)):
        return result_text

    if isinstance(tokens, ParseResults):
        tokens = tokens.asList()

    for token in tokens:
        if isinstance(token, (list, ParseResults)):
            result_text.extend(get_result_text(token))
        else:
            result_text.append(token)

    return result_text


# Liter tokens
# pyparsing verion 3.1.1 (using_each)
# (
#     SEMI,
#     COLON,
#     LPAR,
#     RPAR,
#     LBRACE,
#     RBRACE,
#     LBRACK,
#     RBRACK,
#     DOT,
#     COMMA,
#     EQ,
#     UND,
#     HASHTAG,
#     QUESTION_MARK,
#     DOUBLE_COLON,
#     DOLLAR_SIGN,
#     APOSTROPHE,
#     TICK,
#     ZERO,
#     ONE,
#     LE,
#     STAR,
# ) = Literal.using_each(
#     [
#         ";",
#         ":",
#         "(",
#         ")",
#         "{",
#         "}",
#         "[",
#         "]",
#         ".",
#         ",",
#         "=",
#         "_",
#         "#",
#         "?",
#         "::",
#         "$",
#         "'",
#         "`",
#         "0",
#         "1",
#         "<=",
#         "*",
#     ]
# )
#  pyparsing verion 2.4.7
SEMI = Literal(";")
COLON = Literal(":")
LPAR = Literal("(")
RPAR = Literal(")")
LBRACE = Literal("{")
RBRACE = Literal("}")
LBRACK = Literal("[")
RBRACK = Literal("]")
DOT = Literal(".")
COMMA = Literal(",")
EQ = Literal("=")
UND = Literal("-")
HASHTAG = Literal("#")
QUESTION_MARK = Literal("?")
DOUBLE_COLON = Literal("::")
DOLLAR_SIGN = Literal("$")
APOSTROPHE = Literal("'")
TICK = Literal("`")
ZERO = Literal("0")
ONE = Literal("1")
LE = Literal("<=")
STAR = Literal("*")

# pyparsing verion 3.1.1 (using_each)
# (B, D, E, H, O, S, X, Z,) = CaselessLiteral.using_each(
#     [
#         "b",
#         "d",
#         "e",
#         "h",
#         "o",
#         "s",
#         "x",
#         "z",
#     ]
# )
#  pyparsing verion 2.4.7
B = CaselessLiteral("b")
D = CaselessLiteral("d")
E = CaselessLiteral("e")
H = CaselessLiteral("h")
O = CaselessLiteral("o")
S = CaselessLiteral("s")
X = CaselessLiteral("x")
Z = CaselessLiteral("z")

vp_module_kw = CaselessKeyword("&Module")
vp_moduledef_kw = CaselessKeyword("&ModuleDef")
vp_ports_kw = CaselessKeyword("&Ports")
vp_logics_kw = CaselessKeyword("&Logics")
vp_regs_kw = CaselessKeyword("&Regs")
vp_wires_kw = CaselessKeyword("&Wires")
vp_gendrive0_kw = CaselessKeyword("&GenDrive0")
vp_gendrivez_kw = CaselessKeyword("&GenDriveZ")
vp_gendrive0andz_kw = CaselessKeyword("&GenDrive0andZ")
vp_gendrive0_parameter_kw = CaselessKeyword("&GenDrive0_parameter")
vp_genparam_kw = CaselessKeyword("&GenParam")
vp_genparam_no_gen_rtl_kw = CaselessKeyword("&GenParamNoGenRtl")
vp_gennoifdefdrive0_kw = CaselessKeyword("&GenNoifdefDrive0")
vp_parseroff_kw = CaselessKeyword("&ParserOff")
vp_parseron_kw = CaselessKeyword("&ParserOn")
vp_beginskip_kw = CaselessKeyword("&BeginSkip")
vp_endskip_kw = CaselessKeyword("&EndSkip")
vp_beginskipifdef_kw = CaselessKeyword("&BeginSkipIfdef")
vp_endskipifdef_kw = CaselessKeyword("&EndSkipIfdef")
vp_pythonbegin_kw = CaselessKeyword("&PythonBegin")
vp_pythonend_kw = CaselessKeyword("&PythonEnd")
vp_pythonpostbegin_kw = CaselessKeyword("&PythonPostBegin")
vp_pythonpostend = CaselessKeyword("&PythonPostEnd")
vp_python_kw = CaselessKeyword("&Python")
vp_begininstance_kw = CaselessKeyword("&BeginInstance")
vp_endinstance_kw = CaselessKeyword("&EndInstance")
vp_asyncreset_kw = CaselessKeyword("&AsyncReset")
vp_syncreset_kw = CaselessKeyword("&SyncReset")
vp_clock_kw = CaselessKeyword("&Clock")
vp_posedge_kw = CaselessKeyword("&PosEdge")
vp_endposedge_kw = CaselessKeyword("&EndPosEdge")
vp_negedge_kw = CaselessKeyword("&NegEdge")
vp_endnegedge_kw = CaselessKeyword("&EndNegEdge")
vp_force_kw = CaselessKeyword("&Force")
vp_force_internal_kw = CaselessKeyword("&Force internal")
vp_force_width_kw = CaselessKeyword("&Force width")
vp_force_depth_kw = CaselessKeyword("&Force depth")
vp_force_wire_kw = CaselessKeyword("&Force wire")
vp_force_reg_kw = CaselessKeyword("&Force reg")
vp_force_logic_kw = CaselessKeyword("&Force logic")
vp_force_bind_kw = CaselessKeyword("&Force bind")
vp_pkg2assign_kw = CaselessKeyword("&Pkg2Assign")
vp_assign2pkg_kw = CaselessKeyword("&Assign2Pkg")
vp_param_kw = CaselessKeyword("&Param")
vp_include_kw = CaselessKeyword("&Include")
vp_depend_kw = CaselessKeyword("&Depend")
vp_connect_kw = CaselessKeyword("&Connect")
vp_buildcommand_kw = CaselessKeyword("&BuildCommand")
vp_printtext_kw = CaselessKeyword("&PrintText")
vp_printio_kw = CaselessKeyword("&PrintIO")
# Veripy constructs to skip
vp_fsm_kw = CaselessKeyword("&Fsm")
vp_pipe_kw = CaselessKeyword("&Pipe")
vp_ecc_memgen_kw = CaselessKeyword("&ECC_Memgen")
vp_hls_memgen_kw = CaselessKeyword("&HLS_Memgen")
vp_memgen_kw = CaselessKeyword("&Memgen")
vp_clockgen_kw = CaselessKeyword("&ClockGen")
vp_clockgen_v2_kw = CaselessKeyword("&ClockGen_V2")
vp_clockresetgen_kw = CaselessKeyword("&ClockResetGen")
vp_artclockresetgen_kw = CaselessKeyword("&ArtClockResetGen")
vp_syncgen_kw = CaselessKeyword("&SyncGen")
vp_syncgen3_kw = CaselessKeyword("&SyncGen3")
vp_fb_enflop_kw = CaselessKeyword("&FB_EnFlop")
vp_fb_enflop_rs_kw = CaselessKeyword("&FB_EnFlop_RS")
vp_fb_enflop_rst_kw = CaselessKeyword("&FB_EnFlop_RST")

# number
sign = Word("-+")
signed = Literal("signed")
base = Regex("'[bBoOdDhH]")("base")
decimal_base = Optional("'") + Optional(S) + D
binary_base = Optional("'") + Optional(S) + B
octal_base = Optional("'") + Optional(S) + O
hex_base = Optional("'") + Optional(S) + H

x_digit = "xX"
z_digit = "zZ"
decimal_digit = nums
non_zero_decimal_digit = "123456789"
binary_digit = "01"
octal_digit = "01234567"
hex_digit = "0123456789abcdefABCDEF" + x_digit + z_digit

unsigned_number = Word(decimal_digit, decimal_digit + "_")
non_zero_unsigned_number = Word(non_zero_decimal_digit, decimal_digit + "_")
size = non_zero_unsigned_number
binary_value = Word(binary_digit, binary_digit + "_")
octal_value = Word(octal_digit, octal_digit + "_")
hex_value = Word(hex_digit, hex_digit + "_")
x_value = Word(x_digit, x_digit + "_")
z_value = Word(z_digit, z_digit + "_")

decimal_number = unsigned_number ^ (
    Optional(size) + decimal_base + (unsigned_number | x_value | z_value)
)

binary_number = Optional(size) + binary_base + binary_value

octal_number = Optional(size) + octal_base + octal_value

hex_number = Combine(Optional(size) + hex_base + hex_value)

fixed_point_number = Combine(unsigned_number + DOT + unsigned_number)

real_number = Combine(
    (fixed_point_number + E + Optional(sign) + unsigned_number) | fixed_point_number
)

integer_number = Combine(decimal_number ^ binary_number ^ octal_number ^ hex_number)

# number = real_number | integer_number
number = real_number | integer_number

# z_or_x := x | X | z | Z
# unbased_unsized_literal := '0 | '1 | 'z_or_x
unbased_unsized_literal = Combine(APOSTROPHE + (ZERO | ONE | X | Z))

# simple_identifier := [a-zA-Z_]{ [a-zA-Z0-9_$] }
simple_identifier = Word(alphas + "_", alphanums + "_$")

extended_identifier = Word(alphas + '_"', alphanums + '_$.{}[]"')

# escaped_identifier := \{any_printable_ASCII_character_except_white_space}white_space
escaped_identifier = Regex(r"\\\S+").setParseAction(lambda t: t[0][1:])

# identifier := simple_identifier | escaped_identifier
identifier = simple_identifier | escaped_identifier | extended_identifier

expr = Forward()

tick_constant = Combine(TICK + identifier)

package_import_item = Combine(identifier + "::" + (identifier | "*"))

rnge = expr + COLON + expr

packed_dimension = Combine(LBRACK + Optional(rnge | expr) + RBRACK)

unpacked_dimension = Combine(LBRACK + Optional(rnge | expr) + RBRACK)

concat = Group(LBRACE + delimitedList(Combine(expr)) + RBRACE)

package_scope = Combine(identifier + DOUBLE_COLON)

function_call = Group(
    Combine(Optional(DOLLAR_SIGN | package_scope) + identifier("function_name"))
    + "("
    + Optional(delimitedList(Combine(expr))("function_parameters") | Empty())
    + ")"
)

bit_select = Group(LBRACK + Combine(expr)("select_bit") + RBRACK)

# hierarchical_identifier := [ $root . ] { identifier constant_bit_select . } identifier
# hierarchical_variable_identifier := hierarchical_identifier
hierarchical_variable_identifier = Combine(
    ZeroOrMore(identifier + ZeroOrMore(bit_select) + DOT) + identifier
)

primary = (
    number
    ^ unbased_unsized_literal
    ^ hierarchical_variable_identifier + ZeroOrMore(LBRACK + expr + RBRACK)
    ^ tick_constant
    ^ package_import_item
    ^ dblQuotedString
    ^ function_call
    # RecursionError: maximum recursion depth exceeded while calling a Python object
    ^ concat + Optional(packed_dimension)
    # | LPAR +  mintypmax + RPAR
)

unop = oneOf("+  -  !  ~  &  ~&  |  ^|  ^  ~^")("unop")

binop = oneOf(
    "+  -  *  /  %  ==  !=  ===  !==  &&  "
    "||  <  <=  >  >=  &  |  ^  ^~  >>  << ** <<< >>>"
)("binop")

binary_expr = ((primary | (LPAR + expr + RPAR)) + binop + expr)("binary_expr")

# (expression | cond_pattern) { &&&  (expression | cond_pattern)}
# cond_pattern := expression matches pattern
cond_predicate = (LPAR + Combine(expr)("cond_predicate") + RPAR)("cond_predicate")

conditional_expression = (
    LPAR
    + cond_predicate
    + "?"
    + expr("true_expr")
    + COLON
    + expr("false_express")
    + RPAR
)("conditional_expression")

multiple_concatenation = Group(LBRACE + expr + concat + RBRACE)(
    "multiple_concatenation"
)

expr <<= (
    unop + expr
    ^ binary_expr
    ^ primary
    # ^ (primary + QUESTION_MARK + expr + COLON + expr)
    ^ conditional_expression
    ^ LPAR + expr + RPAR
    ^ multiple_concatenation
)

# port_direction : input | output | inout | ref
port_direction = oneOf(
    "input output inout ref",
    # as_keyword=True, # pyparsing 3.1.1 only
)

# parameter_identifier { unpacked_dimension } [ = constant_param_expression ]
param_assignment = Group(
    Optional(oneOf("parameter localparam"))
    + Optional(unpacked_dimension)
    + identifier
    + Optional(unpacked_dimension)
    + Optional(EQ + Combine(expr))
)("param_assignment")

parameter_list = (
    Suppress(LPAR)
    + Optional(delimitedList(param_assignment)("param_assignment"))
    + Suppress(RPAR)
)("parameter_list")

# integer_vector_type: bit | logic | reg
integer_vector_type = Regex(r"\b(bit|logic|reg|wire)\b")


def vp_module_callback(s, loc, toks):
    global g_psv_parser

    if "param_assignment" in toks:
        param_assignments_text = ", ".join(
            [" ".join(pl) for pl in toks["param_assignment"].asList()]
        )
        if param_assignments_text != "":
            g_psv_parser.module_param_line = param_assignments_text
            g_psv_parser.param_proc(
                "TOP", g_psv_parser.module_param_line, "", "", "module_header"
            )


# veripy expressions
vp_module = (vp_module_kw + Optional(parameter_list("parameter_list")) + (SEMI))(
    "vp_module"
).setParseAction(vp_module_callback)


def vp_moduledef_callback(s, loc, toks):
    global g_psv_parser

    # g_psv_parser was reset back to None for unknown reason ????
    i_spec_flow = spec_flow(
        g_psv_parser.interface_spec_files,
        g_psv_parser.interface_def_files,
        g_psv_parser.module_def_files,
        g_psv_parser.moduledef_name,
        g_psv_parser.incl_dirs,
        g_psv_parser.files,
        g_psv_parser.debug,
        g_psv_parser,
    )

    i_spec_flow.load_files()
    i_spec_flow.module_info = i_spec_flow.get_module_definition(i_spec_flow.module_name)

    g_psv_parser.module_info = i_spec_flow.module_info
    g_psv_parser.ports_w_comment.update(i_spec_flow.inports_w_comment)

    # Check if any errors when running spec flow
    if i_spec_flow.found_error:
        g_psv_parser.found_error = 1

    g_psv_parser.dbg(i_spec_flow.debug_info)

    g_psv_parser.dbg(json.dumps(i_spec_flow.module_info, indent=2))

    for c_param in i_spec_flow.module_info["PARAM"]:
        c_param = re.sub(r"\s+", " ", c_param)
        g_psv_parser.param_proc("TOP", c_param, "", "", "module_header")

    for c_port in i_spec_flow.module_info["IN"]:
        c_port = re.sub(r"\s+", " ", c_port)
        g_psv_parser.parse_ios(
            "TOP", "SPEC", "input", c_port + ";", g_psv_parser.module_name
        )

    for c_port in i_spec_flow.module_info["OUT"]:
        c_port = re.sub(r"\s+", " ", c_port)
        g_psv_parser.parse_ios(
            "TOP", "SPEC", "output", c_port + ";", g_psv_parser.module_name
        )

    for c_port in i_spec_flow.module_info["INOUT"]:
        c_port = re.sub(r"\s+", " ", c_port)
        g_psv_parser.parse_ios(
            "TOP", "SPEC", "inout", c_port + ";", g_psv_parser.module_name
        )

    if "IN_NOTYPE" in i_spec_flow.module_info:
        for c_port in i_spec_flow.module_info["IN_NOTYPE"]:
            c_port = re.sub(r"\s+", " ", c_port)
            g_psv_parser.parse_ios(
                "TOP", "SPEC", "input_notype", c_port + ";", g_psv_parser.module_name
            )

    if "OUT_NOTYPE" in i_spec_flow.module_info:
        for c_port in i_spec_flow.module_info["OUT_NOTYPE"]:
            c_port = re.sub(r"\s+", " ", c_port)
            g_psv_parser.parse_ios(
                "TOP", "SPEC", "output_notype", c_port + ";", g_psv_parser.module_name
            )

    if "INOUT_NOTYPE" in i_spec_flow.module_info:
        for c_port in i_spec_flow.module_info["INOUT_NOTYPE"]:
            c_port = re.sub(r"\s+", " ", c_port)
            g_psv_parser.parse_ios(
                "TOP", "SPEC", "inout_notype", c_port + ";", g_psv_parser.module_name
            )

    ################################################################################
    # Loading the module dependencies with spec files list
    ################################################################################
    if g_psv_parser.gen_dependencies:
        if g_psv_parser.interface_spec_files is not None:
            for c_file in g_psv_parser.interface_spec_files:
                g_psv_parser.dependencies["spec_files"].append(
                    {c_file: {"mtime": os.path.getmtime(c_file)}}
                )

        if g_psv_parser.interface_def_files is not None:
            for c_file in g_psv_parser.interface_def_files:
                g_psv_parser.dependencies["interface_files"].append(
                    {c_file: {"mtime": os.path.getmtime(c_file)}}
                )

        if g_psv_parser.module_def_files is not None:
            for c_file in g_psv_parser.module_def_files:
                g_psv_parser.dependencies["module_files"].append(
                    {c_file: {"mtime": os.path.getmtime(c_file)}}
                )


vp_moduledef = (vp_moduledef_kw + Optional(parameter_list("parameter_list")) + SEMI)(
    "vp_moduledef"
).setParseAction(vp_moduledef_callback)

vp_ports = Group(vp_ports_kw + SEMI)("vp_ports")
vp_logics = Group(vp_logics_kw + SEMI)("vp_logics")
vp_regs = Group(vp_regs_kw + SEMI)("vp_regs")
vp_wires = Group(vp_wires_kw + SEMI)("vp_wires")
vp_gendrive0 = Group(vp_gendrive0_kw + SEMI)("vp_gendrive0")
vp_gendrivez = Group(vp_gendrivez_kw + SEMI)("vp_gendrivez")
vp_gendrive0andz = Group(vp_gendrive0andz_kw + SEMI)("vp_gendrive0andz")
vp_gennoifdefdrive0 = Group(vp_gennoifdefdrive0_kw + SEMI)("vp_gennoifdefdrive0")


def vp_genparam_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.genparam = 1


vp_genparam = Group(vp_genparam_kw + SEMI)("vp_genparam").setParseAction(
    vp_genparam_callback
)


def vp_genparam_no_gen_rtl_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.genparam_no_gen_rtl = 1


vp_genparam_no_gen_rtl = Group(vp_genparam_no_gen_rtl_kw + SEMI)(
    "vp_genparam_no_gen_rtl"
).setParseAction(vp_genparam_no_gen_rtl_callback)


def vp_gendrive0_parameter_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.gendrive0_parameter = 1


vp_gendrive0_parameter = Group(vp_gendrive0_parameter_kw + SEMI)(
    "vp_gendrive0_parameter"
).setParseAction(vp_gendrive0_parameter_callback)

vp_begin_skip_ifdef = Group(vp_beginskipifdef_kw + SEMI)("vp_begin_skip_ifdef")
vp_end_skip_ifdef = Group(vp_endskipifdef_kw + SEMI)("vp_end_skip_ifdef")

vp_async_reset = Group(
    vp_asyncreset_kw + delimitedList(identifier, delim=",")("async_reset") + SEMI
)("vp_async_reset")

vp_sync_reset = Group(
    vp_syncreset_kw + delimitedList(identifier, delim=",")("sync_reset") + SEMI
)("vp_sync_reset")

vp_clock = Group(vp_clock_kw + delimitedList(identifier, delim=",")("clock") + SEMI)(
    "vp_clock"
)


def vp_posedge_callback(s, loc, toks):
    global g_psv_parser

    if g_psv_parser.auto_reset_en >= 0:
        g_psv_parser.dbg(
            f"\nError: Missing paired &EndPosEdge/&EndNegEdge for &PosEdge/&NegEdge (line {g_psv_parser.auto_reset_en}) detected."
        )
        print(
            f"\nError: Missing paired &EndPosEdge/&EndNegEdge for &PosEdge/&NegEdge (line {g_psv_parser.auto_reset_en}) detected."
        )
        sys.exit(1)

    g_psv_parser.auto_reset_en = loc
    g_psv_parser.auto_reset_data[g_psv_parser.auto_reset_index] = {}


vp_posedge = (vp_posedge_kw + SEMI).setParseAction(vp_posedge_callback)


def vp_endposedge_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.auto_reset_en = -1
    g_psv_parser.auto_reset_index = g_psv_parser.auto_reset_index + 1
    g_psv_parser.auto_reset_vals.clear()


vp_endposedge = (vp_endposedge_kw + SEMI).setParseAction(vp_endposedge_callback)


def vp_posedge_item_callback(s, loc, toks):
    global g_psv_parser

    RE_RESET_VAL_LINE = re.compile(
        r"^((.*)\s)*(([0-9A-Za-z'_{},\[\]:]+)\s*<)([0-9A-Za-z'_{},]+)(=.*)$"
    )
    lines = get_result_text(toks)
    vplines = lines[0].split("\n")
    svlines = []
    g_psv_parser.auto_reset_lines = {}
    for vpline in vplines:
        svline = vpline[:]
        assign_str_reset_val_regex = RE_RESET_VAL.search(vpline)
        if assign_str_reset_val_regex:
            lines_ = []
            match = re.search(r"(.*begin)(.*)(end.*)", vpline)
            if match:
                lines_.append(f"{match.group(1)}")
                lines_.extend(
                    [
                        ln + ";"
                        for ln in match.group(2).split(";")
                        if len(ln.strip()) > 0
                    ]
                )
                lines_.append(f"{match.group(3)}")
            else:
                lines_.append(vpline)

            for line_ in lines_:
                assign_str_reset_val_line_regex = RE_RESET_VAL_LINE.search(line_)
                if assign_str_reset_val_line_regex:
                    if assign_str_reset_val_line_regex.group(1):
                        svline = (
                            assign_str_reset_val_line_regex.group(1)
                            + assign_str_reset_val_line_regex.group(3)
                            + assign_str_reset_val_line_regex.group(6)
                        )
                        key_line = assign_str_reset_val_line_regex.group(
                            3
                        ) + assign_str_reset_val_line_regex.group(6)
                        value_line = (
                            assign_str_reset_val_line_regex.group(3)
                            + assign_str_reset_val_line_regex.group(5)
                            + assign_str_reset_val_line_regex.group(6)
                        )
                        lhs_assign_str = assign_str_reset_val_line_regex.group(4)
                        reset_value = assign_str_reset_val_line_regex.group(5)
                    else:
                        svline = assign_str_reset_val_line_regex.group(
                            3
                        ) + assign_str_reset_val_line_regex.group(6)
                        key_line = assign_str_reset_val_line_regex.group(
                            3
                        ) + assign_str_reset_val_line_regex.group(6)
                        value_line = (
                            assign_str_reset_val_line_regex.group(3)
                            + assign_str_reset_val_line_regex.group(5)
                            + assign_str_reset_val_line_regex.group(6)
                        )
                        lhs_assign_str = assign_str_reset_val_line_regex.group(4)
                        reset_value = assign_str_reset_val_line_regex.group(5)

                    g_psv_parser.auto_reset_lines[re.sub(r"\s*", "", key_line)] = (
                        value_line
                    )
                    lhs_assign_comma_regex = RE_COMMA.search(lhs_assign_str)

                    lhs_assign_str_array = []
                    # If multiple declarations on the same line, then break it
                    if lhs_assign_comma_regex:
                        # removing space, { and }
                        lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                        lhs_assign_str_array = lhs_assign_str.split(",")
                    else:  # Single declaration, then append to the array
                        lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                        lhs_assign_str_array.append(lhs_assign_str)

                    for curr_lhs in lhs_assign_str_array:
                        curr_lhs = curr_lhs.replace("[", " ", 1)
                        signal_str_array = curr_lhs.split()
                        g_psv_parser.auto_reset_vals[signal_str_array[0]] = reset_value
                else:
                    assign_str_reset_val_regex = RE_RESET_VAL.search(line_)
                    if assign_str_reset_val_regex:
                        svline = assign_str_reset_val_regex.group(
                            1
                        ) + assign_str_reset_val_regex.group(3)
                        key_line = svline
                        value_line = (
                            assign_str_reset_val_regex.group(1)
                            + assign_str_reset_val_regex.group(2)
                            + assign_str_reset_val_regex.group(3)
                        )
                        g_psv_parser.auto_reset_lines[re.sub(r"\s*", "", key_line)] = (
                            value_line
                        )

                        lhs_assign_str = assign_str_reset_val_regex.group(1)
                        lhs_assign_comma_regex = RE_COMMA.search(lhs_assign_str)

                        lhs_assign_str_array = []
                        # If multiple declarations on the same line, then break it
                        if lhs_assign_comma_regex:
                            # removing space, { and }
                            lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                            lhs_assign_str_array = lhs_assign_str.split(",")
                        else:  # Single declaration, then append to the array
                            lhs_assign_str = re.sub(r"[{}\s]<", "", lhs_assign_str)
                            lhs_assign_str_array.append(lhs_assign_str)

                        for curr_lhs in lhs_assign_str_array:
                            curr_lhs = curr_lhs.replace("[", " ", 1)
                            signal_str_array = curr_lhs.split()
                            g_psv_parser.auto_reset_vals[signal_str_array[0]] = (
                                assign_str_reset_val_regex.group(2)
                            )
                    else:
                        svline = line_[:]
                svlines.append(f"{svline}\n")

        elif len(svline) > 0:
            svlines.append(f"{svline}\n")

    g_psv_parser.sv_parser.add_parser_mode_directive(svlines)
    string = "".join(svlines)
    syntax_data = g_psv_parser.sv_parser.parse(string)
    if syntax_data is None or syntax_data.errors is None:
        if g_psv_parser.debug:
            with open(
                f"{g_psv_parser.input_file}_posedge_{time.time()}.cst",
                "w",
            ) as cstfile:
                for prefix, _, node in anytree.RenderTree(syntax_data.tree):
                    # print(f"{prefix}{node.to_formatted_string()}", file=cstfile)
                    print(f"{prefix}{repr(node)}", file=cstfile)
                    # print(f"{prefix}{repr(node)}")
                print(file=cstfile)
            print(f"# of verilog lines parsed: {len(svlines)} => No syntax error.")

        if syntax_data is not None and syntax_data.tree is not None:
            g_psv_parser.sv_parser.process(syntax_data)


vp_posedge_item = SkipTo(vp_endposedge).setParseAction(vp_posedge_item_callback)

vp_posedge_endposedge = Group(
    vp_posedge + vp_posedge_item("posedge_item") + vp_endposedge
)("vp_posedge_endposedge*")


def vp_negedge_callback(s, loc, toks):
    global g_psv_parser

    if g_psv_parser.auto_reset_en >= 0:
        g_psv_parser.dbg(
            f"\nError: Missing paired &EndPosEdge/&EndNegEdge for &PosEdge/&NegEdge (line {g_psv_parser.auto_reset_en}) detected."
        )
        print(
            f"\nError: Missing paired &EndPosEdge/&EndNegEdge for &PosEdge/&NegEdge (line {g_psv_parser.auto_reset_en}) detected."
        )
        sys.exit(1)

    g_psv_parser.auto_reset_en = loc
    g_psv_parser.auto_reset_data[g_psv_parser.auto_reset_index] = {}


vp_negedge = (vp_negedge_kw + SEMI).setParseAction(vp_negedge_callback)


def vp_endnegedge_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.auto_reset_en = -1
    g_psv_parser.auto_reset_index = g_psv_parser.auto_reset_index + 1
    g_psv_parser.auto_reset_vals.clear()


vp_endnegedge = (vp_endnegedge_kw + SEMI).setParseAction(vp_endnegedge_callback)


def vp_negedge_item_callback(s, loc, toks):
    global g_psv_parser

    RE_RESET_VAL_LINE = re.compile(
        r"^((.*)\s)*(([0-9A-Za-z'_{},\[\]:]+)\s*<)([0-9A-Za-z'_{},]+)(=.*)$"
    )
    lines = get_result_text(toks)
    vplines = lines[0].split("\n")
    svlines = []
    g_psv_parser.auto_reset_lines = {}
    for vpline in vplines:
        svline = vpline[:]
        assign_str_reset_val_regex = RE_RESET_VAL.search(vpline)
        if assign_str_reset_val_regex:
            lines_ = []
            match = re.search(r"(.*begin)(.*)(end.*)", vpline)
            if match:
                lines_.append(f"{match.group(1)}")
                lines_.extend(
                    [
                        ln + ";"
                        for ln in match.group(2).split(";")
                        if len(ln.strip()) > 0
                    ]
                )
                lines_.append(f"{match.group(3)}")
            else:
                lines_.append(vpline)

            for line_ in lines_:
                assign_str_reset_val_line_regex = RE_RESET_VAL_LINE.search(line_)
                if assign_str_reset_val_line_regex:
                    if assign_str_reset_val_line_regex.group(1):
                        svline = (
                            assign_str_reset_val_line_regex.group(1)
                            + assign_str_reset_val_line_regex.group(3)
                            + assign_str_reset_val_line_regex.group(6)
                        )
                    else:
                        svline = assign_str_reset_val_line_regex.group(
                            3
                        ) + assign_str_reset_val_line_regex.group(6)
                    key_line = assign_str_reset_val_line_regex.group(
                        3
                    ) + assign_str_reset_val_line_regex.group(6)
                    value_line = (
                        assign_str_reset_val_line_regex.group(3)
                        + assign_str_reset_val_line_regex.group(4)
                        + assign_str_reset_val_line_regex.group(6)
                    )
                    g_psv_parser.auto_reset_lines[re.sub(r"\s*", "", key_line)] = (
                        value_line
                    )

                    lhs_assign_str = assign_str_reset_val_line_regex.group(4)
                    lhs_assign_comma_regex = RE_COMMA.search(lhs_assign_str)

                    lhs_assign_str_array = []
                    # If multiple declarations on the same line, then break it
                    if lhs_assign_comma_regex:
                        # removing space, { and }
                        lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                        lhs_assign_str_array = lhs_assign_str.split(",")
                    else:  # Single declaration, then append to the array
                        lhs_assign_str = re.sub(r"[{}\s]", "", lhs_assign_str)
                        lhs_assign_str_array.append(lhs_assign_str)

                    for curr_lhs in lhs_assign_str_array:
                        g_psv_parser.auto_reset_vals[curr_lhs] = (
                            assign_str_reset_val_line_regex.group(5)
                        )
                else:
                    assign_str_reset_val_regex = RE_RESET_VAL.search(line_)
                    if assign_str_reset_val_regex:
                        svline = assign_str_reset_val_regex.group(
                            1
                        ) + assign_str_reset_val_regex.group(3)
                        key_line = svline
                        value_line = (
                            assign_str_reset_val_regex.group(1)
                            + assign_str_reset_val_regex.group(2)
                            + assign_str_reset_val_regex.group(3)
                        )
                        g_psv_parser.auto_reset_lines[re.sub(r"\s*", "", key_line)] = (
                            value_line
                        )
                    else:
                        svline = line_[:]
                svlines.append(f"{svline}\n")

        elif len(svline) > 0:
            svlines.append(f"{svline}\n")

    g_psv_parser.sv_parser.add_parser_mode_directive(svlines)
    string = "".join(svlines)
    syntax_data = g_psv_parser.sv_parser.parse(string)
    if syntax_data is None or syntax_data.errors is None:
        if g_psv_parser.debug:
            with open(
                f"{g_psv_parser.input_file}_posedge_{time.time()}.cst",
                "w",
            ) as cstfile:
                for prefix, _, node in anytree.RenderTree(syntax_data.tree):
                    # print(f"{prefix}{node.to_formatted_string()}", file=cstfile)
                    print(f"{prefix}{repr(node)}", file=cstfile)
                    # print(f"{prefix}{repr(node)}")
                print(file=cstfile)
            print(f"# of verilog lines parsed: {len(svlines)} => No syntax error.")

        if syntax_data is not None and syntax_data.tree is not None:
            g_psv_parser.sv_parser.process(syntax_data)


vp_negedge_item = SkipTo(vp_endnegedge).setParseAction(vp_negedge_item_callback)

vp_negedge_endnegedge = Group(
    vp_negedge + vp_negedge_item("negedge_item") + vp_endnegedge
)("vp_negedge_endnegedge*")

vp_python_begin = vp_pythonbegin_kw + SEMI
vp_python_end = vp_pythonend_kw + SEMI
vp_python_item = SkipTo(vp_python_end)
vp_python_begin_end = Group(
    vp_python_begin + vp_python_item("python_item") + vp_python_end
)("vp_python_begin_end")

vp_python_post_begin = vp_pythonpostbegin_kw + SEMI
vp_python_post_end = vp_pythonpostend + SEMI
vp_python_post_item = SkipTo(vp_python_post_end)
vp_python_post_begin_end = Group(
    vp_python_post_begin + vp_python_post_item("python_post_item") + vp_python_post_end
)("vp_python_post_begin_end")

vp_buildcommand = Group(
    vp_buildcommand_kw
    + Group(SkipTo(SEMI).setParseAction(lambda ts: [t.strip() for t in ts[0].split()]))(
        "build_command"
    )
    + SkipTo(SEMI)
    + SEMI
)("vp_buildcommand")

vp_param = Group(vp_param_kw + SkipTo(SEMI) + SEMI)("vp_param")

vp_include = Group(vp_include_kw + SkipTo(SEMI) + SEMI)("vp_include")

vp_connect = Group(vp_connect_kw + SkipTo(SEMI) + SEMI)("vp_connect")

vp_printtext = Group(vp_printtext_kw + SkipTo(SEMI) + SEMI)("vp_printtext")

vp_printio = Group(vp_printio_kw + SkipTo(SEMI) + SEMI)("vp_printio")

vp_begin_instance = (
    vp_begininstance_kw
    + identifier("module_identifier")
    # + Optional(expr)("module_instance_identifier")
    # + Optional(Combine(identifier + "." + identifier))("module_file")
    + SkipTo(SEMI)
    + SEMI
)
vp_end_instance = vp_endinstance_kw + SEMI
vp_instance_item = (
    # SkipTo(vp_end_instance)
    # AtLineStart("//&")
    # + (
    vp_buildcommand("vp_buildcommand*")
    | vp_param("vp_param*")
    | vp_include("vp_include*")
    | vp_connect("vp_connect*")
    | vp_printtext("vp_printtext*")
    | vp_printio("vp_printio*")
    # )
)


def vp_auto_instance_callback(s, loc, toks):
    global g_psv_parser

    lines = s.split("\n")
    g_psv_parser.parse_auto_instance(lines)


vp_auto_instance = Group(
    vp_begin_instance + ZeroOrMore(vp_instance_item) + vp_end_instance
)("vp_auto_instance").setParseAction(vp_auto_instance_callback)

vp_parser_off = vp_parseroff_kw + Optional(SEMI)
vp_parser_on = vp_parseron_kw + Optional(SEMI)
vp_parser_off_on_item = SkipTo(vp_parser_on)
vp_parser_off_on = Group(
    vp_parser_off + vp_parser_off_on_item("parser_off_on_item") + vp_parser_on
)("vp_parser_off_on")

vp_begin_skip = vp_beginskip_kw + SEMI
vp_end_skip = vp_endskip_kw + SEMI
vp_begin_end_skip_item = SkipTo(vp_end_skip)
vp_begin_end_skip = Group(
    vp_begin_skip + vp_begin_end_skip_item("begin_end_skip_item") + vp_end_skip
)("vp_begin_end_skip")


def vp_force_internal_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.force_internals.append(toks[-2])


vp_force_internal = (vp_force_kw + CaselessLiteral("internal") + SkipTo(SEMI) + SEMI)(
    "vp_force_internal"
).setParseAction(vp_force_internal_callback)


def vp_force_width_callback(s, loc, toks):
    global g_psv_parser

    g_psv_parser.force_widths.append(toks[2])


vp_force_width = (vp_force_kw + CaselessLiteral("width") + SkipTo(SEMI) + SEMI)(
    "vp_force_width*"
).setParseAction(vp_force_width_callback)

vp_force_depth = Group(
    vp_force_kw + CaselessLiteral("depth") + expr("regex") + expr("expression") + SEMI
)("vp_force_depth")

typedef = Group(
    (
        (
            package_import_item("package_import_item")
            | identifier
            | (
                Optional(integer_vector_type)("integer_vector_type")
                + Optional(signed)("signed")
            )
        )
        + ZeroOrMore(packed_dimension)("bitdef")
    )
)("typedef")


def vp_force_port_callback(s, loc, toks):
    global g_psv_parser

    io_dir = toks[1]
    io_str = toks[2]
    io_double_colon_regex = re.compile(r"^(\w*)::(\w+)\b").search(io_str)
    io_double_double_colon_regex = re.compile(r"^(\w+)::(\w+)::(\w+)\b").search(io_str)

    bind_package = "default"
    bind_class = "default"

    if io_double_double_colon_regex:
        bind_package = io_double_double_colon_regex.group(1)
        bind_class = io_double_double_colon_regex.group(2)
        bind_typedef = io_double_double_colon_regex.group(3)

        if bind_package not in g_psv_parser.packages:
            g_psv_parser.load_import_or_include_file(
                "TOP",
                "IMPORT_COMMANDLINE",
                bind_package + ".sv",
            )

        g_psv_parser.binding_typedef("TOP", "FORCE", io_str)
    elif io_double_colon_regex:
        bind_package = io_double_colon_regex.group(1)
        bind_typedef = io_double_colon_regex.group(2)

        if bind_package not in g_psv_parser.packages:
            g_psv_parser.load_import_or_include_file(
                "TOP",
                "IMPORT_COMMANDLINE",
                bind_package + ".sv",
            )

        g_psv_parser.binding_typedef(
            "TOP", "FORCE", io_str
        )  # io_str '[CCP1_CNOC_NUM-1:0][$bits(ath_pkg::control_noc_t)-1:0]   ccp1_mb_cnoc'

    g_psv_parser.parse_ios("TOP", "FORCE", io_dir, io_str)


# &Force  input  [signed]  [BITDEF]  <port_name>  [DEPTHDEF];
# &Force  output  [wire|reg|logic]  [signed]  [BITDEF]  <port_name> [DEPTHDEF];
vp_force_port = (vp_force_kw + port_direction("port_direction") + SkipTo(SEMI) + SEMI)(
    "vp_force_port"
).setParseAction(vp_force_port_callback)

vp_force_wire = Group(
    vp_force_kw
    + CaselessLiteral("wire")
    + Optional(signed)("signed")
    + ZeroOrMore(packed_dimension)("packed_dimension*")
    + identifier("wire_identifier")
    + Optional(expr)("depthdef")
    + SEMI
)("vp_force_wire")

vp_force_reg = Group(
    vp_force_kw
    + CaselessLiteral("reg")
    + Optional(signed)("signed")
    + ZeroOrMore(packed_dimension)("packed_dimension*")
    + identifier("reg_identifier")
    + Optional(expr)("depthdef")
    + SEMI
)("vp_force_reg")


def vp_force_others_callback(s, loc, toks):
    global g_psv_parser

    # print(f"s: {s}")
    if "type" in toks:
        declare_type = toks["type"]
    else:
        declare_type = "logic"

    declare_str = ""
    if "signed" in toks:
        declare_str += " signed"
    if "packed_dimension" in toks and len(toks["packed_dimension"]):
        packed_dimensions = get_result_text(toks["packed_dimension"])
        # print(f"packed_dimensions: {packed_dimensions}")
        # print(f"toks['packed_dimension'].asList(): {toks['packed_dimension'].asList()}")
        declare_str += "".join(packed_dimensions)

    if "logic_identifier" in toks:
        declare_str += f" {','.join(toks['logic_identifier'])}"

    if "depthdef" in toks:
        declare_str += toks["depthdef"]

    # declare_str = " ".join(get_result_text(toks[2:-1]))
    g_psv_parser.parse_reg_wire_logic(
        "TOP",
        "FORCE",
        declare_type,
        declare_str,
        "",
        "",
    )


vp_force_others = (
    vp_force_kw
    + (CaselessLiteral("logic") | CaselessLiteral("reg") | CaselessLiteral("wire"))(
        "type"
    )
    + Optional(signed)("signed")
    + ZeroOrMore(packed_dimension)("packed_dimension*")
    + Group(delimitedList(identifier))("logic_identifier")
    + Optional(SkipTo(SEMI))("depthdef")
    + SEMI
)("vp_force_others").setParseAction(vp_force_others_callback)


def vp_force_bind_callback(s, loc, toks):
    global g_psv_parser

    typedef = " ".join(toks[2])
    variable = ",".join(toks[3])
    bind_str = typedef + " " + variable
    g_psv_parser.binding_typedef("TOP", "FORCE", bind_str)

    g_psv_parser.update_typedef_regs("logic", "FORCE", variable)


vp_force_bind = (
    vp_force_kw
    + CaselessLiteral("bind")
    + typedef("typedef")
    # + Group(delimitedList(extended_identifier)("variable_identifier"))
    + Group(SkipTo(SEMI))
    + SEMI
)("vp_force_bind").setParseAction(vp_force_bind_callback)


def vp_pkg2assign_callback(s, loc, toks):
    global g_psv_parser

    pkg2assign_regex = RE_PKG2ASSIGN.search(" ".join(toks))
    assign2pkg_regex = RE_ASSIGN2PKG.search(" ".join(toks))

    if pkg2assign_regex or assign2pkg_regex:
        g_psv_parser.parse_pkg2assign_assign2pkg(pkg2assign_regex, assign2pkg_regex)


vp_pkg2assign = (
    vp_pkg2assign_kw
    + LPAR
    + dblQuotedString("prefix")
    + COMMA
    + dblQuotedString("pkgmember")
    + COMMA
    + dblQuotedString("bus")
    + RPAR
    + SEMI
)("vp_pkg2assign").setParseAction(vp_pkg2assign_callback)


def vp_assign2pkg_callback(s, loc, toks):
    global g_psv_parser

    pkg2assign_regex = RE_PKG2ASSIGN.search(" ".join(toks))
    assign2pkg_regex = RE_ASSIGN2PKG.search(" ".join(toks))

    if pkg2assign_regex or assign2pkg_regex:
        gen_lines = g_psv_parser.parse_pkg2assign_assign2pkg(
            pkg2assign_regex, assign2pkg_regex
        )


vp_assign2pkg = (
    vp_assign2pkg_kw
    + LPAR
    + dblQuotedString("prefix")
    + COMMA
    + dblQuotedString("pkgmember")
    + COMMA
    + dblQuotedString("bus")
    + RPAR
    + SEMI
)("vp_assign2pkg").setParseAction(vp_assign2pkg_callback)

vp_python_single_line = Group(vp_python_kw + SkipTo(lineEnd())("python_command"))(
    "vp_python_single_line"
)


def vp_include_callback(s, loc, toks):
    global g_psv_parser

    if g_psv_parser is not None:
        g_psv_parser.sub_include_files_list.extend(toks)


vp_include = Group(
    vp_include_kw
    + Group(SkipTo(SEMI).setParseAction(vp_include_callback))("include_files")
    + SEMI
)("vp_include")


def vp_depend_callback(s, loc, toks):
    global g_psv_parser

    if g_psv_parser is not None:
        targets = re.split("\s*,\s*", re.sub(r'"', "", toks[0]))
        for target in targets:
            target = target.strip()
            g_psv_parser.dependencies["depends"].append(
                {re.sub(r"##", "//", target): {}}
            )


vp_depend = Group(
    vp_depend_kw
    + Group(SkipTo(SEMI).setParseAction(vp_depend_callback))("external_targets")
    + SEMI
)("vp_depend")

vp_to_skip = Group(
    (
        vp_fsm_kw
        | vp_pipe_kw
        | vp_ecc_memgen_kw
        | vp_hls_memgen_kw
        | vp_memgen_kw
        | vp_clockgen_kw
        | vp_clockgen_v2_kw
        | vp_clockresetgen_kw
        | vp_artclockresetgen_kw
        | vp_syncgen_kw
        | vp_syncgen3_kw
        | vp_fb_enflop_kw
        | vp_fb_enflop_rs_kw
        | vp_fb_enflop_rst_kw
    )
    + SkipTo(SEMI)("vp_item")
    + SEMI
)("vp_to_skip")

to_eol = Suppress(SkipTo(lineEnd(), include=True))

vp_bnf = (
    # AtLineStart("//&")
    # + (
    vp_module
    | vp_moduledef
    | vp_ports
    | vp_logics
    | vp_regs
    | vp_wires
    | vp_gendrive0
    | vp_gendrivez
    | vp_gendrive0andz
    | vp_gendrive0_parameter
    | vp_genparam
    | vp_genparam_no_gen_rtl
    | vp_gennoifdefdrive0
    | vp_begin_skip_ifdef("vp_begin_skip_ifdef*")
    | vp_end_skip_ifdef("vp_end_skip_ifdef*")
    | vp_async_reset
    | vp_sync_reset
    | vp_clock
    | vp_posedge_endposedge("vp_posedge_endposedge*")
    | vp_negedge_endnegedge("vp_posedge_endposedge*")
    | vp_python_begin_end("vp_python_begin_end*")
    | vp_python_post_begin_end("vp_python_post_begin_end*")
    | vp_auto_instance("vp_auto_instance*")
    | vp_parser_off_on("vp_parser_off_on*")
    | vp_begin_end_skip("vp_begin_end_skip*")
    | vp_force_port("vp_force_port*")
    | vp_force_internal("vp_force_internal*")
    | vp_force_width("vp_force_width*")
    | vp_force_depth("vp_force_depth*")
    | vp_force_others("vp_force_others*")
    | vp_force_bind("vp_force_bind*")
    | vp_pkg2assign("vp_pkg2assign*")
    | vp_assign2pkg("vp_assign2pkg*")
    | vp_python_single_line("vp_python_single_line*")
    | vp_include("vp_include*")
    | vp_depend("vp_depend*")
    | vp_to_skip("vp_to_skip*")
)[1, ...] + StringEnd()


# Ignoring comments seems to slow down the run time significantly
vp_bnf.ignore(dblSlashComment)
vp_bnf.ignore(cppStyleComment)


class veripy_parser:
    def __init__(self, psv_parser):
        global g_psv_parser
        g_psv_parser = psv_parser
        self.psv_parser = psv_parser

        try:
            ParserElement.enable_packrat()
        except Exception:
            pass

    def parse(self, string, index, construct):
        """
        Function to parsed a list of veripy constructs in specific veripy construct section
        """
        error_msg = None
        tokens = []
        try:
            time1 = time.perf_counter()

            tokens = vp_bnf.parseString(string)
            # tokens = self.vp_bnf.parse_file(self.input_file)
            time2 = time.perf_counter()
            if self.psv_parser.debug:
                print(f"\nparse_vp() - Total run time: {time2 - time1}")

        except ParseException as pe:
            time2 = time.perf_counter()
            print(f"\nparse_vp() - Total run time: {time2 - time1}")
            msg = f"Veripy syntax error - Line: {pe.line}, Lineno: {construct['start_line'] + pe.lineno}, Col: {pe.col}."
            print(msg)
            error_msg = msg

        return tokens, error_msg

    def parse_and_process(self, index, construct):
        """
        Function to parsed and process a construct section that contains systemverilog
         constructs, and report syntax errors with details if any.
        """
        error_count = 0

        string = "\n".join([l.strip() for l in construct["lines"]])
        tokens, error_msg = self.parse(string, index, construct)
        if len(tokens) > 0 or len(construct["lines"]) == 0:
            if self.psv_parser.debug:
                print(
                    f"# of veripy lines parsed: {len(construct['lines'])} => # tokens: {len(tokens)}."
                )
        else:
            error_count += 1
            print(
                f"Error - Parse # of veripy lines: {len(construct['lines'])} => Token(s): {tokens}.\n"
            )
            if error_msg is not None:
                with open(
                    f"{self.psv_parser.input_file}_{construct['context']}_{index}.error",
                    "w",
                ) as errfile:
                    print(f"{error_msg}", file=errfile)

        return error_count
