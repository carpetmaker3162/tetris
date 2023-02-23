import sys
import threading
import random
import os
import termios
import time
from utils import getch
from utils import Fmt
from utils import Controls as Ctrls

WINDOWS = os.name == "nt"
fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)

event_queue = []
BLOCK = "  "

def colored_block(ansi):
    return f"{ansi}{BLOCK}{Fmt.end}"

TEXTURE = {
    0: ". ",
    1: colored_block(Fmt.red_highlight_text),
    2: colored_block(Fmt.yellow_highlight_text),
    3: colored_block(Fmt.green_highlight_text),
    4: colored_block(Fmt.cyan_highlight_text),
    5: colored_block(Fmt.blue_highlight_text),
    6: colored_block(Fmt.magenta_highlight_text),
    7: colored_block(Fmt.light_gray_highlight_text),
    8: colored_block(Fmt.gray_highlight_text),
}

# 0001111000

# 0000110000
# 0000110000

# 0000100000
# 0000100000
# 0000110000

# 0000100000
# 0000110000
# 0000010000

# 0000111000
# 0000010000

def log(content="", end: str="\n"):
    with open("debug_logs.txt", "a") as f:
        f.write(str(content) + end)

BLOCKS = {
    0: [(0, 3), (0, 4), (0, 5), (0, 6)], # straight
    1: [(0, 4), (0, 5), (1, 4), (1, 5)], # square
    2: [(0, 4), (1, 4), (2, 4), (2, 5)], # L
    3: [(0, 4), (1, 4), (1, 5), (2, 5)], # skew
    4: [(0, 4), (0, 5), (0, 6), (1, 5)], # T
}

def process_keyboard_events(q):
    while True:
        q.append(getch())

class Block:
    def __init__(self, block: int, color: int) -> None:
        assert block in range(1, 5)
        assert color in range(1, 9)

        self.squares = BLOCKS[block][:]
        self.id = block
        self.color = color
    
    @classmethod
    def random(cls):
        return cls(random.randrange(1, 5), random.randrange(1, 9))

class Game:
    def __init__(self) -> None:
        self.width = 10
        self.height = 20
        self.grid = [[0 for i in range(self.width)] for i in range(self.height)]
        self.active_block = Block.random() # collection of row #'s and col #'s
        self.next_block = Block.random()
        for br, bc in self.active_block.squares:
            self.grid[br][bc] = self.active_block.color

    def refresh_scene(self):
        if not self.block_can_fall(self.grid, self.active_block):
            self.active_block = Block(self.next_block.id, self.next_block.color)
            self.next_block = Block.random()
            log(self.active_block.squares, end="\n\n")
            self.draw_block(self.active_block)
        else:
            for br, bc in self.active_block.squares:
                self.grid[br][bc] = 0
            self.grid = self.apply_gravity(self.grid, self.active_block)
            self.draw_block(self.active_block)
    
    def move_block(self, block: Block, newpos: list=None, displacement: tuple=(0, 0)):
        dy, dx = displacement
        
        if newpos is None:
            new_position = block.squares[:]
        else:
            new_position = newpos[:]
        
        for i in range(len(new_position)):
            r, c = new_position[i]
            new_position[i] = (r+dy, c+dx)
        
        for r, c in new_position:
            if not (0<=r<self.height and 0<=c<self.width):
                return -1
            elif self.grid[r][c] != 0 and (r, c) not in block.squares:
                return -1
        
        for r, c in block.squares:
            self.grid[r][c] = 0
        
        block.squares = new_position[:]
        return 0
    
    def draw_block(self, block: Block):
        for br, bc in block.squares:
            self.grid[br][bc] = block.color
    
    def block_can_fall(self, grid, active_block: Block):
        for br, bc in active_block.squares:
            if br == self.height - 1:
                return False
            elif grid[br+1][bc] != 0 and all([br > r for r, c in active_block.squares if c == bc and r != br]):
                return False
        return True

    def apply_gravity(self, grid, active_block: Block): # apply gravity to a grid
        new_grid = [x[:] for x in grid[:]]
        # new_block = [x[:] for x in active_block.squares[:]]
        for i, block in enumerate(active_block.squares):
            active_block.squares[i] = (active_block.squares[i][0] + 1, active_block.squares[i][1])
        
        return new_grid
    
    def print(self):
        print("\033[H", end="\n\r")
        buf = str()
        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                buf += TEXTURE[cell]
            buf += "\n\r"
        print(buf, end="")

if __name__ == "__main__":
    try:
        last_update = 0
        thread = threading.Thread(target=process_keyboard_events, args=(event_queue,), daemon=True)
        thread.start()

        tetris = Game()

        while True:
            if event_queue:
                key = event_queue.pop(0)
                id = ord(key)
                curr_blockpos = tetris.active_block.squares
                if id == 3:
                    break
                elif id == Ctrls.LEFT:
                    tetris.move_block(tetris.active_block, displacement=(0, -1))
                elif id == Ctrls.RIGHT:
                    tetris.move_block(tetris.active_block, displacement=(0, 1))
                elif id == Ctrls.DOWN:
                    tetris.move_block(tetris.active_block, displacement=(1, 0))
                elif id == Ctrls.DROP:
                    while tetris.move_block(tetris.active_block, displacement=(1, 0)) != -1:
                        pass
                tetris.draw_block(tetris.active_block)
                
                sys.stdout.flush()
            
            if time.time() - last_update > 0.1:
                tetris.refresh_scene()
                tetris.print()
                last_update = time.time()

    except Exception as e:
        raise e
    finally:
        if not WINDOWS:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
