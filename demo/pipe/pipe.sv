////////////////////////////////////////////////////////////////////////////////////
// Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved.
// The following information is considered proprietary and confidential to Facebook,
// and may not be disclosed to any third party nor be used for any purpose other
// than to full fill service obligations to Facebook
////////////////////////////////////////////////////////////////////////////////////

//&Module;
module pipe (
  output  logic             ss_i_stall,
  output  logic             ss_o_valid,
  output  logic     [31:0]  ss_o_data,
  output  logic     [31:0]  sv_o_data,
  output  logic             svs_o_valid,
  output  logic     [31:0]  svs_o_data,
  output  logic             ssv_i_stall,
  output  logic     [31:0]  ssv_o_data,
  input   logic             ss_i_valid,
  input   logic             ss_o_stall,
  input   logic             clk,
  input   logic             arst_n,
  input   logic     [31:0]  ss_i_data,
  input   logic             sv_o_stall,
  input   logic             sv_i_valid,
  input   logic     [31:0]  sv_i_data,
  input   logic             svs_i_valid,
  input   logic     [31:0]  svs_i_data,
  input   logic             svs_o_stall,
  input   logic             ssv_i_valid,
  input   logic     [31:0]  ssv_i_data,
  input   logic             ssv_o_stall
); 


//&Logics;
logic             set_ss_i_skid_valid;
logic             clr_ss_i_skid_valid;
logic             ss_i_skid_valid_nxt;
logic             ss_i_skid_valid;
logic     [31:0]  ss_i_skid_data;
logic             sv_i_stall;
logic             sv_o_valid;
logic             svs_i_stall;
logic     [31:0]  svs_i_pipe_data;
logic             svs_i_pipe_valid;
logic             set_svs_i_skid_valid;
logic             clr_svs_i_skid_valid;
logic             svs_i_skid_valid_nxt;
logic             svs_i_skid_valid;
logic             svs_i_pipe_stall;
logic     [31:0]  svs_i_skid_data;
logic             set_ssv_i_skid_valid;
logic             clr_ssv_i_skid_valid;
logic             ssv_i_skid_valid_nxt;
logic             ssv_i_skid_valid;
logic     [31:0]  ssv_i_skid_data;
logic             ssv_i_pipe_valid;
logic     [31:0]  ssv_i_pipe_data;
logic             ssv_i_pipe_stall;
logic             ssv_o_valid;


// split with stall
//&Pipe(ss, 32, ss_i, ss_o);


assign set_ss_i_skid_valid = ss_i_valid & !ss_i_skid_valid & ss_o_stall;
assign clr_ss_i_skid_valid = ss_i_skid_valid & !ss_o_stall;
assign ss_i_skid_valid_nxt = set_ss_i_skid_valid? 1'b1 : clr_ss_i_skid_valid? 1'b0 : ss_i_skid_valid;

always_ff @ (posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        ss_i_skid_valid <= 1'b0;
    end
    else begin
        ss_i_skid_valid <= ss_i_skid_valid_nxt;
    end
end

assign ss_i_stall = ss_i_skid_valid;

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        ss_i_skid_data <= '0;
    end
    else if ( set_ss_i_skid_valid ) begin
        ss_i_skid_data[31 :0] <= ss_i_data[31 :0];
    end
end

assign ss_o_valid = ss_i_skid_valid ? 1'b1 : ss_i_valid;
assign ss_o_data[31 :0] = ss_i_skid_valid ? ss_i_skid_data : ss_i_data;




// split with valid/data
//&Pipe(sv, 32, sv_i, sv_o);


assign sv_i_stall = (sv_o_valid & sv_o_stall);

always_ff @(posedge clk or negedge arst_n ) begin
    if (!arst_n ) begin
        sv_o_data <= '0;
    end
    else if ( sv_i_valid & !sv_i_stall ) begin
        sv_o_data[31 :0] <= sv_i_data[31 :0];
    end
end

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        sv_o_valid <= 1'b0;
    end
    else if ( !sv_i_stall ) begin
        sv_o_valid <= sv_i_valid;
    end
end




// split first valid/data then stall
//&Pipe(svs, 32, svs_i, svs_o);


assign svs_i_stall = (svs_i_pipe_valid & svs_i_pipe_stall);

always_ff @(posedge clk or negedge arst_n ) begin
    if (!arst_n ) begin
        svs_i_pipe_data <= '0;
    end
    else if ( svs_i_valid & !svs_i_stall ) begin
        svs_i_pipe_data[31 :0] <= svs_i_data[31 :0];
    end
end

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        svs_i_pipe_valid <= 1'b0;
    end
    else if ( !svs_i_stall ) begin
        svs_i_pipe_valid <= svs_i_valid;
    end
end



assign set_svs_i_skid_valid = svs_i_pipe_valid & !svs_i_skid_valid & svs_o_stall;
assign clr_svs_i_skid_valid = svs_i_skid_valid & !svs_o_stall;
assign svs_i_skid_valid_nxt = set_svs_i_skid_valid? 1'b1 : clr_svs_i_skid_valid? 1'b0 : svs_i_skid_valid;

always_ff @ (posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        svs_i_skid_valid <= 1'b0;
    end
    else begin
        svs_i_skid_valid <= svs_i_skid_valid_nxt;
    end
end

assign svs_i_pipe_stall = svs_i_skid_valid;

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        svs_i_skid_data <= '0;
    end
    else if ( set_svs_i_skid_valid ) begin
        svs_i_skid_data[31 :0] <= svs_i_pipe_data[31 :0];
    end
end

assign svs_o_valid = svs_i_skid_valid ? 1'b1 : svs_i_pipe_valid;
assign svs_o_data[31 :0] = svs_i_skid_valid ? svs_i_skid_data : svs_i_pipe_data;




// split first stall then valid/data
//&Pipe(ssv, 32, ssv_i, ssv_o);


assign set_ssv_i_skid_valid = ssv_i_valid & !ssv_i_skid_valid & ssv_i_pipe_stall;
assign clr_ssv_i_skid_valid = ssv_i_skid_valid & !ssv_i_pipe_stall;
assign ssv_i_skid_valid_nxt = set_ssv_i_skid_valid? 1'b1 : clr_ssv_i_skid_valid? 1'b0 : ssv_i_skid_valid;

always_ff @ (posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        ssv_i_skid_valid <= 1'b0;
    end
    else begin
        ssv_i_skid_valid <= ssv_i_skid_valid_nxt;
    end
end

assign ssv_i_stall = ssv_i_skid_valid;

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        ssv_i_skid_data <= '0;
    end
    else if ( set_ssv_i_skid_valid ) begin
        ssv_i_skid_data[31 :0] <= ssv_i_data[31 :0];
    end
end

assign ssv_i_pipe_valid = ssv_i_skid_valid ? 1'b1 : ssv_i_valid;
assign ssv_i_pipe_data[31 :0] = ssv_i_skid_valid ? ssv_i_skid_data : ssv_i_data;



assign ssv_i_pipe_stall = (ssv_o_valid & ssv_o_stall);

always_ff @(posedge clk or negedge arst_n ) begin
    if (!arst_n ) begin
        ssv_o_data <= '0;
    end
    else if ( ssv_i_pipe_valid & !ssv_i_pipe_stall ) begin
        ssv_o_data[31 :0] <= ssv_i_pipe_data[31 :0];
    end
end

always_ff @(posedge clk or negedge arst_n ) begin
    if ( !arst_n ) begin
        ssv_o_valid <= 1'b0;
    end
    else if ( !ssv_i_pipe_stall ) begin
        ssv_o_valid <= ssv_i_pipe_valid;
    end
end




endmodule
