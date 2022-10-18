//&module ( parameter ROW = 8, parameter COL = 4, parameter WIDTH = 10);
module test_forloop_multiple_array # (
  parameter ROW = 8,
            parameter COL = 4,
            parameter WIDTH = 10
) (
  input        [ROW_SIZE-1:0][COL_SIZE-1:0][WIDTH-1:0]  array1,
  input        [COL_SIZE-1:0][ROW_SIZE-1:0][WIDTH-1:0]  array2
); 
// generate0 ( array1, array2, array3);

// parameter ROW = 8;
// parameter COL = 4;
// parameter WIDTH = 10;

// input [ROW-1:0][COL-1:0][WIDTH-1:0] array1;
// input [COL-1:0][ROW-1:0][WIDTH-1:0] array2;
// output reg [7:0][7:0][9:0] array3;





localparam ROW_SIZE =  2^^ROW;
localparam COL_SIZE =  2^^COL;

always@* begin
for (int i = 0; i < ROW_SIZE ;i=i+1)
   for (int j = 0; j < COL_SIZE ;j=j+1)
      array3 [i][j][WIDTH-1:0] = 0;
for (int i = 0; i < ROW_SIZE;i=i+1)
   for (int j = 0; j < COL_SIZE;j=j+1)
      array3 [i][j][WIDTH-1:0] = array3 [i][j][WIDTH-1:0] + array1 [i][j][WIDTH-1:0] * array2[j][i][WIDTH-1:0];
end


endmodule


