////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// File Name         : reset_sync.v                                           //
// Module Name       : reset_sync                                             //
// Author            : saminathan                                             //
// Author E-mail     : saminathan@fb.com                                      //
// Function          : Reset Synchronization Function                         //
// Associated modules:                                                        //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
//Information                                                                 //
//===========                                                                 //
// glitch less clock gating circuit                                           //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////
module reset_sync
   //Parameter Declaration
   #(
      parameter SYNC_STAGE = 3
    )

  (
    input  wire                     clk     ,
    input  wire                     i_rst_n ,
    output wire                     o_rst_n
  );



`ifdef ASIC_SYN

   //Instantiate the reset synchronizer cell


`else
  //----------Reg  Declaration--------------------//
   reg   [SYNC_STAGE-1:0]         rest_sync_r;
   generate
     if(SYNC_STAGE==0)
       begin:COMBO
        assign  o_rst_n =  i_rst_n ;
       end //COMBO
     else
       begin:SEQ
         //Synchronization logic
         always @ (posedge clk or negedge i_rst_n)
           begin
            if(!i_rst_n)
               begin
               rest_sync_r  <= {SYNC_STAGE{1'b0}};
               end
            else
               begin
               rest_sync_r  <= {rest_sync_r[SYNC_STAGE-2:0],1'b1};
               end
           end
           assign o_rst_n = rest_sync_r[SYNC_STAGE-1] ;
       end //SEQ
   endgenerate

`endif
endmodule //reset_sync
/////////////////////////////////////////////////////////////////////////////////
//Revision History :                                                           //
// [Rev] --- [Date] ----- [Name] ---- [Description] ---------------------------//
//  0.1   26-June-2018    Sami        Initial Revision                         //
/////////////////////////////////////////////////////////////////////////////////
