module test_verilog_basic3 (
  //&ports;
  output  logic        a,
  input wire [3:0]         d,
  input wire [3:0]         e,
  // output wire [3:0]        a
);
//&regs;
//&wires;


`ifdef behavioral
     assign a = b & c;
`else
     assign a= d & e;
`endif
endmodule


