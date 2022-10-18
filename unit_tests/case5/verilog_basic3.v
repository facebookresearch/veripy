module test_verilog_basic3 (
  input wire [3:0]         d,
  input wire [3:0]         e,
  output wire [3:0]        a
); 
// and_op (a, b, c);
// output a;
// input b, c;
//&regs;
//&wires;


`ifdef behavioral
     assign a = b & c;
`else
     assign a= d & e;
`endif
endmodule


