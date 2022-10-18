////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// File Name         : generic_mem_wrapper.v                                  //
// Module Name       : generic_mem_wrapper                                    //
// Author            : saminathan                                             //
// Author E-mail     : saminathan@fb.com                                      // 
// Function          : RAM generic behavioral model                           //
//                     -1R1W to 1RW conversion                                //
//                     -With and Without Bit enable options                   //  
// Associated modules:                                                        //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
//Information                                                                 //          
//===========                                                                 //
// Generate the RAM instances based on the below parameters                   //
//                                                                            //
////////////////////////////////////////////////////////////////////////////////
module generic_mem_wrapper
        #(
           parameter  R1W1    =    0 , //dual port memory(1) or single port memory (0)
           parameter  BE      =    1 , //Bit enable option enabled/disabled
           parameter  NO_RAM  =    4 , //No Of RAM to be generated
           parameter  DW      =   12 , //RAM Data Width of each location
           parameter  AW      =   11   //RAM Address Width 
         ) 
  (
    input  wire                     clk      ,
    input  wire [ NO_RAM    -1:0]   wr_en    ,
    input  wire [(NO_RAM*AW)-1:0]   wr_addr  ,
    input  wire [(NO_RAM*DW)-1:0]   wr_data  , 
    input  wire [ NO_RAM    -1:0]   rd_en    ,    
    input  wire [(NO_RAM*AW)-1:0]   rd_addr  ,
    output wire [(NO_RAM*DW)-1:0]   rd_data     
  );
 
  //-----Wire Declaration---------//
   wire                   mem_en      ;
   wire                   mem_we      ;
   wire [DW-1:0] wr_be [0:NO_RAM-1]   ;
   wire [(NO_RAM*DW)-1:0] mem_be      ; 
                                      
   assign mem_en = 1'b1               ;
   assign mem_we = |wr_en[NO_RAM-1:0] ; 
   
   genvar j;
   generate
     for (j=0 ; j < NO_RAM; j=j+1)
       begin
         assign wr_be[j]                      ={DW{wr_en[j]}}              ;
         assign mem_be[(((j+1)*DW)-1) -: DW]  = wr_be[j]                   ;
       end
   endgenerate
         
 //Line Buffer Multiple instance generation based on the parameter configuration
 genvar i;
  generate 
    if ((R1W1==1) && (BE==1))  //1R1W with BE of Single RAM (multiple RAM option cascaded) 
       generic_dual_port_ram
          #(
              . BE     (BE        ),
              . DW     (DW*NO_RAM ),
              . AW     (AW        )
           )
        u_generic_dual_port_ram       
         (
           . clk     (clk                      ),
           . mem_en  (mem_en                   ),
           . wr_be   (mem_be[(NO_RAM*DW)-1:0]  ),
           . wr_en   (mem_we                   ),
           . rd_en   (rd_en[0]                 ),
           . wr_addr (wr_addr[AW-1:0]          ),
           . wr_data (wr_data[(NO_RAM*DW)-1:0] ),  
           . rd_addr (rd_addr[AW-1:0]          ),
           . rd_data (rd_data[(NO_RAM*DW)-1:0] )   
         );  
     else if((R1W1==0) && (BE==1)) //1RW RAM
        generic_single_port_ram_wrapper
               #(
                   . BE     (BE       ),
                   . DW     (DW*NO_RAM),
                   . AW     (AW       )
                )
        u_generic_single_port_ram     
         (
           . clk     (clk                      ),
           . mem_en  (mem_en                   ),
           . wr_be   (mem_be[(NO_RAM*DW)-1:0]  ),
           . wr_en   (mem_we                   ),
           . rd_en   (rd_en[0]                 ),
           . wr_addr (wr_addr[AW-1:0]          ),
           . wr_data (wr_data[(NO_RAM*DW)-1:0] ),  
           . rd_addr (rd_addr[AW-1:0]          ),
           . rd_data (rd_data[(NO_RAM*DW)-1:0] )   
         );  

     else if((R1W1==0) && (BE==0))
        for (i=0 ; i < NO_RAM; i=i+1) 
          begin : ram_1rw_nobe_      
        generic_single_port_ram_wrapper
               #(
                   . BE     (BE),
                   . DW     (DW),
                   . AW     (AW)
                )
        u_generic_single_port_ram     
         (
           . clk     (clk                            ),
           . mem_en  (mem_en                         ),
           . wr_be   ({DW{1'b0}}                     ),
           . wr_en   (wr_en  [i]                     ),
           . rd_en   (rd_en  [i]                     ),
           . wr_addr (wr_addr[(((i+1)*AW)-1) : i*AW] ),
           . wr_data (wr_data[(((i+1)*DW)-1) : i*DW] ),  
           . rd_addr (rd_addr[(((i+1)*AW)-1) : i*AW] ),
           . rd_data (rd_data[(((i+1)*DW)-1) : i*DW] )   
         );   
           end          
     else if((R1W1==0) && (BE==1))
        for (i=0 ; i < NO_RAM; i=i+1) 
          begin : ram_1r1w_nobe_        
            generic_dual_port_ram
                   #(
                       . BE     (BE ),
                       . DW     (DW ),
                       . AW     (AW )
                    )
            u_generic_dual_port_ram        
             (
               . clk     (clk                            ),
               . mem_en  (mem_en                         ),
               . wr_be   (mem_be [(NO_RAM*DW)-1:0]       ),
               . wr_en   (wr_en  [   i                 ] ),
               . rd_en   (rd_en  [   i                 ] ),
               . wr_addr (wr_addr[(((i+1)*AW)-1) : i*AW] ),
               . wr_data (wr_data[(((i+1)*DW)-1) : i*DW] ),  
               . rd_addr (rd_addr[(((i+1)*AW)-1) : i*AW] ),
               . rd_data (rd_data[(((i+1)*DW)-1) : i*DW] )   
             );  
          end          
  endgenerate
  
endmodule //generic_mem_wrapper
/////////////////////////////////////////////////////////////////////////////////
//Revision History :                                                           //
// [Rev] --- [Date] ----- [Name] ---- [Description] ---------------------------//
//  0.1   11-April-2018  Sami        Initial Revision                          //
/////////////////////////////////////////////////////////////////////////////////
