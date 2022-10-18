//&module;
module test_verilog_basic0 (
  input          d,
  input          e
); 
//&regs;
//&wires;


`ifdef behavioral
     wire a = b & c;
`else
     wire a= d & e;
`endif




endmodule
