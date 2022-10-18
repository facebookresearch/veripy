module test_verilog_basic0 (
  input          d,
  input          e,
  output         a
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


