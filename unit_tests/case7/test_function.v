module fibonacci0 ( clk, resetn, start, n, data );

input           clk;
input           resetn;
input           start;
input  [3:0]    n;
output [31:0]   data;

//&Wires;
//&Regs;
reg        data_temp;

/*
wire            clk;
wire            resetn;
wire            start;
wire   [3:0]    n;
reg    [31:0]   data;
wire    [31:0]   data_temp;
*/

always@(*)
begin
  data_temp = fibonacci(0,1,5);
end

always@(posedge clk) begin
if (!resetn)
  data <= 32'b0;
else if (start) begin
  data <= data_temp;
  end
end


function automatic [31:0] fibonacci ( input [31:0] a, input [31:0] b, input [3:0]  n);

reg [31:0]  c, d;
reg [31:0] data_temp0;

for (int i=0; i <= 31; i++) begin
  if ( i == 0 )
      begin
            fibonacci = a + b;
            c          = b;
      end
  else if (i <= n)
      begin
            d          =  fibonacci;
            fibonacci =  c + fibonacci;
            c          =  d;
      end
end

endfunction


endmodule

/*
module gray2bin1 (bin, gray);
parameter SIZE = 8; // this module is parameterizable output [SIZE-1:0] bin;
input [SIZE-1:0] gray;
genvar i;
generate for (i=0; i<SIZE; i=i+1) begin:bit assign bin[i] = ^gray[SIZE-1:i];
end endgenerate endmodule

module gray2bin2 (bin, gray);
parameter SIZE = 8; // this module is parameterizable output [SIZE-1:0] bin;
input [SIZE-1:0] gray;
reg [SIZE-1:0] bin;
genvar i;
generate for (i=0; i<SIZE; i=i+1) begin:bit
always @(gray[SIZE-1:i]) // fixed part select
bin[i] = ^gray[SIZE-1:i];
end endgenerate endmodule
*/
