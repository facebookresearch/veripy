#!/usr/local/bin/asicpy

####################################################################################
#   Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
#   The following information is considered proprietary and confidential to Facebook,
#   and may not be disclosed to any third party nor be used for any purpose other
#   than to full fill service obligations to Facebook
####################################################################################


import argparse
import logging
import os
import re
import string
import subprocess
import sys
import copy
from collections import OrderedDict
from math import ceil, log
from time import localtime, strftime
from typing import Callable, Dict, List, Iterator

try:
   os.environ["INFRA_ASIC_FPGA_ROOT"]
except KeyError:
   print ("Please set the environment variable INFRA_ASIC_FPGA_ROOT")
else:
    infra_dir = os.path.dirname(os.path.realpath(os.environ["INFRA_ASIC_FPGA_ROOT"]))
    sys.path.append(infra_dir)
    veripy_dir = infra_dir + '/infra_asic_fpga/common/tools/veripy/3_0'
    sys.path.append(veripy_dir)

from fb_utils import convert_to_hash, convert_to_yaml, log2

epilog = """

Keywords in verilog:
    &pythonBegin: The code after this will be executed as a block until the
                  &pythonEnd keyword.
    &pythonEnd: Shows the end of the python code block.
    &python: Single line python code.
    &declarations: The script will auto declare the wires when it encounters
                   this keyword.
    &template <file name>: Adds the code from the given file.
    $${xxx}: If you have this notation in the code that is not part of the
             python code, the script will convert it into the value of xxx
             variable. You can do operations within the {} and they will be
             executed (i.e. $${x + y} will execute x+y and print out the
             result in the verilog file).

Variables you can use and change inside the pre-verilog file:
    clk: Name of the clock.
    reset: Name of the reset signal.
    declare_separately: If you want to temporarily disable auto declaration
                        for some signals (might be useful within generate
                        statements), you can set this variable to False and set it
                        back to True (or store the old value in a temp variable
                        and load back).
    t: Base indentation/tab. By default it is 4 spaces.
    lines: If you want to print to the output file using a function in python
           code, use lines_append(<text>).

Functions:
    reg: This function declares registers and does the necessary wire
         declarations as well. These are the arguments this function takes:
         (flop_type, name, parameters, signals, tab)
         flop_type: Can be d, den, dr, dren.
            d: A flop flop with no enable or reset.
            den: A flop with enable control.
            dr: A resettable flop.
            dren: A resettable flop with enable control.
         name: Name of the register. Note that this name may not be the same
               as the output of this flop. The signal `flop_type + "_" + name`
               is created and used inside the always_ff block.
               Setting this to None, will result in the always_ff block to use
               the output specified in `signals` directly.
         parameters: Given as a string with 1 or 2 values separated by a comma.
                     The first value is the width of the flip flop (how many
                     bits it has) and the second value is the optional reset
                     value.
                     TODO: add info about shift reg parameter when it's ready.
         signals: A string with 2 or 3 values separated by spaces. For den and
                  dren, there has to be 3 values. For d and dr, there has to
                  be 2 values. The first value is the input, the second value
                  is the output, and the third value is the enable signal.
                  If you add "-l" after the name, that signal will be declared.
         tab: This is the indentation you want for this code to have. This
              defaults to indent the generated code based on the source
              indentation.
         You can change the reset type to synchronous reset by setting the
         reset_type to 'sync'. Default is 'async'.
"""

ios = []
io_names = [] # stores just the top level io names
connection_display = []
connection_dict = {} # to store the connection wires
instances = []
LHS_list = []

# define Python user-defined exceptions
class RegisterGenerationError(Exception):
    """Base class for other exceptions"""

    pass


class Port:
    dir2int = {"input":0, "output":1}
    int2dir = {v:k for k, v in dir2int.items()}
    def __init__(
        self,
        direction:str = "",
        atype:str = "",
        width:int = 1,
        name:str = "",
        array: int = 1,
        src: str = "",
        dst: str = "",
        isMaster: bool = True,
        hasFT: bool = False,
        module_name: str ="",
        modules: List[str] = None
    ) -> None:
        """
        direction: a direction object that can flip its direction by "~"
        atype: the signal type of the port.
        width: the integer value of the width of the signal. width_str will
               return the string representation of this width, in verilog format
        name: the name of the port
        array: the integer value of the array size. By default it is 1 and it's not
               an array. If it's greater than 1, "[x]" will be appeneded to the end
               of the signal in port declaration to make the port an unpacked array
        src: the name of the src interface.
        dst: the name of the destination interface.
        isMaster: if the module is the master interface
        phy_src: when there's feedthrough port e.g "a-b-c-d", physical src/dst is
                 different from logical src/dst. this is the physical src
        phy_dst: defines the physical destination
        hasFT: if this port is connected to a FT or not
        """
        self.dir = direction
        self.atype = atype
        self.width = width
        self.name = name
        self.array = array
        self.src = src
        self.dst = dst
        self.isMaster = isMaster
        self.hasFT = hasFT
        self.modules = modules
        if modules:
            self.set_physical_conn(module_name, modules)
            if isMaster:
                if direction == "input":
                    self.src, self.dst = self.dst, self.src
                    self.phy_src, self.phy_dst = self.phy_dst, self.phy_src
            else:
                if direction == "input":
                    self = ~self
                else:
                    self.dir = Port.int2dir[1^Port.dir2int[self.dir]]

    def __str__(self) -> str:
        return self.display_port()

    def __repr__(self) -> str:
        return str(self)

    def __invert__(self) -> "Port":
        """
        negate a port changes the direction of the port
        and also swap the src and destination
        """
        self.dir = Port.int2dir[1^Port.dir2int[self.dir]]
        self.src, self.dst = self.dst, self.src
        self.phy_src, self.phy_dst = self.phy_dst, self.phy_src
        return self

    def flip_direction(self) -> "Port":
        self.dir = Port.int2dir[1^Port.dir2int[self.dir]]
        return self

    @property
    def name(self) -> str:
        return self._actualname

    @name.setter
    def name(self, n) -> None:
        self._actualname = n

    @property
    def port_name(self) -> str:
        return self.src + "_" + self.dst + "_" + self._actualname

    @property
    def wire_name(self) -> str:
        if self.hasFT:
            wire_name = f"{self.phy_src}_{self.phy_dst}_ft_" + self.port_name
        else:
            wire_name = self.port_name

        return wire_name

    @property
    def width_str(self) -> str:
        """
        convert the width integer to a string that can be displayed in verilog port
        declarations
        """
        if self.atype.lower() not in ["logic", "wire", "reg"] or self.width == 1:
            return ""
        else:
            return f"[{self.width}-1:0]"

    @property
    def array_str(self) -> str:
        """
        convert the array integer to a string that can be displayed in verilog port
        declarations
        """
        return f"[{self.array}]" if self.array>1 else ""

    def display_port(
            self,
            end: bool = False,
            t1: int = 0,
            t2: int = 0,
            t3: int = 0
    ) -> str:
        """
        print the port in tabulated verilog format
        """
        end_str = "" if end else ","
        return " "*4 + \
               "{:<{x}} {:<{y}} {:<{z}} {}{}\n".format(str(self.dir),
                                                       self.atype,
                                                       self.width_str,
                                                       self.port_name + self.array_str,
                                                       end_str,
                                                       x=t1, y=t2, z=t3)
    def display_logic(
            self,
            end: bool = False,
            t1: int = 0,
            t2: int = 0,
    ) -> str:
        """
        print the port in tabulated verilog format
        """
        return " "*4 + \
               "{:<{x}} {:<{y}} {};\n".format(self.atype,
                                              self.width_str,
                                              self.name + self.array_str,
                                              x=t1, y=t2)

    def set_physical_conn(self, module_name, modules) -> None:
        src, *ft, dst = modules
        p_src = p_mid = p_nxt = p_dst = ""

        if module_name in ft:
            p_src = src if modules.index(module_name) == 0 \
                    else modules[modules.index(module_name)-1]
            p_mid = module_name
            p_dst = dst if modules.index(module_name) == len(modules)-1 \
                    else modules[modules.index(module_name)+1]
            if self.isMaster:
                self.phy_src, self. phy_dst = p_mid, p_dst
            else:
                self.phy_src, self. phy_dst = p_src, p_mid
        elif ft:
            p_src = src
            p_mid = ft[0]
            p_nxt = ft[-1] if len(ft) > 1 else ft[0]
            p_dst = dst
            if self.isMaster:
                self.phy_src, self. phy_dst = p_src, p_mid
            else:
                self.phy_src, self. phy_dst = p_nxt, p_dst
        else:
            self.phy_src, self. phy_dst = "", ""


class ClockResetPort(Port):
    """
    clock reset port is a special port that cannot negate
    its direction, and is always input with width of 1
    never a feedthrough port, no path
    """
    def __init__(self, name: str) -> None:
        super().__init__("input", "logic", 1, name, 1)

    def __invert__(self) -> Port:
        return self

    @property
    def port_name(self) -> str:
        """
        clk reset does not need to have src_dst prefix
        """
        return self._actualname

    @property
    def wire_name(self) -> str:
        return self._actualname


class AXIPort(Port):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bundle = self.modules[0]

    @property
    def name(self) -> str:
        return "_".join(self._actualname + [self.bundle, self._channelname])

    @name.setter
    def name(self, n) -> None:
        *self._actualname, self._channelname = n.split("_")

    @property
    def port_name(self) -> str:
        return self.src + "_" + self.dst + "_" + self.name


class FeedthroughPort(AXIPort):
    """
    ready port is a special port that always has the opposite direction
    of other signals in an interface. but it's naming is still as if
    has the same direction
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # need to set this ft before flipping ready direction
        # so ready still has the right fto/fti even though direction is flipped
        self._ft = "fti" if self.dir == "input" else "fto"

    @property
    def port_name(self) -> str:
        """
        feedthrough ports name is
        physrc_phydst_fti/o_src_dst_name
        """
        return "_".join([self._ft, self.src, self.dst]) + "_" + self.name

    @property
    def wire_name(self) -> str:
        """
        feedthrough ports name is
        physrc_phydst_fti/o_src_dst_name
        """
        return "_".join([self.phy_src, self.phy_dst, "ft", self.src, self.dst]) + \
               "_" + self.name


class VerilogInterface:
    """
    a container class that stores ports in a given interface
    """
    def __init__(
            self,
            name: str = "",
    ) -> None:
        self.name = name
        self.ports = []
        self.__clkrst = {}

    def add_port(
        self,
        p: Port,
        num: int=1,
        io_out: List[str]=None,
        declare: bool=False,
        assign_out: List[str]=None
    ) -> None:
        """
        adds the same port multiple times if "num" is greater than 1
        add port_name to external list if one is provided
        """
        for i in range(num):
            pp = copy.deepcopy(p)
            if num > 1:
                pp.name = p.name + f"_{i}"
            self.ports.append(pp)
            if io_out is not None:
                io_out.append(pp.port_name)
            if assign_out is not None:
                if declare and "fto" == pp._ft:
                    assign_out.append(pp.port_name)

    def add_ports(
        self,
        ports: List[Port],
        num: int=1,
        io_out: List[str]=None,
        declare: bool=False,
        assign_out: List[str]=None
    ) -> None:
        for p in ports:
            self.add_port(p, num, io_out, declare, assign_out)

    def add_clkrst(self, c: str, io_out: List[str]=None) -> None:
        """
        add clk/reset to port list if they don't already exist
        add port_name to external list if one is provided
        """
        if c not in self.__clkrst:
            self.__clkrst[c] = True
            self.ports.append(ClockResetPort(c))
            if io_out:
                io_out.append(c)

    def __iter__(self) -> Iterator[Port]:
        """
        returns a generator
        """
        for p in self.ports:
            yield p

    def __len__(self) -> int:
        return len(self.ports)

    def __str__(self) -> str:
        return self.tabulate_ports()

    def __repr__(self) -> str:
        return str(self)

    def tabulate_ports(self) -> str:
        """
        convert the interface to string in a tabulated format
        """
        def sort_method(x):
            if isinstance(x, AXIPort) or isinstance(x, FeedthroughPort):
                return "_".join(x._actualname + [x.bundle])
            else:
                return x.name
        direction, typedef, width = [], [], []
        result = ""
        length = len(self.ports)
        for io in self.ports:
            direction.append(len(io.dir))
            typedef.append(len(io.atype))
            width.append(len(io.width_str))
        max_direction = max(direction)
        max_typedef = max(typedef)
        max_width = max(width)
        for idx, io in enumerate(sorted(self.ports, key=sort_method), 1):
            result += io.display_port(idx == length,
                                      max_direction,
                                      max_typedef,
                                      max_width)
        return result

    @staticmethod
    def tabulate_logics(ports: List[Port]) -> str:
        """
        convert the interface to string in a tabulated format
        """
        typedef, width = [], []
        result = ""
        length = len(ports)
        for io in ports:
            typedef.append(len(io.atype))
            width.append(len(io.width_str))
        max_typedef = max(typedef)
        max_width = max(width)
        for idx, io in enumerate(sorted(ports, key=lambda x:x.name), 1):
            result += io.display_logic(idx == length,
                                       max_typedef,
                                       max_width)
        return result


class ModuleInstance:
    def __init__(
        self,
        module_name: str = "",
        inst_name: str = ""
    ) -> None:
        self.module_name = module_name
        self.inst_name = inst_name
        self.itfc = None
        self.connection = {}

    def set_interface(
        self,
        module_name: str,
        inst_name: str,
        io: dict,
        itfc: dict=None,
        struct_definition: dict=None
    ) -> None:
        self.module_name = module_name
        self.inst_name = inst_name
        self.itfc = generate_module_io(io, itfc, struct_definition, False)

    def set_connection(self, m: List[str], res: Dict[str, Port]) -> None:
        """
        create a dummy port for each port, assign the wire name as their
        _actualname, and put it in the connection dictionary. for each port
        also see if user has provided custom connection rule (regex), if yes
        replace the wire with new string. update the result dict with self connection
        """
        for p in self.itfc:
            # use its _actualname as the wirename
            # not using src/dst. So when printing these wire names, will use
            # p.name, not p.port_name
            np = Port(name=p.wire_name, atype=p.atype, width=p.width)
            self.connection[p.port_name] = np
            if not isinstance(p, ClockResetPort): # don't apply regular expression rule to clk and reset
                for src, dst in zip(m[:-1:2], m[1::2]):
                    if re.search(src, p.wire_name):
                        self.connection[p.port_name].name = re.sub(src, dst, p.wire_name)
        res.update({v.name :  v for v in self.connection.values()})

    def __str__(self) -> str:
        """
        convert the instance to verilog format, with parathesis aligned
        """
        text = " "*4 + f"{self.module_name} {self.inst_name}(\n"
        max_port = max([len(x.port_name) for x in self.itfc])
        length = len(self.itfc)
        for idx, p in enumerate(self.itfc, 1):
            end_str = "" if idx==length else ","
            text += " "*8 + ".{:<{x}} ({}){}\n".format(p.port_name,
                                                       self.connection[p.port_name].name,
                                                       end_str,
                                                       x=max_port)
        text += " "*4 + f");\n"
        return text

    def display_instance(self) -> None:
        declare_instance(str(self))


def generate_instances(
    name: str,
    inst_name: str,
    io: dict,
    interfaces: dict,
    struct_definition: dict,
    *mapping: dict
) -> None:
    # convert mapping pairs into a dictionary
    assert len(mapping)%2==0, "connection should be in pairs"
    mi = ModuleInstance()
    mi.set_interface(name, inst_name, io, interfaces, struct_definition)
    mi.set_connection(mapping, connection_dict)
    mi.display_instance()

def get_ftport_pair(
    config: dict,
    declare: bool=False,
    flip_dir: bool=False
) -> List[Port]:
    cfg = copy.deepcopy(config)
    cfg["isMaster"] = True
    port_a = FeedthroughPort(**cfg)
    cfg["isMaster"] = False
    port_b = FeedthroughPort(**cfg)
    if flip_dir:
        return port_a.flip_direction(), port_b.flip_direction()
    else:
        return port_a, port_b

def generate_module_io(
    io: dict,
    interfaces: dict=None,
    struct_definition: dict=None,
    declare: bool = True
) -> VerilogInterface:
    itfc = VerilogInterface()
    config = {} # configuration dictionary for the factory

    for interface in io:
        config["module_name"] = module_name = re.sub(r"\(.+\)$", "", io[interface]["side"])
        config["modules"] = modules = interface.split("-")
        src, *ft, dst = modules
        src = re.sub(r"\(.+\)$", "", src)
        dst = re.sub(r"\(.+\)$", "", dst)
        # assert module_name in modules, f"interface does not contain module {module_name}"

        config["isMaster"] = isMaster = module_name.lower() == src
        config["src"] = src
        config["dst"] = dst
        config["hasFT"] = hasFT = len(modules) > 2
        isFT = module_name.lower() in ft # is feedthrough
        repeat = io[interface].get("num", 1)

        assert all([isMaster, isFT]) == False, "can't be master and feedthrough at the same time"

        # if this interface in the contract has a None value, this interface must be sharing the same
        # the signals with the interface that goes the opposite direction. e.g.
        # a-b:
        # b-a:
        #    input:
        #    output
        # b-a and a-b share the same ports so they are defined together. a-b's value is None it can use b-a's
        if interfaces.get(interface) is None:
            interface = "-".join(interface.split("-")[::-1])

        # interfaces[interface] contains either input/output, or AXI where direction is inferred
        for direction in interfaces[interface]:
            for names in interfaces[interface][direction]:
                for name in names.split(","):
                    name = name.strip()
                    if "AXI" in direction:
                        add_axi_ports(name,
                                      itfc,
                                      interfaces[interface][direction][names],
                                      config,
                                      struct_definition,
                                      repeat,
                                      declare,
                                      io_names,
                                      isFT)
                    else:
                        config["direction"] = direction
                        # prefix = get_prefix(isFT, direction, master, slave)
                        custom_width_dict = interfaces[interface][direction][names].get("width", {})
                        config["array"] = array = interfaces[interface][direction][names].get("array", 1)
                        # declaration for structs
                        if "type" in interfaces[interface][direction][names]:
                            port_type = interfaces[interface][direction][names]["type"]
                            port_def = struct_definition[port_type]
                            underscore = "" if "no_underscore" in port_def["meta"] else "_"
                            if "flat" in interfaces[interface][direction][names]:
                                for field in port_def["fields"]:
                                    config["atype"] = port_def["package"] + "::" + port_def["fields"][field]["type"] \
                                                      if "type" in port_def["fields"][field] \
                                                      else "logic"
                                    config["width"] = custom_width_dict[field] \
                                                      if field in custom_width_dict \
                                                      else port_def["fields"][field]["width"]
                                    config["name"] = name + field
                                    if isFT:
                                        ports = get_ftport_pair(config, declare)
                                        itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                                    else:
                                        port = Port(**config)
                                        itfc.add_port(port, repeat, io_names)
                            elif "fields" in port_def:
                                config["atype"] = port_def["package"]+"::"+port_type+"_t"
                                config["width"] = 1
                                config["name"] = name
                                if isFT:
                                    ports = get_ftport_pair(config, declare)
                                    itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                                else:
                                    port = Port(**config)
                                    itfc.add_port(port, repeat, io_names)
                            # add valid, ready clk and reset
                            itfc.add_clkrst(port_def["meta"]["clk"], io_names)
                            itfc.add_clkrst(port_def["meta"]["reset"], io_names)
                            if "ready" in port_def["meta"]["flow_control"]:
                                config["atype"] = "logic"
                                config["width"] = array
                                config["array"] = 1
                                config["name"] = name+f"{underscore}ready"
                                if isFT:
                                    ports = get_ftport_pair(config, declare, True)
                                    itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                                else:
                                    port = Port(**config)
                                    itfc.add_port(port.flip_direction(), repeat, io_names)
                            if "valid" in port_def["meta"]["flow_control"]:
                                config["atype"] = "logic"
                                config["width"] = array
                                config["array"] = 1
                                config["name"] = name+f"{underscore}valid"
                                if isFT:
                                    ports = get_ftport_pair(config, declare)
                                    itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                                else:
                                    port = Port(**config)
                                    itfc.add_port(port, repeat, io_names)
                            if "wakeup" in port_def["meta"]["flow_control"]:
                                config["atype"] = "logic"
                                config["width"] = array
                                config["array"] = 1
                                config["name"] = name+f"{underscore}wakeup"
                                if isFT:
                                    ports = get_ftport_pair(config, declare)
                                    itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                                else:
                                    port = Port(**config)
                                    itfc.add_port(port, repeat, io_names, LHS_list)
                        else: #regular logic
                            config["atype"] = "logic"
                            config["width"] = interfaces[interface][direction][names].get("size", 1)
                            config["array"] = array
                            config["name"] = name
                            if isFT:
                                ports = get_ftport_pair(config, declare)
                                itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                            else:
                                port = Port(**config)
                                itfc.add_port(port, repeat, io_names)
    if declare:
        declare_io(itfc)
    return itfc

def add_axi_ports(name: str,
                  itfc: VerilogInterface,
                  itfc_def: dict,
                  config: dict,
                  struct_definition: dict,
                  repeat: int,
                  declare: bool,
                  io_names: list,
                  isFT: bool):
    config = copy.deepcopy(config)

    for channel in itfc_def:
        assert channel in "ar r aw w b".split(), f"no such channel {channel} in AXI interface"
        config["direction"] = "output" if channel in "ar aw w".split() else "input"
        type_def = struct_definition[itfc_def[channel]["type"]]
        custom_width_dict = itfc_def[channel].get("width", {})
        config["array"] = array = itfc_def[channel].get("array", 1)
        underscore = "" if "no_underscore" in type_def["meta"] else "_"
        if "flat" in itfc_def[channel]:
            for field in type_def["fields"]:
                config["atype"] = type_def["package"] + "::" + type_def["fields"][field]["type"] \
                                  if "type" in type_def["fields"][field] \
                                  else "logic"
                config["width"] = custom_width_dict[field] \
                                  if field in custom_width_dict \
                                  else type_def["fields"][field]["width"]
                config["name"] = name + "_" + channel + field
                if isFT:
                    ports = get_ftport_pair(config, declare)
                    itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
                else:
                    port = AXIPort(**config)
                    itfc.add_port(port, repeat, io_names)
        elif "fields" in type_def:
            config["atype"] = type_def["package"]+"::"+itfc_def[channel]["type"]+"_t"
            config["width"] = 1
            config["name"] = name + "_" + channel
            if isFT:
                ports = get_ftport_pair(config, declare)
                itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
            else:
                port = AXIPort(**config)
                itfc.add_port(port, repeat, io_names)
        if "ready" in type_def["meta"]["flow_control"]:
            config["atype"] = "logic"
            config["width"] = array
            config["array"] = 1
            config["name"] = name + "_" + channel + f"{underscore}ready"
            if isFT:
                ports = get_ftport_pair(config, declare, True)
                itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
            else:
                port = AXIPort(**config)
                itfc.add_port(port.flip_direction(), repeat, io_names)
        if "valid" in type_def["meta"]["flow_control"]:
            config["atype"] = "logic"
            config["width"] = array
            config["array"] = 1
            config["name"] = name + "_" + channel + f"{underscore}valid"
            if isFT:
                ports = get_ftport_pair(config, declare)
                itfc.add_ports(ports, repeat, io_names, declare, LHS_list)
            else:
                port = AXIPort(**config)
                itfc.add_port(port, repeat, io_names)
        itfc.add_clkrst(type_def["meta"]["clk"], io_names)
        itfc.add_clkrst(type_def["meta"]["reset"], io_names)

def tabulate_assigns(alist: List[str]):
    RHS = []
    result = ""
    max_len = 0
    for LHS in alist:
        if len(LHS) > max_len:
            max_len = len(LHS)
        RHS.append(LHS.replace("fto_", "fti_"))
    for idx, LHS in enumerate(alist):
        result += " "*4+"assign {:<{x}} = {};\n".format(LHS, RHS[idx], x=max_len)

    return result

def get_args():

    parser = argparse.ArgumentParser(
        description="Generates verilog code expanding embedded python code.",
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    requiredNamed = parser.add_argument_group("required named arguments")

    requiredNamed.add_argument(
        "--input",
        "-i",
        metavar="<input file>",
        type=str,
        nargs=1,
        required=True,
        help="input file",
    )
    requiredNamed.add_argument(
        "--output",
        "-o",
        metavar="<output file>",
        type=str,
        nargs=1,
        required=True,
        help="output file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="turn on verbosity"
    )
    parser.add_argument(
        "--language",
        type=str,
        help="language is used to determine how to do comments",
        default="auto",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="turns on debug messages and stores file.time.log in /tmp",
    )
    parser.add_argument(
        "--sources",
        type=str,
        help="file that has the list of sources used to generate the given input (optional)",
    )

    args = parser.parse_args()

    input_file = open(args.input[0], "r")
    output_file = open(args.output[0], "w")
    return (args, input_file, output_file)


# Constants
RESET_TYPES = {
    "async": ("negedge", "!"),
    "async_low": ("negedge", "!"),
    "async_high": ("posedge", ""),
    "sync": ("", "!"),
    "sync_low": ("", "!"),
    "sync_high": ("", ""),
}

# Defaults that can be overridden per .p* file.
t = "    "
clk = "clk"
reset = "reset_n"
reset_type = "async"
time_unit = "1ps"
time_precision = "1ps"

lines = []
wires = []

dictionary_for_passing_variable = {}


declare_separately = False
auto_indent = ""
ios_limiter = ","
wires_limiter = ";"

print_to_stdio = True
assertion_support_code_printed = False
assertion_counter = 0

cover_support_code_printed = False

def return_html_style():
    html_style = """
        <style>
        table, th, td {
            border: 1px solid black;
            border-collapse: collapse;
        }
        th, td {
            padding: 5px;
            text-align: left;
        }
        #myBtn {
            display: none;
            position: fixed;
            bottom: 20px;
            right: 30px;
            z-index: 99;
            font-size: 18px;
            border: none;
            outline: none;
            background-color: gray;
            color: white;
            cursor: pointer;
            padding: 15px;
            border-radius: 4px;
        }

        #myBtn:hover {
            background-color: #aaa;
        }

        </style>
    """
    return html_style


def return_html_body(current_revision):
    #<p>Generated from revision {current_revision}</p>
    html_body = f"""
    <button onclick="topFunction()" id="myBtn" title="Go to top">Top</button>

    <script>
    // When the user scrolls down 20px from the top of the document, show the button
    window.onscroll = function() {{scrollFunction()}};

    function scrollFunction() {{
        if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {{
            document.getElementById("myBtn").style.display = "block";
        }} else {{
            document.getElementById("myBtn").style.display = "none";
        }}
    }}

    // When the user clicks on the button, scroll to the top of the document
    function topFunction() {{
        document.body.scrollTop = 0;
        document.documentElement.scrollTop = 0;
    }}
    </script>
    """
    return html_body

html_table_width = "95%"


def declare_signals(tab, width, *signals, struct=False):
    logic = "logic " if not struct else ""

    if not declare_separately:
        lines_append(
            tab + logic + width + " " + ",".join(i for i in signals) + ";\n"
        )
    else:
        declare_wire(logic + width + " " + ",".join(i for i in signals))


def reg(
    flop_type,
    parameters,
    signals=None,
    inp=None,
    out=None,
    en=None,
    name=None,
    tab="auto",
    clk_sig=None,
    reset_sig=None,
    reset_type_local=None,
    reset_value_override="",
    pre="",
):
    # Parse the name.
    if name is not None:
        name = name.split("-")
    else:
        name = [name]

    # Parse the input/output signals.
    declare_split_re_str = r"-(?![^\[\]]*\])"  # Delimiter is - except between [].

    if signals is not None:
        vartuple = signals.split(" ")
        if flop_type == "d" or flop_type == "dr":
            assert len(vartuple) == 2, vartuple
            inp = re.split(declare_split_re_str, vartuple[0])
            out = re.split(declare_split_re_str, vartuple[1])
            en = ""
        elif flop_type == "den" or flop_type == "dren":
            assert len(vartuple) == 3, vartuple
            inp = re.split(declare_split_re_str, vartuple[0])
            out = re.split(declare_split_re_str, vartuple[1])
            en = re.split(declare_split_re_str, vartuple[2])
    else:
        if flop_type == "den" or flop_type == "dren":
            assert en is not None, "Enable signal not provided"
        if en is None:
            en = " "
        assert (
            inp is not None and out is not None
        ), "Input and output signals should be provided"
        inp = re.split(declare_split_re_str, inp)
        out = re.split(declare_split_re_str, out)
        en = re.split(declare_split_re_str, en)

    # Parse the parameters.
    if type(parameters) is int:
        parameters = str(parameters)
    parameters = parameters.split(",")

    # Parse defaults
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if clk_sig is None:
        clk_sig = clk
    if reset_sig is None:
        reset_sig = reset
    if reset_type_local is None:
        reset_type_local = reset_type

    # Determine the reg_name (ie. separate signals in always block)
    if name[0] is None:
        reg_name = out[0]
    else:
        reg_name = flop_type + "_" + name[0]

    # Add module-wide signals to be auto declared.
    if len(inp) > 1:
        declare_signals(tab, "{} [{}-1:0]".format(pre, parameters[0]), inp[0])
    if len(out) > 1:
        declare_signals(tab, "{} [{}-1:0]".format(pre, parameters[0]), out[0])
    if len(en) > 1:
        declare_signals(tab, "", en[0])

    if name[0] is not None and len(name) > 1:
        declare_signals(tab, "{} [{}-1:0]".format(pre, parameters[0]), reg_name)

    # Size the reset literal value for readability.
    unsized_base_re = re.compile("^'[dDhHoObB]")
    sized_base_re = re.compile("^([0-9]+)'[dDhHoObB]")
    dec_literal_re = re.compile("([0-9]+)")

    reset_value = "'d0"
    if len(parameters) > 1:
        unsized_base_match = unsized_base_re.match(parameters[1])
        sized_base_search = sized_base_re.search(parameters[1])
        dec_literal_match = dec_literal_re.match(parameters[1])

        if unsized_base_match:
            reset_value = parameters[0] + parameters[1]
        elif sized_base_search:
            assert sized_base_search.group(1) == parameters[0], (
                "Width != reset literal size (%s != %s)"
                % (parameters[0], sized_base_search.group(1))
            )
            reset_value = parameters[1]
        elif dec_literal_match:
            reset_value = parameters[0] + "'d" + parameters[1]
        else:
            # parameters[1] either is sized already or '1.
            reset_value = parameters[1]
    if reset_value_override != "":
        reset_value = reset_value_override

    # Final output assignment.
    if name[0] is not None:
        lines_append(tab + "assign " + out[0] + " = " + reg_name + ";\n")

    # always_ff declaration.
    if flop_type == "dr" or flop_type == "dren":
        if reset_type_local.startswith("async"):
            lines_append(
                tab
                + "always_ff @(posedge "
                + clk_sig
                + ", "
                + RESET_TYPES[reset_type_local][0]
                + " "
                + reset_sig
                + ") begin\n"
            )
        else:
            lines_append(tab + "always_ff @(posedge " + clk_sig + ") begin\n")
    else:
        lines_append(tab + "always_ff @(posedge " + clk_sig + ") begin\n")

    # always_ff body.
    text = ""
    if flop_type == "dr" or flop_type == "dren":
        text = text + (
            tab
            + t
            + "if ("
            + RESET_TYPES[reset_type_local][1]
            + reset_sig
            + ") begin "
            + reg_name
            + " <= "
            + reset_value
            + "; end\n"
            + tab
            + t
            + "else "
        )
    if flop_type == "den" or flop_type == "d":
        text = text + (tab + t)
    if flop_type == "d" or flop_type == "dr":
        text = text + (reg_name + " <= " + inp[0] + ";\n")
    if flop_type == "den" or flop_type == "dren":
        text = text + (
            "if (" + en[0] + ") begin " + reg_name + " <= " + inp[0] + "; end\n"
        )
    text = text + (tab + "end\n")
    lines_append(text)
    if print_to_stdio:
        print_lines()


def cover_property(
    condition="",
    name=None,
    tab="auto",
    clk_sig=None,
    reset_sig=None,
    reset_type_local=None,
):
    # Parse defaults
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    clk_reset = ""
    if clk_sig is None:
        clk_sig = clk
    if reset_sig is None:
        reset_sig = reset
    if (clk_sig != "clk") or (reset_sig != "reset_n"):
        clk_reset = f",, {clk_sig}, {reset_sig}"

    if reset_type_local is None:
        reset_type_local = "async"

    if not globals()["cover_support_code_printed"]:
        lines_append(f"{tab}`ifdef FB_BEH_SIM\n")
        lines_append(f"{tab}`ifndef COVER_OFF\n")
        lines_append(f"{tab}logic enable_coverpoints;\n")
        cover_direction_reset = RESET_TYPES[reset_type_local][0]
        deassert_direction_reset = "negedge" if cover_direction_reset == "posedge" else "posedge"
        lines_append(f"{tab}initial begin enable_coverpoints = 1'b0; @({cover_direction_reset} {reset_sig}); @({deassert_direction_reset} {reset_sig}); @(posedge {clk_sig}); @(posedge {clk_sig}) enable_coverpoints = 1'b1; end\n")
        lines_append(f"{tab}`endif\n")
        lines_append(f"{tab}`else\n")
        lines_append(f"{tab}wire enable_coverpoints = 1'b0; // spyglass disable W528\n")
        lines_append(f"{tab}`endif\n")
        globals()["cover_support_code_printed"] = True

    if name is None:
        name = "cover" + str(globals()["assertion_counter"])
        globals()["assertion_counter"] += 1
    lines_append(
        tab + f'`SV_COVER({name}, enable_coverpoints & {condition}{clk_reset})\n')


def assert_property(
    condition="",
    text="",
    assert_name=None,
    tab="auto",
    clk_sig=None,
    reset_sig=None,
    reset_type_local=None,
    msg_cmd="ERROR",
    print_common_code_only=False,
    use_macro=True,
):
    # Parse defaults
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    clk_reset = ""
    if clk_sig is None:
        clk_sig = clk
    if reset_sig is None:
        reset_sig = reset
    if reset_type_local is None:
        reset_type_local = reset_type
    if (clk_sig != "clk") or (reset_sig != "reset_n"):
        clk_reset = f",,,, {clk_sig}, {reset_sig}"


    if not globals()["assertion_support_code_printed"]:
        lines_append(f"{tab}`ifdef FB_BEH_SIM\n")
        lines_append(f"{tab}`ifndef ASSERT_OFF\n")
        lines_append(f"{tab}logic enable_assertions;\n")
        assert_direction_reset = RESET_TYPES[reset_type_local][0]
        deassert_direction_reset = "negedge" if assert_direction_reset == "posedge" else "posedge"
        lines_append(f"{tab}initial begin enable_assertions = 1'b0; @({assert_direction_reset} {reset_sig}); @({deassert_direction_reset} {reset_sig}); @(posedge {clk_sig}); @(posedge {clk_sig}) enable_assertions = 1'b1; end\n")
        lines_append(f"{tab}`endif\n")
        lines_append(f"{tab}`else\n")
        lines_append(f"{tab}wire enable_assertions = 1'b0; // spyglass disable W528\n")
        lines_append(f"{tab}`endif\n")
        globals()["assertion_support_code_printed"] = True

    if not print_common_code_only:
        if assert_name is None:
            assert_name = "assertion" + str(globals()["assertion_counter"])
            globals()["assertion_counter"] += 1
        if use_macro:
            if "|->" not in condition and "|=>" not in condition:
                lines_append(
                    tab + f'`SV_ASSERT({assert_name}, ~enable_assertions | ({condition}), "{msg_cmd}: {text}"{clk_reset})\n')
            else:
                lines_append(
                    tab + f'`SV_ASSERT({assert_name}, enable_assertions & {condition}, "{msg_cmd}: {text}"{clk_reset})\n')
        else:
            lines_append(
                tab
                + 'assert property (@(posedge {}) disable iff ({}{} | !enable_assertions) ({})) else begin ${}("{}"); end\n'.format(
                    clk_sig,
                    RESET_TYPES[reset_type_local][1],
                    reset_sig,
                    condition,
                    msg_cmd,
                    text,
                )
            )
    if print_to_stdio:
        print_lines()


def one_hot(
    output_signal,
    select_width,
    select_signal,
    input_list,
    width,
    define_output=False,
    tab="auto",
    type_cast="",
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    local_list = []
    for i in range(select_width):
        lines_append(
            tab
            + "wire [{w}-1:0] {out}_sel{i} = {inp};\n".format(
                w=width, i=i, out=output_signal, inp=input_list[i]
            )
        )
        local_list.append("{out}_sel{i}".format(i=i, out=output_signal))
    if define_output:
        if not declare_separately:
            lines_append(
                tab + "logic [{w}-1:0] {out};\n".format(w=width, out=output_signal)
            )
        else:
            declare_wire("logic [{w}-1:0] {out}".format(w=width, out=output_signal))
    list_new = map(lambda x: f"({{{width}{{{select_signal}[{x}]}}}} & {local_list[x]})", range(select_width))
    select_equation = " | ".join(list_new)
    if type_cast != "":
        select_equation = f"{type_cast}'({select_equation})"
    lines_append(
        tab
        + "assign {out} = {inp};\n".format(out=output_signal, inp=select_equation)
    )


def pipeline_signals(signals, pipe, pipe_n, declare_separately_local=True, tab="auto", clk=None):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    dummy = globals()["declare_separately"]
    globals()["declare_separately"] = declare_separately_local
    dummy_clk = globals()["clk"]
    if clk is not None:
        globals()["clk"] = clk
    for key in sorted(signals):
        # .get is used to either get the defined key or return a default if
        # that key is not defined.
        en = signals[key].get("en", "en{}".format(pipe)).replace(" ", "")
        output_wire = (
            signals[key].get("output", "{}_p{}".format(key, pipe_n)).replace(" ", "")
        )
        input_wire = (
            signals[key].get("input", "{}_p{}".format(key, pipe)).replace(" ", "")
        )
        pre = signals[key].get("pre", "")
        struct = False
        if "dont_declare" not in signals[key]:
            if "declare" in signals[key]:
                struct = True
            else:
                struct = False
            declare_signals(
                tab,
                signals[key].get(
                    "declare", "[{}-1:0]".format(signals[key].get("size", 0))
                ),
                output_wire,
                struct=struct,
            )
        if "size" not in signals[key] and "declare" not in signals[key]:
            # Don't instantiate a flop. This entry is only for declaration.
            pass
        elif struct and "reset" in signals[key]:
            reg(
                "dren",
                "$bits({}),{}".format(signals[key]["declare"], signals[key]["reset"]),
                "{} {} {}".format(input_wire, output_wire, en),
                "{}_pipe_{}-l".format(key, pipe_n),
                t,
                pre=pre,
            )
        elif struct:
            reg(
                "den",
                "$bits({})".format(signals[key]["declare"]),
                "{} {} {}".format(input_wire, output_wire, en),
                "{}_pipe_{}-l".format(key, pipe_n),
                t,
                pre=pre,
            )
        elif "reset" in signals[key]:
            reg(
                "dren",
                "{},{}".format(signals[key]["size"], signals[key]["reset"]),
                "{} {} {}".format(input_wire, output_wire, en),
                "{}_pipe_{}-l".format(key, pipe_n),
                t,
                pre=pre,
            )
        else:
            reg(
                "den",
                "{}".format(signals[key]["size"]),
                "{} {} {}".format(input_wire, output_wire, en),
                "{}_pipe_{}-l".format(key, pipe_n),
                t,
                pre=pre,
            )
    globals()["declare_separately"] = dummy
    globals()["clk"] = dummy_clk


def generate_register_declarations(m, registers, package=None):
    if package is None:
        package = m + "_pkg"
    there_are_inputs = False
    registers_registers_sorted = sorted(registers["registers"])

    for i in registers_registers_sorted:
        for field in registers["registers"][i]["fields"]:
            if "external_in" in registers["registers"][i]["fields"][field]:
                there_are_inputs = True
            if "external_en" in registers["registers"][i]["fields"][field]:
                there_are_inputs = True

    declare_wire("{p}::{m}_struct all_registers".format(p=package, m=m))
    declare_wire("{p}::{m}_rw_en_struct rw_en".format(p=package, m=m))
    if there_are_inputs:
        declare_wire("{p}::{m}_inputs inputs".format(p=package, m=m))


def generate_register_structs(
    registers,
    tab=t,
    pre="",
):
    # Name of the block. This is used to generate the struct that has all the
    # registers.
    block_name = registers["block_name"].lower()
    registers_registers_sorted = sorted(registers["registers"])

    lines_append(tab + "// ---------- Struct for all the " + pre + " registers ----------\n")
    # lines_append(tab + "typedef struct packed\n")
    lines_append(tab + "typedef struct\n")
    lines_append(tab + "{\n")
    for i in registers_registers_sorted:
        reg_name = registers["registers"][i]["name"]
        reg_array = registers["registers"][i]["array"]
        if reg_array > 1:
            reg_array_select = " [{}]".format(registers["registers"][i]["array"])
        else:
            reg_array_select = ""
        lines_append(
            tab
            + t
            + "{}{} {}{};\n".format(
                pre.upper(),
                reg_name.upper(),
                reg_name, reg_array_select
            )
        )
    lines_append(tab + "}} {}_struct;\n".format(block_name))
    lines_append("\n")

def generate_register_enables(
    registers,
    tab=t,
    pre="",
):
    # Name of the block. This is used to generate the struct that has all the
    # registers.
    block_name = registers["block_name"].lower()
    registers_registers_sorted = sorted(registers["registers"])

    lines_append("\n")
    lines_append(tab + "// ---------- Struct for all read/write enables ----------\n")
    lines_append(tab + "typedef struct packed\n")
    lines_append(tab + "{\n")
    lines_append(tab + t + "bool rd_en;\n")
    lines_append(tab + t + "bool wr_en;\n")
    for i in registers_registers_sorted:
        reg_name = registers["registers"][i]["name"]
        reg_array = registers["registers"][i]["array"]
        if reg_array > 1:
            reg_array_select = "[{}] ".format(
                registers["registers"][i]["array"] - 1
            )
        else:
            reg_array_select = ""
        lines_append(
            tab + t + "bool {}_ren {};\n".format(reg_name, reg_array_select,)
        )
        lines_append(
            tab + t + "bool {}_wen {};\n".format(reg_name, reg_array_select)
        )
    lines_append(tab + "}} {}_rw_en_struct;\n".format(block_name))
    lines_append("\n")

def generate_all_register_structs(
    registers,
    tab=t,
    pre="",
):
    generate_register_structs(registers=registers, tab=tab, pre=pre)
    generate_register_enables(registers=registers, tab=tab, pre=pre)

def generate_register_write_case_statements_for_capi(
    registers,
    target="",
    pre="",
    discard_ro=False,
    cmodel=False,
):
    tab = "    "
    registers_registers_sorted = sorted(registers["registers"])
    text = []
    there_are_registers = False
    for i in registers_registers_sorted:
        if 'target' in registers["registers"][i]:
            if target in registers["registers"][i]['target']:
                reg_name = registers["registers"][i]["name"]
                reg_array = registers["registers"][i]["array"]
                reg_type = registers["registers"][i]["type"]
                if 'hw_readable' in registers["registers"][i].keys():
                    reg_hw_readable = registers["registers"][i]["hw_readable"]
                else:
                    reg_hw_readable = False
                if reg_type != "ro" or not discard_ro:
                    if reg_hw_readable:
                        there_are_registers = True
                        if reg_array > 1:
                            for reg_index in range(reg_array):
                                # append a line like:
                                #  CAPI_REG_WRITE_CASE(sfu_regs,FB_INFERENCE_PE_SFU_MODE_REGISTER__ADDR,sfu_mode_register);
                                text.append(
                                    tab
                                    + "CAPI_REGARRAY_WRITE_CASE( {}_regs, {}PE_{}__ADDR, {}, {});\n".format(
                                        target,
                                        pre.upper(),
                                        reg_name.upper(),
                                        reg_index,
                                        reg_name
                                    )
                                )
                        else:
                            if reg_name != "counter_control":
                                # append a line like:
                                #  CAPI_REG_WRITE_CASE(sfu_regs,FB_INFERENCE_PE_SFU_MODE_REGISTER__ADDR,sfu_mode_register);
                                text.append(
                                    tab
                                    + "CAPI_REG_WRITE_CASE( {}_regs, {}PE_{}__ADDR, {});\n".format(
                                        target,
                                        pre.upper(),
                                        reg_name.upper(),
                                        reg_name
                                    )
                                )
                                pass
                            else:
                                # We special-case this one shared register for now.
                                # The reg 'counter_control' is shared between dpe & sfu
                                # We gen one case statement to set both.
                                if target == "sfu":
                                    text.append(
                                        tab
                                        + "CAPI_REG_WRITE_CASE_SHARED2( {}_regs, {}_regs, {}PE_{}__ADDR, {});\n".format(
                                            'sfu',
                                            'dpe',
                                            pre.upper(),
                                            reg_name.upper(),
                                            reg_name
                                        )
                                    )
    text.append("\n")
    if there_are_registers:
        lines_extend(text)


def generate_registers_struct_for_target(
    registers,
    tab="auto",
    target="",
    pre="",
    discard_ro=False,
    cmodel=False,
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    registers_registers_sorted = sorted(registers["registers"])
    lines_append(tab + f"// ---------- Struct for {target} registers ----------\n")
    text = []
    text.append(tab + "typedef struct\n")
    text.append(tab + "{\n")
    there_are_registers = False
    for i in registers_registers_sorted:
        if 'target' in registers["registers"][i]:
            if target in registers["registers"][i]['target']:
                reg_name = registers["registers"][i]["name"]
                reg_array = registers["registers"][i]["array"]
                reg_type = registers["registers"][i]["type"]
                if 'hw_readable' in registers["registers"][i].keys():
                    reg_hw_readable = registers["registers"][i]["hw_readable"]
                else:
                    reg_hw_readable = False
                if reg_array > 1:
                    reg_array_select = " [{}]".format(registers["registers"][i]["array"])
                else:
                    reg_array_select = ""
                if reg_type != "ro" or not discard_ro:
                    if cmodel is True:
                        if reg_hw_readable:
                            there_are_registers = True
                            text.append(
                                tab
                                + t
                                + "{}PE_{} {}{};\n".format(
                                    pre.upper(),
                                    reg_name.upper(),
                                    reg_name,
                                    reg_array_select
                                )
                            )
                    else:
                        there_are_registers = True
                        text.append(
                            tab
                            + t
                            + "{}_struct {}{};\n".format(
                                reg_name,
                                reg_name,
                                reg_array_select
                            )
                        )
    text.append(tab + f"}} registers_for_{target}_struct;\n")
    text.append("\n")
    if there_are_registers:
        lines_extend(text)

def generate_register_json_decls_cmodel(registers, targets, pre):
    registers_registers_sorted = sorted(registers["registers"])
#    print("targets ", targets, file=sys.stderr)
    for i in registers_registers_sorted:
        reg_name = registers["registers"][i]["name"]
        lines_append("""
// Register {0}
bool operator==(const {0}& a, const {0}& b);
bool operator!=(const {0}& a, const {0}& b);
void fromJSON({0}& tp, const rapidjson::Value& j);
string toJSON(const {0}& tp, rapidjson::Value* j = nullptr);
""".format(pre.upper() + "PE_" + reg_name.upper()))
    lines_append("\n// Register collections")
    for target in targets:
#        print("targets ", targets, "target ", target, file=sys.stderr)
        lines_append("""
// Registers for {1}
bool operator==(const {0}& a, const {0}& b);
bool operator!=(const {0}& a, const {0}& b);
void fromJSON({0}& tp, const rapidjson::Value& j);
string toJSON(const {0}& tp, /* unused */ rapidjson::Value* j = nullptr);
""".format("registers_for_" + target + "_struct", target))
    lines_append("\n")

def generate_register_json_cmodel(registers, targets, pre):
    registers_registers_sorted = sorted(registers["registers"])
    for i in registers_registers_sorted:
        reg_name = registers["registers"][i]["name"]
        to_txt = []
        fr_txt = []
        name = pre.upper() + "PE_" + reg_name.upper()
        to_txt.append(f"""
// Register {name}
bool operator==(const {name}& a, const {name}& b) {{ return (a.val == b.val); }}
bool operator!=(const {name}& a, const {name}& b) {{ return (a.val != b.val); }}
string toJSON(const {name}& tp, rapidjson::Value* j) {{
  stringstream ss;
  ss << "{{";
""")
        fr_txt.append(f"""
void fromJSON({name}& tp, const rapidjson::Value& j) {{
  setValField(j, &tp);
""")
        comma = "  ss << "
        for field in registers["registers"][i]["fields"]:
            fr_txt.append(f"  setField(j,tp.str, {field.upper()});\n")
            to_txt.append(f"{comma}outputField(tp.str, {field.upper()});\n")
            comma = "  ss << \",\" << "

        to_txt.append("""\
  if (j) outputValField(ss,*j,&tp);
  ss << \"}\";
  return ss.str();
}
""")
        fr_txt.append("}\n")
        lines_extend(to_txt);
        lines_extend(fr_txt);
    #Now generate for the functional unit structs
    for target in targets:
        to_txt = []
        fr_txt = []
        eq_txt = []
        reg_struct = f"registers_for_{target}_struct"
        to_txt.append("""
// Register {0}
string toJSON(const {0}& tp, /* unused */ rapidjson::Value* j) {{
  stringstream ss;
  ss << "{{";
""".format(reg_struct))
        eq_txt.append("""
bool operator==(const {0}& a, const {0}& b) {{
  bool ret = true;
""".format(reg_struct))
        fr_txt.append(f"void fromJSON({reg_struct}& tp, const rapidjson::Value& j) {{\n")

        # Loop over all registers but extract for this target
        comma = "  ss << "
        for i in registers_registers_sorted:
            if 'target' not in registers["registers"][i]: continue
            if target not in registers["registers"][i]['target']: continue
            reg_name = registers["registers"][i]["name"]
            reg_array = registers["registers"][i]["array"]
            reg_type = registers["registers"][i]["type"]
#            print(f" r {target} {reg_name} {reg_array} {reg_type}", file=sys.stderr)
            if reg_type == "ro": continue
            if reg_array > 1:
                to_txt.append(f"  outputArrayField(ss,tp,{reg_name},{reg_array});\n")
                fr_txt.append(f"  setArrayField(j,tp,{reg_name},{reg_array});\n")
                eq_txt.append(f"""  for (int i = 0; i < {reg_array}; ++i)
    ret &= (a.{reg_name}[i] == b.{reg_name}[i]);
""")
            else:
                to_txt.append(f"{comma}outputStructField(tp,{reg_name});\n")
                fr_txt.append(f"  setStructField(j,tp,{reg_name});\n")
                eq_txt.append(f"  ret &= (a.{reg_name} == b.{reg_name});\n")
            comma = "  ss << \",\" << "
        to_txt.append("  ss << \"}\";\n  return ss.str();\n}\n")
        fr_txt.append("}\n")
        eq_txt.append("  return ret;\n}\n")
        lines_extend(to_txt);
        lines_extend(fr_txt);
        lines_extend(eq_txt);
        lines_append("""
bool operator!=(const {0}& a, const {0}& b) {{
  return !(a == b);
}}
""".format(reg_struct))


def generate_registers_struct_for_target_inputs(
    registers,
    tab="auto",
    target="",
    pre="",
    cmodel=False,
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    registers_registers_sorted = sorted(registers["registers"])
    lines_append(tab + f"// ---------- Struct for register inputs from {target} ----------\n")
    text = []
    text.append(tab + "typedef struct\n")
    text.append(tab + "{\n")
    there_are_registers = False
    for i in registers_registers_sorted:
        if 'target' in registers["registers"][i]:
            if target in registers["registers"][i]['target']:
                reg_name = registers["registers"][i]["name"]
                reg_array = registers["registers"][i]["array"]
                reg_type = registers["registers"][i]["type"]
                if 'hw_writeable' in registers["registers"][i].keys():
                    reg_hw_writeable = registers["registers"][i]["hw_writeable"]
                else:
                    reg_hw_writeable = False
                if reg_array > 1:
                    reg_array_select = " [{}]".format(registers["registers"][i]["array"])
                else:
                    reg_array_select = ""
                if reg_type == "ro" or reg_hw_writeable:
                    there_are_registers = True
                    if cmodel is True:
                        text.append(
                            tab
                            + t
                            + "{}PE_{} {}{};\n".format(
                                pre.upper(),
                                reg_name.upper(),
                                reg_name,
                                reg_array_select
                            )
                        )
                    else:
                        text.append(
                            tab
                            + t
                            + "{}_inputs {}{};\n".format(
                                reg_name,
                                reg_name,
                                reg_array_select
                            )
                        )
    if cmodel:
        if not there_are_registers:
            text.append(tab + t + "bool status;\n")
        there_are_registers = True
        text.append(tab +f"}} registers_for_{target}_inputs_struct;\n")
    else:
        text.append(tab + f"}} {pre}{target}_reg_inputs_struct;\n")
    text.append("\n")
    if there_are_registers:
        lines_extend(text)


def declare_wire(
    wire,
    tab="auto",
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if print_to_stdio:
        if 'logic ' in wire or 'wire ' in wire:
            print(f"{tab}&Force {wire};\n")
        else:
            print(f"{tab}&Force bind {wire};\n")
    else:
        wires.append(wire)


def declare_io(
    io,
    tab="auto",
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if print_to_stdio:
        print(f"{tab}&Force {io};\n")
    else:
        ios.append(io)


def declare_instance(instance: str) -> None:
    instances.append(instance)

def declare_logics(logic_str: str) -> None:
    connection_display.append(logic_str)

def lines_append(
    text,
):
    if print_to_stdio:
        #text.rstrip()
        print(text)
    else:
        lines.append(text)

def lines_append_auto(text):
    tab = auto_indent
    for line in text.split("\n"):
        if print_to_stdio:
            print(tab + line + "\n")
        else:
            lines.append(tab + line + "\n")

def lines_extend(
    text,
):
    if print_to_stdio:
        #text.rstrip()
        print("".join(text))
    else:
        lines.extend(text)


def return_lines():
    lines = globals()["lines"]
    text = "".join(lines)
    globals()["lines"] = []
    return text


def print_lines(inp=None):
    if inp is None:
        lines = globals()["lines"]
        text = "".join(lines)
        globals()["lines"] = []
    else:
        text = "".join(inp)
    print(text)


def println(text):
    print(text + "\n")


def print_list(list_to_print, insert_return=True, pre="", post=""):
    for i in list_to_print:
        print(f"{pre}{i}{post}")
        if insert_return:
            print("\n")


def insert_current_directories_to_path():
    current_dir = os.getcwd()
    dirs = [dI for dI in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, dI))]
    for dir in dirs:
        sys.path.append(os.path.join(current_dir, dir))


def print_links_html(field_hash):
    links_list = []
    if "links" in field_hash:
        for i in field_hash["links"]:
            links_list.append('<a href="{}">{}</a>'.format(field_hash["links"][i], i))
    elif "link" in field_hash:
        links_list = ['<a href="{}">{}</a>'.format(field_hash["link"], "link")]
    return ", ".join(links_list)


def generate_registers_html(registers, enums=None):
    register_list_lines = ""
    register_lines = ""
    registers_registers = registers["registers"]
    colspan = 6
    if enums is None:
        enums = {}
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    lines_append(
        """
        <!DOCTYPE html>
        <html>
        <head>
        {style}
        </head>
        <body>
        {body}
        """.format(
            body=return_html_body(current_revision),
            style=return_html_style(),
        )
    )

    register_list_lines = (
        register_list_lines
        + """
        <table border="1" class="register_list" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: left;">
              <th>Address</th>
              <th>Register Name</th>
            </tr>
          </thead>
    """.format(
            html_table_width=html_table_width
        )
    )

    for i in sorted(registers_registers):
        reg_name = registers["registers"][i]["name"]
        reg_addr = i * registers["address_in_n_bytes"]
        reg_type = registers["registers"][i]["type"]
        reg_array = registers["registers"][i]["array"]
        if reg_array > 1:
            reg_array_define = "[{}]".format(reg_array)
        else:
            reg_array_define = ""
        if "text" in registers["registers"][i]:
            reg_text = '<th colspan="{colspan}"; style="font-weight: normal;">{text}</th>'.format(
                colspan=colspan, text=registers["registers"][i]["text"]
            )
        else:
            reg_text = ""
        register_list_lines = (
            register_list_lines
            + """
            <tr><td>0x{reg_addr:08x}</td><td><a href="#{reg_name_anchor}">{reg_name}{reg_array_define}</a></td></tr>
        """.format(
                reg_name_anchor=reg_name,
                reg_name=reg_name.upper(),
                reg_addr=reg_addr,
                reg_array_define=reg_array_define,
            )
        )
        register_lines = (
            register_lines
            + """
        <a id="{reg_name_anchor}"></a>
        <table border="1" class="register_definition" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: center;">
            <th>Address: 0x{reg_addr:08x}</th>
            <th colspan="{colspan}-1">Name: {reg_name}{reg_array_define}</th>
            </tr>
            {reg_text}
            <tr style="text-align: right;">
              <th>Field</th>
              <th>Type</th>
              <th>Lsb</th>
              <th>Width</th>
              <th>Reset</th>
              <th>Explanation</th>
            </tr>
          </thead>
        <br /><br /><br />
        """.format(
                reg_name_anchor=reg_name,
                reg_name=reg_name,
                reg_text=reg_text,
                colspan=colspan,
                reg_addr=reg_addr,
                reg_array_define=reg_array_define,
                html_table_width=html_table_width,
            )
        )

        for field in registers["registers"][i]["fields"]:
            if "type" in registers["registers"][i]["fields"][field]:
                field_type = registers["registers"][i]["fields"][field]["type"]
            else:
                field_type = reg_type

            field_width = "Not Defined"
            if "width" in registers["registers"][i]["fields"][field]:
                field_width = registers["registers"][i]["fields"][field]["width"]
            elif "enum" in registers["registers"][i]["fields"][field]:
                if registers["registers"][i]["fields"][field]["enum"] in enums:
                    field_width = enums[
                        registers["registers"][i]["fields"][field]["enum"]
                    ]["width"]

            # Add the text from the field and the text from the enum if
            # applicable.
            field_text = ""
            if "text" in registers["registers"][i]["fields"][field]:
                field_text = (
                    registers["registers"][i]["fields"][field]["text"] + "<br />\n"
                )
            if "enum" in registers["registers"][i]["fields"][field]:
                if registers["registers"][i]["fields"][field]["enum"] in enums:
                    enum_name = registers["registers"][i]["fields"][field]["enum"]
                    if ("text" in enums[enum_name]):
                        field_text = field_text + enum_name + ": " + enums[enum_name]["text"] + "<br />\n"
                        for value in enums[enum_name]["values"]:
                            field_text = field_text + "{}: {}<br />\n".format(value, enums[enum_name]["values"][value])
            if "auto_enum" in registers["registers"][i]["fields"][field]:
                for value in registers["registers"][i]["fields"][field]["auto_enum"]:
                    field_text = field_text + "{}: {}<br />\n".format(value, registers["registers"][i]["fields"][field]["auto_enum"][value])
            external_signals_text = ""
            external_in_present = "external_in" in registers["registers"][i]["fields"][field]
            external_en_present = "external_en" in registers["registers"][i]["fields"][field]
            reset = "N/A"
            if "reset" in registers["registers"][i]["fields"][field]:
                reset = registers["registers"][i]["fields"][field]['reset']
            if "value" in registers["registers"][i]["fields"][field]:
                reset = f"{registers['registers'][i]['fields'][field]['value']} - hard coded"
            if type(reset) == int:
                reset = f"0x{reset:x}"
            elif "::" in reset:
                reset = reset.split("_E_")[-1]
            if external_in_present and external_en_present:
                external_signals_text += " - with hw update"
            if "pulse1" in registers["registers"][i]["fields"][field]:
                external_signals_text += " - pulse1"
            register_lines = (
                register_lines
                + """
            <tr style="text-align: left;">
              <td>{field}</td>
              <td>{type}</td>
              <td>{lsb}</td>
              <td>{width}</td>
              <td>{reset}</td>
              <td>{text}</td>
            </tr>
            """.format(
                    field=field,
                    type=field_type + external_signals_text,
                    lsb=registers["registers"][i]["fields"][field]["lsb"],
                    width=field_width,
                    text=field_text,
                    reset=reset,
                )
            )
        register_lines = register_lines + "</table>"
    register_list_lines = register_list_lines + "</table>"
    lines_append(register_list_lines)
    lines_append(register_lines)
    lines_append(
        """
</body>
</html>
"""
    )


def generate_commands_html( # noqa
    commands,
    enums=None,
    aligned_lsb=None,
):
    command_list_lines = ""
    command_lines = ""
    colspan = 4
    if enums is None:
        enums = {}

    command_list_lines = (
        command_list_lines
        + """
        <table border="1" class="register_list" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: left;">
              <th>Command</th>
            </tr>
          </thead>
    """.format(
            html_table_width=html_table_width
        )
    )

    for cmd in commands:
        cmd_name = cmd
        description = ""
        if "text" in commands[cmd]:
            description = description + commands[cmd]["text"] + "<br />"
        if "beat_count" in commands[cmd]:
            for item in commands[cmd]["beat_count"]:
                description = description + f"Beat count for {item}: {commands[cmd]['beat_count'][item]}<br />"
        if "data_size" in commands[cmd]:
            for item in commands[cmd]["data_size"]:
                description = description + f"Data size for {item}: {commands[cmd]['data_size'][item]}<br />"
        cmd_text = f'<th colspan="{colspan}"; style="font-weight: normal;">{description}</th>'
        command_list_lines = (
            command_list_lines
            + """
            <tr><td><a href="#{cmd_name_anchor}">{cmd_name}</a></td></tr>
        """.format(
                cmd_name_anchor=cmd_name, cmd_name=cmd_name.upper()
            )
        )
        command_lines = (
            command_lines
            + """
        <a id="{cmd_name_anchor}"></a>
        <table border="1" class="command_definition" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: center;">
            <th colspan="{colspan}">Name: {cmd_name}</th>
            </tr>
            {cmd_text}
            <tr style="text-align: right;">
              <th>Field</th>
              <th>Width</th>
              <th>Bits</th>
              <th>Explanation</th>
            </tr>
          </thead>
        <br /><br /><br />
        """.format(
                cmd_name_anchor=cmd_name,
                cmd_name=cmd_name,
                cmd_text=cmd_text,
                colspan=colspan,
                html_table_width=html_table_width,
            )
        )

        field_lsb = 0
        for field in commands[cmd]["fields"]:
            field_width = "Not Defined"
            if "width" in commands[cmd]["fields"][field]:
                field_width = commands[cmd]["fields"][field]["width"]
            elif "enum" in commands[cmd]["fields"][field]:
                if commands[cmd]["fields"][field]["enum"] in enums:
                    field_width = enums[commands[cmd]["fields"][field]["enum"]]["width"]

            if aligned_lsb is not None and field != "rest":
                field_lsb = max(field_lsb, aligned_lsb(field))

            field_bits = "{}:{}".format(field_width + field_lsb - 1, field_lsb)
            field_lsb += field_width
            link = print_links_html(commands[cmd]["fields"][field])

            # Add the text from the field and the text from the enum if
            # applicable.
            field_text = ""
            if "text" in commands[cmd]["fields"][field]:
                field_text = commands[cmd]["fields"][field]["text"]
            if "enum" in commands[cmd]["fields"][field]:
                if "text" in commands[cmd]["fields"][field]:
                    field_text = field_text + "<br />\n"
                if commands[cmd]["fields"][field]["enum"] in enums:
                    enum = enums[commands[cmd]["fields"][field]["enum"]]
                    enum_name = commands[cmd]["fields"][field]["enum"]
                    if "text" in enum:
                        field_text = (
                            field_text + enum_name + ": " + enum["text"] + "<br />\n"
                        )
                        if (
                            type(enum["values"]) == dict
                            or type(enum["values"]) == OrderedDict
                        ):
                            for e in enum["values"]:
                                field_text = field_text + "{} = {}<br />\n".format(
                                    e, enum["values"][e]
                                )
                        else:  # Convert to a hash with default values.
                            i = 0
                            for e in enum["values"]:
                                field_text = field_text + "{} = {}<br />\n".format(e, i)
                                i += 1
            if link != "":
                field_text = field_text + "{}\n".format(link)
            command_lines = (
                command_lines
                + """
            <tr style="text-align: left;">
              <td>{field}</td>
              <td>{width}</td>
              <td>{bits}</td>
              <td>{text}</td>
            </tr>
            """.format(
                    field=field, width=field_width, text=field_text, bits=field_bits
                )
            )
        command_lines = command_lines + "</table>"
    command_list_lines = command_list_lines + "</table>"
    lines_append(command_list_lines)
    lines_append(command_lines)
    lines_append("<br>\n")
    lines_append("<hr>\n")


def html_common_top():
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    lines_append(
        """
        <!DOCTYPE html>
        <html>
        <head>
        {style}
        </head>
        <body>
        {body}
        """.format(
            body=return_html_body(current_revision),
            style=return_html_style(),
        )
    )


def html_common_bottom():
    lines_append(
        """
</body>
</html>
        """
    )

#for generating register map for CP to send register configuraiton trans to Funtion Units
#target may be a list
def get_FU_name_cmodel(target):
    target_fus =['dpe','fi','mlu','re','sfu', 'sdma']
    if target_fus.count(target[0]):
        return target[0]+"_"
    return ""


def generate_registers_map_cmodel(registers, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    #for CP's registers
    register_lines = """// rev: {}
#define REGS_MAP """.format(current_revision)
    registers_registers = registers["registers"]
    if enums is None:
        enums = {}

    for i in registers_registers:
        reg_name = registers["registers"][i]["name"]
        reg_addr = i * registers["address_in_n_bytes"]
        reg_array = registers["registers"][i]["array"]
        register_lines = (
            register_lines
            + """REG_MAP({}, {}, {}); \\
    """.format(hex(reg_addr), reg_name, reg_array)
        )
    register_lines = register_lines + ";"
    lines_append(register_lines)

    # generate FU's registers map
    register_lines="\n\n//FU registers map for CP to generate trans to configure FU registers"
    lines_append(register_lines)
    register_lines = "\n#define FU_REGS_MAP          \\\n"
    for reg_idx in registers_registers:
        if 'target' in registers["registers"][reg_idx]:
            target = registers["registers"][reg_idx]['target']
            reg_name = registers["registers"][reg_idx]["name"]
            reg_type = registers["registers"][reg_idx]["type"]
            fu_name= get_FU_name_cmodel(target)
            if reg_type == "ro" or not fu_name : continue
            reg_addr = reg_idx * registers["address_in_n_bytes"]
            reg_array = registers["registers"][reg_idx]["array"]
            register_lines = (
                register_lines
                + f"    FU_REG_MAP({hex(reg_addr)}, {fu_name}, {reg_name}, {reg_array} ); \\\n"
            )
    register_lines = register_lines + ";"
    lines_append(register_lines)


def generate_interfaces_cmodel(name, unit_interfaces, interfaces, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    interface_lines = "// rev: {}\n".format(current_revision)
    inputs = unit_interfaces["inputs"]
    outputs = unit_interfaces["outputs"]
    interface_lines = (
        """
//@nolint
#pragma once
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/simenv/simulator.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/simenv/ports.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/util/SPtr.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/fb_inference_intf_cmodel.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/fb_inference_cmodel_registers.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/parameters.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/test_harness.h"

#define SP Utils::SPtr

class {}: public TestHarnessBase {{
  public:

  //Interface Signals\n""".format(name)
    )

    all_interfaces = {}
    all_interfaces.update(inputs)
    all_interfaces.update(outputs)

    for interface in all_interfaces:
        interface_type = all_interfaces[interface]['type']
        if type(interface_type) == str:
            if interface_type in interfaces:
                all_interfaces[interface]['type'] = interfaces[interface_type]
            else:
                import sys
                sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))

    # Interface signals
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            interface_lines = (
                interface_lines
                + """  {}<SP<{}> > *{};\n""".format(
                    port_type,
                    interface_type,
                    interface_name + str(a),
                )
            )

    # Constructor
    interface_lines = (
        interface_lines
	+ """ // End of interface signals\n\n  {}( Sim* s\n""".format(name)
    )
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            interface_lines = (
                interface_lines
                + """    ,{}<SP<{}> > *{}\n""".format(
                    port_type,
                    interface_type,
                    interface_name + str(a),
                )
            )
    interface_lines = (
        interface_lines
	+ """  );\n"""
    )
    interface_lines = (
        interface_lines
	+ """  void eval() override;\n """
    )
    interface_lines = (
        interface_lines
	+ """ }; """
    )
    lines_append(interface_lines)

def generate_module_cmodel(name, unit_interfaces, interfaces, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    module_lines = "// rev: {}\n".format(current_revision)
    inputs = unit_interfaces["inputs"]
    outputs = unit_interfaces["outputs"]
    all_interfaces = {}
    all_interfaces.update(inputs)
    all_interfaces.update(outputs)
    short_name = name.replace('fb_inf_', '').replace('_scalar', '').replace('_vector', '')
    lines_append("""\
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/{}/{}.h"

void {}::eval() {{ }};\n""".format(short_name, name, name))

    for interface in all_interfaces:
        interface_type = all_interfaces[interface]['type']
        if type(interface_type) == str:
            if interface_type in interfaces:
                all_interfaces[interface]['type'] = interfaces[interface_type]
            else:
                import sys
                sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))

    # Constructor
    lines_append("\n  {}::{}(Sim* s\n".format(name, name))
    cnstr_txt = []
    argum_txt = []
    hanmp_txt = []
    for i in all_interfaces:
        isIn = i in inputs
        intf = inputs[i] if isIn else outputs[i]
        interface_type = intf["type"]["name"]
        interface = intf["type"]
        array = int(intf['array']) if "array" in intf else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            cnstr_txt.append("    ,{}<SP<{}> > *{}\n".format(port_type,
                    interface_type, interface_name + str(a)))
            argum_txt.append("    ,{0}({0})\n".format(interface_name + str(a)))
            hanmp_txt.append("""\
    {0}HANDLER_MAP({1}, {2}, {3});
""".format("" if port_type == "CPort" else "BPORT_", interface_type,
        interface_name + str(a), "false" if isIn else "true"))

    lines_extend(cnstr_txt)
    lines_append("  )\n")
    lines_append("    : TestHarnessBase(s)\n")
    lines_extend(argum_txt)
    lines_append("{\n")
    lines_extend(hanmp_txt)
    lines_append("}\n")

def generate_module_testharness_cmodel(name, unit_interfaces, interfaces, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    header_lines = "// rev: {}\n".format(current_revision)
    inputs = unit_interfaces["inputs"]
    outputs = unit_interfaces["outputs"]
    short_name = name.replace('fb_inf_', '').replace('_scalar', '').replace('_vector', '')
    header_lines = (
      header_lines
        + """
#pragma once
//@nolint

#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/test_harness.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/{}/{}.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/test/testexit.h"

// Type specific test harness, auto generated.
class {}_test : public TestHarnessBase {{
public:
""".format(short_name, name, name)
    )
    # declare member var for the model instance
    header_lines = (
        header_lines
        + """\n  {}* inst;\n""".format(name)
    )
    all_interfaces = {}
    all_interfaces.update(inputs)
    all_interfaces.update(outputs)

    for interface in all_interfaces:
        interface_type = all_interfaces[interface]['type']
        if type(interface_type) == str:
            if interface_type in interfaces:
                all_interfaces[interface]['type'] = interfaces[interface_type]
            else:
                import sys
                sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))

    # Interface signals
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            header_lines = (
                header_lines
                + """  {}<SP<{}> > *{};\n""".format(
                    port_type,
                    interface_type,
                    interface_name + str(a),
                )
            )

    header_lines = (
        header_lines
        + """
  CPort<int> *testexitport;
  TestExit *testexit;
"""
    )

    # Constructor
    header_lines = (
        header_lines
	+ """
  {}_test(Sim *sim)
  : TestHarnessBase(sim)
  {{
""".format(name)
    )

    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            header_lines = (
                header_lines
                + """    {} = new {}<SP<{}> >(sim);\n""".format(
                    interface_name + str(a),
                    port_type,
                    interface_type
                )
            )

    header_lines = (
        header_lines
        + """    inst = new {}(sim, this, "{}"\n""".format(name, short_name)
    )
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            header_lines = (
                header_lines
                + """      ,{}\n""".format(
                    interface_name + str(a),
                )
            )
    header_lines = (
        header_lines
        + """    );\n"""
    )
    header_lines = (
        header_lines
        + """
    testexitport = new CPort<int>(sim);
    testexit = new TestExit(sim,testexitport);

    // Setup the handlers for the different ports
"""
    )
    # Setup the handlers for the different ports
    for i in all_interfaces:
        isOut = True
        if i in inputs:
            isOut = False;
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i
        handler_type = "BPort" if "register" in interface_type else ""
        for a in range(array):
            header_lines = (
                header_lines
                + """ \
    handler_map["{portName}"] =
      new Handler{handlerType}<{portType}>({portName}, *this, {isOut});
""".format(
                        handlerType = handler_type,
                        portName=interface_name+str(a),
                        portType=interface_type,
                        isOut = "true" if (isOut) else "false"
                    )
                )

    header_lines = (
        header_lines
        + """
  }
"""
    )

    # Destructor
    header_lines = (
        header_lines
        + """\n  ~{}_test() {{\n""".format(name)
    )
    header_lines = (
        header_lines
        + """    delete inst;\n"""
    )
    for i in all_interfaces:
        if i in inputs:
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            header_lines = (
                header_lines
                + """    delete {};\n""".format(
                    interface_name + str(a)
                )
            )

    header_lines = (
        header_lines
        + """
    delete testexitport;
    delete testexit;
  }
  void exit(int status, int time) {
    testexitport->write(status, time);
  }
};
"""
    )
    lines_append(header_lines)


def generate_topmodule_header_cmodel(name, unit_interfaces, interfaces, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    header_lines = (
        """
// rev: {}
#pragma once

#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/headers/top.h"

class {}_top : public Top {{
    public:
    void create_top(Sim *sim) override;
}};
    """.format(current_revision, name)
    )
    lines_append(header_lines)


def generate_topmodule_cmodel(name, unit_interfaces, interfaces, enums=None):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    module_lines = "// rev: {}\n".format(current_revision)
    inputs = unit_interfaces["inputs"]
    outputs = unit_interfaces["outputs"]
    short_name = name.replace('fb_inf_', '').replace('_scalar', '').replace('_vector', '')
    module_lines = (
        """
#include <iostream>
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/{}/{}_top.h"
#include "infra_asic_fpga/ip/fb_inference_gen2/main/cmodel/model/{}/{}.h"

void {}_top::create_top(Sim* sim) {{
""".format(short_name, name, short_name, name, name)
    )

    all_interfaces = {}
    all_interfaces.update(inputs)
    all_interfaces.update(outputs)

    for interface in all_interfaces:
        interface_type = all_interfaces[interface]['type']
        if type(interface_type) == str:
            if interface_type in interfaces:
                all_interfaces[interface]['type'] = interfaces[interface_type]
            else:
                import sys
                sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))

    # Interface signals
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            port_type = "BPort" if "register" in interface_type else "CPort"
            module_lines = (
                module_lines
                + """  {}<SP<{}> > *{} = new {}<SP<{}> >(sim);\n""".format(
                    port_type,
                    interface_type,
                    interface_name + str(a),
                    port_type,
                    interface_type,
                )
            )

    # Constructor
    module_lines = (
        module_lines
	+ """ // End of interface signals\n\n  new {}(sim\n""".format(name)
    )
    for i in all_interfaces:
        if i in inputs:
            interface_type = inputs[i]["type"]["name"]
            interface = inputs[i]["type"]
            array = int(inputs[i]['array']) if "array" in inputs[i] else 1
        else:
            interface_type = outputs[i]["type"]["name"]
            interface = outputs[i]["type"]
            array = int(outputs[i]['array']) if "array" in outputs[i] else 1
        interface_name = i

        for a in range(array):
            module_lines = (
                module_lines
                + """    ,{}\n""".format(
                    interface_name + str(a),
                )
            )
    module_lines = (
        module_lines
	+ """  );\n"""
    )
    module_lines = (
        module_lines
	+ """ } """
    )
    lines_append(module_lines)

def generate_interfaces_html(unit_interfaces, interfaces, enums=None):
    interface_list_lines = ""
    interface_lines = ""
    inputs = unit_interfaces["inputs"]
    outputs = unit_interfaces["outputs"]
    colspan = 3
    if enums is None:
        enums = {}
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    lines_append(
        """
        <!DOCTYPE html>
        <html>
        <head>
        {style}
        </head>
        <body>
        {body}
        """.format(
            body=return_html_body(current_revision),
            style=return_html_style(),
        )
    )

    interface_list_lines = (
        interface_list_lines
        + """
        <table border="1" class="interface_list" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: left;">
              <th>Direction</th>
              <th>Name</th>
              <th>Type</th>
              <th>Description</th>
            </tr>
          </thead>
    """.format(
            html_table_width=html_table_width
        )
    )

    all_interfaces = {}
    all_interfaces.update(inputs)
    all_interfaces.update(outputs)

    for interface in all_interfaces:
        interface_type = all_interfaces[interface]['type']
        if type(interface_type) == str:
            if interface_type in interfaces:
                all_interfaces[interface]['type'] = interfaces[interface_type]
            else:
                import sys
                sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))

    array = ""
    for i in all_interfaces:
        if i in inputs:
            io = "input"
            interface_type = inputs[i]["type"]["name"]
            interface_description = (
                inputs[i]["type"]["text"] if "text" in inputs[i]["type"] else ""
            )
            interface = inputs[i]["type"]
            array = "[{}]".format(inputs[i]['array']) if "array" in inputs[i] else ""
        else:
            io = "output"
            interface_type = outputs[i]["type"]["name"]
            interface_description = (
                outputs[i]["type"]["text"] if "text" in outputs[i]["type"] else ""
            )
            interface = outputs[i]["type"]
            array = "[{}]".format(outputs[i]['array']) if "array" in outputs[i] else ""
        interface_direction = io
        interface_name = i
        interface_description = interface_description + "<br />Meta: {}".format(
            convert_to_yaml(interface["meta"])
        )

        def replace_with_meta_if_present(s):
            y = s
            if y in interface["meta"]:
                y = interface["meta"][y]
            return y

        interface_list_lines = (
            interface_list_lines
            + """
            <tr><td>{direction}</td><td><a href="#{name_anchor}">{name}{array}</a></td><td>{type}</td><td>{description}</td></tr>
        """.format(
                direction=interface_direction,
                name_anchor=interface_name.upper(),
                name=interface_name,
                type=interface_type,
                description=interface_description,
                array=array,
            )
        )
        interface_lines = (
            interface_lines
            + """
        <a id="{name_anchor}"></a>
        <table border="1" class="interface_definition" style="width:{html_table_width}">
          <thead>
            <tr style="text-align: center;">
            <th colspan="{colspan}">Name: {name}</th>
            </tr>
            <tr><td colspan="{colspan}">
            {description}
            </td></tr>
            <tr style="text-align: right;">
              <th>Field</th>
              <th>Width</th>
              <th>Explanation</th>
            </tr>
          </thead>
        <br /><br /><br />
        """.format(
                name_anchor=interface_name.upper(),
                name=interface_name,
                description=interface_description,
                colspan=colspan,
                html_table_width=html_table_width,
            )
        )
        if 'fields' in interface:
            for field in interface["fields"]:
                field_width = "Not Defined"
                if "width" in interface["fields"][field]:
                    field_width = replace_with_meta_if_present(
                        interface["fields"][field]["width"]
                    )
                elif "enum" in interface["fields"][field]:
                    if interface["fields"][field]["enum"] in enums:
                        field_width = enums[interface["fields"][field]["enum"]]["width"]
                elif "type" in interface["fields"][field]:
                    field_width = "$bits({}::{})".format(
                        interface["package"], interface["fields"][field]["type"]
                    )

                # Add the text from the field and the text from the enum if
                # applicable.
                field_text = ""
                if "text" in interface["fields"][field]:
                    field_text = interface["fields"][field]["text"] + "<br />\n"
                if "enum" in interface["fields"][field]:
                    if interface["fields"][field]["enum"] in enums:
                        enum_name = interface["fields"][field]["enum"]
                        if "text" in enums[interface["fields"][field]["enum"]]:
                            field_text = (
                                field_text
                                + enum_name
                                + ": "
                                + enums[interface["fields"][field]["enum"]]["text"]
                                + "<br />\n"
                            )
                            k = 0
                            for value in enums[interface["fields"][field]["enum"]][
                                "values"
                            ]:
                                if (
                                    type(
                                        enums[interface["fields"][field]["enum"]]["values"]
                                    )
                                    == OrderedDict
                                    or type(
                                        enums[interface["fields"][field]["enum"]]["values"]
                                    )
                                    == dict
                                ):
                                    field_text = field_text + "{}: {}<br />\n".format(
                                        value,
                                        enums[interface["fields"][field]["enum"]]["values"][
                                            value
                                        ],
                                    )
                                else:
                                    field_text = field_text + "{}: {}<br />\n".format(
                                        value, k
                                    )
                                    k += 1
                if "lsb" in interface["fields"][field]:
                    field_text = field_text + "<br /> Lsb: {}, Msb: {}\n".format(interface["fields"][field]['lsb'], field_width-1)
                    field_width = field_width - interface["fields"][field]['lsb']
                interface_lines = (
                    interface_lines
                    + """
                <tr style="text-align: left;">
                  <td>{field}</td>
                  <td>{width}</td>
                  <td>{text}</td>
                </tr>
                """.format(
                        field=field, width=field_width, text=field_text
                    )
                )
            interface_lines = interface_lines + "</table>"
    interface_list_lines = interface_list_lines + "</table>"
    lines_append(interface_list_lines)
    lines_append(interface_lines)
    lines_append(
        """
</body>
</html>
"""
    )


def generate_interface_struct(
        interface,
        tab="auto",
        enums=None,
        enum_wrap=False,
        unique_enum_name=True,
        use_full_reference=False,
        package="",
        use_package=False,
        cmodel=False
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if "unpacked" in interface:
        struct_type = ""
    else:
        struct_type = " packed"
    if enums is None:
        enums = {}
    if "fields" in interface:
        lines_append(tab + "typedef struct{}\n".format(struct_type))
        lines_append(tab + "{\n")

        def replace_with_meta_if_present(s):
            y = s
            if y in interface["meta"]:
                y = interface["meta"][y]
            return y

        fields_list = interface["fields"] if cmodel is True else reversed(list(interface["fields"]))


        for f in fields_list:
            if "width" in interface["fields"][f]:
                width = replace_with_meta_if_present(interface["fields"][f]["width"])
                msb = "{}-1".format(width)
                if "lsb" in interface["fields"][f]:
                    lsb = replace_with_meta_if_present(interface["fields"][f]["lsb"])
                else:
                    lsb = 0
                if cmodel is True:
                    lines_append(tab + t + "int {};\n".format(f))
                elif "declare" in interface["fields"][f]:
                    lines_append(tab + t + "logic {} {};\n".format(interface["fields"][f]["declare"], f))
                else:
                    lines_append(tab + t + "logic [{}:{}] {};\n".format(msb, lsb, f))
            elif "enum" in interface["fields"][f]:
                enum_name = interface["fields"][f]["enum"]
                enum_class = enum_2_class_name(enum_name)
                if enum_wrap:
                    enum_name = "{}::{}".format(enum_class, enum_name)
                if use_full_reference:
                    enum_name = "{}::{}".format(package, enum_name)
                if use_package:
                    enum_name = "{}::{}".format(enums[enum_name]['package'], enum_name)
                assert cmodel is False
                lines_append(tab + t + "{} {};\n".format(enum_name, f))
            else:
                if (
                    type(interface["fields"][f]["type"]) == dict
                    or type(interface["fields"][f]["type"]) == OrderedDict
                ):
                    struct = interface["fields"][f]["type"]["name"]
                else:
                    struct = replace_with_meta_if_present(interface["fields"][f]["type"])
                    if "package" in interface["fields"][f]:
                        struct = "{}::{}".format(interface["fields"][f]["package"], struct)
                lines_append(tab + t + "{} {};\n".format(struct, f))
        postfix = "" if cmodel is True else "_t"
        lines_append(tab + "} " + "{}{};\n".format(interface["name"], postfix))


def generate_interface_structs(interfaces, tab="auto", enums=None, cmodel=False, use_package=False):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if enums is None:
        enums = {}
    for i in interfaces:
        # FBIA Cmodel uses the PKTGen generated interfaces except for registers
        if cmodel is False or "register" in interfaces[i]["name"]:
            generate_interface_struct(interfaces[i], tab=tab, enums=enums, cmodel=cmodel, use_package=use_package)
            newln()

def generate_interface_json_decls_cmodel(interfaces):
    for i in sorted(interfaces, key=lambda key: key):
        # FBIA Cmodel uses the PKTGen generated interfaces except for registers
        if "registers" not in interfaces[i]["name"]: continue
        if "fields" not in interfaces[i]: continue
        lines_append("""
// Register {0}
bool operator==(const {0}& a, const {0}& b);
bool operator!=(const {0}& a, const {0}& b);
void fromJSON({0}& tp, const rapidjson::Value& j);
string toJSON(const {0}& tp, /* unused */ rapidjson::Value* j = nullptr);
""".format(interfaces[i]["name"]))
    newln()

def generate_interface_json_cmodel(interfaces):
    for i in sorted(interfaces, key=lambda key: key):
        # FBIA Cmodel uses the PKTGen generated interfaces except for registers
        if "registers" not in interfaces[i]["name"]: continue
        if "fields" not in interfaces[i]: continue
        name = interfaces[i]["name"]
        to_txt = []
        fr_txt = []
        eq_txt = []
        to_txt.append("""
// Register bport struct {0}
string toJSON(const {0}& tp, /* unused */ rapidjson::Value* j) {{
  stringstream ss;
  ss << "{{";
""".format(name))
        eq_txt.append("""
bool operator==(const {0}& a, const {0}& b) {{
  return (""".format(name))
        fr_txt.append(f"void fromJSON({name}& tp, const rapidjson::Value& j) {{\n")
        andIt = ""
        comma = ""
        for f in interfaces[i]["fields"]:
            if "enum" in interfaces[i]["fields"][f]: continue
            ft = "" if "width" in interfaces[i]["fields"][f] else "Struct"
            to_txt.append(f"  ss << {comma}output{ft}Field(tp,{f})\n")
            fr_txt.append(f"  set{ft}Field(j,tp,{f})\n")
            eq_txt.append(f"{andIt}(a.{f} == b.{f})\n")
            andIt = "    && "
            comma = "\",\" << "
        to_txt.append("  ss << \"}\";\n  return ss.str();\n}\n")
        fr_txt.append("}\n");
        eq_txt.append("  );\n}\n")
        lines_extend(to_txt)
        lines_extend(fr_txt)
        lines_extend(eq_txt)
        lines_append("""
bool operator!=(const {0}& a, const {0}& b) {{
  return !(a == b);
}}
""".format(name))
    newln()

def generate_enum(enum, tab="auto", enum_wrap=False, unique_enum_name=True):
    """
    Generate a typedef enum based on the enum input dict.

    enum: Dict with fields specifying an enum.
    tab: The initial indentation string to use for the generated code. If set to 'auto', then it's
        determined based on the &python* placement.
    enum_wrap: Boolean that specifies if the typedef enum is wrapped around a dummy class. This is
        needed if multiple enums have common value names.
    """

    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if enum["width"] == "auto":
        if type(enum["values"]) == list:
            width = log2(len(enum["values"]))
        else:
          width = max(log2(len(enum["values"])), log2(max(list(enum["values"].values()))))
    else:
        width = enum["width"]
        assert width >= log2(
            len(enum["values"])
        ), "Wrong enum width for {} - {} !>= {} - {}.\n".format(
            enum["name"], width, log2(len(enum["values"])), enum["values"]
        )

    enum_wrap_tab = ""
    if enum_wrap:
        class_name = enum_2_class_name(enum["name"])

        # Wrap typedef enum around a dummy class so other enums are in different
        # scopes. Declare virtual to prevent users from create an object.
        lines_append(tab + "virtual class {};\n".format(class_name))
        enum_wrap_tab = t
    lines_append(tab + enum_wrap_tab + "typedef enum logic [{}-1:0]\n".format(width))
    lines_append(tab + enum_wrap_tab + "{\n")

    if type(enum["values"]) == dict or type(enum["values"]) == OrderedDict:
        enum_list = enum["values"]
    else:  # Convert to a hash with default values.
        i = 0
        enum_list = OrderedDict()
        for e in enum["values"]:
            enum_list[e] = i
            i += 1
        enum_list = enum_list
    all_enum_values = []
    for k in enum_list:
        if unique_enum_name:
            kk = enum['name'].upper() + "_" + k
        else:
            kk = k
        all_enum_values.append(
            tab + enum_wrap_tab + t + "{} = {}".format(kk, enum_list[k])
        )

    lines_append(",\n".join(all_enum_values) + "\n")
    lines_append(tab + enum_wrap_tab + "} " + "{};\n".format(enum["name"]))

    if enum_wrap:
        lines_append(tab + "endclass\n")


def generate_enums(enums, tab="auto", enum_wrap=False, unique_enum_name=True):
    """
    Generate typedef enums based on a dict of enum dicts.

    enums: Dict with fields specifying one or more enums.
    tab: The initial indentation string to use for the generated code. If set to 'auto', then it's
        determined based on the &python* placement.
    enum_wrap: Boolean that specifies if the typedef enum is wrapped around a dummy class. This is
        needed if multiple enums have common value names.
    """

    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    for i in sorted(enums, key=lambda key: key):
        generate_enum(enums[i], tab=tab, enum_wrap=enum_wrap, unique_enum_name=unique_enum_name)
        newln()

def generate_enums_definition(enums, tab="auto", enum_wrap=False):
    """
    This method generates the opcode enum in verilog `define syntax.
    """
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent

    opcode_enum = enums["OPCODE_e"]
    i = 0
    for value in opcode_enum["values"]:
        lines_append(f"`define OPCODE_E_{value} {i}\n")
        i += 1
    newln()

def generate_command_field_definition(commands, enums, aligned_lsb):
    """
    This method generates all customized instructions with fields aligned in
    verilog `define syntax.
    """
    for _, command in commands.items():
        command["fields"] = add_reserved_fields(command["fields"], enums, aligned_lsb)

        lsb = 0
        for f in command["fields"]:
            if "rest" in f:
                continue

            if "reserved" in f:
                lsb += command["fields"][f]["width"]
                continue

            width = (
                command["fields"][f]["width"]
                if "width" in command["fields"][f]
                else enums[command["fields"][f]["enum"]]["width"]
            )
            lines_append(f"`define {command['name']}_{f.upper()} {lsb+width-1}:{lsb}\n")
            lsb += width

        newln()

def add_reserved_fields(
    fields: OrderedDict,
    enums: OrderedDict,
    aligned_lsb: Callable,
) -> OrderedDict:
    aligned_fields = OrderedDict()

    field_lsb = 0
    rsvd_idx = 0
    for field in fields:
        if field != "rest" and field_lsb < aligned_lsb(field):
            aligned_fields[f"reserved_{rsvd_idx}"] = {
                "width": aligned_lsb(field) - field_lsb
            }
            field_lsb = aligned_lsb(field)
            rsvd_idx += 1

        aligned_fields[field] = fields[field]
        width = (
            fields[field]["width"]
            if "width" in fields[field]
            else enums[fields[field]["enum"]]["width"]
        )
        field_lsb += width

    return aligned_fields


def generate_command_struct(    # noqa
    command,
    enums=None,
    tab="auto",
    enum_wrap=False,
    unique_enum_name=True,
    use_full_reference=False,
    package="",
    use_package=False,
    aligned_lsb=None,
):
    """
    Generate command structs based on the command dict.

    command: Dict with fields specifying a command.
    tab: The initial indentation string to use for the generated code. If set to 'auto', then it's
        determined based on the &python* placement.
    enum_wrap: Boolean that specifies if the typedef enum is wrapped around a dummy class. This is
        needed if multiple enums have common value names.
    """

    if enums is None:
        enums = {}

    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent

    newln()
    if "text" in command:
        lines_append(tab + "// {}\n".format(command["text"]))
    if "width" in command:
        lines_append(tab + "// Command width: {}\n".format(command["width"]))
    if "union" in command:
        lines_append(tab + "typedef union packed\n")
    else:
        lines_append(tab + "typedef struct packed\n")
    lines_append(tab + "{\n")

    if aligned_lsb is not None:
        command["fields"] = add_reserved_fields(command["fields"], enums, aligned_lsb)

    for f in reversed(list(command['fields'])):
        ifdef = command["fields"][f].get("ifdef", "")
        ifndef = command["fields"][f].get("ifndef", "")
        # surround the field with ifdef/ifndef macro in the RTL
        # having two parallel ifs allows user to define ifdef and ifndef at the same time
        if ifdef:
            lines_append(tab + f"`ifdef {ifdef}")
        if ifndef:
            lines_append(tab + f"`ifndef {ifndef}")

        if "width" in command["fields"][f]:
            width = command["fields"][f]["width"]
            msb = "{}-1".format(width)
            if "lsb" in command["fields"][f]:
                lsb = command["fields"][f]["lsb"]
            else:
                lsb = 0
            lines_append(tab + t + "logic [{}:{}] {};\n".format(msb, lsb, f))
        elif "type" in command["fields"][f]:
            lines_append(tab + t + "{} {};\n".format(command["fields"][f]["type"], f))
        else:
            if command["fields"][f]["enum"] in enums:
                struct = command["fields"][f]["enum"]
                if enum_wrap:
                    struct = "{}::{}".format(enum_2_class_name(struct), struct)
                if use_full_reference:
                    struct = "{}::{}".format(package, struct)
                if use_package:
                    struct = "{}::{}".format(enums[command["fields"][f]["enum"]]['package'], struct)
                width = enums[command["fields"][f]["enum"]]['width']
            else:
                struct = command["fields"][f]["enum"]
                width = "N/A"
            lines_append(tab + t + "{} {}; // {}\n".format(struct, f, width))
        if ifdef:
            lines_append(tab + f"`endif")
        if ifndef:
            lines_append(tab + f"`endif")
    lines_append(tab + "} " + "{}_t;\n".format(command["name"]))


def generate_command_structs(
    commands,
    enums=None,
    tab="auto",
    enum_wrap=False,
    unique_enum_name=True,
    use_full_reference=False,
    package="",
    use_package=False,
    aligned_lsb=None,
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    if enums is None:
        enums = {}
    for i in commands:
        generate_command_struct(
            commands[i],
            tab=tab,
            enum_wrap=enum_wrap,
            unique_enum_name=True,
            enums=enums,
            use_full_reference=use_full_reference,
            package=package,
            use_package=use_package,
            aligned_lsb=aligned_lsb,
        )
        newln()


def generate_command_union(
    commands, union_name="all_commands_t", union_type="packed", tab="auto", uppercase=True, prefix=""
):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    lines_append(tab + "typedef union {}\n".format(union_type))
    lines_append(tab + "{\n")
    for i in commands:
        command_name = commands[i]["name"]
        lines_append(
            tab + t + "{}_t {};\n".format((prefix+command_name).upper() if uppercase else (prefix+command_name).lower(), command_name.lower())
        )
    lines_append(tab + "}} {};\n".format(union_name))


def cal_command_width(command, enums=None, structs=None, aligned_lsb=None):
    command_width = 0
    for field in command['fields']:
        if aligned_lsb is not None:
            command_width = max(command_width, aligned_lsb(field))
        if 'width' in command['fields'][field]:
            command_width += command['fields'][field][
                'width']
        elif 'type' in command['fields'][field]:
            typename = re.search(r'(.*)_t', command['fields'][field]['type']).group(1)
            command_width += cal_command_width(structs[typename], enums, structs)
        else:
            command_width += enums[command['fields'][field]['enum']]['width']

    return command_width


def reorder_fields(
    commands,
    order = [],
) -> OrderedDict:
    for command in commands:
        fields = copy.deepcopy(commands[command]["fields"])
        commands[command]["fields"] = OrderedDict()
        for ordered_field in order:
            commands[command]["fields"][ordered_field] = copy.deepcopy(fields[ordered_field])
            del(fields[ordered_field])
        for field in fields:
            commands[command]["fields"][field] = copy.deepcopy(fields[field])
    return commands


def add_dummy_command(
    commands,
    enums=None,
    fields=["opcode"],
    fields_to_remove=None,
    dummy_cmd_name='DUMMY',
    structs=None,
    aligned_lsb=None,
    aligned_command_width=None,
):
    if enums is None:
        enums = {}
    if fields_to_remove is None:
        fields_to_remove = []

    # First reorder the fields to match the order that is required.
    commands = reorder_fields(commands, fields)

    # Find out how many bits are needed for the widest command.
    command_width = 0
    first_command = ""
    for command in commands:
        # Remove fields.
        for ftr in fields_to_remove:
            if ftr in commands[command]["fields"]:
                del(commands[command]["fields"][ftr])
        if first_command == "":
            first_command = command
        current_command_width = cal_command_width(
            commands[command], enums, structs, aligned_lsb
        )
        commands[command]['width'] = current_command_width
        if current_command_width > command_width:
            command_width = current_command_width

    if aligned_lsb is not None:
        command_width = aligned_command_width

    # Add an extra field to match the width of the maximum command.
    for command in commands:
        if commands[command]['width'] < command_width:
            commands[command]['fields']['rest'] = {
                'width': command_width - commands[command]['width']
            }
        if aligned_lsb is not None:
            commands[command]["width"] = aligned_command_width

    command = f"""
        name: {dummy_cmd_name}
        text: >
            This is a dummy command description to get the opcode.
        fields:
    """
    command = convert_to_hash(command)
    command["fields"] = OrderedDict()
    rest = command_width
    for field in fields:
        command["fields"][field] = copy.deepcopy(commands[first_command]["fields"][field])
        if "enum" in command["fields"][field]:
            rest -= enums[command["fields"][field]["enum"]]["width"]
        else:
            rest -= command["fields"][field]["width"]
    command["fields"]["rest"] = {"width": rest, "text": "Rest of the fields."}
    commands[command['name']] = command

    return commands


def flatten_struct_fields(name, interface, direction, custom_width):
    fields = interface["fields"]
    pkg = interface["package"]
    def get_sigtype(field):
        return pkg+"::"+fields[field]["type"] if "type" in fields[field] else "logic"
    def get_width(field):
        return f"{custom_width[field]}" if field in custom_width else f"{fields[field]['width']}"

    return [f"{direction} {get_sigtype(f)} {name}{f}" if "type" in fields[f]
            else f"{direction} {get_sigtype(f)} [{get_width(f)}-1:0] {name}{f}"
            for f in fields]


def generate_interface(name, interface, direction, tab="auto", ios=None, flat=False):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    interface_type = interface["type"]
    space = " "
    limiter = ","
    if direction == "input":
        reverse_direction = "output"
    elif direction == "output":
        reverse_direction = "input"
    else:
        reverse_direction = ""
        space = ""
        limiter = ";"

    try:
        if "fields" in interface_type:
            array = "" if "array" not in interface else "[{}]".format(interface['array'])
            if flat:
                custom_width_dict = interface["width"] if "width" in interface else {}
                for text in flatten_struct_fields(name, interface_type, direction, custom_width_dict):
                    if ios is None:
                        lines_append(tab + f"{text}{limiter}\n")
                    else:
                        declare_io(text)
            else:
                text = "{}{}{}::{}_t {}{}".format(
                    direction, space, interface_type["package"], interface_type["name"], name, array
                )
                if ios is None:
                    lines_append(tab + "{}{}\n".format(text, limiter))
                else:
                    declare_io(text)
    except KeyError:
        print("Key error: name: {}, hash: {}".format(name, interface))

    try:
        array = "" if "array" not in interface else "[{}-1:0] ".format(interface['array'])
    except KeyError:
        print("Key error: name: {}, hash: {}".format(name, interface))

    if "ready" in interface_type["meta"]["flow_control"]:
        underscore = "" if "no_underscore" in interface_type["meta"] else "_"
        text = "{}{}logic {}{}{}ready".format(direction, space, array, name, underscore) if "debug_mon" in interface_type["meta"] else "{}{}logic {}{}{}ready".format(reverse_direction, space, array, name, underscore)
        if ios is None:
            lines_append(tab + "{}{}\n".format(text, limiter))
        else:
            declare_io(text)
    if "valid" in interface_type["meta"]["flow_control"]:
        underscore = "" if "no_underscore" in interface_type["meta"] else "_"
        text = "{}{}logic {}{}{}valid".format(direction, space, array, name, underscore)
        if ios is None:
            lines_append(tab + "{}{}\n".format(text, limiter))
        else:
            declare_io(text)
    if "wakeup" in interface_type["meta"]["flow_control"]:
        text = "{}{}logic {}{}_wakeup".format(direction, space, array, name)
        if ios is None:
            lines_append(tab + "{}{}\n".format(text, limiter))
        else:
            declare_io(text)


def generate_interface_perf_counters(intf_names, intf_type="ready-valid", print_period=4096, sim_only_macro="FB_BEH_SIM", tab="auto", print_cycle_counter=True, clk="clk", reset="reset_n", use_signal_directly=False, module_name="pe") -> str:
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    counter_width = 64
    text = ""

    text += f"{tab}`ifdef {sim_only_macro}\n"

    text += "`ifdef FB_PERF_PRINT_ON\n"
    text += "`ifndef EMU_PERF_CNTRS_ON\n"
    text += "// synopsys translate_off\n"
    text += "`endif // EMU_PERF_CNTRS_ON\n"

    if print_cycle_counter:
        text += f"{tab}logic [{counter_width-1}:0] cycle_counter_sim_only;\n"
        text += f"{tab}always_ff @(posedge {clk}, negedge {reset}) begin\n"
        text += f"{tab}{t}if (!{reset}) begin cycle_counter_sim_only <= 'd0; end\n"
        text += f"{tab}{t}else begin cycle_counter_sim_only <= cycle_counter_sim_only + 'd1; end\n"
        text += f"{tab}end\n"

    for intf in intf_names:
        if "[" in intf:
            valid = intf.replace("[", "_valid[")
            ready = intf.replace("[", "_ready[")
            name = intf.replace("[", "_").replace("]", "_")
        else:
            valid = f"{intf}_valid"
            ready = f"{intf}_ready"
            name = intf
        text += f"{tab}logic [{counter_width-1}:0] {name}_transactions_sim_only;\n"
        text += f"{tab}always_ff @(posedge {clk}, negedge {reset}) begin\n"
        text += f"{tab}{t}if (!{reset}) begin {name}_transactions_sim_only <= 'd0; end\n"
        if use_signal_directly:
            text += f"{tab}{t}else if ({intf}) begin {name}_transactions_sim_only <= {name}_transactions_sim_only + 'd1; end\n"
        elif intf_type == "ready-valid":
            text += f"{tab}{t}else if ({valid} & {ready}) begin {name}_transactions_sim_only <= {name}_transactions_sim_only + 'd1; end\n"
        else:
            text += f"{tab}{t}else if ({valid}) begin {name}_transactions_sim_only <= {name}_transactions_sim_only + 'd1; end\n"
        text += f"{tab}end\n"

        if intf_type == "ready-valid":
            text += f"{tab}logic [{counter_width-1}:0] {name}_stalls_sim_only;\n"
            text += f"{tab}always_ff @(posedge {clk}, negedge {reset}) begin\n"
            text += f"{tab}{t}if (!{reset}) begin {name}_stalls_sim_only <= 'd0; end\n"
            text += f"{tab}{t}else if ({valid} & ~{ready}) begin {name}_stalls_sim_only <= {name}_stalls_sim_only + 'd1; end\n"
            text += f"{tab}end\n"
        else:
            text += f"{tab}logic [{counter_width-1}:0] {name}_stalls_sim_only;\n"
            text += f"{tab}assign {name}_stalls_sim_only = {counter_width}'d0;\n"


        text += f"{tab}logic [{counter_width-1}:0] {name}_idles_sim_only;\n"
        text += f"{tab}always_ff @(posedge {clk}, negedge {reset}) begin\n"
        text += f"{tab}{t}if (!{reset}) begin {name}_idles_sim_only <= 'd0; end\n"
        if use_signal_directly:
            text += f"{tab}{t}else if (~{intf}) begin {name}_idles_sim_only <= {name}_idles_sim_only + 'd1; end\n"
        else:
            text += f"{tab}{t}else if (~{valid}) begin {name}_idles_sim_only <= {name}_idles_sim_only + 'd1; end\n"
        text += f"{tab}end\n"

        text += f"{tab}always_ff @(posedge {clk}, negedge {reset}) begin\n"
        text += f"{tab}{t}if (&cycle_counter_sim_only[{log2(print_period)-1}:0] & ($test$plusargs(\"{module_name}_perf_prints\"))) begin $display(\"{intf} FB_PERF_REPORT: %08d | m: %m | time: %0t | transactions: %d | stalls: %d | idle: %d\", cycle_counter_sim_only, $time, {name}_transactions_sim_only, {name}_stalls_sim_only, {name}_idles_sim_only); end\n"
        text += f"{tab}end\n"

    text += "`ifndef EMU_PERF_CNTRS_ON\n"
    text += "// synopsys translate_on\n"
    text += "`endif // EMU_PERF_CNTRS_ON\n"
    text += "`endif // FB_PERF_PRINT_ON\n"

    text += f"{tab}`endif // {sim_only_macro}\n"
    return(text)


def generate_interfaces(
    interfaces,
    generate_declarations=False,
    tab="auto",
    final_comma="",
    only=None,
    ios=None,
    all_interfaces=None,
    print_clocks=True,
):
    if only is None:
        only = []
    if all_interfaces is None:
        all_interfaces = {}
    else:
        for io in interfaces:
            for interface in interfaces[io]:
                interface_type = interfaces[io][interface]['type']
                flat = True if "flat" in interfaces[io][interface] else False
                if type(interface_type) == str:
                    if interface_type in all_interfaces:
                        interfaces[io][interface]['type'] = all_interfaces[interface_type]
                        interfaces[io][interface]['flat'] = flat
                    else:
                        import sys
                        sys.exit("Interface definition for {} (type: {}) could not be found".format(interface, interface_type))
    clocks_resets = OrderedDict()
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent

    if ios is None:
        lines_append(tab + "// Inputs.\n")
    if "inputs" in interfaces:
        for i in sorted(interfaces["inputs"], key=lambda key: key):
            if i in only or len(only) == 0:
                io = "input" if not generate_declarations else ""
                flat = interfaces["inputs"][i]["flat"] if "flat" in interfaces["inputs"][i] else False
                generate_interface(i, interfaces["inputs"][i], io, tab=tab, ios=ios, flat=flat)
                interface_type = interfaces["inputs"][i]["type"]
                clocks_resets[interface_type["meta"]["clk"]] = 1
                clocks_resets[interface_type["meta"]["reset"]] = 1
                newln(1 if ios is None else 0)

    if ios is None:
        lines_append(tab + "// Outputs.\n")
    if "outputs" in interfaces:
        for i in sorted(interfaces["outputs"], key=lambda key: key):
            if i in only or len(only) == 0:
                io = "output" if not generate_declarations else ""
                flat = interfaces["outputs"][i]["flat"] if "flat" in interfaces["outputs"][i] else False
                generate_interface(i, interfaces["outputs"][i], io, tab=tab, ios=ios, flat=flat)
                interface_type = interfaces["outputs"][i]["type"]
                clocks_resets[interface_type["meta"]["clk"]] = 1
                clocks_resets[interface_type["meta"]["reset"]] = 1
                newln(1 if ios is None else 0)

    if (not generate_declarations) and print_clocks:
        if ios is None:
            lines_append(tab + "// Clocks, resets.\n")
        if ios is None:
            lines_append(
                tab
                + "input {}{}".format(
                    ", ".join(i for i in sorted(clocks_resets)), final_comma
                )
            )
        else:
            for i in sorted(clocks_resets):
                declare_io("input {}".format(i))
    newln(1 if ios is None else 0)


def generate_interface_senders_receivers(interfaces, tab="auto"):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent

    RE_FIFO = re.compile(r"^fifo(\d+)$")

    for i in interfaces["inputs"]:
        interface_type = interfaces["inputs"][i]["type"]
        array = "" if "array" not in interfaces["inputs"][i] else "[{}]".format(interfaces["inputs"][i]['array'])
        array_bits = "" if "array" not in interfaces["inputs"][i] else "[{}:0] ".format(interfaces["inputs"][i]['array']-1)
        gen_loop = 0 if "array" not in interfaces["inputs"][i] else interfaces["inputs"][i]['array']

        if "receiver" in interfaces["inputs"][i]:
            receiver = interfaces["inputs"][i]["receiver"]
            clk = interface_type["meta"]["clk"]
            reset = interface_type["meta"]["reset"]
            if receiver is None:
                receiver = ""
            reg_fifo = re.match(RE_FIFO, receiver)
            pkg = interface_type["package"]
            struct = interface_type["name"] + "_t"
            if "valid" in interface_type["meta"]["flow_control"]:
                declare_wire("logic {array_bits}{i}_internal_valid".format(array_bits=array_bits, i=i))
            if "ready" in interface_type["meta"]["flow_control"]:
                declare_wire("logic {array_bits}{i}_internal_ready".format(array_bits=array_bits, i=i))
            declare_wire("{pkg}::{struct} {i}_internal{a}".format(pkg=pkg, struct=struct, i=i, a=array))
            if gen_loop > 0:
                gen_var = "i_{}".format(i)
                gen_ind = "[i_{}]".format(i)
                text = tab + "genvar {};\n".format(gen_var)
                text = text + tab + "for ({gen_var}=0; {gen_var}<{gen_loop}; {gen_var}={gen_var}+1) begin : {i}_loop\n".format(gen_var=gen_var, gen_loop=gen_loop, i=i)
                tab_ = tab + t
            else:
                text = ""
                tab_ = tab
                gen_ind = ""
            if reg_fifo:
                depth = reg_fifo.group(1)
                width = "$bits({pkg}::{struct})".format(pkg=pkg, struct=struct)
                text = text + (
                    tab_
                    + "fb_fifo_dvr #(.DEPTH({depth}), .WIDTH({width}), .FLOP_BASED(1)) {i}_fifo (\n".format(
                        i=i, depth=depth, width=width
                    )
                )
                text = text + tab_ + t + ".out({}_internal{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".out_valid({}_internal_valid{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".out_ready({}_internal_ready{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in({}{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in_valid({}_valid{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in_ready({}_ready{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".clk({clk}),\n".format(clk=clk)
                text = text + tab_ + t + ".{reset}({reset}),\n".format(reset=reset)
                text = text + tab_ + t + ".scan(1'b0)\n"
                text = text + tab_ + ");\n"
            else:
                if "valid" in interface_type["meta"]["flow_control"]:
                    text = text + tab_ + "assign {i}_internal_valid{ii} = {i}_valid{ii};\n".format(i=i, ii=gen_ind)
                if "ready" in interface_type["meta"]["flow_control"]:
                    text = text + tab_ + "assign {i}_ready{ii} = {i}_internal_ready{ii};\n".format(i=i, ii=gen_ind)
                text = text + tab_ + "assign {i}_internal{ii} = {i}{ii};\n".format(i=i, ii=gen_ind)
            if gen_loop > 0:
                text = text + tab + "end\n"
            lines_append(text)

    for i in interfaces["outputs"]:
        interface_type = interfaces["outputs"][i]["type"]
        array = "" if "array" not in interfaces["outputs"][i] else "[{}]".format(interfaces["outputs"][i]['array'])
        array_bits = "" if "array" not in interfaces["outputs"][i] else "[{}:0] ".format(interfaces["outputs"][i]['array']-1)
        gen_loop = 0 if "array" not in interfaces["outputs"][i] else interfaces["outputs"][i]['array']

        if "sender" in interfaces["outputs"][i]:
            sender = interfaces["outputs"][i]["sender"]
            clk = interface_type["meta"]["clk"]
            reset = interface_type["meta"]["reset"]
            if sender is None:
                sender = ""
            reg_fifo = re.match(RE_FIFO, sender)
            pkg = interface_type["package"]
            struct = interface_type["name"] + "_t"
            declare_wire("{pkg}::{struct} {i}_internal{a}".format(pkg=pkg, struct=struct, i=i, a=array))
            if "valid" in interface_type["meta"]["flow_control"]:
                declare_wire("logic {array_bits}{i}_internal_valid".format(array_bits=array_bits, i=i))
            if "ready" in interface_type["meta"]["flow_control"]:
                declare_wire("logic {array_bits}{i}_internal_ready".format(array_bits=array_bits, i=i))
            if gen_loop > 0:
                gen_var = "i_{}".format(i)
                gen_ind = "[i_{}]".format(i)
                text = tab + "genvar {};\n".format(gen_var)
                text = text + tab + "for ({gen_var}=0; {gen_var}<{gen_loop}; {gen_var}={gen_var}+1) begin : {i}_loop\n".format(gen_var=gen_var, gen_loop=gen_loop, i=i)
                tab_ = tab + t
            else:
                text = ""
                tab_ = tab
                gen_ind = ""
            if reg_fifo:
                depth = reg_fifo.group(1)
                width = "$bits({pkg}::{struct})".format(pkg=pkg, struct=struct)
                text = text + (
                    tab
                    + "fb_fifo_dvr #(.DEPTH({depth}), .WIDTH({width}), .FLOP_BASED(1)) {i}_fifo (\n".format(
                        i=i, depth=depth, width=width
                    )
                )
                text = text + tab_ + t + ".out({}{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".out_valid({}_valid{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".out_ready({}_ready{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in({}_internal{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in_valid({}_internal_valid{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".in_ready({}_internal_ready{}),\n".format(i, gen_ind)
                text = text + tab_ + t + ".clk({clk}),\n".format(clk=clk)
                text = text + tab_ + t + ".{reset}({reset}),\n".format(reset=reset)
                text = text + tab_ + t + ".scan(1'b0)\n"
                text = text + tab_ + ");\n"
            else:
                if "valid" in interface_type["meta"]["flow_control"]:
                    text = text + tab_ + "assign {i}_valid{ii} = {i}_internal_valid{ii};\n".format(i=i, ii=gen_ind)
                if "ready" in interface_type["meta"]["flow_control"]:
                    text = text + tab_ + "assign {i}_internal_ready{ii} = {i}_ready{ii};\n".format(i=i, ii=gen_ind)

                text = text + tab_ + "assign {i}{ii} = {i}_internal{ii};\n".format(i=i, ii=gen_ind)

            if gen_loop > 0:
                text = text + tab + "end\n"
            lines_append(text)


def newln(count=1):
    for _ in range(count):
        if print_to_stdio:
            print("\n")
        else:
            lines_append("\n")


def enum_2_class_name(enum_name):
    class_name = re.sub(r"_e$", "", enum_name)
    class_name = string.capwords(class_name, "_")
    class_name = class_name.replace("_", "")

    return class_name


def insert_enum(enum, enums):
    enum = convert_to_hash(enum)
    if 'width' not in enum:
        enum['width'] = log2(len(enum['values']))
    elif enum['width'] == -1:
        enum['width'] = log2(len(enum['values']))
    if enum['width'] == 0:
        enum['width'] = 1
    if type(enum["values"]) == dict or type(enum["values"]) == OrderedDict:
        pass
    else:
        new_values = OrderedDict()
        i = 0
        for value in enum['values']:
            new_values[value] = i
            i += 1
        enum['values'] = new_values
    enums[enum['name']] = enum
    return(enums)

def register_reset_value(registers, i):
    reset_value = 0
    for field in registers["registers"][i]["fields"]:
        if "reset" in registers["registers"][i]["fields"][field]:
            reset = registers["registers"][i]["fields"][field]['reset']
        if "value" in registers["registers"][i]["fields"][field]:
            reset = registers['registers'][i]['fields'][field]['value']
        if type(reset) == int:
            if reset != 0:
                lsb = registers['registers'][i]['fields'][field]["lsb"]
                reset_value = reset_value | (reset << lsb)
    return reset_value

def generate_registers_map_amodel(registers, pre=''):
    current_revision = subprocess.check_output(["hg", "whereami"]).decode("utf-8").rstrip()
    #for CP's registers
    register_lines = """// rev: {}
#define {}REGS_MAP \\\n""".format(current_revision, pre.upper())
    registers_registers = registers["registers"]

    for i in registers_registers:
        reg_name = registers["registers"][i]["name"]
        reg_addr = i * registers["address_in_n_bytes"]
        reg_array = registers["registers"][i]["array"]
        reg_access = registers["registers"][i]["type"]
        reg_mask = registers["registers"][i]["field_mask"]
        reg_reset = register_reset_value(registers, i)
        if "text" in registers["registers"][i]:
            reg_text = '"{text}"'.format(
                text=registers["registers"][i]["text"]
                .replace("\n", " ").replace('"', '\\"').strip()
            )
        else:
            reg_text = '" "'
        register_lines = (
            register_lines
            + """    {}REG_MAP({}, {}, {}, {}, {}, {}, \\\n        {}) \\\n"""
            .format(pre.upper(), hex(reg_addr), reg_name, reg_array, reg_access,
            hex(reg_mask), hex(reg_reset), reg_text)
        )
    register_lines = register_lines + "\n"
    lines_append(register_lines)


def gen_amodel_c_headers_base(registers, reg_name, reg_addr):
    register_lines = """\n#define {reg_name}_BASE    {reg_addr}\n""".format(
        reg_name=reg_name.upper(),
        reg_addr=hex(reg_addr),
    )
    return register_lines


def gen_amodel_c_headers_offset(registers, reg_name, index, reg_bytes):
    offset = index * reg_bytes
    register_lines = """#define {reg_name}{index}    {offset}\n""".format(
        reg_name=reg_name.upper(),
        index=index,
        offset=offset,
    )
    return register_lines


def gen_amodel_c_headers_field(registers, reg_name, i, enums=None):
    register_lines = ""
    if enums is None:
        enums = {}
    for field in registers["registers"][i]["fields"]:
        field_width = "Not Defined"
        if "width" in registers["registers"][i]["fields"][field]:
            field_width = registers["registers"][i]["fields"][field]["width"]
        elif "enum" in registers["registers"][i]["fields"][field]:
            if registers["registers"][i]["fields"][field]["enum"] in enums:
                field_width = enums[registers["registers"][i]["fields"][field]["enum"]][
                    "width"
                ]
        register_lines = (register_lines
        + """#define FROM_{reg_name}_{field}(d) FROM_REG(d, {lsb}, {width})\n#define TO_{reg_name}_{field}(d) TO_REG(d, {lsb}, {width})\n""".format(
            reg_name=reg_name.upper(),
            field=field.upper(),
            lsb=registers["registers"][i]["fields"][field]["lsb"],
            width=field_width,
        ))
    return register_lines


def generate_registers_amodel_c_headers(registers, enums):
    register_lines = (
        """//Auto generated.
        //Use buck build //infra_asic_fpga/ip/fb_inference_gen2/main/design/... --no-cache --deep"""
    )
    lines_append("")
    registers_registers = registers["registers"]

    for i in registers_registers:
        reg_name = registers["registers"][i]["name"]
        reg_addr = i * registers["address_in_n_bytes"]
        reg_array = registers["registers"][i]["array"]
        reg_bytes = registers["alignment"]
        register_lines = register_lines + gen_amodel_c_headers_base(
            registers,
            reg_name,
            reg_addr
        )
        if reg_array > 1:
            for k in range(reg_array):
                register_lines = register_lines + gen_amodel_c_headers_offset(
                    registers,
                    reg_name,
                    k,
                    reg_bytes
                )
        register_lines = register_lines + gen_amodel_c_headers_field(
            registers, reg_name, i, enums)
    lines_append(register_lines)
    lines_append("\n")


def generate_commands_trace_amodel_c_headers(commands, enums=None):
    """
    This function dumps the c header files for ISA trace dump.
    """
    command_lines = (
        "\n"
        "// Auto generated.\n"
        "// Use buck build //infra_asic_fpga/ip/fb_inference_gen2/main/design/...\n"
        "\n"
    )

    for cmd in commands:
        command_lines = command_lines + "void "
        cmd_name = cmd.upper()
        #command_lines += cmd_name + "_dump(FILE* file, const CoreID* cid,\n"
        command_lines += cmd_name + "_dump("

        # Signature of the function
        for field in commands[cmd]["fields"]:
            if field == "opcode" or field == "rest":
                continue
            if "addr" in field:
                command_lines = command_lines + "FbaAddr " + field + ",\n"
            else:
                command_lines = command_lines + "Uns32 " + field + ",\n"
        command_lines = command_lines.strip(",\n") + ") {\n"

        command_lines += """CoreID cid;
        getPEid(&cid);
        if (!is_master_pe(cid.pe_id))
            return;\n """
        # format of printf
        command_lines += """fprintf(DUMP_FILE, "r:%d,c:%d,v:%d,dt:1,op:{},""".format(cmd)
        for field in commands[cmd]["fields"]:
            if field == "opcode" or field == "rest":
                continue
            if "addr" in field:
                command_lines = command_lines + field + ":%lx,"
            else:
                command_lines = command_lines + field + ":%x,"
        command_lines = command_lines.strip(",\n") + "\\n" + """ ",\n"""

        # arguments to printf
        command_lines += "cid.pe_id[0],cid.pe_id[1],cid.is_vec,\n"
        for field in commands[cmd]["fields"]:
            if field == "opcode" or field == "rest":
                continue
            command_lines = command_lines + field + ",\n"
        command_lines = command_lines.strip(",\n") + ");\n}\n\n"
    lines_append(command_lines)


def generate_commands_amodel_c_headers(commands, enums=None):
    """
    This function dumps the c header files for ISA. For now all the fields are
    defined as Uns32.
    """
    command_lines = (
        "\n"
        "// Auto generated.\n"
        "// Use buck build //infra_asic_fpga/ip/fb_inference_gen2/main/design/... --no-cache --deep\n"
        "\n"
    )

    for cmd in commands:
        command_lines = command_lines + "void "
        cmd_name = cmd.upper()
        #command_lines += cmd_name + "(FILE* file, const CoreID* cid,\n"
        command_lines += cmd_name + "(\n"

        for field in commands[cmd]["fields"]:
            if field == "opcode" or field == "rest":
                continue
            if "addr" in field:
                command_lines = command_lines + "FbaAddr " + field + ", "
            else:
                command_lines = command_lines + "Uns32 " + field + ", "
        command_lines = command_lines.strip(", ") + ");\n\n"
    lines_append(command_lines)


def generate_enums_amodel_c_headers(enums: Dict[str, Dict[str, Dict[str, int]]]) -> None:
    """
    This function dumps a c header file for enums.
    """
    command_lines = (
        "\n"
        "// This file is auto generated.\n"
        "// Use buck build //infra_asic_fpga/ip/fb_inference_gen2/main/design/... --no-cache --deep\n"
        "\n"
    )

    for enum_name, enum_dict in enums.items():
        command_lines += "enum " + enum_name + " {\n"

        for type, value in enum_dict["values"].items():
            # NOTE: Since enums are global until c++11, the type names need to be
            #       prefixed to be type safe. This also provides more context when
            #       "." or "::" access is not supported.
            type_name = enum_name + "_" + type.upper()
            command_lines = command_lines + "  " + type_name + " = " + str(value) + ",\n"

        command_lines += "};\n\n"

    lines_append(command_lines)


def arbiter(valid, data, ready, stype, output, width, tab="auto", declare_outputs=True, declare_output_ready=False, only_one_hot=True, type_cast="", arbiter_type="round_robin", clk_sig="clk"):
    """This function takes arrays for the input valid, ready, and data
    signal names and does round robin arbitration among them to generate
    the output. <output> is the name of the selected data. Output valid and
    ready signals are assumed to be <output>_valid and <output>_ready. <stype>
    shows how the output data will be declared. It can be a struct or it can
    be "logic [w-1:0]"."""

    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent

    assert len(valid) == len(ready), "Wrong array length."
    assert len(valid) == len(data), "Wrong array length."
    w = len(valid)
    bits = log2(w)
    name = output

    valid.reverse()
    ready.reverse()

    if declare_outputs:
        declare_wire("{} {}".format(stype, output))
        declare_wire("logic {}_valid".format(output))
    if declare_output_ready:
        declare_wire("logic {}_ready".format(output))

    lines_append(tab + "wire [{w}:0] {n}_valid_vector = {{".format(w=w - 1, n=name) + ",".join(valid) + "};\n")
    lines_append(tab + "logic [{w}:0] {n}_ready_vector;\n".format(w=w - 1, n=name))
    lines_append(tab + "assign {" + ",".join(ready) + "}} = {n}_ready_vector;\n".format(n=name))

    if len(valid) == 1:
        lines_append(f"{tab}wire {name}_winner = 'd0;\n")
        lines_append(f"{tab}wire [0:0] {name}_winner_one_hot = 1'b1;\n")
        lines_append(
            tab + "wire [{w}:0] {n}_transaction_vector = {n}_valid_vector & {n}_ready_vector; // spyglass disable W528\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_valid = |{n}_valid_vector;\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_ready_vector = {{{w}{{{n}_ready}}}} & {w}'(1'b1 << {n}_winner);\n".format(n=name, w=w)
        )

    elif arbiter_type == "flopped_winner":
        if not only_one_hot:
            lines_append(f"{tab}logic [{bits-1}:0] {name}_winner, {name}_next_winner;\n")

        lines_append(
            tab + "logic [{w}:0] {n}_winner_one_hot, {n}_next_winner_one_hot;\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_valid = |({n}_valid_vector & {n}_winner_one_hot);\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_ready_vector = {{{w}{{{n}_ready}}}} & {n}_winner_one_hot;\n".format(n=name, w=w)
        )

        if not only_one_hot:
            reg("dren", bits, "{n}_next_winner {n}_winner |{n}_valid_vector".format(n=name), tab=tab, clk_sig=clk_sig)
        reg("dren", "{},'d1".format(w), "{n}_next_winner_one_hot {n}_winner_one_hot |{n}_valid_vector".format(n=name), tab=tab, clk_sig=clk_sig)

        # Generate the logic to find the current winner.
        text = ""
        tt = tab + t
        for i in range(w):
            dum0 = "else if"
            if i == 0:
                dum0 = "unique if"
            elif i == (w-1):
                dum0 = "else"
            if dum0 == "else":
                text += tt + "{dum0} begin\n".format(n=name, i=i, dum0=dum0)
            else:
                text += tt + "{dum0} ({n}_winner_one_hot[{i}]) begin\n".format(n=name, i=i, dum0=dum0)
            for ii in range(w):
                dum1 = "else if"
                if ii == 0:
                    dum1 = "if"
                j = (ii + i + 1) % w
                if not only_one_hot:
                    text += tt + t + "{dum1} ({n}_valid_vector[{j}]) begin {n}_next_winner = 'd{j}; {n}_next_winner_one_hot = 'd{one_hot}; end\n".format(n=name, j=j, dum1=dum1, one_hot=(1 << j))
                else:
                    text += tt + t + "{dum1} ({n}_valid_vector[{j}]) begin {n}_next_winner_one_hot = 'd{one_hot}; end\n".format(n=name, j=j, dum1=dum1, one_hot=(1 << j))
            text += tt + "end\n"

        next_winner_text = tab + "    {n}_next_winner = {n}_winner;\n".format(n=name) if not only_one_hot else ""
        lines_append(
            tab + "always_comb begin\n"
            + next_winner_text
            + tab + "    {n}_next_winner_one_hot = {n}_winner_one_hot;\n".format(n=name)
            + text
            + tab + "end\n"
        )

    else:
        if not only_one_hot:
            lines_append(f"{tab}logic [{bits-1}:0] {name}_winner, {name}_last_winner;\n")
        else:
            lines_append(f"{tab}logic [{bits-1}:0] {name}_winner;\n")

        lines_append(
            tab + "wire [{w}:0] {n}_transaction_vector = {n}_valid_vector & {n}_ready_vector;\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_valid = |{n}_valid_vector;\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "logic [{w}:0] {n}_winner_one_hot, {n}_last_winner_one_hot;\n".format(b=bits - 1, n=name, w=w - 1)
            + tab + "assign {n}_ready_vector = {{{w}{{{n}_ready}}}} & {w}'(1'b1 << {n}_winner);\n".format(n=name, w=w)
        )

        if not only_one_hot:
            reg("dren", bits, "{n}_winner {n}_last_winner |{n}_transaction_vector".format(n=name), tab=tab, clk_sig=clk_sig)
        reg("dren", "{},'d1".format(w), "{n}_winner_one_hot {n}_last_winner_one_hot |{n}_transaction_vector".format(n=name), tab=tab, clk_sig=clk_sig)

        # Generate the logic to find the current winner.
        text = ""
        tt = tab + t
        for i in range(w):
            dum0 = "else if"
            if i == 0:
                dum0 = "unique if"
            elif i == (w-1):
                dum0 = "else"
            if dum0 == "else":
                text += tt + "{dum0} begin\n".format(n=name, i=i, dum0=dum0)
            else:
                text += tt + "{dum0} ({n}_last_winner_one_hot[{i}]) begin\n".format(n=name, i=i, dum0=dum0)
            for ii in range(w):
                dum1 = "else if"
                if ii == 0:
                    dum1 = "if"
                j = (ii + i + 1) % w
                text += tt + t + "{dum1} ({n}_valid_vector[{j}]) begin {n}_winner = 'd{j}; {n}_winner_one_hot[{j}] = 'b1; end\n".format(n=name, j=j, dum1=dum1)
            text += tt + "end\n"

        lines_append(
            tab + "always_comb begin\n"
            + tab + "    {n}_winner = 'd0;\n".format(n=name)
            + tab + "    {n}_winner_one_hot = 'd0;\n".format(n=name)
            + text
            + tab + "end\n"
        )
    one_hot(output, w, "{n}_winner_one_hot".format(n=name), data, width=width, type_cast=type_cast)


def instantiate_fifo(inp, out, depth, fifo_type="fb_fifo_dvr", tab="auto", declare_outputs=True, struct=None, width=None, clk=None, reset=None, scan="1'b0", output_flopped=0, count="", params=None, in_ready_dangle=False):
    if tab == "auto":
        if print_to_stdio:
            tab = ""
        else:
            tab = auto_indent
    params_text = ""
    if params is None:
        params = {}
    else:
        for p in params:
            params_text += f", .{p}({params[p]})"
    if clk is None:
        clk = globals()['clk']
    if reset is None:
        reset = globals()['reset']
    assert (struct is not None) or (width is not None), "Wrong function call: instantiate_fifo!"
    assert (fifo_type == "fb_fifo_dvr"), "That FIFO type instantiation is not supported yet!"
    if declare_outputs:
        declare_wire("logic {}_valid".format(out))
        declare_wire("logic {}_ready".format(inp))
    if struct is not None:
        width = "$bits({})".format(struct)
        if declare_outputs:
            declare_wire("{} {}".format(struct, out))
    else:
        if declare_outputs:
            declare_wire("logic [{}-1:0] {}".format(width, out))
    text = ""
    if depth > 0:
        text += tab + f"fb_fifo_dvr #(.DEPTH({depth}), .WIDTH({width}), .FLOP_BASED(1), .OUTPUT_FLOPPED({output_flopped}){params_text}) {out}_fifo (\n"
        text += tab + t + ".out({}),\n".format(out)
        text += tab + t + ".count({}),\n".format(count)
        text += tab + t + ".out_valid({}_valid),\n".format(out)
        text += tab + t + ".out_ready({}_ready),\n".format(out)
        text += tab + t + ".in({}),\n".format(inp)
        text += tab + t + ".in_valid({}_valid),\n".format(inp)
        if in_ready_dangle:
            text += tab + t + ".in_ready(), // spyglass disable W287b\n"
        else:
            text += tab + t + ".in_ready({}_ready),\n".format(inp)
        text += tab + t + ".clk({clk}),\n".format(clk=clk)
        text += tab + t + ".{reset}({reset}),\n".format(reset=reset)
        text += tab + t + ".scan({})\n".format(scan)
        text += tab + ");\n"
    else:
        text += tab + "assign {} = {};\n".format(out, inp)
        text += tab + "assign {}_valid = {}_valid;\n".format(out, inp)
        text += tab + "assign {}_ready = {}_ready;\n".format(inp, out)
    return text


def beautify_io(io_list):
    direction, typedef, width, name = [], [], [], []
    new_io_list = []
    for io in io_list:
        d = t = w = n = ""
        content = io.split()
        if len(content) == 2:
            d, n = content
        elif len(content) == 3:
            d, t, n = content
        elif len(content) == 4:
            d, t, w, n = content
        direction.append(d)
        typedef.append(t)
        width.append(w)
        name.append(n)

    idx_list = sorted(range(len(name)), key=lambda x : name[x])

    max_direction = max(direction, key=len)
    max_typedef = max(typedef, key=len)
    max_width = max(width, key=len)

    for i in idx_list:
        io = direction[i] + " " * (len(max_direction) - len(direction[i]))\
            + " " + typedef[i] + " " * (len(max_typedef) - len(typedef[i]))\
            + " " + width[i] + " " * (len(max_width) - len(width[i]))\
            + " " + name[i]

        new_io_list.append(io)

    return new_io_list


if __name__ == "__main__":
    print('''
!!!!!!!!!! STOP !!!!!!!!!!!!
You are using verilog_generator.py as script which is outdated and unsupported.
Please contact the share_asic_cad oncall team for more information.
    ''')
    sys.exit(1)
