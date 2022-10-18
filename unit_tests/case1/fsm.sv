//1. Indent problem for state <= next;


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
 DLY = 2'b10,
 DONE = 2'b11,
 XXX = 'x } state_e0;
endpackage

import fsm1_pkg::*; 
import fsm2_pkg::*;

module fsm1_2x 
(
output logic rd, ds,
input logic go, ws, clk, rst_n);


state_e0 state, next;
always_ff @(posedge clk, negedge rst_n) 
 if (!rst_n) begin
    state <= IDLE;
 end 
 else begin
    state <= next;
 end

always_comb begin 
next = XXX;
rd ='0;
ds ='0; 
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


