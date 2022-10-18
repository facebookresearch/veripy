////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

module booth_mult_pp
         ( /*AUTOARG*/
   // Outputs
   pp,
   // Inputs
   a, b
   );
    //----------Parameter Declarations----------------//
    parameter  AW        = 12                          ; //Multiplier Data Width
    parameter  BW        =  6                          ; //Multiplicand Data Width
    parameter  A_SIGNED  =  1                          ; //A- Signed 2's Compliment ; 0 - Unsigned
    parameter  B_SIGNED  =  1                          ; //B- Singed  or Unsigned
    //---------Local Paramter-------------------------//
    localparam [31:0] MDW = (AW >= BW) ?  AW+1 : BW+1  ; //Multiplicand(MD) data width(W)
    localparam [31:0] MRW = (AW >= BW) ?  BW+3 : AW+3  ; //Multiplier(MR) data width(W)
    localparam [31:0] NPP = MRW/2                      ; //Number(N) of partial(P) Products(P)  - (NPP)
    localparam [31:0] PPW = AW+BW                      ; //Partial(P) Products(p) data width(W) - (PPW)
    localparam [31:0] BPW = MDW +1                     ; //Booth(B)Product(P) width(W) - (BPW)
    //---------Input and Output Declaration-----------//
    input   wire   [AW-1:0]                   a        ; //Multiplicand or Multiplier
    input   wire   [BW-1:0]                   b        ; //Multiplicand or Multiplier
    output  wire   [(NPP*(AW+BW))-1:0]        pp       ; //Partial(P) Products(P) - PP  short name
    //---------Wire Delcaration-----------------------//
    wire [MDW-1:0]     multiplicand                    ; //Multiplicand
    wire [MRW  :0]     multiplier                      ; //Multiplier
    wire [NPP-1:0]     booth_flag                      ; //Booth Encoding Flag
    //---------Reg  Delcaration-----------------------//
    reg  [(NPP*BPW)-1:0] booth_pp                      ; //Booth Partical Products

    //swap the a & b based on the bit width and extend the sign bit and left shift by 2
    generate
        if(AW >= BW)
          begin:AW_BIG_EQ
             if(A_SIGNED==1)
               begin: A_S
                assign multiplicand = {a[AW-1],a};
               end
             else
               begin: A_US
                assign multiplicand = {1'b0,a}   ;
               end
            if(B_SIGNED==1)
              begin:B_S
                assign multiplier   =  {b[BW-1],b[BW-1],b[BW-1],b,1'b0};
              end
            else
              begin:B_US
                assign multiplier   =  {3'b000,b,1'b0};
              end
          end
        else
          begin:BW_BIG
            if(B_SIGNED==1)
              begin: B_S
                assign multiplicand = {b[BW-1],b};
              end
            else
              begin: B_US
                assign multiplicand = {1'b0,b};
              end
            if(A_SIGNED==1)
              begin:A_S
                assign multiplier   =  {a[AW-1],a[AW-1],a[AW-1],a,1'b0};
              end
            else
              begin:A_US
                assign multiplier   =  {3'b000,a,1'b0};
              end
          end
    endgenerate

    //&BeginSkip;
   //Booth Encoding
    genvar s ;
    generate
      for ( s = 0 ; s < NPP ; s = s+1)
        begin:B_PP_
         //Radix-4 Booth Encoding - 1 bit growth in booth encoding
         always @ ( * )
           begin:B_T_
             case (multiplier[((s*2)+2) -: 3]) //Booth Encoding ( MDW+1) - 1 bit growth due to booth encoding
              3'b001,3'b010: begin //+1 Multiplicand
                               booth_pp[(((s+1)*BPW)-1) -: BPW] =  {multiplicand[MDW-1],multiplicand} ;
                             end
              3'b011       : begin //+2 BPW
                               booth_pp[(((s+1)*BPW)-1) -: BPW] =  {multiplicand,1'b0}                ;
                             end
              3'b100       : begin //-2 Multiplicand
                               booth_pp[(((s+1)*BPW)-1) -: BPW] = ~{multiplicand,1'b0}                ;
                             end
              3'b101,3'b110: begin //-1 Multiplicand
                               booth_pp[(((s+1)*BPW)-1) -: BPW] = ~{multiplicand[MDW-1],multiplicand} ;
                             end
              default      : begin //0 Multiplicand
                               booth_pp[(((s+1)*BPW)-1) -: BPW] =  {BPW{1'b0}}                        ;
                             end
             endcase
           end
         //Booth Flag for next product addition, this flag will be asserted for (-1) & (-2) cases alone
         assign booth_flag[s] =  multiplier[(s*2)+2] & (~&multiplier[((s*2)+1) -: 2]);
         //Final Partial Product Terms
         if(s==0)
           begin
               assign pp[(((s+1)*PPW)-1) -: PPW ] = {{(PPW-BPW){booth_pp[((s+1)*BPW)-1]}},booth_pp[(((s+1)*BPW)-1) -: BPW]};
           end
         else
           begin
               assign pp[(((s+1)*PPW)-1) -: PPW]  = {{(PPW-(BPW)){booth_pp[(((s+1)*BPW)-1)]}},booth_pp[(((s+1)*BPW)-1) -: BPW],
                                                                     1'b0,booth_flag[s-1],{(2*(s-1)){1'b0}}};
           end
       end
    endgenerate
    //&EndSkip;

endmodule //booth_mult_pp
/////////////////////////////////////////////////////////////////////////////////
//Revision History :                                                           //
// [Rev] --- [Date] ----- [Name] ---- [Description] ---------------------------//
//  0.1    22-June-2018    Sami        Initial Revision                        //
/////////////////////////////////////////////////////////////////////////////////
