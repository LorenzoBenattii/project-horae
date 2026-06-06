import os
import pygame

from config import *
from random import randint, sample, choice
from heapq import heappush, heappop


class Animal:
    def __init__(self, world_chunks : dict):
        self.world_chunks = world_chunks

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
        self.position_chunk, self.position_local = self._get_initial_position(Tile.PLAIN, Tile.FOREST)
        self.movement_target_chunk, self.movement_target_local = self._get_random_tile(Tile.PLAIN, Tile.FOREST)
        self.path = self.get_path(self.position_chunk, self.position_local, self.movement_target_chunk, self.movement_target_local)
        self.t = 0 # the progress from 0 to 1 when moving to one tile to the next
        self.speed = 0.05
        self.next_chunk, self.next_local = None, None
        


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
        TILE_W = 32 * SCALE
        TILE_H = 16 * SCALE
        half_w = TILE_W // 2
        half_h = TILE_H // 2
        TREE_OVERHEAD = 96
        origin_x = half_w  # = 16

        def tile_to_iso(chunk, local):
            chk_y, chk_x = chunk
            loc_y, loc_x = local
            
            x = (chk_x - chk_y) * half_w - origin_x + origin_x + (32 * CHUNK_SIZE) // 2 + loc_x * 16 - loc_y * 16
            y = (chk_x + chk_y) * half_h + loc_x * 8 + loc_y * 8 + TREE_OVERHEAD
            return x, y

        cur_x, cur_y = tile_to_iso(self.position_chunk, self.position_local)

        if self.next_chunk is not None:
            nxt_x, nxt_y = tile_to_iso(self.next_chunk, self.next_local)
            world_x = cur_x + (nxt_x - cur_x) * self.t
            world_y = cur_y + (nxt_y - cur_y) * self.t
        else:
            world_x, world_y = cur_x, cur_y

        draw_x = world_x - cam_x + half_w - self.image.get_width() // 2
        draw_y = world_y - cam_y - (self.image.get_height() - half_h)

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


    # -- Update -- #

    def update(self):
        self._handle_needs()
        self._update_animation_frame()
        self._move()      
    


class Stag(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)

class Badger(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)

class Boar(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)

class Wolf(Animal):
    def __init__(self, world_chunks):
        super().__init__(world_chunks)


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









