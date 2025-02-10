from hub75 import Hub75
import random

# Create an instance of the Hub75 display.
display = Hub75()

# draw_text options:
#
# after r,g,b there are two more parameter arguments (optional)
# argument 1: color based
# 0 = default r g b
# 1 = individual pixels set to a random (non black) color
# 2 = whole text pixels set to a single random (non black) color
#
# argument 2: masking
# 0 = default - the background of the text is made black
# 1 = the background is not drawn, so text appears over other pixels
# 2 - 8 = the background is set to a color (2 = red, 3 = green etc)

try:
    while True:
        display.clear() # clear back buffer
        display.draw_line(32,32,56,18,0,1,0) # x1,y1,x2,y2,r,g,b
        display.draw_line(32,32,36,8,0,1,1) # x1,y1,x2,y2,r,g,b
        display.draw_circle(31,31,31,0,0,1) # x,y,radius,r,g,b
        display.draw_box(14,39,38,11,0,1,0,1) # x,y,width,height,filled (0 or 1), r,g,b (either 0 or 1)
        display.draw_text(15,41,"font_8x5","HUB 75 :)",1,1,1,0,0) # x,y,font to use,text to draw, r,g,b, OPTIONAL 0 = normal, 1 = rainbow, OPTIONAL 0 = black background, 1 = no background, 2 = red, 3 = green etc 
        display.draw_text(random.randint(0,45),random.randint(0,50),"font_8x5","¬",0,1,1,2,1) # x,y,font to use,text to draw, r,g,b, OPTIONAL 0 = normal, 1 = rainbow, OPTIONAL 0 = black background, 1 = no background, 2 = red, 3 = green etc
        display.draw_text(random.randint(0,45),random.randint(0,50),"font_8x5","`",0,1,1,1,1) # x,y,font to use,text to draw, r,g,b, OPTIONAL 0 = normal, 1 = rainbow, OPTIONAL 0 = black background, 1 = no background, 2 = red, 3 = green etc
        display.copy_back_buffer() # copy back buffer to draw buffer
        
except KeyboardInterrupt:
    pass
