//&module;
module test_inout (
  input          out_en,
  input          clk,
  input          resetn,
  input          a,
  input          b
); 

// test_inout ( input clk ,resetn, inout [7:0] c, input  out_en , input [3:0] a, input [1:0] b);
 //&wires;
 wire        c;
 //&regs;

reg [7:0] c_reg;
reg [7:0] sum;
reg [7:0] count;



assign c = out_en ? 8'hz : sum;

always@(posedge clk or negedge resetn)
begin
    if (!resetn)
       c_reg <= 'b0;
    else if (count == 50)
       c_reg <= c;
end

always@(posedge clk or negedge resetn)
begin
    if (!resetn) begin count <= 'b0; sum   <= 'b0; end
    else         begin count <= count <= 100 ? count + 1 : 0 ; sum <= a + b; end
end





endmodule
