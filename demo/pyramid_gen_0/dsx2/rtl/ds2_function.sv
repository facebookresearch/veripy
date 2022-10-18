////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

// #include pyramid_gen_include.h

//&Module( parameter BPP = 8, DS_Y = 1, COFF_W = 3, MW = 3, O_DW = 12);
module ds2_function # (
  parameter BPP = 8,
            DS_Y = 1,
            COFF_W = 3,
            MW = 3,
            O_DW = 12
) (
  input   logic                   clk,
  input   logic     [MW-1:0]      mode,
  input   logic     [3*BPP-1:0]   pixel,
  output  logic     [O_DW+1:0]    sum_out,
  input   logic     [COFF_W-1:0]  weight
); 

// #include ds2_function_include.vh

  //-------------LocalParam Declaration-----------//
   localparam [7:0]  EXT   = O_DW - BPP                        ;
   localparam [31:0] AW    = BPP+2                             ;
   localparam [31:0] BW    = COFF_W+1                          ;
   localparam [31:0] MDW   = (AW >= BW) ?  AW+1        : BW+1  ; //Multiplicand(MD) data width(W)
   localparam [31:0] MRW   = (AW >= BW) ? (BW[0]? BW+2 : BW+3) :
                                          (AW[0]? AW+2 : AW+3) ; //Multiplier(MR) data width(W)
   localparam [31:0] NPP   = MRW/2                             ; //Number(N) of partial(P) Products(P)  - (NPP)
   localparam [31:0] PPW   = AW+BW                             ; //Partial(P) Products(p) data width(W) - (PPW)
   localparam [31:0] BPW   = MDW +1                            ; //Booth(B)Product(P) width(W) - (BPW)
   localparam [31:0] PP_3  = FSIZE + 1                         ;
   localparam [31:0] N_4_2_CSA    = PP_3 - 2                   ;
   localparam [31:0] N_4_2_CSA_O  = (3*PP_3)-5                 ;
   localparam [31:0] CSA_4_2_TW   = N_4_2_CSA_O * AW           ;
   localparam [31:0] CSA_3X3_TW   = N_4_2_CSA_O * PPW          ;


   //&Force wire [AW-1:0]               csa_4_2 [0:N_4_2_CSA_O]         ;
   //&Force wire [PPW-1:0]              csa_4x2 [0:N_4_2_CSA_O]         ;
   //&Force wire [BPP-1:0]              pix_w [0:FSIZE-1]               ;


   //&Wires;
   logic     [AW-1:0]   csa_4_2[0:N_4_2_CSA_O];
   logic     [PPW-1:0]  csa_4x2[0:N_4_2_CSA_O];
   logic     [BPP-1:0]  pix_w[0:FSIZE-1];


   //&Regs;
   logic     [2:0]                  pix_w;
   logic     [O_DW-1:0]             sum_2x2_intr;
   logic     [O_DW-1:0]             sum_2x2;
   logic     [(PP_3*AW)-1:0]        pix_3;
   logic     [7:0]                  csa_4_2;
   logic     [AW-1:0]               sum_3x3_intr;
   logic     [BW-1:0]               dsx2_weight;
   logic     [AW-1:0]               dsx2_3pixel;
   logic     [(NPP*(PPW))-1:0]      dsx2_pp;
   logic     [BPP-1:0]              pix_cen_r;
   logic     [((NPP+1)*(PPW))-1:0]  csa_3x3;
   logic     [7:0]                  csa_4x2;
   logic     [PPW-1:0]              sum_3x3;
   logic                            mode_compare;



  //Bifuricate the Pixel information 0 previous, 1-current, 2 - next
  //&Force width pixel 3*BPP;
//&pythonBegin;
// for a in range (0, (self.get_hash_defval("FSIZE")-1)):
//   print_line = """
//   assign pix_w[{0}] = pixel[((({0}+1)*BPP) -1) -: BPP];
//   """
//   print(print_line.format(0))
//&pythonEnd;

  assign pix_w[0] = pixel[(((0+1)*BPP) -1) -: BPP];

  assign pix_w[0] = pixel[(((0+1)*BPP) -1) -: BPP];



  //HorSum[x>>1][y] = PixelIn[x-1,y] + PixelIn[x,y] //12 bits unsigned
  always @ ( posedge clk)
    begin: S0_2X2
      sum_2x2_intr[O_DW-1:0] <= {{EXT{1'b0}},pix_w[0]} + {{EXT{1'b0}},pix_w[1]} ; //Unsigned- 0 padding
    end
  always @ ( posedge clk)
    begin: S1_2X2
      sum_2x2[O_DW-1:0]    <= sum_2x2_intr  ;
    end
  // Compute PixelIn[x-1,y] + PixelIn[x+1,y] - (PixelIn[x,y]<<1)
  assign pix_3[(PP_3*AW)-1:0]    = {2'b0,pix_w[0],2'b0,pix_w[2],~{1'b0,pix_w[1],1'b0},{{AW-1{1'b0}},1'b1}}; //-1,0,+1 - 4 terms

//&pythonBegin;
// for p in range (0, (self.get_hash_defval("PP_3")-1)):
//   print_line = """
//   assign csa_4_2[{0}] = pix_3[((({0}+1)*AW) -1) -: AW] ;
//   """
//   print(print_line.format(p))
//&pythonEnd;

  assign csa_4_2[0] = pix_3[(((0+1)*AW) -1) -: AW] ;

  assign csa_4_2[1] = pix_3[(((1+1)*AW) -1) -: AW] ;

  assign csa_4_2[2] = pix_3[(((2+1)*AW) -1) -: AW] ;



//&pythonBegin;
// for i in range (0, ((self.get_hash_defval("N_4_2_CSA")-1)*3), 3):
//   print_line = """
//   &BeginInstance generic_csa u_generic_4_2_csa_0_{0};
//   &Param DW AW;
//   &Connect in1 csa_4_2[({0})];
//   &Connect in2 csa_4_2[({0}+1)];
//   &Connect in3 csa_4_2[({0}+2)];
//   &Connect out1 csa_4_2[({0}/3)+({0}/3)+PP_3];
//   &Connect out2 csa_4_2[({0}/3)+({0}/3)+PP_3+1];
//   &EndInstance;
//   """
//   print(print_line.format(i))
//&pythonEnd;

  //&BeginInstance generic_csa u_generic_4_2_csa_0_0;
  //&Param DW AW;
  //&Connect in1 csa_4_2[(0)];
  //&Connect in2 csa_4_2[(0+1)];
  //&Connect in3 csa_4_2[(0+2)];
  //&Connect out1 csa_4_2[(0/3)+(0/3)+PP_3];
  //&Connect out2 csa_4_2[(0/3)+(0/3)+PP_3+1];
  //&EndInstance;
  //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/common/generic_csa/rtl/generic_csa.sv
  generic_csa # (
      .DW  (AW)
  ) u_generic_4_2_csa_0_0 (
      .in1   (csa_4_2[(0)]),
      .in2   (csa_4_2[(0+1)]),
      .in3   (csa_4_2[(0+2)]),
      .out1  (csa_4_2[(0/3)+(0/3)+PP_3]),
      .out2  (csa_4_2[(0/3)+(0/3)+PP_3+1])
  );



  always @ ( posedge clk)
    begin:S0_3X3
      sum_3x3_intr[AW-1:0] <= csa_4_2[N_4_2_CSA_O] + csa_4_2[N_4_2_CSA_O-1]  ; //10bits signed
    end

  //Comet_DSX2_UID_Weight * ( PixelIn[x-1,y] + PixelIn[x+1,y] - (PixelIn[x,y]<<1) )
  assign dsx2_weight[BW-1:0] = {1'b0,weight[COFF_W-1:0]}        ;//4bits
  assign dsx2_3pixel[AW-1:0] = sum_3x3_intr         ;

  //&BeginInstance booth_mult_pp u_booth_mult_pp;
  //&Param AW AW;
  //&Param BW BW;
  //&Param A_SIGNED BPP_S;
  //&Param B_SIGNED COF_S;
  //&Connect a dsx2_3pixel;
  //&Connect b dsx2_weight;
  //&Connect pp dsx2_pp[(NPP*(PPW))-1:0];
  //&EndInstance;
  //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/common/booth_mult_pp/rtl/booth_mult_pp.sv
  booth_mult_pp # (
      .AW        (AW),
      .BW        (BW),
      .A_SIGNED  (BPP_S),
      .B_SIGNED  (COF_S)
  ) u_booth_mult_pp (
      .a   (dsx2_3pixel),
      .b   (dsx2_weight),
      .pp  (dsx2_pp[(NPP*(PPW))-1:0])
  );

  always @ ( posedge clk) //pipeline register
    begin
      pix_cen_r[BPP-1:0] <= pix_w[1] ;
    end

  assign csa_3x3[((NPP+1)*(PPW))-1:0] = {dsx2_pp,2'd0,pix_cen_r,4'd0} ;

//&pythonBegin;
// for s in range (0, (self.get_hash_defval("PP_3")-1)):
//   print_line = """
//   assign csa_4x2[{0}] = csa_3x3[((({0}+1)*PPW) -1) -: PPW] ;
//   """
//   print(print_line.format(s))
//&pythonEnd;

  assign csa_4x2[0] = csa_3x3[(((0+1)*PPW) -1) -: PPW] ;

  assign csa_4x2[1] = csa_3x3[(((1+1)*PPW) -1) -: PPW] ;

  assign csa_4x2[2] = csa_3x3[(((2+1)*PPW) -1) -: PPW] ;



// PixelIn[x,y]<<4 +
// Comet_DSX2_UID_Weight * ( PixelIn[x-1,y] + PixelIn[x+1,y] - (PixelIn[x,y]<<1))

//&pythonBegin;
// for j in range (0, ((self.get_hash_defval("N_4_2_CSA")-1)*3), 3):
//   print_line = """
//   &BeginInstance generic_csa u_generic_4_2_csa_1_{0};
//   &Param DW PPW;
//   &Connect in1 csa_4x2[({0})];
//   &Connect in2 csa_4x2[({0}+1)];
//   &Connect in3 csa_4x2[({0}+2)];
//   &Connect out1 csa_4x2[({0}/3)+({0}/3)+PP_3];
//   &Connect out2 csa_4x2[({0}/3)+({0}/3)+PP_3+1];
//   &EndInstance;
//   """
//   print(print_line.format(j))
//&pythonEnd;

  //&BeginInstance generic_csa u_generic_4_2_csa_1_0;
  //&Param DW PPW;
  //&Connect in1 csa_4x2[(0)];
  //&Connect in2 csa_4x2[(0+1)];
  //&Connect in3 csa_4x2[(0+2)];
  //&Connect out1 csa_4x2[(0/3)+(0/3)+PP_3];
  //&Connect out2 csa_4x2[(0/3)+(0/3)+PP_3+1];
  //&EndInstance;
  //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/common/generic_csa/rtl/generic_csa.sv
  generic_csa # (
      .DW  (PPW)
  ) u_generic_4_2_csa_1_0 (
      .in1   (csa_4x2[(0)]),
      .in2   (csa_4x2[(0+1)]),
      .in3   (csa_4x2[(0+2)]),
      .out1  (csa_4x2[(0/3)+(0/3)+PP_3]),
      .out2  (csa_4x2[(0/3)+(0/3)+PP_3+1])
  );



  always @ ( posedge clk)
    begin:S1_3X3
      sum_3x3[PPW-1:0] <= csa_4x2[N_4_2_CSA_O] + csa_4x2[N_4_2_CSA_O-1] ; //14bits signed
    end

  always @ (posedge clk)
    begin
      mode_compare <= ~(|mode[MW-1:0]) ;//mode==0
    end

// #ifdef (DS_Y==1)
  assign  sum_out[O_DW+1:0] = mode_compare ? {4'd0,sum_2x2[O_DW-1:2]} : sum_3x3 ;
// #else
//   assign  sum_out[O_DW+1:0] = mode_compare ? {2'd0,sum_2x2}           : sum_3x3 ;
// #endif



endmodule //ds2_function
