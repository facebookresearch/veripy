////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&ModuleDef;
module xdfil # (
  parameter RAM_DEPTH = 128,
            RAM_WIDTH = 32
) (
  output  logic                 sch2xdfil_stall,
  output  logic                 re2xdfil_stall,
  output  logic                 s0_xdfil2dma_req_valid,
  output  logic                 s1_xdfil2dma_req_valid,
  output  logic     [42:0]      s0_xdfil2dma_req_data,
  output  logic     [42:0]      s1_xdfil2dma_req_data,
  output  logic                 xdfil2dma_wr_valid,
  output  logic     [127:0]     xdfil2dma_wr_data,
  output  logic                 xdfil2scl_valid,
  output  logic     [127:0]     xdfil2scl_data,
  output  logic                 xdfil_intr,
  output  logic                 xdfilram_ren,
  output  logic     [7:0]       xdfilram_raddr,
  output  logic                 xdfilram_wen,
  output  logic     [7:0]       xdfilram_waddr,
  output  logic     [127:0]     xdfilram_wdata,
  input   logic                 xdfil_clk,
  input   logic                 xdfil_rst_n,
  input   logic     [1:0][2:0]  xdfil_in[0-9],
  input   logic                 sch2xdfil_valid,
  input   logic     [31:0]      sch2xdfil_data,
  input   logic                 re2xdfil_valid,
  input   logic     [63:0]      re2xdfil_data,
  input   logic                 s0_xdfil2dma_req_stall,
  input   logic                 s1_xdfil2dma_req_stall,
  input   logic                 xdfil2dma_wr_stall,
  input   logic                 xdfil2scl_stall,
  input   logic     [127:0]     xdfilram_rdata
); 


//&Logics;


//&GenDrive0;
`ifdef XDFIL_DRIVE_0
  assign  sch2xdfil_stall = {$bits(sch2xdfil_stall){1'b0}};
  assign  re2xdfil_stall = {$bits(re2xdfil_stall){1'b0}};
  assign  s0_xdfil2dma_req_valid = {$bits(s0_xdfil2dma_req_valid){1'b0}};
  assign  s1_xdfil2dma_req_valid = {$bits(s1_xdfil2dma_req_valid){1'b0}};
  assign  s0_xdfil2dma_req_data = {$bits(s0_xdfil2dma_req_data){1'b0}};
  assign  s1_xdfil2dma_req_data = {$bits(s1_xdfil2dma_req_data){1'b0}};
  assign  xdfil2dma_wr_valid = {$bits(xdfil2dma_wr_valid){1'b0}};
  assign  xdfil2dma_wr_data = {$bits(xdfil2dma_wr_data){1'b0}};
  assign  xdfil2scl_valid = {$bits(xdfil2scl_valid){1'b0}};
  assign  xdfil2scl_data = {$bits(xdfil2scl_data){1'b0}};
  assign  xdfil_intr = {$bits(xdfil_intr){1'b0}};
  assign  xdfilram_ren = {$bits(xdfilram_ren){1'b0}};
  assign  xdfilram_raddr = {$bits(xdfilram_raddr){1'b0}};
  assign  xdfilram_wen = {$bits(xdfilram_wen){1'b0}};
  assign  xdfilram_waddr = {$bits(xdfilram_waddr){1'b0}};
  assign  xdfilram_wdata = {$bits(xdfilram_wdata){1'b0}};
`else



`endif



endmodule
