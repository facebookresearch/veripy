////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// Author            : Saminathan Chockalingam                                //
// Author E-mail     : saminathan@fb.com                                      //
// File Name         : down_scale.v                                           //
// Module Name       : down_scale                                             //
// Function          : Top level down scale function                          //
// Associated modules:                                                        //
//                    - down_scale .v                                         //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
//Information                                                                 //
//===========                                                                 //
//  (1) Down scaling by 2, 4, 8, 16 and so on                                 //
////////////////////////////////////////////////////////////////////////////////

//&Module(parameter NUMLAYERS = 4, CAMSIZEX = 640, DS_R1W1 = 0, DS_BE = 1, MW = 3, WW = 3, BPP = 10);
module down_scale # (
  parameter NUMLAYERS = 4,
            CAMSIZEX = 640,
            DS_R1W1 = 0,
            DS_BE = 1,
            MW = 3,
            WW = 3,
            BPP = 10
) (
  input   logic                clk,
  input   logic                i_frame_valid,
  input   logic                i_line_valid,
  input   logic     [BPP-1:0]  i_pixel,
  input   logic                i_pixel_valid,
  input   logic     [MW-1:0]   mode,
  output  logic                o_frame_valid,
  output  logic                o_line_valid,
  output  logic     [BPP-1:0]  o_pixel,
  output  logic                o_pixel_valid,
  input   logic                rst_n,
  input   logic     [2:0]      weight
); 


   //&Regs;
   logic                line_valid_r;
   logic                frame_valid_r;
   logic     [BPP-1:0]  pixel_r;
   logic                pixel_valid_r;
   logic                ds2_frame_valid;
   logic                ds2_line_valid;
   logic     [BPP-1:0]  ds2_pixel;
   logic                ds2_pixel_valid;


   //&Wires;


   //&Clock clk;

   //&AsyncReset rst_n;


   assign  o_line_valid    = line_valid_r      ;
   assign  o_frame_valid   = frame_valid_r     ;
   assign  o_pixel[BPP-1:0] = pixel_r           ;
   assign  o_pixel_valid   = pixel_valid_r     ;

   //&Posedge;
   always_ff @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       line_valid_r <= {$bits(line_valid_r){1'b0}};
       frame_valid_r <= {$bits(frame_valid_r){1'b0}};
       pixel_r <= {$bits(pixel_r){1'b0}};
       pixel_valid_r <= {$bits(pixel_valid_r){1'b0}};
     end
     else begin
       line_valid_r   <= ds2_line_valid  ;
       frame_valid_r  <= ds2_frame_valid ;
       pixel_r[BPP-1:0] <= ds2_pixel       ;
       pixel_valid_r  <= ds2_pixel_valid ;
     end
   end
   //&EndPosedge;


  //&BeginInstance dsx2 u_dsx2;
  //&Param NUMLAYERS NUMLAYERS;
  //&Param CAMSIZEX CAMSIZEX;
  //&Param DS_R1W1 DS_R1W1;
  //&Param DS_BE DS_BE;
  //&Param MW MW;
  //&Param WW WW;
  //&Param BPP BPP;
  //&EndInstance;
  //FILE: $INFRA_ASIC_FPGA_ROOT/common/tools/veripy/open_source/demo/pyramid_gen_0/dsx2/rtl/dsx2.sv
  dsx2 # (
      .NUMLAYERS  (NUMLAYERS),
      .CAMSIZEX   (CAMSIZEX),
      .DS_R1W1    (DS_R1W1),
      .DS_BE      (DS_BE),
      .MW         (MW),
      .WW         (WW),
      .BPP        (BPP)
  ) u_dsx2 (
      .clk              (clk),
      .ds2_frame_valid  (ds2_frame_valid),
      .ds2_line_valid   (ds2_line_valid),
      .ds2_pixel        (ds2_pixel[BPP-1:0]),
      .ds2_pixel_valid  (ds2_pixel_valid),
      .i_frame_valid    (i_frame_valid),
      .i_line_valid     (i_line_valid),
      .i_pixel          (i_pixel[BPP-1:0]),
      .i_pixel_valid    (i_pixel_valid),
      .mode             (mode[MW-1:0]),
      .rst_n            (rst_n),
      .weight           (weight[2:0])
  );


endmodule //down_scale
