import time
from hub75 import Hub75
import random

# Create an instance of the Hub75 display.
display = Hub75()


display.draw_line(32,32,56,18,0,1,0)
display.draw_line(32,32,36,8,0,1,1)
display.draw_circle(31,31,31,0,0,1)
display.draw_box(14,39,37,11,0,1,0,1) # x,y,width,height,filled (0 or 1), r,g,b (either 0 or 1)
display.draw_text(15,41,"font_8x5","12:22:34",1,1,1,1) # x,y,font to use,text to draw, r,g,b, OPTIONAL 1 = rainbow
display.draw_text(10,11,"font_8x5","¬  `",0,1,1)


