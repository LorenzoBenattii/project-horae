import numpy as np
import numpy.typing as npt
import pygame

from config import *
from noise import pnoise2
from collections import deque

class Chunk:
    def __init__(self, index: tuple[int, int], seed: int, background_assets : dict):
        self.index = index
        self.chunk_size = CHUNK_SIZE
        self.biome = Biome.EMPTY
        self.seed = seed
        self.background_assets = background_assets



        # -- Numpy Arrays -- #
        self.chunk : npt.NDArray = np.full((self.chunk_size, self.chunk_size), Tile.EMPTY.value)
        self.chunk_raw : npt.NDArray = np.full((self.chunk_size, self.chunk_size), Tile.EMPTY.value)
        self.tree_probs : npt.NDArray = np.random.random((self.chunk_size, self.chunk_size))
        self.tree_types : npt.NDArray = np.random.randint(0, 10, (self.chunk_size, self.chunk_size))
        
        

        # -- Pygame Surfaces -- #
        self.image : dict = {"summer" : [], "autumn" : [], "winter" : []}
        self.tree  : dict = {"summer" : None, "autumn" : None, "winter" : None}

        self.biome_offset = (self.seed * 0.001, self.seed * 0.002)
        self.tile_offset = (self.seed * 0.003, self.seed * 0.007)


        self.animals = set()

        self._generate_chunk()

    
    # -- Noise Helpres -- #

    def _biome_noise(self, wx: float, wy: float) -> float:
        ox, oy = self.biome_offset

        warp_strength = 18.0 #20-30 range means more fractal coast. #8-12 range gentler coastal curves
        warp_x = pnoise2(wx * 0.015 + ox + 1.7, wy * 0.015 + oy + 9.2, octaves=2)
        warp_y = pnoise2(wx * 0.015 + ox + 5.3, wy * 0.015 + oy + 3.1, octaves=2)

        return pnoise2(
            (wx + warp_x * warp_strength) * BIOME_SCALE + ox,
            (wy + warp_y * warp_strength) * BIOME_SCALE + oy,
            octaves=5,
            persistence=0.55,
            lacunarity=2.1
        )
        
    def _tile_noise(self, wx: float, wy: float) -> float:
        '''
        Fine scale noise that decides individual tiles
        '''
        ox, oy = self.tile_offset
        return pnoise2(
            wx * TILE_SCALE + ox,
            wy * TILE_SCALE + oy,
            octaves = 4,
            persistence = 0.5,
            lacunarity = 2.0
        )


    # -- Biome / Tile Mapping -- #

    def _noise_to_biome(self, value: float) -> Biome:
        if value < -0.05:   return Biome.OCEAN
        elif value < 0.05:  return Biome.PLAIN
        else:               return Biome.FOREST

    def _noise_to_tile(self, tile_value: float, biome_value: float) -> int:
        if biome_value < -0.05:      # OCEAN
            if tile_value < 0.30:    return Tile.WATER.value
            else:                    return Tile.PLAIN.value

        elif biome_value < 0.10:     # PLAIN
            if tile_value < -0.35:   return Tile.WATER.value
            elif tile_value < 0.15:  return Tile.PLAIN.value
            else:                    return Tile.FOREST.value

        else:                        # FOREST
            if tile_value < 0.0:     return Tile.PLAIN.value
            else:                    return Tile.FOREST.value


    # -- Chunk Generation -- #

    def _assign_biome(self) -> None:
        y0, x0 = self.index

        #sample noise at chunk center
        cx, cy = (x0 + self.chunk_size/2), (y0 + self.chunk_size/2)
        value = self._biome_noise(cx, cy)
        self.biome = self._noise_to_biome(value)

    def _generate_tiles(self) -> None:
        y0, x0 = self.index
        chunk = self.chunk

        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                wx, wy = x0 + x, y0 + y
                tile_value  = self._tile_noise(wx, wy)
                biome_value = self._biome_noise(wx, wy)
                chunk[y, x] = self._noise_to_tile(tile_value, biome_value)

        self.chunk = chunk

    def _generate_tree_probabilities(self) -> None:
        self.tree_probs = np.random.random((self.chunk_size, self.chunk_size))
        self.tree_types = np.random.randint(0, 10, (self.chunk_size, self.chunk_size))

    def _collapse_water(self, neighbor_chunks: dict[tuple[int,int], "Chunk"]) -> None:
        '''Classify raw WATER tiles into edge variants based on neighbors.'''
        WATER_VAL = Tile.WATER.value
        y0, x0 = self.index

        def get_tile(y, x) -> int:
            cy = (y0 + (y // self.chunk_size) * self.chunk_size
                if y >= self.chunk_size else
                y0 - self.chunk_size if y < 0 else y0)
            cx = (x0 + (x // self.chunk_size) * self.chunk_size
                if x >= self.chunk_size else
                x0 - self.chunk_size if x < 0 else x0)
            ly = y % self.chunk_size
            lx = x % self.chunk_size
            nidx = (cy, cx)
            if nidx == (y0, x0):
                t = int(self.chunk[ly, lx])
            elif nidx in neighbor_chunks:
                t = int(neighbor_chunks[nidx].chunk_raw[ly, lx])
            else:
                return Tile.PLAIN.value

            if t in (Tile.WATER_EXT.value, Tile.WATER_INT.value,
                    Tile.WATER_LEFT.value, Tile.WATER_RIGHT.value,
                    Tile.WATER_MID.value):
                return WATER_VAL
            return t

        chunk = self.chunk

        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                if chunk[y, x] != WATER_VAL:
                    continue

                above = get_tile(y - 1, x) == WATER_VAL
                left  = get_tile(y, x - 1) == WATER_VAL
                diag  = get_tile(y - 1, x - 1) == WATER_VAL

                if   not above and not left:             chunk[y, x] = Tile.WATER_INT.value
                elif not above and     left:             chunk[y, x] = Tile.WATER_LEFT.value
                elif     above and not left:             chunk[y, x] = Tile.WATER_RIGHT.value
                elif not diag  and     above and left:   chunk[y, x] = Tile.WATER_EXT.value
                else:                                    chunk[y, x] = Tile.WATER_MID.value

        self.chunk = chunk
        
    def _generate_chunk(self) -> None:
        self.chunk = np.full((self.chunk_size, self.chunk_size), Tile.EMPTY.value)
        self._generate_tree_probabilities()
        self._assign_biome()
        self._generate_tiles()
        self.chunk_raw = self.chunk.copy()



    # -- Surfaces Generation -- #

    def _generate_chunk_image(self) -> None:
        chunk = self.chunk
        TILE_W = 32 * SCALE
        TILE_H = 32 * SCALE
        TREE_OVERHEAD = 96

        surf_w = 32 * self.chunk_size + TILE_W
        surf_h = 16 * self.chunk_size + 32 + TREE_OVERHEAD

        origin_x = TILE_W // 2

        # Output surfaces
        out_summer = [pygame.Surface((surf_w, surf_h), pygame.SRCALPHA) for _ in range(8)]
        out_autumn = [pygame.Surface((surf_w, surf_h), pygame.SRCALPHA) for _ in range(8)]
        out_winter = [pygame.Surface((surf_w, surf_h), pygame.SRCALPHA) for _ in range(8)]

        tree_surface_summer = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        tree_surface_autumn = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)
        tree_surface_winter = pygame.Surface((surf_w, surf_h), pygame.SRCALPHA)

        # --- BATCHES ---
        summer_batches = [[] for _ in range(8)]
        autumn_batches = [[] for _ in range(8)]
        winter_batches = [[] for _ in range(8)]

        tree_batch_summer = []
        tree_batch_autumn = []
        tree_batch_winter = []

        
        water_ext   = [self.background_assets[f"WATER_EXT_{i}"] for i in range(8)]
        water_int   = [self.background_assets[f"WATER_INT_{i}"] for i in range(8)]
        water_left  = [self.background_assets[f"WATER_LEFT_{i}"] for i in range(8)]
        water_right = [self.background_assets[f"WATER_RIGHT_{i}"] for i in range(8)]
        water_mid   = [self.background_assets[f"WATER_MID_{i}"] for i in range(8)]

        for y in range(self.chunk_size):
            for x in range(self.chunk_size):
                tile = Tile(chunk[y, x])

                img_summer = img_autumn = img_winter = None
                tree_img_summer = tree_img_autumn = tree_img_winter = None

                blit_x = origin_x + (32 * self.chunk_size) // 2 + x * 16 - y * 16
                blit_y = x * 8 + y * 8 + TREE_OVERHEAD
                pos = (blit_x, blit_y)

                match tile:
                    case Tile.PLAIN:
                        img_summer = self.background_assets["PLAIN_SUMMER"]
                        img_autumn = self.background_assets["PLAIN_AUTUMN"]
                        img_winter = self.background_assets["PLAIN_WINTER"]

                    case Tile.FOREST:
                        img_summer = self.background_assets["PLAIN_SUMMER"]
                        img_autumn = self.background_assets["PLAIN_AUTUMN"]
                        img_winter = self.background_assets["PLAIN_WINTER"]

                        if self.tree_probs[y, x] <= TREE_PROBABILITY:
                            t = self.tree_types[y, x]
                            tree_img_summer = self.background_assets[f"tree_{t}_summer"]
                            tree_img_autumn = self.background_assets[f"tree_{t}_autumn"]
                            tree_img_winter = self.background_assets[f"tree_{t}_winter"]

                    case Tile.WATER_EXT:
                        for i in range(8):
                            img = water_ext[i]
                            summer_batches[i].append((img, pos))
                            autumn_batches[i].append((img, pos))
                            winter_batches[i].append((img, pos))

                    case Tile.WATER_INT:
                        for i in range(8):
                            img = water_int[i]
                            summer_batches[i].append((img, pos))
                            autumn_batches[i].append((img, pos))
                            winter_batches[i].append((img, pos))

                    case Tile.WATER_LEFT:
                        for i in range(8):
                            img = water_left[i]
                            summer_batches[i].append((img, pos))
                            autumn_batches[i].append((img, pos))
                            winter_batches[i].append((img, pos))

                    case Tile.WATER_RIGHT:
                        for i in range(8):
                            img = water_right[i]
                            summer_batches[i].append((img, pos))
                            autumn_batches[i].append((img, pos))
                            winter_batches[i].append((img, pos))

                    case Tile.WATER_MID:
                        for i in range(8):
                            img = water_mid[i]
                            summer_batches[i].append((img, pos))
                            autumn_batches[i].append((img, pos))
                            winter_batches[i].append((img, pos))

                
                if img_summer is not None:
                    for i in range(8):
                        summer_batches[i].append((img_summer, pos))
                        autumn_batches[i].append((img_autumn, pos))
                        winter_batches[i].append((img_winter, pos))

                
                if tree_img_summer is not None:
                    anchor_x, anchor_y = TREE_ANCHORS.get(
                        self.tree_types[y, x],
                        (tree_img_summer.get_width() // 2, tree_img_summer.get_height())
                    )

                    tile_center_x = origin_x + (32 * self.chunk_size) // 2 + x * 16 - y * 16 + 16
                    tile_base_y   = x * 8 + y * 8 + 16 * SCALE + TREE_OVERHEAD

                    tree_blit_x = tile_center_x - anchor_x
                    tree_blit_y = tile_base_y - anchor_y
                    tree_pos = (tree_blit_x, tree_blit_y)

                    tree_batch_summer.append((tree_img_summer, tree_pos))
                    tree_batch_autumn.append((tree_img_autumn, tree_pos))
                    tree_batch_winter.append((tree_img_winter, tree_pos))

        
        for i in range(8):
            out_summer[i].blits(summer_batches[i])
            out_autumn[i].blits(autumn_batches[i])
            out_winter[i].blits(winter_batches[i])

        tree_surface_summer.blits(tree_batch_summer)
        tree_surface_autumn.blits(tree_batch_autumn)
        tree_surface_winter.blits(tree_batch_winter)

        self.image["summer"] = out_summer
        self.image["autumn"] = out_autumn
        self.image["winter"] = out_winter

        self.tree["summer"] = tree_surface_summer
        self.tree["autumn"] = tree_surface_autumn
        self.tree["winter"] = tree_surface_winter

    def finalize_chunk_creation(self, neighbor_dict : dict) -> None:
        '''
        Collapses water and creates images
        '''
        self._collapse_water(neighbor_dict)
        self._generate_chunk_image()

    # -- Rendering -- #

    def draw_background_layer(self, screen : pygame.Surface, camera_pos: tuple[int, int], season: str, water_frame: int) -> None: 
        cam_x, cam_y = camera_pos

        
        half_w = TILE_W // 2
        half_h = TILE_H // 2

        origin_x = half_w

        y0, x0 = self.index

        surface = self.image[season][water_frame]
        iso_x = (x0 - y0) * half_w - origin_x
        iso_y = (x0 + y0) * half_h

        draw_x = iso_x - cam_x
        draw_y = iso_y - cam_y

        screen.blit(surface, (draw_x, draw_y))

    def draw_tree_layer(self, screen : pygame.Surface, camera_pos: tuple[int, int], season: str) -> None:
        cam_x, cam_y = camera_pos

        
        half_w = TILE_W // 2
        half_h = TILE_H // 2

        origin_x = half_w

        y0, x0 = self.index


        surface = self.tree[season]

        iso_x = (x0 - y0) * half_w - origin_x
        iso_y = (x0 + y0) * half_h

        draw_x = iso_x - cam_x
        draw_y = iso_y - cam_y

        screen.blit(surface, (draw_x, draw_y))

    def draw_animals(self, screen : pygame.Surface, camera_pos: tuple[int, int]) -> None:
        for animal in self.animals:
            animal.draw(screen, camera_pos)






