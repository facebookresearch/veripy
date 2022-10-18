//&module;
module test_verilog_basic1 (
  input          b,
  input          c,
  output         a
); 
// and_op (a, b, c);
// output a;
// input b, c;
//&regs;
//&wires;

wire a = b & c;
endmodule


