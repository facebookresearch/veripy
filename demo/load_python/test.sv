////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&Module;
module test (
  output  logic     [3:0]   fil2dma_out,
  output  logic             fil2dma_full,
  output  logic             fil2dma_empty,
  output  logic     [15:0]  out,
  input   logic             fil2dma_push,
  input   logic             fil2dma_pop,
  input   logic     [3:0]   fil2dma_in,
  input   logic             fil_clk,
  input   logic             fill_rstn,
  input   logic     [15:0]  in_a,
  input   logic     [15:0]  in_b
); 

//&Logics;

//&Python self.inst_syncfifo("fil2dma", "fil_clk", "fill_rstn", "32", "4");
//&BeginInstance fb_fifo u_fil2dma_fb_fifo;
//&Param DEPTH 32;
//&Param WIDTH 4;
//&Connect /^/ /fil2dma_/;
//&Connect clk fil_clk;
//&Connect rst_n fill_rstn;
//&EndInstance;
//FILE: fb_fifo.v
fb_fifo # (
    .DEPTH  (32),
    .WIDTH  (4)
) u_fil2dma_fb_fifo (
    .out    (fil2dma_out[3:0]),
    .full   (fil2dma_full),
    .empty  (fil2dma_empty),
    .push   (fil2dma_push),
    .pop    (fil2dma_pop),
    .in     (fil2dma_in[3:0]),
    .clk    (fil_clk),
    .rst_n  (fill_rstn)
);

//&pythonBegin;
// for a in range (0, self.num_inputs):
//   print_line = """
//   assign out[{0}] = in_a[{0}] & in_b[{0}];
//   """
//   print(print_line.format(a))
//&pythonEnd;

  assign out[0] = in_a[0] & in_b[0];

  assign out[1] = in_a[1] & in_b[1];

  assign out[2] = in_a[2] & in_b[2];

  assign out[3] = in_a[3] & in_b[3];

  assign out[4] = in_a[4] & in_b[4];

  assign out[5] = in_a[5] & in_b[5];

  assign out[6] = in_a[6] & in_b[6];

  assign out[7] = in_a[7] & in_b[7];

  assign out[8] = in_a[8] & in_b[8];

  assign out[9] = in_a[9] & in_b[9];

  assign out[10] = in_a[10] & in_b[10];

  assign out[11] = in_a[11] & in_b[11];

  assign out[12] = in_a[12] & in_b[12];

  assign out[13] = in_a[13] & in_b[13];

  assign out[14] = in_a[14] & in_b[14];

  assign out[15] = in_a[15] & in_b[15];



endmodule
