////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&Module( parameter NUM_BITS = 1, STAGE = 2, EDGE  = 1);
module fb_bit_sync # (
  parameter NUM_BITS = 1,
            STAGE = 2,
            EDGE = 1
) (
  output  logic     [NUM_BITS-1:0]  sync_out,
  input   logic                     clk,
  input   logic                     reset_n,
  input   logic     [NUM_BITS-1:0]  sync_in
); 

    //input                 clk,
    //input                 reset_n,
    //input  [NUM_BITS-1:0] sync_in,
    //output [NUM_BITS-1:0] sync_out

    //&Logics;
    logic     [STAGE-1:0][NUM_BITS-1:0]  sync_pipe;


    //&Force logic [STAGE-1:0][NUM_BITS-1:0] sync_pipe;

    generate
        if(EDGE == 0) begin// negedge synchronizer
            always_ff @(negedge clk or negedge reset_n) begin : neg_sync
                if(~reset_n) begin
                    sync_pipe <= 0;
                end
                else begin
                    sync_pipe <= {sync_pipe[0], sync_in[NUM_BITS-1:0]};
                end
            end
        end else if(EDGE == 1) begin// posedge synchronizer
            always_ff @(posedge clk or negedge reset_n) begin : pos_sync
                if(~reset_n) begin
                    sync_pipe <= 0;
                end
                else begin
                    sync_pipe <= {sync_pipe[0], sync_in};
                end
            end
        end
    endgenerate

    assign sync_out[NUM_BITS-1:0] = sync_pipe[STAGE-1];

endmodule // fb_bit_sync
