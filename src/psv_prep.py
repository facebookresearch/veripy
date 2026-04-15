import re
import sys

from .regex import (
    RE_CUSTOM_STUB_DEF,
    RE_TICK_DEFINE,
    RE_TICK_ELSE,
    RE_TICK_ELSIF,
    RE_TICK_ENDIF,
    RE_TICK_IFDEF,
    RE_TICK_IFDEF_ENABLE_CUSTOM_STUB,
    RE_TICK_IFNDEF,
    RE_TICK_INCLUDE,
    RE_TICK_UNDEF,
)

# For preparing PSV
RE_VLP_BLOCK_COMMENT_BEGIN_BEGIN = re.compile(r"^\/\*")
RE_VLP_BLOCK_COMMENT_END_END = re.compile(r"\*\/$")
RE_VLP_BLOCK_COMMENT_BEGIN_END = re.compile(r"^(.*)\/\*(.*)\*\/(.*)")
RE_VLP_BLOCK_COMMENT_BEGIN = re.compile(r"^(.+)\/\*")
RE_VLP_BLOCK_COMMENT_END = re.compile(r"\*\/(.+)$")

RE_DBL_SLASH_COMMENT_BEGIN = re.compile(r"^\s*\/{2,}")
RE_DBL_SLASH_COMMENT = re.compile(r"^(.+)\/{2,}")

sv_construct_stack = []
vp_construct_stack = []

SV_CONSTRUCT_BEGIN_END = {
    "generate": "endgenerate",
    "begin": "end",
}

VP_CONSTRUCT_END_BEGIN = {
    "&parseron": "&parseroff",
    "&endskip": "&beginskip",
    "&endskipifdef": "&beginskipifdef",
    "&pythonend": "&pythonbegin",
    "&pythonpostend": "&pythonpostbegin",
    "&endposedge": "&posedge",
    "&endnegedge": "&negedge",
    "&endinstance": "&begininstance",
}

VP_CONSTRUCT_BEGIN_END = {v: k for k, v in VP_CONSTRUCT_END_BEGIN.items()}

VP_KEYWORDS = [
    "&Module",
    "&ModuleDef",
    "&Ports",
    "&Logics",
    "&Regs",
    "&Wires",
    "&GenDrive0",
    "&GenDriveZ",
    "&GenDrive0andZ",
    "&GenDrive0_parameter",
    "&GenParam",
    "&GenParamNoGenRtl",
    "&GenNoifdefDrive0",
    "&ParserOff",
    "&ParserOn",
    "&BeginSkip",
    "&EndSkip",
    "&BeginSkipIfdef",
    "&EndSkipIfdef",
    "&PythonBegin",
    "&PythonEnd",
    "&PythonPostBegin",
    "&PythonPostEnd",
    "&Python",
    "&BeginInstance",
    "&EndInstance",
    "&AsyncReset",
    "&SyncReset",
    "&Clock",
    "&PosEdge",
    "&EndPosEdge",
    "&NegEdge",
    "&EndNegEdge",
    "&Force",
    "&Force internal",
    "&Force width",
    "&Force depth",
    "&Force wire",
    "&Force reg",
    "&Force logic",
    "&Force bind",
    "&Pkg2Assign",
    "&Assign2Pkg",
    "&Param",
    "&Include",
    "&Depend",
    "&Connect",
    "&BuildCommand",
    "&PrintText",
    "&PrintIO",
    # Veripy constructs to skip
    "&Fsm",
    "&Pipe",
    "&ECC_Memgen",
    "&HLS_Memgen",
    "&Memgen",
    "&ClockGen",
    "&ClockGen_V2",
    "&ClockResetGen",
    "&ArtClockResetGen",
    "&SyncGen",
    "&SyncGen3",
    "&FB_EnFlop",
    "&FB_EnFlop_RS",
    "&FB_EnFlop_RST",
]


class psv_prep:
    def __init__(self, psv_parser):
        self.psv_parser = psv_parser
        self.task_context = False

    def parse_compiler_directives(self, line, line_no, construct):
        ################################################################################
        # `include processing
        ################################################################################
        tick_include_regex = RE_TICK_INCLUDE.search(line)

        if tick_include_regex:
            if self.psv_parser.tick_ifdef_en:
                self.psv_parser.load_import_or_include_file(
                    "TOP", "INCLUDE", tick_include_regex.group(1)
                )
            return True

        tick_define_regex = RE_TICK_DEFINE.search(line)

        if tick_define_regex:
            if self.psv_parser.tick_ifdef_en:
                tick_def_exp = tick_define_regex.group(1)
                tick_def_exp = re.sub(r"\s*\(", " (", tick_def_exp, 1)
                self.psv_parser.tick_def_proc("TOP", tick_def_exp)
            return True

        tick_undef_regex = RE_TICK_UNDEF.search(line)

        if tick_undef_regex:
            if tick_undef_regex.group(1) not in self.psv_parser.tick_defines:
                print(
                    "\nWarning: Unable to find #define to undef\n"
                    + tick_undef_regex.group(0)
                    + "\n"
                )
            else:
                del self.psv_parser.tick_defines[tick_undef_regex.group(1)]
                self.psv_parser.dbg(
                    "  # Removed #define " + tick_undef_regex.group(1) + " for undef"
                )

            return True

        ################################################################################
        # `ifdef/endif ENABLE_CUSTOM_STUB processing
        ################################################################################
        tick_ifdef_enable_custom_stub_regex = RE_TICK_IFDEF_ENABLE_CUSTOM_STUB.search(
            line
        )

        if tick_ifdef_enable_custom_stub_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.enable_custom_stub = 1
            return True
        elif self.psv_parser.enable_custom_stub == 1:
            if not self.psv_parser.tick_ifdef_dis:
                if RE_TICK_ENDIF.search(line):
                    self.psv_parser.enable_custom_stub = 0
                else:
                    match = re.match(RE_CUSTOM_STUB_DEF, line)
                    if match:
                        def_line = {
                            "output_port": match.group("oport"),
                            "rhs_value": match.group("rhs_value"),
                            "line": line,
                        }
                    else:
                        def_line = line
                    self.psv_parser.enable_custom_stub_defs.append(def_line)
                    # construct["lines"].append(line)
            return True

        tick_ifdef_regex = RE_TICK_IFDEF.search(line)
        tick_ifndef_regex = RE_TICK_IFNDEF.search(line)
        tick_elif_regex = RE_TICK_ELSIF.search(line)
        tick_else_regex = RE_TICK_ELSE.search(line)
        tick_endif_regex = RE_TICK_ENDIF.search(line)

        if self.task_context and (
            tick_ifdef_regex
            or tick_ifndef_regex
            or tick_elif_regex
            or tick_else_regex
            or tick_endif_regex
        ):
            construct["lines"].append(line)
            construct["end_line"] = line_no
            return True

        if tick_ifdef_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.tick_ifdef_en = self.psv_parser.tick_ifdef_proc(
                    "ifdef", tick_ifdef_regex.group(1)
                )
            return True
        elif tick_ifndef_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.tick_ifdef_en = self.psv_parser.tick_ifdef_proc(
                    "ifndef", tick_ifndef_regex.group(1)
                )
            return True
        elif tick_elif_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.tick_ifdef_en = self.psv_parser.tick_ifdef_proc(
                    "elif", tick_elif_regex.group(1)
                )
            return True
        elif tick_else_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.tick_ifdef_en = self.psv_parser.tick_ifdef_proc(
                    "else", ""
                )
            return True
        elif tick_endif_regex:
            if not self.psv_parser.tick_ifdef_dis:
                self.psv_parser.tick_ifdef_en = self.psv_parser.tick_ifdef_proc(
                    "endif", ""
                )
            return True

        return False

    def is_orphaned_vp(self, line):
        end_begin_keys = {k.lower() for k in VP_CONSTRUCT_END_BEGIN.keys()}
        for vp_keyword in end_begin_keys:
            if re.match(f"^\s*{vp_keyword}\\b", line.lower()):
                return True
        return False

    def is_vp_context_begin(self, line):
        begin_and_keys = {k.lower() for k in VP_CONSTRUCT_BEGIN_END.keys()}
        end_begin_keys = {k.lower() for k in VP_CONSTRUCT_END_BEGIN.keys()}
        all_keys = {k.strip(";").lower() for k in VP_KEYWORDS}
        for vp_keyword in begin_and_keys:
            if re.match(f"^\s*{vp_keyword}\\b", line.lower()):
                vp_construct_stack.append(vp_keyword)
                return True

        for vp_keyword in all_keys.difference(begin_and_keys.union(end_begin_keys)):
            if re.match(f"^\s*{vp_keyword}\\b", line.lower()):
                vp_construct_stack.append(vp_keyword)
                return True
        return False

    def is_vp_context_end(self, line):
        if len(vp_construct_stack) > 0:
            vp_construct_begin = vp_construct_stack[-1]

            if (
                vp_construct_begin in VP_CONSTRUCT_BEGIN_END.keys()
                and vp_construct_begin in line
            ):
                return False

            if vp_construct_begin not in VP_CONSTRUCT_BEGIN_END.keys():
                if re.search(r";", line):
                    vp_construct_stack.pop()
                    return True
            elif re.match(
                f"^\s*{VP_CONSTRUCT_BEGIN_END[vp_construct_begin]}", line.lower()
            ):
                vp_construct_stack.pop()
                return True
            else:
                return False
        else:
            return True

    def is_sv_construct_begin(self, line):
        line = re.sub(r"\/\/.*", "", line)
        begin_and_keys = {k.lower() for k in SV_CONSTRUCT_BEGIN_END.keys()}
        for vp_keyword in begin_and_keys:
            if re.search(f"\\b{vp_keyword}\\b", line):
                sv_construct_stack.append(vp_keyword)
                return True

        return False

    def is_sv_construct_end(self, line):
        line = re.sub(r"\/\/.*", "", line)
        if len(sv_construct_stack) == 0:
            if re.search(r";\s*$", line):
                return True
            else:
                if line in SV_CONSTRUCT_BEGIN_END.values():
                    return True
                else:
                    return False
        else:
            sv_construct_begin = sv_construct_stack[-1]

            if re.search(f"\\b{SV_CONSTRUCT_BEGIN_END[sv_construct_begin]}\\b", line):
                sv_construct_stack.pop()
                return True
            else:
                return False

    def prepare_psv(self, lines):
        """
        Function to build mixed sv/vp construct sections dynamically based on occurrence order in expanded psv
        """
        # mixed veripy sv/vp constructs
        constructs = []
        # default to sv construct
        construct = {
            "context": "sv",
            "start_line": -1,
            "end_line": -1,
            "lines": [],
        }
        sv_not_end = False
        continued_sv_construct = None

        has_module_declaration = -1
        has_endmodule_declaration = -1
        has_package_declaration = -1
        has_endpackage_declaration = -1

        # Either vp context or sv context
        is_vp_context = False
        # begin of c-style comment line number
        block_comment_line = -1

        for line_no, line in enumerate(lines):
            line = re.sub(r"\s+", " ", line)
            line = re.sub(r"\s*$", "", line)
            if re.match(r"^\s*task\s+.*;", line):
                self.task_context = True
            elif re.match(r"^\s*endtask\s+.*", line):
                self.task_context = False

            if (
                not is_vp_context
                and block_comment_line < 0
                and self.parse_compiler_directives(line, line_no, construct)
            ):
                continue

            if not self.psv_parser.tick_ifdef_dis and not self.psv_parser.tick_ifdef_en:
                continue

            if construct is None:
                print(f"Internal error: current construct is None.")
                sys.exit(1)

            # Empty lines
            if len(line.strip()) == 0:
                # construct["lines"].append(line)
                # construct["end_line"] = line_no
                continue

            # dbl_slash_comment starting at beginning of line
            dbl_slash_comment_begin = re.match(RE_DBL_SLASH_COMMENT_BEGIN, line)
            # dbl_slash_comment not starting at beginning of line
            dbl_slash_comment = re.match(RE_DBL_SLASH_COMMENT, line)

            # block comment starting at beginning of line
            block_comment_begin_begin = re.match(RE_VLP_BLOCK_COMMENT_BEGIN_BEGIN, line)
            # block comment ending to end of line
            block_comment_end_end = re.search(RE_VLP_BLOCK_COMMENT_END_END, line)

            # block comment begin and end at the same line with extra text at both ends
            block_comment_begin_end = re.match(RE_VLP_BLOCK_COMMENT_BEGIN_END, line)
            # block comment not starting at beginning of line
            block_comment_begin = re.match(RE_VLP_BLOCK_COMMENT_BEGIN, line)
            # block comment not ending to end of line
            block_comment_end = re.search(RE_VLP_BLOCK_COMMENT_END, line)

            if dbl_slash_comment_begin:  # // lines
                construct["lines"].append(line)
                construct["end_line"] = line_no
                continue
            elif block_comment_begin_begin:  # ^/* lines
                if not block_comment_end_end:
                    block_comment_line = line_no  # begin of block comment
                continue
            elif block_comment_line < 0:  # not in block comment context
                # begin of vp context
                if not is_vp_context and self.is_vp_context_begin(line):
                    if construct["context"] == "sv":
                        if sv_not_end == True and continued_sv_construct is None:
                            continued_sv_construct = construct
                        elif len(construct["lines"]) > 0:
                            constructs.append(construct)

                    is_vp_context = True
                    construct = {
                        "context": "vp",
                        "start_line": line_no,
                        "end_line": -1,
                        "lines": [],
                    }
                else:
                    if construct["context"] == "vp" and construct in constructs:
                        if sv_not_end and continued_sv_construct:
                            construct = continued_sv_construct
                            sv_not_end = False
                            continued_sv_construct = None
                        else:
                            construct = {
                                "context": "sv",
                                "start_line": line_no,
                                "end_line": -1,
                                "lines": [],
                            }

                if dbl_slash_comment:  # ^(.*)// lines
                    connect_regex = re.search(
                        r"(&connect[^;]*;)(\s*(\/{2,}.*)*;?)", line, re.I
                    )
                    if connect_regex:
                        line = (
                            re.sub(r"\/\/", "##", connect_regex.group(1))
                            + " "
                            + connect_regex.group(2)
                        )
                    param_regex = re.search(
                        r"(&param[^;]*;)(\s*(\/{2,}.*)*;?)", line, re.I
                    )
                    if param_regex:
                        line = (
                            re.sub(r"\/\/", '""', param_regex.group(1))
                            + " "
                            + param_regex.group(2)
                        )
                    depend_regex = re.search(
                        r"(&depend[^;]*;)(\s*(\/{2,}.*)*;?)", line, re.I
                    )
                    if depend_regex:
                        line = (
                            re.sub(r"\/\/", "##", depend_regex.group(1))
                            + " "
                            + depend_regex.group(2)
                        )
                    force_regex = re.search(
                        r"(&force[^;]*;)(\s*(\/{2,}.*)*;?)", line, re.I
                    )
                    if force_regex:
                        line = force_regex.group(1)
                        self.psv_parser.ports_w_comment[line] = force_regex.group(2)

                elif block_comment_begin_end:  # ^(.+)/* ... */(.+)$ lines
                    line = " ".join(
                        [
                            block_comment_begin_end.group(1),
                            block_comment_begin_end.group(3),
                        ]
                    )
                    if len(line.strip()) == 0:
                        continue
                elif block_comment_begin:  # ^(.+)/* lines
                    if not block_comment_end_end:
                        block_comment_line = line_no
                    line = block_comment_begin.group(1)
                    if len(line.strip()) == 0:
                        continue
                if is_vp_context:
                    construct["lines"].append(line)
                    construct["end_line"] = line_no

                    if self.is_vp_context_end(line):
                        is_vp_context = False
                        constructs.append(construct)
                else:
                    if re.match(r"^\s*&", line) and self.is_orphaned_vp(line):
                        continue

                    construct["lines"].append(line)
                    construct["end_line"] = line_no

                    sv_construct_begin = self.is_sv_construct_begin(line)
                    if construct["start_line"] == -1 or len(construct["lines"]) == 0:
                        construct["start_line"] = line_no

                    sv_construct_end = self.is_sv_construct_end(line)
                    sv_not_end = len(sv_construct_stack) != 0 or (
                        not sv_construct_end and not re.search(r";\s*$", line)
                    )
            # block_comment_line >= 0
            else:
                if block_comment_end or block_comment_end_end:  # */ lines
                    block_comment_line = -1
                    if block_comment_end:
                        construct["lines"].append(block_comment_end.group(1))
                    else:
                        continue

        if construct["context"] == "vp":
            vp_kws = vp_construct_stack[:]
            for vp_kw in vp_kws:
                if vp_kw in VP_CONSTRUCT_BEGIN_END:
                    construct["lines"].append(f"{VP_CONSTRUCT_BEGIN_END[vp_kw]};")
                vp_construct_stack.pop()

        if construct["context"] == "sv":
            sv_kws = sv_construct_stack[:]
            for sv_kw in sv_kws:
                if sv_kw in SV_CONSTRUCT_BEGIN_END:
                    construct["lines"].append(f"{SV_CONSTRUCT_BEGIN_END[sv_kw]}")
                sv_construct_stack.pop()

        if (
            continued_sv_construct is not None
            and continued_sv_construct not in constructs
        ):
            constructs.append(continued_sv_construct)

        if construct is not None and construct not in constructs:
            constructs.append(construct)

        if self.psv_parser.debug:
            with open(self.psv_parser.temporary_file, "w") as pfile:
                for line in lines:
                    line = line.rstrip()
                    pfile.write(line + "\n")

        return constructs
        # psv_preper = psv_prep(self)
        # psv_preper.prepare_psv()
