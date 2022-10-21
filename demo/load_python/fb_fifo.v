////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

module fb_fifo
    #( parameter
    DEPTH = 8,
    WIDTH = 32,
    )(
    output logic [WIDTH-1:0] out,
    output logic full,
    output logic empty,
    input push,
    input pop,
    input [WIDTH-1:0] in,

    input clk,
    input rst_n
    );


assign out = 'd0;
assign full = 1'b0;
assign empty = 1'b0;

endmodule
