
//1. Indent problem for state <= next;
//2. give size of state???

// from Finite State Machine (FSM) Design & Synthesis using SystemVerilog - Part I
// Clifford E. Cummings Sunburst Design, Inc. Provo, UT, USA
// www.sunburst‐design.com
// Heath Chambers

package fsm1_pkg;
 typedef enum logic [1:0] {IDLE = 2'b00,
 READ = 2'b01,
 DLY = 2'b11,
 DONE = 2'b10,
 XXX = 'x } state_e0;
endpackage

package fsm2_pkg;
 typedef enum logic [1:0] {IDLE = 2'b00,
 READ = 2'b01,
 DLY = 2'b11,
 DONE = 2'b10,
 XXX = 'x } state_e1;
endpackage



import fsm1_pkg::*;
import fsm2_pkg::*;

//&module; // why comment out state_e line
module test_fsm (
  output  logic        rd,
  output  logic        ds,
  input   logic        clk,
  input   logic        rst_n,
  input   logic        go,
  input   logic        ws
); 

state_e1 state, next;
//&Logics;

//&Clock clk;
//&AsyncReset rst_n;

//&Posedge;
always_ff @ (posedge clk or negedge rst_n) begin
  if (~rst_n) begin
    state <= IDLE;
  end
  else begin
state <=next ;
  end
end
//&EndPosedge;

always_comb begin
next = XXX;
rd =2'0;
ds =2'0;
case (state)
    IDLE : begin
           if (go) next = READ;
           else next = IDLE; //@ LB
           end
    READ : begin
             rd = '1;
             next = DLY;
           end
    DLY  : begin
           rd = '1;
           if (!ws) next = DONE;
           else     next = READ;
         end
  DONE : begin
        ds = '1;
        next = DLY;
         end
  default: begin
           ds = 'x;
           rd = 'x;
end endcase
  end

endmodule


