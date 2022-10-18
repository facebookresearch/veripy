//////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                   //
// Project           : <PROJECT NAME>                   //
// File Name         : clk_gate.v                       //
// Module Name       : clk_gate                         //
// Author            : saminathan                       //
// Author E-mail     : saminathan@fb.com                //
// Function          : clock gate logic                 //
// Associated modules:                                  //
// Note: Please refer Revision History at End of File.  //
//////////////////////////////////////////////////////////
//Information                                           //
//===========                                           //
// Glitch less clock gating circuit                     //
//////////////////////////////////////////////////////////
module clk_gate
  (
    input  wire                     clk_in     ,
    input  wire                     clk_disable,
    input  wire                     scan_en    ,
    input  wire                     clk_en     ,
    output wire                     clk_out
  );

`ifdef ASIC_SYN
  //Instantiate clock gate cell logic


`else
  reg   clk_en_latch  ;

  always @ ( * )
    begin
      if(!clk_in) //Latch to capture the enable signal
        clk_en_latch = clk_en|scan_en      ;
    end

  assign clk_out   = clk_en_latch & clk_in ;

`endif

endmodule //clk_gate
//////////////////////////////////////////////////////////
//Revision History :                                    //
// [Rev] --- [Date] ----- [Name] ---- [Description] ----//
//  0.1   27-June-2017    Sami        Initial Revision  //
//////////////////////////////////////////////////////////
