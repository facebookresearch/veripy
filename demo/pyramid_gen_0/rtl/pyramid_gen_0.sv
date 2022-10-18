
////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// Author            : Saminathan Chockalingam                                //
// Author E-mail     : saminathan@fb.com                                      //
// File Name         : pyramid_gen.v                                          //
// Module Name       : pyramid_gen                                            //
// Function          : Top level Pyramid function                             //
// Associated modules:                                                        //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
//Information                                                                 //
//===========                                                                 //
//  (1) This Block will generate the downscaled versions of the images input  //
//      into "N" stream interfaces.                                           //
//  (2) Down scaling by 2, 4, 8, 16 and so on                                 //
////////////////////////////////////////////////////////////////////////////////

// #include pyramid_gen_include.h

//&Module(parameter NUMLAYERS = 4, CAMSIZEX = 1280, MW = 3, WW = 3, BPP = 8);
module pyramid_gen_0 # (
  parameter NUMLAYERS = 4,
            CAMSIZEX = 1280,
            MW = 3,
            WW = 3,
            BPP = 8
) (
  input   logic                            clk,
  input   logic                            i_frame_valid,
  input   logic                            i_line_valid,
  input   logic     [BPP-1:0]              i_pixel,
  input   logic                            i_pixel_valid,
  input   logic     [(NUMLAYERS*MW)-1:0]   mode,
  output  logic     [NUMLAYERS-1:0]        o_frame_valid,
  output  logic     [NUMLAYERS-1:0]        o_line_valid,
  output  logic     [(NUMLAYERS*BPP)-1:0]  o_pixel,
  output  logic     [NUMLAYERS-1:0]        o_pixel_valid,
  input   logic     [NUMLAYERS-1:0]        pyr_out_en,
  input   logic                            rst_n,
  input   logic     [(NUMLAYERS*MW)-1:0]   weight
); 

// #include pyramid_gen_include.vh

   //&Force width /o_.*_valid/ NUMLAYERS;
   //&Force width pyr_out_en NUMLAYERS;
   //&Force width o_pixel (NUMLAYERS*BPP);
   //&Force width mode (NUMLAYERS*MW);
   //&Force width weight (NUMLAYERS*MW);


   //&Regs;
   logic     [NUMLAYERS-1:0]            downscle_en;
   logic     [NUMLAYERS-1:0]            pyr_clk;
   logic     [NUMLAYERS-1:0]            pyr_rst_n;
   logic     [NUMLAYERS+1-1:0]          line_valid;
   logic     [NUMLAYERS+1-1:0]          frame_valid;
   logic     [NUMLAYERS+1-1:0]          pixel_valid;
   logic     [((NUMLAYERS+1)*BPP)-1:0]  pixel;


   //&Wires;


   //&Force width line_valid NUMLAYERS+1;
   //&Force width frame_valid NUMLAYERS+1;
   //&Force width pixel_valid NUMLAYERS+1;
   //&Force width pixel ((NUMLAYERS+1)*BPP);
   //&Force width pyr_clk NUMLAYERS;
   //&Force width pyr_rst_n NUMLAYERS;
   //&Force width downscle_en NUMLAYERS;


  //clock gate enable generation logic
//&PythonBegin;
// for a in range (0, self.get_hash_defval("NUMLAYERS")):
//     print_line = """
//        assign downscle_en[{0}] = |(pyr_out_en[NUMLAYERS-1:{0}]);
//     """
//     print(print_line.format(a))
//&PythonEnd;

       assign downscle_en[0] = |(pyr_out_en[NUMLAYERS-1:0]);

       assign downscle_en[1] = |(pyr_out_en[NUMLAYERS-1:1]);

       assign downscle_en[2] = |(pyr_out_en[NUMLAYERS-1:2]);

       assign downscle_en[3] = |(pyr_out_en[NUMLAYERS-1:3]);



//&PythonBegin;
// for b in range (0, self.get_hash_defval("NUMLAYERS")):
//    print_line = """
//    &BeginInstance clk_gate u_pyr_cg_{0};
//    &Connect clk_in clk;
//    &Connect clk_disable 1'b0;
//    &Connect clk_en downscle_en[{0}];
//    &Connect scan_en 1'b0;
//    &Connect clk_out pyr_clk[{0}];
//    &EndInstance;
//    """
//    print(print_line.format(b))
//&PythonEnd;

   //&BeginInstance clk_gate u_pyr_cg_0;
   //&Connect clk_in clk;
   //&Connect clk_disable 1'b0;
   //&Connect clk_en downscle_en[0];
   //&Connect scan_en 1'b0;
   //&Connect clk_out pyr_clk[0];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/clk_gate.sv
   clk_gate u_pyr_cg_0 (
       .clk_in       (clk),
       .clk_disable  (1'b0),
       .scan_en      (1'b0),
       .clk_en       (downscle_en[0]),
       .clk_out      (pyr_clk[0])
   );

   //&BeginInstance clk_gate u_pyr_cg_1;
   //&Connect clk_in clk;
   //&Connect clk_disable 1'b0;
   //&Connect clk_en downscle_en[1];
   //&Connect scan_en 1'b0;
   //&Connect clk_out pyr_clk[1];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/clk_gate.sv
   clk_gate u_pyr_cg_1 (
       .clk_in       (clk),
       .clk_disable  (1'b0),
       .scan_en      (1'b0),
       .clk_en       (downscle_en[1]),
       .clk_out      (pyr_clk[1])
   );

   //&BeginInstance clk_gate u_pyr_cg_2;
   //&Connect clk_in clk;
   //&Connect clk_disable 1'b0;
   //&Connect clk_en downscle_en[2];
   //&Connect scan_en 1'b0;
   //&Connect clk_out pyr_clk[2];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/clk_gate.sv
   clk_gate u_pyr_cg_2 (
       .clk_in       (clk),
       .clk_disable  (1'b0),
       .scan_en      (1'b0),
       .clk_en       (downscle_en[2]),
       .clk_out      (pyr_clk[2])
   );

   //&BeginInstance clk_gate u_pyr_cg_3;
   //&Connect clk_in clk;
   //&Connect clk_disable 1'b0;
   //&Connect clk_en downscle_en[3];
   //&Connect scan_en 1'b0;
   //&Connect clk_out pyr_clk[3];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/clk_gate.sv
   clk_gate u_pyr_cg_3 (
       .clk_in       (clk),
       .clk_disable  (1'b0),
       .scan_en      (1'b0),
       .clk_en       (downscle_en[3]),
       .clk_out      (pyr_clk[3])
   );



//&PythonBegin;
// for c in range (0, self.get_hash_defval("NUMLAYERS")):
//    print_line = """
//    &BeginInstance reset_sync u_pyr_reset_sync_{0};
//    &Param SYNC_STAGE SYNC_STAGE;
//    &Connect clk pyr_clk[{0}];
//    &Connect i_rst_n rst_n;        ),
//    &Connect o_rst_n pyr_rst_n[{0}]; )
//    &EndInstance;
//    """
//    print(print_line.format(c))
//&PythonEnd;

   //&BeginInstance reset_sync u_pyr_reset_sync_0;
   //&Param SYNC_STAGE SYNC_STAGE;
   //&Connect clk pyr_clk[0];
   //&Connect i_rst_n rst_n;        ),
   //&Connect o_rst_n pyr_rst_n[0]; )
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/reset_sync.sv
   reset_sync # (
       .SYNC_STAGE  (SYNC_STAGE)
   ) u_pyr_reset_sync_0 (
       .clk      (pyr_clk[0]),
       .i_rst_n  (rst_n),
       .o_rst_n  (pyr_rst_n[0])
   );

   //&BeginInstance reset_sync u_pyr_reset_sync_1;
   //&Param SYNC_STAGE SYNC_STAGE;
   //&Connect clk pyr_clk[1];
   //&Connect i_rst_n rst_n;        ),
   //&Connect o_rst_n pyr_rst_n[1]; )
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/reset_sync.sv
   reset_sync # (
       .SYNC_STAGE  (SYNC_STAGE)
   ) u_pyr_reset_sync_1 (
       .clk      (pyr_clk[1]),
       .i_rst_n  (rst_n),
       .o_rst_n  (pyr_rst_n[1])
   );

   //&BeginInstance reset_sync u_pyr_reset_sync_2;
   //&Param SYNC_STAGE SYNC_STAGE;
   //&Connect clk pyr_clk[2];
   //&Connect i_rst_n rst_n;        ),
   //&Connect o_rst_n pyr_rst_n[2]; )
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/reset_sync.sv
   reset_sync # (
       .SYNC_STAGE  (SYNC_STAGE)
   ) u_pyr_reset_sync_2 (
       .clk      (pyr_clk[2]),
       .i_rst_n  (rst_n),
       .o_rst_n  (pyr_rst_n[2])
   );

   //&BeginInstance reset_sync u_pyr_reset_sync_3;
   //&Param SYNC_STAGE SYNC_STAGE;
   //&Connect clk pyr_clk[3];
   //&Connect i_rst_n rst_n;        ),
   //&Connect o_rst_n pyr_rst_n[3]; )
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/reset_sync.sv
   reset_sync # (
       .SYNC_STAGE  (SYNC_STAGE)
   ) u_pyr_reset_sync_3 (
       .clk      (pyr_clk[3]),
       .i_rst_n  (rst_n),
       .o_rst_n  (pyr_rst_n[3])
   );



   assign line_valid[0]      = i_line_valid  ;
   assign frame_valid[0]     = i_frame_valid ;
   assign pixel_valid[0]     = i_pixel_valid ;
   assign pixel[BPP-1:0]     = i_pixel[BPP-1:0]       ;


//&PythonBegin;
// for j in range (0, self.get_hash_defval("NUMLAYERS")):
//    print_line = """
//    assign o_line_valid [{0}]             = pyr_out_en[{0}] ? line_valid[{0}+1]             : 1'b0        ;
//    assign o_frame_valid[{0}]             = pyr_out_en[{0}] ? frame_valid[{0}+1]            : 1'b0        ;
//    assign o_pixel_valid[{0}]             = pyr_out_en[{0}] ? pixel_valid[{0}+1]            : 1'b0        ;
//    assign o_pixel[(({0}+1)*BPP)-1-:BPP]  = pyr_out_en[{0}] ? pixel[(({0}+2)*BPP)-1-:BPP]  : {{BPP{{1'b0}}}} ;
//    """
//    print(print_line.format(j))
//&PythonEnd;

   assign o_line_valid [0]             = pyr_out_en[0] ? line_valid[0+1]             : 1'b0        ;
   assign o_frame_valid[0]             = pyr_out_en[0] ? frame_valid[0+1]            : 1'b0        ;
   assign o_pixel_valid[0]             = pyr_out_en[0] ? pixel_valid[0+1]            : 1'b0        ;
   assign o_pixel[((0+1)*BPP)-1-:BPP]  = pyr_out_en[0] ? pixel[((0+2)*BPP)-1-:BPP]  : {BPP{1'b0}} ;

   assign o_line_valid [1]             = pyr_out_en[1] ? line_valid[1+1]             : 1'b0        ;
   assign o_frame_valid[1]             = pyr_out_en[1] ? frame_valid[1+1]            : 1'b0        ;
   assign o_pixel_valid[1]             = pyr_out_en[1] ? pixel_valid[1+1]            : 1'b0        ;
   assign o_pixel[((1+1)*BPP)-1-:BPP]  = pyr_out_en[1] ? pixel[((1+2)*BPP)-1-:BPP]  : {BPP{1'b0}} ;

   assign o_line_valid [2]             = pyr_out_en[2] ? line_valid[2+1]             : 1'b0        ;
   assign o_frame_valid[2]             = pyr_out_en[2] ? frame_valid[2+1]            : 1'b0        ;
   assign o_pixel_valid[2]             = pyr_out_en[2] ? pixel_valid[2+1]            : 1'b0        ;
   assign o_pixel[((2+1)*BPP)-1-:BPP]  = pyr_out_en[2] ? pixel[((2+2)*BPP)-1-:BPP]  : {BPP{1'b0}} ;

   assign o_line_valid [3]             = pyr_out_en[3] ? line_valid[3+1]             : 1'b0        ;
   assign o_frame_valid[3]             = pyr_out_en[3] ? frame_valid[3+1]            : 1'b0        ;
   assign o_pixel_valid[3]             = pyr_out_en[3] ? pixel_valid[3+1]            : 1'b0        ;
   assign o_pixel[((3+1)*BPP)-1-:BPP]  = pyr_out_en[3] ? pixel[((3+2)*BPP)-1-:BPP]  : {BPP{1'b0}} ;



//&PythonBegin;
// for i in range (0, self.get_hash_defval("NUMLAYERS")):
//    print_line = """
//    &BeginInstance down_scale u_downscale_{0};
//    &Param NUMLAYERS NUMLAYERS;
//    &Param CAMSIZEX CAMSIZEX>>{0};
//    &Param DS_R1W1 DSS_R1W1;
//    &Param DS_BE DSS_BE;
//    &Param MW MW;
//    &Param WW WW;
//    &Param BPP BPP;
//    &BuildCommand --hash_define_vars ENABLE;
//    &Connect clk pyr_clk[{0}];
//    &Connect rst_n pyr_rst_n[{0}];
//    &Connect mode mode[(({0}+1)*MW)-1-:MW];
//    &Connect weight weight[(({0}+1)*WW)-1-:WW];
//    &Connect i_line_valid line_valid[{0}];
//    &Connect i_frame_valid frame_valid[{0}];
//    &Connect i_pixel pixel[(({0}+1)*BPP)-1-:BPP];
//    &Connect i_pixel_valid pixel_valid[{0}];
//    &Connect o_line_valid line_valid[{0}+1];
//    &Connect o_frame_valid frame_valid[{0}+1];
//    &Connect o_pixel pixel[(({0}+2)*BPP)-1-:BPP];
//    &Connect o_pixel_valid pixel_valid[{0}+1];
//    &EndInstance;
//    """
//    print(print_line.format(i))
//&PythonEnd;

   //&BeginInstance down_scale u_downscale_0;
   //&Param NUMLAYERS NUMLAYERS;
   //&Param CAMSIZEX CAMSIZEX>>0;
   //&Param DS_R1W1 DSS_R1W1;
   //&Param DS_BE DSS_BE;
   //&Param MW MW;
   //&Param WW WW;
   //&Param BPP BPP;
   //&BuildCommand --hash_define_vars ENABLE;
   //&Connect clk pyr_clk[0];
   //&Connect rst_n pyr_rst_n[0];
   //&Connect mode mode[((0+1)*MW)-1-:MW];
   //&Connect weight weight[((0+1)*WW)-1-:WW];
   //&Connect i_line_valid line_valid[0];
   //&Connect i_frame_valid frame_valid[0];
   //&Connect i_pixel pixel[((0+1)*BPP)-1-:BPP];
   //&Connect i_pixel_valid pixel_valid[0];
   //&Connect o_line_valid line_valid[0+1];
   //&Connect o_frame_valid frame_valid[0+1];
   //&Connect o_pixel pixel[((0+2)*BPP)-1-:BPP];
   //&Connect o_pixel_valid pixel_valid[0+1];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/down_scale.sv
   down_scale # (
       .NUMLAYERS  (NUMLAYERS),
       .CAMSIZEX   (CAMSIZEX>>0),
       .DS_R1W1    (DSS_R1W1),
       .DS_BE      (DSS_BE),
       .MW         (MW),
       .WW         (WW),
       .BPP        (BPP)
   ) u_downscale_0 (
       .clk            (pyr_clk[0]),
       .i_frame_valid  (frame_valid[0]),
       .i_line_valid   (line_valid[0]),
       .i_pixel        (pixel[((0+1)*BPP)-1-:BPP]),
       .i_pixel_valid  (pixel_valid[0]),
       .mode           (mode[((0+1)*MW)-1-:MW]),
       .o_frame_valid  (frame_valid[0+1]),
       .o_line_valid   (line_valid[0+1]),
       .o_pixel        (pixel[((0+2)*BPP)-1-:BPP]),
       .o_pixel_valid  (pixel_valid[0+1]),
       .rst_n          (pyr_rst_n[0]),
       .weight         (weight[((0+1)*WW)-1-:WW])
   );

   //&BeginInstance down_scale u_downscale_1;
   //&Param NUMLAYERS NUMLAYERS;
   //&Param CAMSIZEX CAMSIZEX>>1;
   //&Param DS_R1W1 DSS_R1W1;
   //&Param DS_BE DSS_BE;
   //&Param MW MW;
   //&Param WW WW;
   //&Param BPP BPP;
   //&BuildCommand --hash_define_vars ENABLE;
   //&Connect clk pyr_clk[1];
   //&Connect rst_n pyr_rst_n[1];
   //&Connect mode mode[((1+1)*MW)-1-:MW];
   //&Connect weight weight[((1+1)*WW)-1-:WW];
   //&Connect i_line_valid line_valid[1];
   //&Connect i_frame_valid frame_valid[1];
   //&Connect i_pixel pixel[((1+1)*BPP)-1-:BPP];
   //&Connect i_pixel_valid pixel_valid[1];
   //&Connect o_line_valid line_valid[1+1];
   //&Connect o_frame_valid frame_valid[1+1];
   //&Connect o_pixel pixel[((1+2)*BPP)-1-:BPP];
   //&Connect o_pixel_valid pixel_valid[1+1];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/down_scale.sv
   down_scale # (
       .NUMLAYERS  (NUMLAYERS),
       .CAMSIZEX   (CAMSIZEX>>1),
       .DS_R1W1    (DSS_R1W1),
       .DS_BE      (DSS_BE),
       .MW         (MW),
       .WW         (WW),
       .BPP        (BPP)
   ) u_downscale_1 (
       .clk            (pyr_clk[1]),
       .i_frame_valid  (frame_valid[1]),
       .i_line_valid   (line_valid[1]),
       .i_pixel        (pixel[((1+1)*BPP)-1-:BPP]),
       .i_pixel_valid  (pixel_valid[1]),
       .mode           (mode[((1+1)*MW)-1-:MW]),
       .o_frame_valid  (frame_valid[1+1]),
       .o_line_valid   (line_valid[1+1]),
       .o_pixel        (pixel[((1+2)*BPP)-1-:BPP]),
       .o_pixel_valid  (pixel_valid[1+1]),
       .rst_n          (pyr_rst_n[1]),
       .weight         (weight[((1+1)*WW)-1-:WW])
   );

   //&BeginInstance down_scale u_downscale_2;
   //&Param NUMLAYERS NUMLAYERS;
   //&Param CAMSIZEX CAMSIZEX>>2;
   //&Param DS_R1W1 DSS_R1W1;
   //&Param DS_BE DSS_BE;
   //&Param MW MW;
   //&Param WW WW;
   //&Param BPP BPP;
   //&BuildCommand --hash_define_vars ENABLE;
   //&Connect clk pyr_clk[2];
   //&Connect rst_n pyr_rst_n[2];
   //&Connect mode mode[((2+1)*MW)-1-:MW];
   //&Connect weight weight[((2+1)*WW)-1-:WW];
   //&Connect i_line_valid line_valid[2];
   //&Connect i_frame_valid frame_valid[2];
   //&Connect i_pixel pixel[((2+1)*BPP)-1-:BPP];
   //&Connect i_pixel_valid pixel_valid[2];
   //&Connect o_line_valid line_valid[2+1];
   //&Connect o_frame_valid frame_valid[2+1];
   //&Connect o_pixel pixel[((2+2)*BPP)-1-:BPP];
   //&Connect o_pixel_valid pixel_valid[2+1];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/down_scale.sv
   down_scale # (
       .NUMLAYERS  (NUMLAYERS),
       .CAMSIZEX   (CAMSIZEX>>2),
       .DS_R1W1    (DSS_R1W1),
       .DS_BE      (DSS_BE),
       .MW         (MW),
       .WW         (WW),
       .BPP        (BPP)
   ) u_downscale_2 (
       .clk            (pyr_clk[2]),
       .i_frame_valid  (frame_valid[2]),
       .i_line_valid   (line_valid[2]),
       .i_pixel        (pixel[((2+1)*BPP)-1-:BPP]),
       .i_pixel_valid  (pixel_valid[2]),
       .mode           (mode[((2+1)*MW)-1-:MW]),
       .o_frame_valid  (frame_valid[2+1]),
       .o_line_valid   (line_valid[2+1]),
       .o_pixel        (pixel[((2+2)*BPP)-1-:BPP]),
       .o_pixel_valid  (pixel_valid[2+1]),
       .rst_n          (pyr_rst_n[2]),
       .weight         (weight[((2+1)*WW)-1-:WW])
   );

   //&BeginInstance down_scale u_downscale_3;
   //&Param NUMLAYERS NUMLAYERS;
   //&Param CAMSIZEX CAMSIZEX>>3;
   //&Param DS_R1W1 DSS_R1W1;
   //&Param DS_BE DSS_BE;
   //&Param MW MW;
   //&Param WW WW;
   //&Param BPP BPP;
   //&BuildCommand --hash_define_vars ENABLE;
   //&Connect clk pyr_clk[3];
   //&Connect rst_n pyr_rst_n[3];
   //&Connect mode mode[((3+1)*MW)-1-:MW];
   //&Connect weight weight[((3+1)*WW)-1-:WW];
   //&Connect i_line_valid line_valid[3];
   //&Connect i_frame_valid frame_valid[3];
   //&Connect i_pixel pixel[((3+1)*BPP)-1-:BPP];
   //&Connect i_pixel_valid pixel_valid[3];
   //&Connect o_line_valid line_valid[3+1];
   //&Connect o_frame_valid frame_valid[3+1];
   //&Connect o_pixel pixel[((3+2)*BPP)-1-:BPP];
   //&Connect o_pixel_valid pixel_valid[3+1];
   //&EndInstance;
   //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/rtl/down_scale.sv
   down_scale # (
       .NUMLAYERS  (NUMLAYERS),
       .CAMSIZEX   (CAMSIZEX>>3),
       .DS_R1W1    (DSS_R1W1),
       .DS_BE      (DSS_BE),
       .MW         (MW),
       .WW         (WW),
       .BPP        (BPP)
   ) u_downscale_3 (
       .clk            (pyr_clk[3]),
       .i_frame_valid  (frame_valid[3]),
       .i_line_valid   (line_valid[3]),
       .i_pixel        (pixel[((3+1)*BPP)-1-:BPP]),
       .i_pixel_valid  (pixel_valid[3]),
       .mode           (mode[((3+1)*MW)-1-:MW]),
       .o_frame_valid  (frame_valid[3+1]),
       .o_line_valid   (line_valid[3+1]),
       .o_pixel        (pixel[((3+2)*BPP)-1-:BPP]),
       .o_pixel_valid  (pixel_valid[3+1]),
       .rst_n          (pyr_rst_n[3]),
       .weight         (weight[((3+1)*WW)-1-:WW])
   );



endmodule //pyramid_gen
