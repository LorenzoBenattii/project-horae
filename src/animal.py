import os
import pygame
import numpy as np
import random


from config import *
from random import randint, sample, choice
from heapq import heappush, heappop



class Animal:
    def __init__(self, world_chunks_raws : dict):
        self.world_chunks = world_chunks_raws
        self.animation_assets = {}
        self._load_assets()
        self.clock = pygame.time.Clock().tick(FPS)

        # -- Animations -- #

        self.animation_type = "idle"
        self.animation_direction = "north-east"
        self.animation_frame = 0
        self.animation_cooldown = 100
        self.animation_update_time = pygame.time.get_ticks()
        self.image = self.animation_assets[self.animation_type][self.animation_direction][self.animation_frame]


        # -- Needs -- #

        self.max_hunger = 400
        self.hunger = randint(self.max_hunger // 2, self.max_hunger)
        self.is_hungry = False
        self.max_thirst = 400
        self.thirst = randint(self.max_thirst // 2, self.max_thirst)
        self.is_thirsty = False


        # -- Movement -- #
        self.position_chunk, self.position_local = self._choose_starting_position()
        self.target_chunk, self.target_local = self._choose_target_position()
        self.can_move = True # If this ever becomes false then the Animal has no valid target within a 10 chunk radius and should be despawned
        self.path = self._get_path(self.position_chunk, self.position_local, self.target_chunk, self.target_local)
        self.next_chunk, self.next_local = None, None
        self.movement_progress = 0
        self.speed = 0.02
        self.movement_cooldown = 800
        self.is_movement_in_cooldown = False
        self.movement_update_time = pygame.time.get_ticks()
        



    def _load_assets(self) -> None:
        animal_path = os.path.join(ASSET_PATH_ANIMALS, self.__class__.__name__.lower())
        
        for anim_name in os.listdir(animal_path):
            animation_path = os.path.join(animal_path, anim_name)
            self.animation_assets[anim_name] = {}
            
            for direction in os.listdir(animation_path):
                img_path = os.path.join(animation_path, direction)
                out = []
                
                for img in os.listdir(img_path):
                    load_img = pygame.image.load(os.path.join(img_path, img)).convert_alpha()
                    load_img = pygame.transform.scale_by(load_img, SCALE)
                    out.append(load_img)
                
                self.animation_assets[anim_name][direction] = out


    # -- Animations -- #

    def _reset_animation(self) -> None:
        self.animation_frame = 0
        self.animation_update_time = pygame.time.get_ticks()
        self.image = self.animation_assets[self.animation_type][self.animation_direction][self.animation_frame]

    def _update_animation_frame(self) -> None:
        if pygame.time.get_ticks() - self.animation_update_time >= self.animation_cooldown:
            self.animation_update_time = pygame.time.get_ticks()
            self.animation_frame = (self.animation_frame + 1) % len(self.animation_assets[self.animation_type][self.animation_direction])
            self.image = self.animation_assets[self.animation_type][self.animation_direction][self.animation_frame]

    def _update_animation_direction(self, new_dir: str) -> None:
        self.animation_direction = new_dir
        self._reset_animation()

    def _update_animation_type(self, new_type: str) -> None:
        self.animation_type = new_type
        self._reset_animation()

    def draw(self, screen: pygame.Surface, camera_pos: tuple[int, int]) -> None:
        cam_x, cam_y = camera_pos

        half_w = TILE_W // 2
        half_h = TILE_H // 2

        def tile_to_iso(chunk, local):
            chk_y, chk_x = chunk
            loc_y, loc_x = local

            x = (chk_x - chk_y) * half_w + (32 * CHUNK_SIZE) // 2 + loc_x * 16 - loc_y * 16
            y = (chk_x + chk_y) * half_h + loc_x * 8 + loc_y * 8 + TREE_OVERHEAD
            return x, y

        
        cur_x, cur_y = tile_to_iso(self.position_chunk, self.position_local)

        
        world_x, world_y = cur_x, cur_y

        
        if self.next_chunk is not None:
            nxt_x, nxt_y = tile_to_iso(self.next_chunk, self.next_local)
            world_x = cur_x + (nxt_x - cur_x) * self.movement_progress
            world_y = cur_y + (nxt_y - cur_y) * self.movement_progress

        
        anchor_x, anchor_y = self.ANCHOR

        draw_x = world_x - cam_x - anchor_x
        draw_y = world_y - cam_y - anchor_y

        
        screen.blit(self.image, (draw_x, draw_y))

        

    # -- Needs -- #

    def _handle_needs(self) -> None:
        self.hunger -= 0.2
        self.thirst -= 0.2

        if self.thirst <= 0:
            self.thirst = 0
            self.is_thirsty = True

        if self.hunger <= 0:
            self.hunger = 0
            self.is_hungry = True


    # -- Movement -- #


    def _choose_starting_position(self) -> tuple[tuple[int, int], tuple[int, int]]:
        '''Returns chunk index and (y, x) within the chunk'''        
        while True:
            chunk_index = choice(list(self.world_chunks.keys()))
            chunk = self.world_chunks[chunk_index]
            coords = np.argwhere(chunk == Tile.PLAIN.value)

            if len(coords) > 0:
                #print("STARTING POSITION FOUND.", chunk_index, coords[0])
                y, x = coords[0]
                return chunk_index, (int(y), int(x))

    def _choose_target_position(self) -> tuple[tuple[int, int], tuple[int, int]]:
        ''' Returns chunk index and (y, x) within the chunk.
            Searches with iterative deepening bordering chunks to not explode the pathfinding.
        '''
        depth = 1
        cy, cx = self.position_chunk

        while True:
            searchable_chunks = set([
                (cy + dy * CHUNK_SIZE * depth, cx + dx * CHUNK_SIZE * depth)
                for dy, dx in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)]
            ])

            candidates = set()
            for chunk_index in searchable_chunks:
                if chunk_index == self.position_chunk:
                    continue
                if chunk_index not in self.world_chunks:
                    continue
                if np.any(self.world_chunks[chunk_index] == Tile.PLAIN.value):
                    candidates.add(chunk_index)

            if candidates:
                chunk_index = random.choice(list(candidates))
                chunk = self.world_chunks[chunk_index]
                coords = np.argwhere(chunk == Tile.PLAIN.value)
                y, x = coords[random.randint(0, len(coords) - 1)]
                #print("TARGET POSITION FOUND.", chunk_index, (int(y), int(x)))
                return chunk_index, (int(y), int(x))

            depth += 1

            if depth == 10:
                self.can_move = False
                break

        return self.position_chunk, self.position_local

    def _get_heuristic(self,    chunk_position : tuple[int, int], 
                                local_position : tuple[int, int], 
                                target_chunk   : tuple[int, int], 
                                target_local : tuple[int, int]) -> int:
        ''' Manhattan Distance'''
        cy, cx = chunk_position
        ly, lx = local_position
        tcy, tcx = target_chunk
        tly, tlx = target_local

        
        y1 = cy * CHUNK_SIZE + ly
        x1 = cx * CHUNK_SIZE + lx

        y2 = tcy * CHUNK_SIZE + tly
        x2 = tcx * CHUNK_SIZE + tlx



        return abs(y1 - y2) + abs(x1 - x2)
            
    def _get_path(self, start_chunk: tuple[int, int],
                        start_local: tuple[int, int],
                        target_chunk:tuple[int, int],
                        target_local:tuple[int, int]) -> list:
        '''
        A* with water as unwalkable tiles.
        Returns empty list if unreachable.
        '''

        if start_chunk == target_chunk and start_local == target_local:
            return [(start_chunk, start_local)]
        
        
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]

        open_set = []
        heappush(open_set, (
            self._get_heuristic(start_chunk, start_local, target_chunk, target_local),
            0, start_chunk, start_local, [(start_chunk, start_local)]))
        
        visited = set()

        while open_set:
            f, g, chunk, local, path = heappop(open_set)

            if (chunk, local) in visited:
                continue

            visited.add((chunk, local))

            if chunk == target_chunk and local == target_local:
                return path
            
            cy, cx = chunk
            y, x = local

            for dy, dx in directions:
                ny, nx = y + dy, x + dx
                nchunk = (cy, cx)

                if ny < 0:
                    nchunk = (cy - CHUNK_SIZE, cx)
                    ny += CHUNK_SIZE
                elif ny >= CHUNK_SIZE:
                    nchunk = (cy + CHUNK_SIZE, cx)
                    ny -= CHUNK_SIZE

                if nx < 0:
                    nchunk = (nchunk[0], cx- CHUNK_SIZE) #not ny cause it could be changed by previous check
                    nx += CHUNK_SIZE
                
                elif nx >= CHUNK_SIZE:
                    nchunk = (nchunk[0], cx + CHUNK_SIZE)
                    nx -= CHUNK_SIZE

                if (nchunk, (ny, nx)) in visited:
                    continue

                if nchunk not in self.world_chunks:
                    continue

                if self.world_chunks[nchunk][ny, nx] in WATER_TILES or self.world_chunks[nchunk][ny, nx] == Tile.FOREST.value:
                    continue

                new_g = g+1
                heappush(   open_set, 
                            (new_g + self._get_heuristic(nchunk, (ny, nx), target_chunk, target_local),
                            new_g,
                            nchunk,
                            (ny, nx),
                            path + [(nchunk, (ny, nx))]))
                
        return []

    def _move(self) -> None:
        if self.next_chunk is None:
            if not self.path:
                self._update_animation_type("idle")
                if not self.is_movement_in_cooldown:
                    self.is_movement_in_cooldown = True
                    self.movement_update_time = pygame.time.get_ticks()
                return

            self.next_chunk, self.next_local = self.path.pop(0)
            
            self._update_animation_type("walk")

            cy, cx = self.position_chunk
            ly, lx = self.position_local
            ncy, ncx = self.next_chunk
            ny, nx = self.next_local

            dy = (ncy * CHUNK_SIZE + ny) - (cy * CHUNK_SIZE + ly)
            dx = (ncx * CHUNK_SIZE + nx) - (cx * CHUNK_SIZE + lx)

            match (dx, dy):
                case (1, 0):  direction = "south-east"
                case (0, 1):  direction = "south-west"
                case (-1, 0): direction = "north-west"
                case (0, -1): direction = "north-east"
                case _:       direction = self.animation_direction

            if direction != self.animation_direction:
                self._update_animation_direction(direction)

        self.movement_progress += self.speed

        if self.movement_progress >= 1.0:
            self.position_chunk = self.next_chunk
            self.position_local = self.next_local
            self.next_chunk, self.next_local = None, None
            self.movement_progress = 0
            


    # -- Update -- #

    def update(self):

        if self.is_movement_in_cooldown: #TODO this can generate a thread to calculate path so animation runs smoothly
            if pygame.time.get_ticks() - self.movement_update_time >= self.movement_cooldown:
                self.target_chunk, self.target_local = self._choose_target_position()
                self.path = self._get_path(self.position_chunk, self.position_local, self.target_chunk, self.target_local)
                self.is_movement_in_cooldown = False


        self._handle_needs()
        self._update_animation_frame()
        self._move()

        
            
                    
    


class Stag(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)
        self.ANCHOR = (8, 10)

class Badger(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)
        self.ANCHOR = ()

class Boar(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)
        self.ANCHOR = (22, 22)
class Wolf(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)
        self.ANCHOR = (31, 40)

class AnimalManager:
    '''
    Class that assigns animals to chunks
    '''
    def __init__(self, world_chunks: dict):
        self.chunks = world_chunks
        self.animals = set()

    def _reset_chunks_animals(self) -> None:
        for chunk in self.chunks.values():
            chunk.animals = set()

    def _update_chunks(self) -> None:
        self._reset_chunks_animals()

        animal: Animal
        for animal in self.animals:
            self.chunks[animal.position_chunk].animals.add(animal)



if __name__ == "__main__":
    screen = pygame.display.set_mode((SCREENW, SCREENH))
    

    a = Stag()









