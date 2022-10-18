
input a,b,c;
output d;
 
reg stage1, stage2, p,q;
 
always @(posedge clk)
begin    
   add (a, b, p);
   stage1 <= p;   
   add (stage1, c, q);
   stage2 <= q;
end
 
assign d = stage2;
 
task automatic add (input x, y, output z);
   begin
     z = x + y;
   end
endtask
endmodule
