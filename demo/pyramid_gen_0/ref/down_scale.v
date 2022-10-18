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
  output  wire                o_line_valid,
  output  wire                o_pixel_valid,
  output  wire                o_frame_valid,
  output  wire     [BPP-1:0]  o_pixel,
  input                       i_frame_valid,
  input            [2:0]      weight,
  input                       rst_n,
  input                       i_pixel_valid,
  input                       clk,
  input            [BPP-1:0]  i_pixel,
  input            [MW-1:0]   mode,
  input                       i_line_valid
); 


   //&Regs;
   reg     [BPP-1:0]  pixel_r;
   reg                line_valid_r;
   reg                frame_valid_r;
   reg                pixel_valid_r;


   //&Wires;
   wire                ds2_frame_valid;
   wire                ds2_line_valid;
   wire                ds2_pixel_valid;
   wire     [BPP-1:0]  ds2_pixel;


   //&Clock clk;

   //&AsyncReset rst_n;


   assign  o_line_valid    = line_valid_r      ;
   assign  o_frame_valid   = frame_valid_r     ;
   assign  o_pixel[BPP-1:0] = pixel_r           ;
   assign  o_pixel_valid   = pixel_valid_r     ;

   //&Posedge;
   always @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       pixel_r <= {BPP{1'b0}};
       line_valid_r <= 1'b0;
       frame_valid_r <= 1'b0;
       pixel_valid_r <= 1'b0;
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
  //FILE: dsx2.v
  dsx2 # (
      .CAMSIZEX   (CAMSIZEX),
      .DS_R1W1    (DS_R1W1),
      .DS_BE      (DS_BE),
      .WW         (WW),
      .BPP        (BPP),
      .MW         (MW),
      .NUMLAYERS  (NUMLAYERS)
  ) u_dsx2 (
      .i_frame_valid    (i_frame_valid),
      .weight           (weight[2:0]),
      .clk              (clk),
      .ds2_line_valid   (ds2_line_valid),
      .i_pixel_valid    (i_pixel_valid),
      .ds2_pixel_valid  (ds2_pixel_valid),
      .ds2_frame_valid  (ds2_frame_valid),
      .i_pixel          (i_pixel[BPP-1:0]),
      .mode             (mode[MW-1:0]),
      .i_line_valid     (i_line_valid),
      .rst_n            (rst_n),
      .ds2_pixel        (ds2_pixel[BPP-1:0])
  );


endmodule //down_scale
