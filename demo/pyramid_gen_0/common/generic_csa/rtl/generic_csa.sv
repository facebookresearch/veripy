////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// File Name         : generic_csa.v                                          //
// Module Name       : generic_csa                                            //
// Author            : Saminathan Chockalingam                                //
// Author E-mail     : saminathan@fb.com                                      //
// Function          : Top level for carry save adder function                //
// Associated modules:                                                        //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
module generic_csa
         #(parameter DW = 32)
        (
          input  wire [DW-1:0]  in1 ,
          input  wire [DW-1:0]  in2 ,
          input  wire [DW-1:0]  in3 ,
          output wire [DW-1:0]  out1,
          output wire [DW-1:0]  out2

        );

       assign out1  = in1 ^ in2 ^ in3 ;
       assign out2  = { (((in1[DW-2:0]) & (in2[DW-2:0])) |
                         ((in2[DW-2:0]) & (in3[DW-2:0])) |
                         ((in3[DW-2:0]) & (in1[DW-2:0]))  ),1'b0 };

endmodule //generic_csa
/////////////////////////////////////////////////////////////////////////////////
//Revision History :                                                           //
// [Rev] --- [Date] ----- [Name] ---- [Description] ---------------------------//
//  0.1    22-June-2018    Sami        Initial Revision                        //
/////////////////////////////////////////////////////////////////////////////////
