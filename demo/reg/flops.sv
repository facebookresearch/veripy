////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&Module;
module flops (
  output  logic     [3:0]  local_lb_buf,
  output  logic            local_lb_raddrRR,
  output  logic     [8:0]  pre_gntR,
  input   logic            clk,
  input   logic            local_lb_we,
  input   logic     [3:0]  local_lb_wdata,
  input   logic            rst_n,
  input   logic            local_lb_rd,
  input   logic            local_lb_raddrR,
  input   logic            pre_gnt_we,
  input   logic     [8:0]  pre_gnt_nt
); 


//&Logics;


//&FB_ENFLOP (clk, local_lb_we, local_lb_wdata[3:0], local_lb_buf[3:0])
always_ff @(posedge clk) begin
    if (local_lb_we) begin local_lb_buf[3:0] <= local_lb_wdata[3:0]; end
end


//&FB_ENFLOP_RST (clk, rst_n, local_lb_rd, local_lb_raddrR, local_lb_raddrRR)
always_ff @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin local_lb_raddrRR <= '0; end
    else if (local_lb_rd) begin local_lb_raddrRR <= local_lb_raddrR; end
end


//&FB_ENFLOP_RS(clk, rst_n, 2'b00, pre_gnt_we, pre_gnt_nt[8:0], pre_gntR[8:0])
always_ff @(posedge clk or negedge rst_n) begin
    if (~rst_n) begin pre_gntR[8:0] <= 2'b00; end
    else if (pre_gnt_we) begin pre_gntR[8:0] <= pre_gnt_nt[8:0]; end
end


endmodule
