////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&Module;
module fsm (
  input  logic        clk,
  input  logic        arst_n,
  input  logic        clken,
  input  logic        start,
  input  logic        mode_l0,
  input  logic        mode_l1
); 


//&Logics;
logic     [1:0]  st;
logic     [1:0]  st_nxt;



// &FSM;
// FSM_REG
//     <- clken
//     st <ST_IDLE=st_nxt;
//
// FSM_INIT
//     st_nxt = st;
//
// FSM_DEFAULT
//     st_nxt = st;
//
// FSM_STATES
//     ST_IDLE:
//       ST_L0 <- start & mode_l0; # commeo
//       ST_L1 <- start & mode_l1; # comme2
//
//     ST_L0:
//       ST_L1 <- !mode_l1;
//       ST_DONE <- 1;
//
//     ST_L1:
//       ST_DONE <- 1;
//
//     ST_DONE:
//       ST_IDLE <- 1;
//&EndFSM;

   localparam ST_IDLE = 2'd0;
   localparam ST_L0 = 2'd1;
   localparam ST_L1 = 2'd2;
   localparam ST_DONE = 2'd3;

   always @(posedge clk or negedge arst_n ) begin
      if (! arst_n ) begin
         st <= ST_IDLE;
      end else if ( clken ) begin
         st[1:0] <= st_nxt[1:0];
      end
   end

   always @(*) begin
      st_nxt = st;

      case (st)
         ST_IDLE : begin
            if (start & mode_l0 )begin
               st_nxt = ST_L0;
            end else if (start & mode_l1) begin
               st_nxt = ST_L1;
            end
         end

         ST_L0 : begin
            if (!mode_l1 )begin
               st_nxt = ST_L1;
            end else begin
               st_nxt = ST_DONE;
            end
         end

         ST_L1 : begin
            end else begin
               st_nxt = ST_DONE;
            end
         end

         ST_DONE : begin
            end else begin
               st_nxt = ST_IDLE;
            end
         end

      endcase
   end




endmodule
