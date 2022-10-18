module test(
          //&Ports;
          output  logic        mux_out,
          input   logic        select,
          input logic [16-1:0] [127:0]  mux_in;

         );

/*
module mux_16(
/* //
    input  logic [0:15] [127:0] mux_in,
//    input  logic [3:0] select,
    output logic [127:0] mux_out
*/ //
);
*/

//  logic [127:0] mux_out_temp;
//&Logics;
logic        mux_out_temp;
logic [0:15] [127:0] temp;


    // The for-loop creates 16 assign statements
    genvar i;
    generate
        for (i=0; i < 16; i++) begin
            assign temp[i] = (select == i) ? mux_in[i] : 0;
        end
    endgenerate

    always@*
       begin
        mux_out_temp = 128'b0;
        for (int j=0; j < 16; j++) begin
            mux_out_temp = mux_out_temp | temp[j];
        mux_out = mux_out_temp;
       end
      end

endmodule





