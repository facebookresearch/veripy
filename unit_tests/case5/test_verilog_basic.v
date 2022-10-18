//&module;
module test_verilog_basic (
  input          d,
  input          e
); 
// and_op (a, b, c);
// output a;
// input b, c;
//&regs;
//&wires;


`ifdef behavioral
     wire a = b & c;
`else
     wire a= d & e;
`endif
endmodule


