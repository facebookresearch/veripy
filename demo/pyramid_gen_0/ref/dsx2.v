
////////////////////////////////////////////////////////////////////////////////
// Project Code      : <PROJECT CODE>                                         //
// Project           : <PROJECT NAME>                                         //
// File Name         : dsx2.v                                                 //
// Module Name       : dsx2                                                   //
// Author            : Saminathan Chockalingam                                //
// Author Email      : saminathan@fb.com                                      //
// Function          : Top level down scale function                          //
// Associated modules:                                                        //
//                    - dsx2.v                                                //
// Note: Please refer Revision History at End of File.                        //
////////////////////////////////////////////////////////////////////////////////
//Information                                                                 //
//===========                                                                 //
//  (1) Down scaling by 2, 4, 8, 16 and so on                                 //
////////////////////////////////////////////////////////////////////////////////


//&Module(parameter   NUMLAYERS = 4, CAMSIZEX = 640, DS_R1W1 = 0, DS_BE = 1, MW = 3, WW = 3, BPP = 8);
module dsx2 # (
  parameter NUMLAYERS = 4,
            CAMSIZEX = 640,
            DS_R1W1 = 0,
            DS_BE = 1,
            MW = 3,
            WW = 3,
            BPP = 8
) (
  output  wire                ds2_line_valid,
  output  wire                ds2_pixel_valid,
  output  wire                ds2_frame_valid,
  output  wire     [BPP-1:0]  ds2_pixel,
  input                       i_frame_valid,
  input            [2:0]      weight,
  input                       clk,
  input                       i_pixel_valid,
  input            [BPP-1:0]  i_pixel,
  input            [MW-1:0]   mode,
  input                       i_line_valid,
  input                       rst_n
); 



  //-------------LocalParam Declaration-----------//
  function integer clog2;
    input integer DW;
      begin
        clog2 = 0;
        while (DW > 0)
          begin
            DW    = DW >> 1  ;
            clog2 = clog2 +1 ;
          end
       end
   endfunction//clog2

   localparam DS_X_PP   = 2                ;
   localparam DS_Y_PP   = 2                ;
   localparam PIX_CW    = 11               ;
   localparam PL        = 10               ;
   localparam BLOCK     = 3                ;
   localparam DSXW      = 12               ;
   localparam NO_RAM    = BLOCK-1          ;
   localparam ADDR_W    = clog2((CAMSIZEX/2)-1);
   localparam PLY       = 5                ;
   localparam PE        = 5                ;
   localparam DSY_PP    = 4                ;


   //&Wires;
   wire                            ds_out_fv;
   wire     [DSXW+1:0]             x_sum;
   wire                            rd_en;
   wire     [DSXW+5:0]             y_sum_int;
   wire     [(NO_RAM*DSXW)-1:0]    wd;
   wire                            ds_out_lv;
   wire                            le;
   wire                            ds2_x_fe;
   wire     [(NO_RAM*DSXW)-1:0]    rd;
   wire     [NO_RAM-1:0]           re;
   wire                            ls;
   wire                            ds_out_pv;
   wire     [(NO_RAM*ADDR_W)-1:0]  ra;
   wire     [DSXW+5:0]             y_sum;
   wire     [NO_RAM-1:0]           we;
   wire                            fs;
   wire     [(NO_RAM*ADDR_W)-1:0]  wa;
   wire                            ds_y_lv_w;
   wire     [(BLOCK*DSXW)-1:0]     pix_y_bus;
   wire                            ds2_x_fs;
   wire     [BPP:0]                dsx2_yp;
   wire                            fe;
   wire     [(BLOCK*BPP)-1:0]      pixel_bus;
   wire                            ds2_x_ls;
   wire                            ds2_x_lv;
   wire     [DSXW-1:0]             ds2_x_p;
   wire                            ram_switch_rst;
   wire                            ds2_x_pv;
   wire                            ds2_x_le;
   wire     [BPP-1:0]              ds_out_p;
   wire                            ds2_x_fv;


   //&Regs;
   reg                        le_r;
   reg                        ds_y_lv_2r;
   reg                        ds2_x_fv_2r;
   reg     [DSXW-1:0]         wr_data_r;
   reg     [DSXW-1:0]         pix_y_r2;
   reg                        lv_mask_r;
   reg                        ds2_x_lv_r;
   reg                        fv_r;
   reg     [MW-1:0]           mode_r;
   reg     [NO_RAM-1:0]       wr_en_r;
   reg                        rd_flag_r;
   reg     [ADDR_W-1:0]       rd_addr;
   reg                        rd_en_r;
   reg                        extra_rd_en;
   reg                        ds_x_pv_r;
   reg                        ds_y_pv_2r;
   reg     [NO_RAM-1:0]       ram_sw;
   reg                        ds2_x_fe_r;
   reg                        frame_mask;
   reg                        pixel_mask;
   reg     [DS_Y_PP-1:0]      ds_y_lv_sr;
   reg                        rd_en_2r;
   reg                        ds_y_pv_r;
   reg                        pv_r;
   reg     [DS_X_PP-1:0]      ll_r_sr;
   reg     [DSY_PP-1:0]       rd_en_sr;
   reg                        ds2_x_lv_2r;
   reg     [(BLOCK*BPP)-1:0]  pix_sr;
   reg                        fe_r;
   reg     [DS_Y_PP-1:0]      ds_y_fv_sr;
   reg                        ds_x_st_idx;
   reg                        ds_x_pv_in;
   reg     [DS_X_PP-1:0]      ds_x_pv_sr;
   reg     [DS_X_PP-1:0]      ds_x_lv_sr;
   reg     [DS_X_PP-1:0]      ds_x_fv_sr;
   reg                        ds_y_fv_2r;
   reg                        ds_y_fv_r;
   reg     [ADDR_W-1:0]       wr_addr_r;
   reg                        ds_y_lv_r;
   reg     [PL-1:0]           lv_sr;
   reg                        line_mask;
   reg     [DS_Y_PP-1:0]      ds_y_pv_sr;
   reg                        ls_flag;
   reg     [DSXW-1:0]         pix_y_r1;
   reg                        ds_x_pv_mask;
   reg     [ADDR_W-1:0]       max_addr;
   reg                        lv_end;
   reg                        ds2_x_fv_r;
   reg                        ds_x_pv_in_r;
   reg                        ll_r;
   reg     [DSXW-1:0]         pix_y_r3;
   reg     [PL-1:0]           fv_sr;
   reg     [PL-1:0]           pv_sr;
   reg                        frame_end_r;
   reg                        lv_r;
   reg                        ll_r_1d;
   reg                        sh_flag;
   reg                        rd_flag;
   reg     [ADDR_W-1:0]       wr_addr;
   reg                        start_y;
   reg                        fl_r;
   reg                        ds_x_pv_out_r;


   assign  ds2_line_valid        =  ds_out_lv         ;
   assign  ds2_frame_valid        =  ds_out_fv         ;
   assign  ds2_pixel[BPP-1:0] =  ds_out_p          ;
   assign  ds2_pixel_valid        =  ds_out_pv         ;

   //&Clock clk;

   //&AsyncReset rst_n;


   //Number of Pipeline stages
   //&Posedge;
   always @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       fv_sr <= {PL{1'b0}};
       pv_sr <= {PL{1'b0}};
       lv_sr <= {PL{1'b0}};
     end
     else begin
       lv_sr[PL-1:0] <=  {lv_sr[PL-2:0],i_line_valid } ;
       fv_sr[PL-1:0] <=  {fv_sr[PL-2:0],i_frame_valid } ;
       pv_sr[PL-1:0] <=  {pv_sr[PL-2:0],i_pixel_valid } ;
     end
   end
   //&EndPosedge;

   //Input Interface wrapper logic to find start and end pulses
   //&Posedge;
   always @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       fe_r <= 1'b0;
       pv_r <= 1'b0;
       le_r <= 1'b0;
       lv_r <= 1'b0;
       fv_r <= 1'b0;
     end
     else begin
       lv_r  <= i_line_valid & i_frame_valid      ;
       fv_r  <= i_frame_valid             ;
       le_r  <= le               ;
       fe_r  <= fe               ;
       pv_r  <= i_pixel_valid             ;
     end
   end
   //&EndPosedge;

    //Protocol Interface
    assign ls = i_line_valid  & (~lv_r )     ;
    assign le = lv_r  & (~i_line_valid )     ;
    assign fs = i_frame_valid  & (~fv_r )     ;
    assign fe = fv_r  & (~i_frame_valid )     ;


   //&Posedge;
   always @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       mode_r <= {MW{1'b0}};
       ls_flag <= 1'b0;
     end
     else begin
       mode_r[MW-1:0] <= mode ;

       if(ls && (!i_pixel_valid))
         ls_flag<= 1'b1 ;
       else if (i_pixel_valid)
         ls_flag<= 1'b0 ;
     end
   end
   //&EndPosedge;

   //Data path line shift register
   always @ (posedge clk)
    begin
      if((ls && i_pixel_valid) || (ls_flag&&i_pixel_valid))
        pix_sr[(BLOCK*BPP)-1:0] <= {i_pixel[BPP-1:0],i_pixel[BPP-1:0],{BPP{1'b0}} } ;
      else if(le)
        pix_sr <= {pix_sr[((3)*BPP)-1  -:  BPP],
                   pix_sr[((3)*BPP)-1  -:  BPP],
                   pix_sr[((2)*BPP)-1  -:  BPP]} ;
      else if (i_pixel_valid)
        pix_sr <= {i_pixel,pix_sr[((BLOCK)*BPP)-1 : BPP]}        ;
      else
        pix_sr <= pix_sr                                     ;
    end

   //&Force internal pixel_bus;
   assign pixel_bus[(BLOCK*BPP)-1:0] =  pix_sr ;

   //&BeginSkip;
   //debug - code
    wire [BPP-1:0] pixel_bus_w [0:BLOCK-1];
    genvar b;
    generate
      for (b=0; b <  (BLOCK) ; b=b+1)
       begin
         assign  pixel_bus_w[b]  = pixel_bus[(((b+1)*BPP) -1) -: BPP];
       end
    endgenerate
   //&EndSkip;


    always @ ( * )
      begin
        ds_x_pv_in = pixel_mask & (pv_r|le_r)                ;
      end

    //generate the pixel and line valid signal
   //&Posedge;
   always @ (posedge clk or negedge rst_n) begin
     if (~rst_n) begin
       line_mask <= 1'b0;
       ds_x_pv_sr <= {DS_X_PP{1'b0}};
       ds_x_pv_r <= 1'b0;
       frame_mask <= 1'b0;
       pixel_mask <= 1'b0;
       ds_x_lv_sr <= {DS_X_PP{1'b0}};
       ds_x_pv_in_r <= 1'b0;
       ds_x_fv_sr <= {DS_X_PP{1'b0}};
       ds_x_pv_mask <= 1'b0;
       ds_x_st_idx <= 1'b0;
       ds_x_pv_out_r <= 1'b0;
     end
     else begin
          ds_x_st_idx   <= mode_r[0]                                           ;//mode 0,2,4 skip first pixel
          pixel_mask    <= le_r ? 1'b0 : pixel_mask ? 1'b1: (pixel_mask^pv_r)  ;//pixel mask
          ds_x_pv_in_r  <= ds_x_pv_in                                          ;//pixel valid
          ds_x_pv_mask  <=  ( ds_x_pv_mask ^ ds_x_pv_in_r) & ds_x_lv_sr[1]     ;
          ds_x_pv_out_r <= ds_x_st_idx ?  ds_x_pv_in_r& (~ds_x_pv_mask ) & ds_x_fv_sr[0] & ds_x_lv_sr[0] :
                                          ds_x_pv_in_r& ( ds_x_pv_mask ) & ds_x_fv_sr[0] & ds_x_lv_sr[0] ;
          line_mask     <= le_r ? 1'b0 : (ls||i_pixel_valid) ? 1'b1: line_mask          ;
          frame_mask    <= fe_r ? 1'b0 : (fs||i_pixel_valid) ? 1'b1: frame_mask         ;
          ds_x_pv_r     <= line_mask ? (i_pixel_valid|le) : 1'b0                        ;
          ds_x_lv_sr[DS_X_PP-1:0]    <=  {ds_x_lv_sr[DS_X_PP-2:0],line_mask  }              ;
          ds_x_fv_sr[DS_X_PP-1:0]    <=  {ds_x_fv_sr[DS_X_PP-2:0],frame_mask }              ;
          ds_x_pv_sr[DS_X_PP-1:0]    <=  {ds_x_pv_sr[DS_X_PP-2:0],ds_x_pv_r  }              ;

     end
   end
   //&EndPosedge;


  //&BeginInstance ds2_function ds2_x_function;
  //&Param BPP BPP;
  //&Param DS_Y 0;
  //&Param COFF_W 3;
  //&Param O_DW DSXb;
  //&Connect pixel pixel_bus;
  //&Connect sum_out x_sum[DSXW+1:0];
  //&EndInstance;
  //FILE: ds2_function.v
  ds2_function # (
      .BPP     (BPP),
      .COFF_W  (3),
      .DS_Y    (0),
      .O_DW    (DSXb)
  ) ds2_x_function (
      .pixel    (pixel_bus[3*BPP-1:0]),
      .sum_out  (x_sum[DSXW+1:0]),
      .mode     (mode[MW-1:0]),
      .weight   (weight[2:0]),
      .clk      (clk)
  );

  //down scale by X output verified
  assign ds2_x_lv = ds_x_lv_sr[1]   ;
  assign ds2_x_fv = ds_x_fv_sr[1]   ;
  assign ds2_x_pv = ds_x_pv_out_r   ;
  assign ds2_x_p[DSXW-1:0]  = x_sum[DSXW-1:0] ;


  //&Force internal ds2_x_fv_2r;
  //&Force internal ds2_x_lv_2r;

  //&Posedge;
  always @ (posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      ds2_x_fv_r <= 1'b0;
      ds2_x_fv_2r <= 1'b0;
      ds2_x_lv_2r <= 1'b0;
      ds2_x_lv_r <= 1'b0;
      ds2_x_fe_r <= 1'b0;
    end
    else begin
       ds2_x_lv_r <= ds2_x_lv   ;
       ds2_x_fv_r <= ds2_x_fv   ;
       ds2_x_fe_r <= ds2_x_fe   ;
       ds2_x_lv_2r<= ds2_x_lv_r ;
       ds2_x_fv_2r<= ds2_x_fv_r ;
    end
  end
  //&EndPosedge;

  assign ds2_x_le = ( ds2_x_lv_r) & (~ds2_x_lv);
  assign ds2_x_fe = ( ds2_x_fv_r) & (~ds2_x_fv);
  assign ds2_x_ls = (~ds2_x_lv_r) & (ds2_x_lv) ;
  assign ds2_x_fs = (~ds2_x_fv_r) & (ds2_x_fv) ;

  //-------------------RAM Write Interface Logic-------------------------//
  //Write RAM Replication logic for all the rams
  assign we[NO_RAM-1:0]       = wr_en_r                                       ;
  assign wa[(NO_RAM*ADDR_W)-1:0]       = {NO_RAM{wr_addr_r}}                           ;
  assign wd[(NO_RAM*DSXW)-1:0]       = {NO_RAM{wr_data_r}}                           ;
  assign ram_switch_rst  = ((ram_sw[NO_RAM-1]) & (ds2_x_le))      ;
  //RAM Write Interface Block

  parameter RAM_SW_RESET_VAL = {{NO_RAM-1{1'b0}},1'b1};

  //&Posedge;
  always @ (posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      wr_data_r <= {DSXW{1'b0}};
      wr_addr <= {ADDR_W{1'b0}};
      wr_en_r <= {NO_RAM{1'b0}};
      wr_addr_r <= {ADDR_W{1'b0}};
      ram_sw <= RAM_SW_RESET_VAL;
    end
    else begin
           wr_data_r[DSXW-1:0]  <= ds2_x_p                                ;
           wr_addr_r[ADDR_W-1:0]  <= wr_addr                                ;
           wr_en_r[NO_RAM-1:0]    <= {NO_RAM{ds2_x_pv}} &  ram_sw           ;
           //RAM Write Adder Generation logic
           if (ds2_x_le ||ds2_x_fe)
             begin
               wr_addr[ADDR_W-1:0] <= {ADDR_W{1'b0}}                        ;
             end
           else if(ds2_x_pv)
             begin
               wr_addr <= wr_addr + {{ADDR_W-1{1'b0}},1'b1}     ;
             end
           else
             begin
               wr_addr <= wr_addr                               ;
             end
           //RAM Switch Logic Counter
           if(ram_switch_rst ||ds2_x_fe )
             begin
               ram_sw[NO_RAM-1:0] <= {{NO_RAM-1{1'b0}},1'b1}                ;
             end
           else if(ds2_x_le)
             begin
               ram_sw <= {ram_sw[NO_RAM-2:0],1'b0}              ;
             end
           else
             begin
               ram_sw <= ram_sw                                 ;
             end
    end
  end
  //&EndPosedge;


  //&BeginInstance generic_mem_wrapper u0_lb_dsx2_x;
  //&Param R1W1 DS_R1W1;
  //&Param BE DS_BE;
  //&Param NO_RAM NO_RAM;
  //&Param DW DSXW;
  //&Param AW ADDR_W;
  //&Connect wr_en we;
  //&Connect rd_en re;
  //&Connect wr_addr wa;
  //&Connect wr_data wd;
  //&Connect rd_addr ra;
  //&Connect rd_data rd[(NO_RAM*DSXW)-1:0];
  //&EndInstance;
  //FILE: ./libs/generic_mem_wrapper.v
  generic_mem_wrapper # (
      .BE      (DS_BE),
      .R1W1    (DS_R1W1),
      .AW      (ADDR_W),
      .NO_RAM  (NO_RAM),
      .DW      (DSXW)
  ) u0_lb_dsx2_x (
      .rd_data  (rd[(NO_RAM*DSXW)-1:0]),
      .clk      (clk),
      .wr_addr  (wa[NO_RAM*ADDR_W-1:0]),
      .wr_en    (we[NO_RAM-1:0]),
      .rd_en    (re[NO_RAM-1:0]),
      .rd_addr  (ra[NO_RAM*ADDR_W-1:0]),
      .wr_data  (wd[NO_RAM*DSXW-1:0])
  );

  //---------------RAM Read Interface Logic---------------//
  assign rd_en       = (rd_flag & ds2_x_pv)|extra_rd_en   ;
  assign ra[(NO_RAM*ADDR_W)-1:0]          = {NO_RAM{rd_addr}}                  ;
  assign re[NO_RAM-1:0]          = {NO_RAM{rd_en}}                    ;
  //RAM Read Interface Block

  //&Force internal rd_en_2r;

  //&Posedge;
  always @ (posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      rd_en_2r <= 1'b0;
      rd_flag <= 1'b0;
      rd_en_sr <= {DSY_PP{1'b0}};
      rd_flag_r <= 1'b0;
      rd_addr <= {ADDR_W{1'b0}};
      rd_en_r <= 1'b0;
    end
    else begin
          rd_en_r  <= rd_en                               ; //read data valid
          rd_en_2r <= rd_en_r                             ; //pixel mux valid
          rd_en_sr[DSY_PP-1:0] <= {rd_en_sr[DSY_PP-2:0],rd_en_r}      ;
          rd_flag_r <= rd_flag                            ;
          //RAM Read flag asseration logic
          if( ds2_x_fe)
            begin
              rd_flag  <= 1'b0                            ;
            end
          else if((ram_sw[NO_RAM-2]) && (ds2_x_le))
            begin
              rd_flag  <= 1'b1                            ;
            end
          else
            begin
              rd_flag  <= rd_flag                         ;
            end

          //Read address generation logic
          if(ds2_x_le ||ds2_x_fe)
            begin
              rd_addr[ADDR_W-1:0] <=  {ADDR_W{1'b0}}                  ;
            end
          else if(rd_en)
            begin
              rd_addr  <= rd_addr + {{ADDR_W-1{1'b0}},1'b1};
            end
          else
            begin
              rd_addr  <= rd_addr                         ;
            end
    end
  end
  //&EndPosedge;


    //Read data first and last line find out logic
  //&Posedge;
  always @ (posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      ll_r <= 1'b0;
      max_addr <= {ADDR_W{1'b0}};
      ll_r_1d <= 1'b0;
      ll_r_sr <= {DS_X_PP{1'b0}};
      fl_r <= 1'b0;
      extra_rd_en <= 1'b0;
      sh_flag <= 1'b0;
    end
    else begin
           sh_flag     <= frame_end_r ? 1'b0 : (ds2_x_ls & (~fl_r) & (~ds2_x_fs)) +  sh_flag ;
           ll_r        <= extra_rd_en                                           ;
           ll_r_sr[DS_X_PP-1:0]     <= {ll_r_sr[DS_X_PP-2:0],ll_r}                           ;
           ll_r_1d     <= ll_r                                                  ;
           max_addr[ADDR_W-1:0]    <= (ds2_x_lv_r && ds2_x_fv_r && |wr_en_r)? wr_addr_r : max_addr ;

           if(ds2_x_fe_r)
             extra_rd_en <= 1'b1       ;
           else if((rd_addr == max_addr)&&(extra_rd_en))
             extra_rd_en <= 1'b0       ;
           else
             extra_rd_en <= extra_rd_en;

           if(ds2_x_fs)
            fl_r <= 1'b1 ;
           else if ((!ram_sw[NO_RAM-1]) && (rd_flag))
            fl_r <= 1'b0 ;
           else
            fl_r <= fl_r ;

    end
  end
  //&EndPosedge;

   //Read Data shift register
   //Data path line shift register
   always @ (posedge clk)
    begin
      if(ll_r && rd_en_r)
        begin
          pix_y_r1[DSXW-1:0] <= sh_flag? rd[(2*DSXW)-1:DSXW ]     :rd[DSXW-1:0 ]       ;
          pix_y_r2[DSXW-1:0] <= sh_flag? rd[DSXW-1:0 ]            :rd[(2*DSXW)-1:DSXW ];
          pix_y_r3[DSXW-1:0] <= sh_flag? rd[DSXW-1:0 ]            :rd[(2*DSXW)-1:DSXW ];
        end
      else if(fl_r && rd_en_r )
        begin
          pix_y_r1 <= rd[DSXW-1:0 ]                   ;
          pix_y_r2 <= rd[DSXW-1:0 ]                   ;
          pix_y_r3 <= wr_data_r                       ;
        end
      else if(rd_en_r)
        begin
          pix_y_r1 <= sh_flag ? rd[DSXW-1:0 ]       : rd[(2*DSXW)-1:DSXW ] ;
          pix_y_r2 <= sh_flag ? rd[(2*DSXW)-1:DSXW ]: rd[DSXW-1:0 ]        ;
          pix_y_r3 <= wr_data_r                                            ;
        end
      else
        begin
          pix_y_r1 <= pix_y_r1                        ;
          pix_y_r2 <= pix_y_r2                        ;
          pix_y_r3 <= pix_y_r3                        ;
        end
    end

   assign pix_y_bus[(BLOCK*DSXW)-1:0] = {pix_y_r3,pix_y_r2,pix_y_r1} ;


   //&BeginInstance ds2_function ds2_y_function;
   //&Param BPP DSXW;
   //&Param DS_Y 1;
   //&Param COFF_W WW;
   //&Param MW MW;
   //&Param O_DW DSXW+4;
   //&Connect pixel pix_y_bus;
   //&Connect sum_out y_sum[DSXW+5:0];
   //&EndInstance;
   //FILE: ds2_function.v
   ds2_function # (
       .BPP     (DSXW),
       .COFF_W  (WW),
       .DS_Y    (1),
       .MW      (MW),
       .O_DW    (DSXW+4)
   ) ds2_y_function (
       .pixel    (pix_y_bus[3*DSXW-1:0]),
       .sum_out  (y_sum[DSXW+5:0]),
       .mode     (mode[MW-1:0]),
       .weight   (weight[WW-1:0]),
       .clk      (clk)
   );

   assign y_sum_int[DSXW+5:0] = ( mode_r == {MW{1'b0}} ) ? y_sum :{{8{y_sum[DSXW+5]}},y_sum[DSXW+5:8]};


   //&BeginInstance generic_rnd_off_sat u_ds2_y_rnd_off_sat;
   //&Param IN_DW DSXW+6;
   //&Param OUT_DW 9;
   //&Param OUT_MSB 8;
   //&Param OUT_LSB 0;
   //&Param ADD_ROUND 0;
   //&Connect data_in y_sum_int;
   //&Connect data_out dsx2_yp[BPP:0];
   //&EndInstance;
   //FILE: ./libs/generic_rnd_off_sat.v
   generic_rnd_off_sat # (
       .OUT_MSB    (8),
       .OUT_LSB    (0),
       .OUT_DW     (9),
       .IN_DW      (DSXW+6),
       .ADD_ROUND  (0)
   ) u_ds2_y_rnd_off_sat (
       .clk       (clk),
       .data_out  (dsx2_yp[BPP:0]),
       .data_in   (y_sum_int[DSXW+6-1:0])
   );

   assign ds_y_lv_w = (rd_flag_r &(ds2_x_lv_r)) | ll_r     ;

  //&Posedge;
  always @ (posedge clk or negedge rst_n) begin
    if (~rst_n) begin
      ds_y_pv_2r <= 1'b0;
      ds_y_lv_sr <= {DS_Y_PP{1'b0}};
      lv_mask_r <= 1'b0;
      ds_y_fv_r <= 1'b0;
      ds_y_lv_2r <= 1'b0;
      ds_y_lv_r <= 1'b0;
      frame_end_r <= 1'b0;
      ds_y_pv_r <= 1'b0;
      ds_y_fv_sr <= {DS_Y_PP{1'b0}};
      ds_y_pv_sr <= {DS_Y_PP{1'b0}};
      start_y <= 1'b0;
      ds_y_fv_2r <= 1'b0;
      lv_end <= 1'b0;
    end
    else begin
           ds_y_pv_r      <=  rd_en_r                                                      ;
           ds_y_lv_r      <=  ds_y_lv_w                                                    ;
           ds_y_fv_r      <=  (~rd_flag_r&rd_flag) ^ (~ll_r & ll_r_1d)^ ds_y_fv_r          ;
           start_y        <=  ((mode_r==3'd0)|(mode_r==3'd3)|(mode_r==3'd4))               ;
           lv_end         <=  ds_y_fv_r & ( ds_y_lv_r & (~(ds_y_lv_w)))                    ;
           lv_mask_r      <=  frame_end_r? 1'b0 : lv_end^lv_mask_r                         ;
           ds_y_pv_2r     <=  start_y ? ds_y_pv_r & lv_mask_r  : ds_y_pv_r & (~lv_mask_r)  ;
           ds_y_lv_2r     <=  start_y ? ds_y_lv_r & lv_mask_r  : ds_y_lv_r & (~lv_mask_r)  ;
           ds_y_fv_2r     <=  start_y ? ds_y_fv_r              : ds_y_fv_r                 ;
           ds_y_pv_sr[DS_Y_PP-1:0]     <= {ds_y_pv_sr[DS_Y_PP-2:0],ds_y_pv_2r   }                      ;
           ds_y_lv_sr[DS_Y_PP-1:0]     <= {ds_y_lv_sr[DS_Y_PP-2:0],ds_y_lv_2r   }                      ;
           ds_y_fv_sr[DS_Y_PP-1:0]     <= {ds_y_fv_sr[DS_Y_PP-2:0],ds_y_fv_2r   }                      ;
           frame_end_r    <= ds_y_fv_sr[DS_Y_PP-1] & (~ds_y_fv_sr[DS_Y_PP-2])             ;
    end
  end
  //&EndPosedge;

    assign ds_out_lv =  ds_y_lv_sr[DS_Y_PP-1] ;
    assign ds_out_fv =  ds_y_fv_sr[DS_Y_PP-1] ;
    assign ds_out_pv =  ds_y_pv_sr[DS_Y_PP-1] ;
    assign ds_out_p[BPP-1:0]  =  dsx2_yp   [BPP-1:0  ] ;


endmodule //dsx2
