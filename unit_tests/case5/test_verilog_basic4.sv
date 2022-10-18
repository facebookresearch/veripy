// cannot generate reg type

module test_verilog_basic3 (
  //&ports;
  output  logic        cc,
  output  logic        dd,
  output  logic        ee,
  output  logic        ff,
  output  logic        add,
  output  logic        sub,
  output  logic        mul,
  output  logic        mul_signed,
  output  logic        hh,
  input  [127:0]       a,
  input  [127:0]       b,
  input  [127:0]       c,
  input  [127:0]       d,
  input  [127:0]       e,
  input  signed  [127:0] f,
  input  signed  [127:0] g,
  input  signed  [127:0] h,
  /*
  output [127:0]       aa,
  output [127:0]       bb,

  output reg              cc,
  output reg              dd,
  output reg              ee,
  output reg              ff,
  output reg[129:0]       add,
  output reg[129:0]       sub,
  output reg[128*3-1:0]   mul,
  output reg signed [128*3-1:0]       mul_signed,
  output reg              hh
  */
);

//&regs;
//&wires;

/*expect this format from veripy ????
reg  cc;
reg  dd;
reg  ee;
reg  ff;

reg [129:0] add;
reg [129:0] sub;
reg [128*3-1:0] mul;
reg signed [128*3-1:0] mul_signed;
reg hh;
*/


wire [127:0] aa = b&c&d&e;
wire [127:0] bb = b^c^d^e;


always@(*) begin

     cc=|(b&c&d&e);
     dd=^(b&c&d&e);
     ee=&(b|c| d|e);

     ff=~^(b|c| d|e);
     add=a+b + c;
     sub=a - b - c;
     mul=a*b * c;
     mul_signed=f*g*h;
     hh=a==b;
end
endmodule

