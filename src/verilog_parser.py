import re
import sys
import time

import anytree
from verilog_syntax_check import BranchNode, Node, TokenNode, VeribleVerilogSyntax

from .verilog_parser_utils import indent, unindent, vp_map


class verilog_parser:
    def __init__(self, psv_parser):
        self.psv_parser = psv_parser

    def add_parser_mode_directive(self, lines):
        """
        Function to check the systemverilog constructs and add required header(s) in order to run
        verible sytnax parser
        """
        has_module_declaration = -1
        has_endmodule_declaration = -1
        has_package_declaration = -1
        has_endpackage_declaration = -1

        for line_no, line in enumerate(lines):
            if re.search(r"^\s*module\b", line):
                has_module_declaration = line_no
            if re.search(r"^\s*endmodule\b", line):
                has_endmodule_declaration = line_no
            if re.search(r"^\s*package\b", line):
                has_package_declaration = line_no
            if re.search(r"^\s*endpackage\b", line):
                has_endpackage_declaration = line_no

        inserted_parse_as_module_body = False
        if has_package_declaration == -1 and has_endpackage_declaration == -1:
            # no module declaration
            if has_module_declaration == -1:
                # has endmodule declaration
                if has_endmodule_declaration >= 0:
                    # comment out the endmodule declaration
                    lines[has_endmodule_declaration] = (
                        "//&" + lines[has_endmodule_declaration]
                    )
                # sv lines not empty and no insertion of parse_as_module_body
                if len(lines) > 0 and not inserted_parse_as_module_body:
                    lines.insert(0, "// verilog_syntax: parse-as-module-body\n")
                    inserted_parse_as_module_body = True
            # module declaration but no endmodule declaration
            elif has_endmodule_declaration == -1:
                # append endmodule declaration
                lines.append("endmodule")

        if has_module_declaration == -1 and has_endmodule_declaration == -1:
            # no package declaration
            if has_package_declaration == -1:
                # has endpackage declaration
                if has_endpackage_declaration >= 0:
                    # comment out the endpackage declaration
                    lines[has_endpackage_declaration] = (
                        "//&" + lines[has_endpackage_declaration]
                    )
                # sv lines not empty and no insertion of parse_as_module_body
                if len(lines) > 0 and not inserted_parse_as_module_body:
                    lines.insert(0, "// verilog_syntax: parse-as-module-body\n")
                    inserted_parse_as_module_body = True

    def parse(self, string):
        """
        Function to parsed a list of systemverilog constructs in specific systemverilog construct section
        """
        options = {}
        options["gen_tree_json"] = True

        verible_verilog_syntax = VeribleVerilogSyntax("verible-verilog-syntax")

        time1 = time.perf_counter()
        sd = verible_verilog_syntax.parse_string(string, options)
        time2 = time.perf_counter()

        if self.psv_parser.debug:
            print(f"\nparse_sv() - Total run time: {time2 - time1}")

        return sd

    def get_map(self, node, map, recursive=False):
        if not isinstance(node, BranchNode):
            return None

        if map is not None:
            if not isinstance(map, dict):
                print(f"Node: {node}, map: {map}")
                return None

            for map_key in map:
                if node.tag == map_key:
                    return map[map_key]

            if recursive:
                for map_key in map:
                    returned_map = self.get_map(node, map[map_key], recursive)
                    if returned_map:
                        return returned_map
                    else:
                        return None
        return None

    def traverse_veripy_nodes(self, node, node_map, parser):
        if isinstance(node, TokenNode):
            return

        # print(f"{indent_spaces()}[")
        indent()
        for child_node in node.iter_find_all(
            lambda n: isinstance(n, Node) and n.parent == node
        ):
            child_node_map = self.get_map(child_node, node_map, False)
            if child_node_map:
                # print(f"{indent_spaces()}Node: {child_node}, veripy parser map: {child_node_map.keys()}\n")

                if "func" in child_node_map:
                    child_node_map["func"](child_node, child_node_map, parser)

                self.traverse_veripy_nodes(child_node, child_node_map, parser)

                if "post_func" in child_node_map:
                    child_node_map["post_func"](child_node, child_node_map, parser)

            # else:
            #     print(f"{indent_spaces()}Node: {child_node}, veripy parser map: None\n")

            # self.traverse_veripy_nodes(child_node, child_node_map)

        unindent()
        # print(f"{indent_spaces()}]")

    def process(self, syntax_data):
        """
        Function to process the systemverilog cst (concrete syntax tree) after successfully parsing
        specific systemverilog construct section
        """
        if self.psv_parser.debug:
            print("\nStart of processing sv ...")
        time1 = time.perf_counter()
        root = syntax_data.tree
        root_map = self.get_map(root, vp_map, True)

        # print(f"Root node: {root}, Root Map: {root_map}\n")
        if root_map is None:
            print(f"Error - No veripy parser map found for node: {root}")
            sys.exit(1)

        self.traverse_veripy_nodes(root, root_map, self.psv_parser)
        time2 = time.perf_counter()

        if self.psv_parser.debug:
            print(f"process_sv() - Total run time: {time2 - time1}")

    def parse_and_process(self, index, construct):
        """
        Function to parsed and process a construct section that contains systemverilog
         constructs, and report syntax errors with details if any.
        """
        error_count = 0

        self.add_parser_mode_directive(construct["lines"])
        string = "\n".join([l.strip() for l in construct["lines"]])
        syntax_data = self.parse(string)

        if syntax_data is None or syntax_data.errors is None:
            if self.psv_parser.debug and syntax_data is not None and syntax_data.tree:
                with open(
                    f"{self.psv_parser.input_file}_{construct['context']}_{index}.cst",
                    "w",
                ) as cstfile:
                    for prefix, _, node in anytree.RenderTree(syntax_data.tree):
                        # print(f"{prefix}{node.to_formatted_string()}", file=cstfile)
                        print(f"{prefix}{repr(node)}", file=cstfile)
                        # print(f"{prefix}{repr(node)}")
                    print(file=cstfile)
                print(
                    f"# of verilog lines parsed: {len(construct['lines'])} => No syntax error."
                )

            if syntax_data is not None and syntax_data.tree is not None:
                self.process(syntax_data)

        else:
            with open(
                f"{self.psv_parser.input_file}_{construct['context']}_{index}.error",
                "w",
            ) as errfile:
                if syntax_data is not None and syntax_data.errors:
                    syntax_errors = [
                        {
                            "column": error.column + 2,
                            "line": error.line + 1,
                            "text": error.message,
                            "phase": error.phase,
                        }
                        for error in syntax_data.errors
                    ]
                    # print(f"Syntax errors: {syntax_errors}")
                    for syntax_error in syntax_errors:
                        lines = construct["lines"]
                        line_no = syntax_error["line"]
                        print(
                            f"{syntax_error}: '{lines[line_no - 1]}'",
                            file=errfile,
                        )
                        error_count += 1
                    print(
                        f"Error - Parse # of verilog lines: {len(construct['lines'])} => Syntax error(s): {syntax_errors}."
                    )
                    if self.psv_parser.module_name is not None:
                        construct_file = f"{self.psv_parser.module_name}.{index}.sv"
                        with open(construct_file, "w") as cf:
                            cf.writelines("\n".join(construct["lines"]))
                        print(
                            f"Review the file {construct_file} to inspect the detailed syntax error(s).\n"
                        )
        return error_count
