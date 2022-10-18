/////////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                              //
// Project           : <PROJECT NAME>                                              //
// File Name         : generic_rnd_off_sat.v                                       //
// Module Name       : generic_rnd_off_sat                                         //
// Author            : saminathan                                                  //
// Author E-mail     : saminathan@fb.com                                           //
// Function          : Signed Round and Saturation Function                        //
// Associated modules:                                                             //
// Note: Please refer Revision History at End of File.                             //
/////////////////////////////////////////////////////////////////////////////////////

module generic_rnd_off_sat 
          #(
             parameter    MINUS_1_CHECK =  0    ,
             parameter    IN_DW         = 32    , //X
             parameter    OUT_DW        = 16    , //Y
             parameter    OUT_MSB       = 16    , //A
             parameter    OUT_LSB       =  1    , //B
             parameter    ADD_ROUND     =  1      // 1 - Round Off ; 0 - Truncation
           )
  (
     input  wire                   clk        ,
     input  wire  [IN_DW -1:0]     data_in    , 
     output reg   [OUT_DW-1:0]     data_out     
  );
  //////////////////////////////////////////////////
  //        Local Parameter Declaration           //       
  //////////////////////////////////////////////////
  localparam  D_DIFF     = OUT_MSB - OUT_LSB       ;
  localparam  POSNEGNO   = IN_DW - OUT_MSB         ;
  ///////////////////////////////////////////////////
  //              Internal Wires                   //
  ///////////////////////////////////////////////////
  wire                        pos_sat              ;
  wire                        neg_sat              ;
  wire  [OUT_DW-1:0]          data_out_next        ;
  wire  [OUT_DW-1:0]          neg_sat_value        ;
  //=========================================================================//
  //=====================round off algorithm=================================//
  //=========================================================================//

  //positive saturation condition checking
  assign pos_sat       = (data_in[OUT_MSB-1:OUT_LSB  ] == {D_DIFF  {1'b1}}) ;
  
  generate 
    if(MINUS_1_CHECK==1)
      assign neg_sat_value = {1'b1,{{OUT_DW-2}{1'b0}},1'b1} ; 
    else
      assign neg_sat_value = {1'b1,{{OUT_DW-1}{1'b0}}} ;
  endgenerate
  //negative saturation condition checking
   generate
    if((OUT_LSB==0)&&(MINUS_1_CHECK==0))
        assign neg_sat       = (data_in[OUT_MSB-2:OUT_LSB  ] == {D_DIFF+1{1'b0}})      ; 
    else if((OUT_LSB==0)&&(MINUS_1_CHECK==1))
        assign neg_sat       = (data_in[OUT_MSB-2:OUT_LSB  ] == {{D_DIFF{1'b0}},1'b1}) ; 
    else if((OUT_LSB!=0)&&(MINUS_1_CHECK==1))
        assign neg_sat       = (data_in[OUT_MSB-1:OUT_LSB-1] == {{D_DIFF{1'b0}},1'b1}) ;   
    else
        assign neg_sat       = (data_in[OUT_MSB-1:OUT_LSB-1] == {D_DIFF+1{1'b0}})      ;
    endgenerate
 //Round off or Truncation Mode
  generate
      if((OUT_LSB==0)||(ADD_ROUND==0))  
          assign data_out_next = data_in[OUT_MSB:OUT_LSB]; //signed addition with truncated bits
      else
          assign data_out_next = data_in[OUT_MSB:OUT_LSB] + {{OUT_DW-1{1'b0}},data_in[OUT_LSB-1]};
  endgenerate
 //Positive and negative saturation check and round off function
always @ ( posedge clk )
  begin
    if(data_in[IN_DW-1:OUT_MSB]=={POSNEGNO{1'b0}})//positive number
      begin
        data_out <= pos_sat ? data_in[OUT_MSB:OUT_LSB]: data_out_next ;
      end
    else if(data_in[IN_DW-1:OUT_MSB]=={POSNEGNO{1'b1}})//negative number         
      begin
        data_out <= neg_sat ? data_in[OUT_MSB:OUT_LSB]: data_out_next ; 
      end
    else //over flow
      begin
        data_out <= data_in[IN_DW-1] ? neg_sat_value : {1'b0,{{OUT_DW-1}{1'b1}}} ;
      end
   end
endmodule // generic_rnd_off_sat
/////////////////////////////////////////////////////////////////////////////////
//Revision History :                                                           //
// [Rev] --- [Date] ----- [Name] ---- [Description] ---------------------------//
//  0.1    22-June-2018    Sami        Initial Revision                        //
/////////////////////////////////////////////////////////////////////////////////
