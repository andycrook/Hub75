# hub75.py for raspberry pi pico

# Andy Crook 2025 https://github.com/andycrook

# acknowledgement of https://github.com/benevpi/PicoPythonHub75

# This will drive a 64x64 led matrix using hub75 encoding.
# 8 colors available through rgb either 0 or 1
# 000 Black
# 100 Red
# 010 Green
# 001 Blue
# 110 Yellow
# 101 Purple
# 011 Cyan
# 111 White



import rp2
import time
from machine import Pin
import array
import _thread
import fonts as FONT
import random

#Wiring:

#     /-----\
# R0  | o o | G0
# B0  | o o | GND
# R1  | o o | G1
# B1  \ o o | E
# A   / o o | B
# C   | o o | D
# CLK | o o | STB
# OEn | o o | GND
#     \-----/

# RGB pins start at GPIO2 ---> GPIO7 for R0 G0 B0 R1 G1 B1
# ROW select pins start at GPIO8 ---> GPIO12  for ABCDE
# CLK 13
# LAT 14
# OEn 15




# ---------------------------------------------------------------------------
# PIO Programs
# ---------------------------------------------------------------------------

@rp2.asm_pio(
    out_shiftdir=1,
    autopull=True,
    pull_thresh=24,
    out_init=(
        rp2.PIO.OUT_HIGH, rp2.PIO.OUT_LOW, rp2.PIO.OUT_HIGH,
        rp2.PIO.OUT_HIGH, rp2.PIO.OUT_HIGH, rp2.PIO.OUT_HIGH
    ),
    sideset_init=(rp2.PIO.OUT_LOW,)
)
def data_hub75():
    # This program clocks out 24 bits (4 pixels × 6 bits per pixel)
    out(pins, 6)
    nop()        .side(1)
    nop()        .side(0)
    out(pins, 6)
    nop()        .side(1)
    nop()        .side(0)
    out(pins, 6)
    nop()        .side(1)
    nop()        .side(0)
    out(pins, 6)
    nop()        .side(1)
    nop()        .side(0)
    wrap()


@rp2.asm_pio(
    out_shiftdir=1,
    autopull=False,
    out_init=(
        rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW,
        rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW
    ),
    sideset_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW)
)
def row_hub75():
    # This program pulls a value to set the row, then toggles the latch.
    wrap_target()
    pull()                   # pull in the row number (not used further here)
    nop()     .side(2)       # set row bits (sideset)
    out(pins, 5)   [2]       # output 6 bits (dummy data)
    nop()      .side(1)      # pulse latch high
    nop()      .side(0)      # bring latch low again
    nop()      .side(0)
    wrap()

# ---------------------------------------------------------------------------
# Hub75 Class Definition
# ---------------------------------------------------------------------------

class Hub75:
    def __init__(self,
                 data_pin_start=2,
                 clock_pin=13,
                 latch_pin_start=14,
                 row_pin_start=8,
                 num_rows=32,        # each “row” in our buffer represents two physical scanlines
                 blocks_per_row=16   # each block covers 4 pixels horizontally (4*6 = 24 bits)
                 ):
        # Save display configuration
        self.num_rows = num_rows      # 32 rows in the buffer (64 physical scanlines)
        self.blocks_per_row = blocks_per_row
        self.buf_size = self.num_rows * self.blocks_per_row

        self.width =64
        self.height =64

        # Create two buffers for double buffering.
        self.buffer1 = array.array("I", [0] * self.buf_size)
        self.buffer2 = array.array("I", [0] * self.buf_size)
        self.draw_buffer = self.buffer1   # draw_buffer is where set_pixel writes
        self.frame_buffer = self.buffer2  # frame_buffer is what the refresh thread sends out

        # Set up the PIO State Machines:
        self.sm_data = rp2.StateMachine(0, data_hub75,
                                        out_base=Pin(data_pin_start),
                                        sideset_base=Pin(clock_pin),
                                        freq=60_000_000)
        self.sm_row = rp2.StateMachine(1, row_hub75,
                                       out_base=Pin(row_pin_start),
                                       sideset_base=Pin(latch_pin_start),
                                       freq=60_000_000)

        self.sm_data.active(1)
        self.sm_row.active(1)
        #print("SETTING UP HUB75...")
        # Flag to control the refresh thread
        self.running = True
        _thread.start_new_thread(self._refresh, ())

    def _refresh(self):
        """
        Continuously send the frame_buffer data to the display.
        Each iteration sends one “row” (a pair of physical scanlines).
        After sending all rows, swap the frame and draw buffers.
        """
        
        row_index = 0
        while self.running:
            # Tell the row state machine which row we’re on.
            self.sm_row.put(row_index)

            # Each row consists of a series of 16 data blocks.
            base = row_index * self.blocks_per_row
            for i in range(self.blocks_per_row):
                val = self.frame_buffer[base + i]
                self.sm_data.put(val)

            row_index += 1
            if row_index >= self.num_rows:
                row_index = 0
                # copy back buffer to frame
                self.frame_buffer= self.draw_buffer
                
                
        
    def set_pixel(self, x, y, r, g, b):
        """
        Set the pixel at coordinate (x, y) to the given color.
        Coordinates are 0-indexed. The physical display is assumed to be 64×64:
          - x: 0..63
          - y: 0..63
        Because of the Hub75 multiplexing, each row in the buffer holds data for
        two physical scanlines:
          - For y in 0..31 (top half): the pixel’s color occupies bits [0..2]
          - For y in 32..63 (bottom half): the pixel’s color occupies bits [3..5]
        Each horizontal block covers 4 pixels (4×6 bits = 24 bits per block).
        Colors are specified as r, g, b (each 0 or 1).
        """
        # Check bounds (optional)
        if not (0 <= x < 64 and 0 <= y < 64):
            return  # or raise ValueError("Pixel coordinate out of range")

        block = x >> 2            # Integer division by 4

        y=y+1
        bit_offset = ((x % 4) * 6)
        if y > 32:          # bottom half: logical rows 33–64
            y = y - 33      # row 33 becomes 0, row 34 becomes 1, etc.
            bit_offset += 3   # use the upper 3 bits for the bottom half
        else:
            y = y - 1       # top half: logical row 1 becomes 0, row 32 becomes 31
        index = (y-2) * self.blocks_per_row + (x >> 2)

        # Create a 3-bit color from r, g, b
        color = (int(r) & 1) | ((int(g) & 1) << 1) | ((int(b) & 1) << 2)
        # Prepare mask to update only the 3 bits for this pixel.
        mask = 0b111 << bit_offset
        # Clear previous value and set the new color.
        self.draw_buffer[index] = (self.draw_buffer[index] & ~mask) | (color << bit_offset)



    def draw_box(self,x,y,w,h,filled,r,g,b):
        if filled==0:
            for i in range(x,x+w):
                self.set_pixel(i,y,r,g,b)
                self.set_pixel(i,y+h-1,r,g,b)
                
            for j in range(y,y+h):
                self.set_pixel(x,j,r,g,b)
                self.set_pixel(x+w-1,j,r,g,b)
        else:
            for i in range(x,x+w):
                for j in range(y,y+h):
                    self.set_pixel(i,j,r,g,b)

    def draw_line(self,x1,y1,x2,y2,r,g,b):
        x,y = x1,y1
        dx = abs(x2 - x1)
        dy = abs(y2 -y1)
        gradient = dy/float(dx)

        if gradient > 1:
            dx, dy = dy, dx
            x, y = y, x
            x1, y1 = y1, x1
            x2, y2 = y2, x2

        p = 2*dy - dx

        for k in range(2, dx + 2):
            if p > 0:
                y = y + 1 if y < y2 else y - 1
                p = p + 2 * (dy - dx)
            else:
                p = p + 2 * dy

            x = x + 1 if x < x2 else x - 1

            self.set_pixel(x,y,r,g,b)


    def draw_circle(self,x0,y0,radius,r,g,b):
        x = radius
        y = 0
        err = 0

        while x >= y:
            self.set_pixel(x0 + x, y0 + y,r,g,b)
            self.set_pixel(x0 + y, y0 + x,r,g,b)
            self.set_pixel(x0 - y, y0 + x,r,g,b)
            self.set_pixel(x0 - x, y0 + y,r,g,b)
            self.set_pixel(x0 - x, y0 - y,r,g,b)
            self.set_pixel(x0 - y, y0 - x,r,g,b)
            self.set_pixel(x0 + y, y0 - x,r,g,b)
            self.set_pixel(x0 + x, y0 - y,r,g,b)

            y += 1
            err += 1 + 2*y
            if 2*(err-x) + 1 > 0:
                x -= 1
                err += 1 - 2*x

    def rand_color(self):
        col = [0,0,0]
        while col[0]+col[1]+col[2]==0:
            col[0] = random.randint(0,1)
            col[1] = random.randint(0,1)
            col[2] = random.randint(0,1)
        return col
      
    def draw_text(self,x,y,font_name,char,r,g,b, *args):

        if not args:
            col_over = 0
        else:
            col_over= args[0]
        xx=0
        yy=0
        for ch in char:
            try:
                char_data = getattr(FONT,font_name)[ch]
            except:
                # char not found
                char_data = [0]
                xx=xx-2

            
            for byte in char_data:  # Iterate through each byte in the list
                xx=xx+1
                if x+xx>self.width-1:
                    y=y+8
                    xx=xx-64
                if y+yy>self.height-1:
                    yy=yy-72  # subtract 64 - the 8 pixels to wrap on the y.
                    
                for bit in range(8):  # Iterate over each bit (8 bits per byte)
                    bit_value = (byte >> (7 - bit)) & 1  # Extract bit from MSB to LSB
                    if bit_value ==1:
                        if col_over==0:
                            self.set_pixel(x+xx,y+yy+bit,r,g,b)
                        if col_over==1:
                            color = self.rand_color()  # get a random rgb for the pixel
                            r = color[0]
                            g = color[1]
                            b = color[2]
                            self.set_pixel(x+xx,y+yy+bit,r,g,b)
                        
            xx=xx+1 # space between characters

                    
    def clear(self):
        """
        Clear the drawing buffer (set all pixels to off).
        """
        for i in range(self.buf_size):
            self.draw_buffer[i] = 0
                    
                    
    def stop(self):
        """
        Stop the refresh thread and disable the state machines.
        """
        self.running = False
        self.sm_data.active(0)
        self.sm_row.active(0)
