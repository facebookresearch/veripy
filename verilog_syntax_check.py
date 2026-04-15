#!/usr/local/bin/asicpy

import argparse
import collections
import dataclasses
import json
import os
import re
import subprocess
import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Union

import anytree

_CSI_SEQUENCE = re.compile("\033\\[.*?m")


def _colorize(formats: List[str], strings: List[str]) -> str:
    result = ""
    fi = 0
    for s in strings:
        result += f"\033[{formats[fi]}m{s}\033[0m"
        fi = (fi + 1) % len(formats)
    return result


# Type aliases

CallableFilter = Callable[["Node"], bool]
KeyValueFilter = Dict[str, Union[str, List[str]]]
TreeIterator = Union["_TreeIteratorBase", anytree.iterators.AbstractIter]


# Custom tree iterators with an option for reverse children iteration


class _TreeIteratorBase:
    def __init__(
        self,
        tree: "Node",
        filter_: Optional[CallableFilter] = None,
        reverse_children: bool = False,
    ):
        self.tree = tree
        self.reverse_children = reverse_children
        self.filter_ = filter_ if filter_ else lambda n: True

    def __iter__(self) -> Iterable["Node"]:
        yield from self._iter_tree(self.tree)

    def _iter_children(self, tree: Optional["Node"]) -> Iterable["Node"]:
        if not tree or not hasattr(tree, "children"):
            return []
        return tree.children if not self.reverse_children else reversed(tree.children)

    def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
        raise NotImplementedError("Subclass must implement '_iter_tree' method")


class PreOrderTreeIterator(_TreeIteratorBase):
    def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
        if self.filter_(tree):
            yield tree
        for child in self._iter_children(tree):
            yield from self._iter_tree(child)


class PostOrderTreeIterator(_TreeIteratorBase):
    def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
        for child in self._iter_children(tree):
            yield from self._iter_tree(child)
        if self.filter_(tree):
            yield tree


class LevelOrderTreeIterator(_TreeIteratorBase):
    def _iter_tree(self, tree: Optional["Node"]) -> Iterable["Node"]:
        queue = collections.deque([tree])
        while len(queue) > 0:
            n = queue.popleft()
            if self.filter_(n):
                yield n
            queue.extend(self._iter_children(n))


class Node(anytree.NodeMixin):
    """Base VeribleVerilogSyntax syntax tree node.

    Attributes:
      parent (Optional[Node]): Parent node.
    """

    def __init__(self, parent: Optional["Node"] = None):
        self.parent = parent

    @property
    def syntax_data(self) -> Optional["SyntaxData"]:
        """Parent SyntaxData"""
        return self.parent.syntax_data if self.parent else None

    @property
    def start(self) -> Optional[int]:
        """Byte offset of node's first character in source text"""
        raise NotImplementedError("Subclass must implement 'start' property")

    @property
    def end(self) -> Optional[int]:
        """Byte offset of a character just past the node in source text."""
        raise NotImplementedError("Subclass must implement 'end' property")

    @property
    def text(self) -> str:
        """Source code fragment spanning all tokens in a node."""
        start = self.start
        end = self.end
        sd = self.syntax_data
        if (
            (start is not None)
            and (end is not None)
            and sd
            and sd.source_code
            and end <= len(sd.source_code)
        ):
            return sd.source_code[start:end].decode("utf-8")
        return ""

    def __repr__(self) -> str:
        return _CSI_SEQUENCE.sub("", self.to_formatted_string())

    def to_formatted_string(self) -> str:
        """Print node representation formatted for printing in terminal."""
        return super().__repr__()


class BranchNode(Node):
    """Syntax tree branch node

    Attributes:
      tag (str): Node tag.
      children (Optional[Node]): Child nodes.
    """

    def __init__(
        self,
        tag: str,
        parent: Optional[Node] = None,
        children: Optional[List[Node]] = None,
    ):
        super().__init__(parent)
        self.tag = tag
        self.children = children if children is not None else []

    @property
    def start(self) -> Optional[int]:
        first_token = self.find(
            lambda n: isinstance(n, TokenNode), iter_=PostOrderTreeIterator
        )
        return first_token.start if first_token else None

    @property
    def end(self) -> Optional[int]:
        last_token = self.find(
            lambda n: isinstance(n, TokenNode),
            iter_=PostOrderTreeIterator,
            reverse_children=True,
        )
        return last_token.end if last_token else None

    def iter_find_all(
        self,
        filter_: Union[CallableFilter, KeyValueFilter, None],
        max_count: int = 0,
        iter_: TreeIterator = LevelOrderTreeIterator,
        **kwargs,
    ) -> Iterable[Node]:
        """Iterate all nodes matching specified filter.

        Args:
          filter_: Describes what to search for. Might be:
            * Callable taking Node as an argument and returning True for accepted
              nodes.
            * Dict mapping Node attribute names to searched value or list of
              searched values.
          max_count: Stop searching after finding that many matching nodes.
          iter_: Tree iterator. Decides in what order nodes are visited.

        Yields:
          Nodes matching specified filter.
        """

        def as_list(v):
            return v if isinstance(v, list) else [v]

        if filter_ and not callable(filter_):
            filters = filter_

            def f(node):
                for attr, value in filters.items():
                    if not hasattr(node, attr):
                        return False
                    if getattr(node, attr) not in as_list(value):
                        return False
                return True

            filter_ = f

        for node in iter_(self, filter_, **kwargs):
            yield node
            max_count -= 1
            if max_count == 0:
                break

    def find(
        self,
        filter_: Union[CallableFilter, KeyValueFilter, None],
        iter_: TreeIterator = LevelOrderTreeIterator,
        **kwargs,
    ) -> Optional[Node]:
        """Find node matching specified filter.

        Args:
          filter_: Describes what to search for. Might be:
            * Callable taking Node as an argument and returning True for accepted
              node.
            * Dict mapping Node attribute names to searched value or list of
              searched values.
          iter_: Tree iterator. Decides in what order nodes are visited.

        Returns:
          First Node matching filter.
        """
        return next(
            self.iter_find_all(filter_, max_count=1, iter_=iter_, **kwargs), None
        )

    def find_all(
        self,
        filter_: Union[CallableFilter, KeyValueFilter, None],
        max_count: int = 0,
        iter_: TreeIterator = LevelOrderTreeIterator,
        **kwargs,
    ) -> List[Node]:
        """Find all nodes matching specified filter.

        Args:
          filter_: Describes what to search for. Might be:
            * Callable taking Node as an argument and returning True for accepted
              nodes.
            * Dict mapping Node attribute names to searched value or list of
              searched values.
          max_count: Stop searching after finding that many matching nodes.
          iter_: Tree iterator. Decides in what order nodes are visited.

        Returns:
          List of nodes matching specified filter.
        """
        return list(
            self.iter_find_all(filter_, max_count=max_count, iter_=iter_, **kwargs)
        )

    def to_formatted_string(self) -> str:
        tag = self.tag if self.tag == repr(self.tag)[1:-1] else repr(self.tag)
        return _colorize(["37", "1;97"], ["[", tag, "]"])


class RootNode(BranchNode):
    """Syntax tree root node."""

    def __init__(
        self,
        tag: str,
        syntax_data: Optional["SyntaxData"] = None,
        children: Optional[List[Node]] = None,
    ):
        super().__init__(tag, None, children)
        self._syntax_data = syntax_data

    @property
    def syntax_data(self) -> Optional["SyntaxData"]:
        return self._syntax_data


class LeafNode(Node):
    """Syntax tree leaf node.

    This specific class is used for null nodes.
    """

    @property
    def start(self) -> None:
        """Byte offset of token's first character in source text"""
        return None

    @property
    def end(self) -> None:
        """Byte offset of a character just past the token in source text."""
        return None

    def to_formatted_string(self) -> str:
        return _colorize(["90"], ["null"])


class TokenNode(LeafNode):
    """Tree node with token data

    Represents single token in a syntax tree.

    Attributes:
      tag (str): Token tag.
    """

    def __init__(self, tag: str, start: int, end: int, parent: Optional[Node] = None):
        super().__init__(parent)
        self.tag = tag
        self._start = start
        self._end = end

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int:
        return self._end

    def to_formatted_string(self) -> str:
        tag = self.tag if self.tag == repr(self.tag)[1:-1] else repr(self.tag)
        parts = [
            _colorize(["37", "1;97"], ["[", tag, "]"]),
            _colorize(["33", "93"], ["@(", self.start, "-", self.end, ")"]),
        ]
        text = self.text
        if self.tag != text:
            parts.append(_colorize(["32", "92"], ["'", repr(text)[1:-1], "'"]))
        return " ".join(parts)


class Token:
    """Token data

    Represents single token in tokens and rawtokens lists.

    Attributes:
      tag (str): Token tag.
      start (int): Byte offset of token's first character in source text.
      end (int): Byte offset of a character just past the token in source text.
      syntax_data (Optional["SyntaxData"]): Parent SyntaxData.
    """

    def __init__(
        self, tag: str, start: int, end: int, syntax_data: Optional["SyntaxData"] = None
    ):
        self.tag = tag
        self.start = start
        self.end = end
        self.syntax_data = syntax_data

    @property
    def text(self) -> str:
        """Token text in source code."""
        sd = self.syntax_data
        if sd and sd.source_code and self.end <= len(sd.source_code):
            return sd.source_code[self.start : self.end].decode("utf-8")
        return ""

    def __repr__(self) -> str:
        return _CSI_SEQUENCE.sub("", self.to_formatted_string())

    def to_formatted_string(self) -> str:
        tag = self.tag if self.tag == repr(self.tag)[1:-1] else repr(self.tag)
        parts = [
            _colorize(["37", "1;97"], ["[", tag, "]"]),
            _colorize(["33", "93"], ["@(", self.start, "-", self.end, ")"]),
            _colorize(["32", "92"], ["'", repr(self.text)[1:-1], "'"]),
        ]
        return " ".join(parts)


@dataclasses.dataclass
class Error:
    line: int
    column: int
    phase: str
    message: str = ""


@dataclasses.dataclass
class SyntaxData:
    source_code: Optional[str] = None
    tree: Optional[RootNode] = None
    tokens: Optional[List[Token]] = None
    rawtokens: Optional[List[Token]] = None
    errors: Optional[List[Error]] = None


class VeribleVerilogSyntax:
    """``verible-verilog-syntax`` wrapper.

    This class provides methods for running ``verible-verilog-syntax`` and
    transforming its output into Python data structures.

    """

    def __init__(self):
        pass

    def __init__(self, executable: str):
        self.executable = executable

    @staticmethod
    def _transform_tree(tree, data: SyntaxData, skip_null: bool) -> RootNode:
        def transform(tree):
            if tree is None:
                return None
            if "children" in tree:
                children = [
                    transform(child) or LeafNode()
                    for child in tree["children"]
                    if not (skip_null and child is None)
                ]
                tag = tree["tag"]
                return BranchNode(tag, children=children)
            tag = tree["tag"]
            start = tree["start"]
            end = tree["end"]
            return TokenNode(tag, start, end)

        if "children" not in tree:
            return None

        children = [
            transform(child) or LeafNode()
            for child in tree["children"]
            if not (skip_null and child is None)
        ]
        tag = tree["tag"]
        return RootNode(tag, syntax_data=data, children=children)

    @staticmethod
    def _transform_tokens(tokens, data: SyntaxData) -> List[Token]:
        return [Token(t["tag"], t["start"], t["end"], data) for t in tokens]

    @staticmethod
    def _transform_errors(tokens) -> List[Error]:
        return [
            Error(t["line"], t["column"], t["phase"], t.get("text", None))
            for t in tokens
        ]

    def _parse(
        self, paths: List[str], input_: str = None, options: Dict[str, Any] = None
    ) -> Dict[str, SyntaxData]:
        """Common implementation of parse_* methods"""
        options = {
            "gen_tree": True,
            "skip_null": False,
            "gen_tokens": False,
            "gen_rawtokens": False,
            **(options or {}),
        }

        args = ["-export_json"]
        if options["gen_tree"]:
            args.append("-printtree")
        if options["gen_tokens"]:
            args.append("-printtokens")
        if options["gen_rawtokens"]:
            args.append("-printrawtokens")

        proc = subprocess.run(
            [self.executable, *args, *paths],
            stdout=subprocess.PIPE,
            input=input_,
            encoding="utf-8",
            check=False,
        )

        json_data = json.loads(proc.stdout)
        data = {}
        for file_path, file_json in json_data.items():
            if file_json is None:
                continue

            file_data = SyntaxData()

            if file_path == "-":
                file_data.source_code = input_.encode("utf-8")
            else:
                with open(file_path, "rb") as f:
                    file_data.source_code = f.read()

            if "tree" in file_json:
                file_data.tree = VeribleVerilogSyntax._transform_tree(
                    file_json["tree"], file_data, options["skip_null"]
                )

            if "tokens" in file_json:
                file_data.tokens = VeribleVerilogSyntax._transform_tokens(
                    file_json["tokens"], file_data
                )

            if "rawtokens" in file_json:
                file_data.rawtokens = VeribleVerilogSyntax._transform_tokens(
                    file_json["rawtokens"], file_data
                )

            if "errors" in file_json:
                file_data.errors = VeribleVerilogSyntax._transform_errors(
                    file_json["errors"]
                )

            data[file_path] = file_data

        return data

    def parse_files(
        self, paths: List[str], options: Dict[str, Any] = None
    ) -> Dict[str, SyntaxData]:
        """Parse multiple SystemVerilog files.

        Args:
          paths: list of paths to files to parse.
          options: dict with parsing options.
            Available options:
              gen_tree (boolean): whether to generate syntax tree.
              skip_null (boolean): null nodes won't be stored in a tree if True.
              gen_tokens (boolean): whether to generate tokens list.
              gen_rawtokens (boolean): whether to generate raw token list.
            By default only ``gen_tree`` is True.

        Returns:
          A dict that maps file names to their parsing results in SyntaxData object.
        """
        return self._parse(paths, options=options)

    def parse_file(
        self, path: str, options: Dict[str, Any] = None
    ) -> Optional[SyntaxData]:
        """Parse single SystemVerilog file.

        Args:
          path: path to a file to parse.
          options: dict with parsing options.
            Available options:
              gen_tree (boolean): whether to generate syntax tree.
              skip_null (boolean): null nodes won't be stored in a tree if True.
              gen_tokens (boolean): whether to generate tokens list.
              gen_rawtokens (boolean): whether to generate raw token list.
            By default only ``gen_tree`` is True.

        Returns:
          Parsing results in SyntaxData object.
        """
        return self._parse([path], options=options).get(path, None)

    def parse_string(
        self, string: str, options: Dict[str, Any] = None
    ) -> Optional[SyntaxData]:
        """Parse a string with SystemVerilog code.

        Args:
          string: SystemVerilog code to parse.
          options: dict with parsing options.
            Available options:
              gen_tree (boolean): whether to generate syntax tree.
              skip_null (boolean): null nodes won't be stored in a tree if True.
              gen_tokens (boolean): whether to generate tokens list.
              gen_rawtokens (boolean): whether to generate raw token list.
            By default only ``gen_tree`` is True.

        Returns:
          Parsing results in SyntaxData object.
        """
        return self._parse(["-"], input_=string, options=options).get("-", None)


def parse_filelist(filelist):
    files = []

    for file in filelist:
        if re.search("^-f ", file):
            file = re.sub(r"-f ", r"", file)
        file = os.path.expandvars(file)
        if os.path.isfile(file):
            ext = os.path.splitext(file)[1]
            if ext == ".sv" or ext == ".v":
                files.append(file)
            else:
                child_filelist = [line.strip() for line in open(file).readlines()]
                files.extend(parse_filelist(child_filelist))

    return files


if __name__ == "__main__":
    prog_name = os.path.basename(__file__)
    argsDescr = (
        f"{prog_name}: checks SystemVerilog syntax.\n"
        + "Synopsis: Checks SystemVerilog syntax for all input SystemVerilog files\n"
    )

    argsEpilog = (
        """
  -- input: Input SystemVerilog files or filelist files.
  -- output: Output file for SystemVerilog syntax errors.

  For example:

  > %s -i systemverilog1.sv systemverilog2.sv -o syntax_errors.json

  """
        % prog_name
    )

    parser = argparse.ArgumentParser(
        prog=prog_name,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="""\n %(prog)s [Options]\n\t\t\tMust specify -i <valid filelist or sv_file>\n""",
        description=argsDescr,
        epilog=argsEpilog,
        prefix_chars="-",
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        action="store",
        dest="input",
        type=str,
        nargs="+",
        default=[],
        help="""Input SystemVerilog files or filelist files""",
        metavar="FILE",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default="syntax_errors.json",
        help="""Output file for SystemVerilog syntax errors""",
    )

    args = parser.parse_known_args()
    if args[0].input is None or len(args[0].input) == 0:
        parser.print_help()
        sys.exit(1)

    filelist = list(set(parse_filelist(args[0].input)))

    parser = VeribleVerilogSyntax(executable="verible-verilog-syntax")

    data = parser.parse_files(filelist)
    file_syntax_errors = {}
    for file, syntax_data in data.items():
        print(f"File: {file}")
        print(f"Syntax error: {data[file].errors}\n")

        errors = data[file].errors
        syntax_errors = []
        if errors is not None:
            syntax_errors = [
                {
                    "column": error.column,
                    "line": error.line,
                    "message": error.message,
                    "phase": error.phase,
                }
                for error in errors
            ]
        file_syntax_errors[file] = syntax_errors

    print(f"Generating the syntax error output to the file '{args[0].output}'. ")
    json.dump(file_syntax_errors, open(args[0].output, "w"), indent=2)
