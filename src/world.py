import pygame
import numpy as np
import numpy.typing as npt
import random



from config import *
from chunk import Chunk
from animal import AnimalManager

'''
NAMING CONVENTION

create_*   → allocates/initialises empty structures
generate_* → fills with actual content (noise, images)


'''


class World:
    def __init__(self, seed: int = None):
        self.gridw, self.gridh = GRIDW, GRIDH
        self.chunk_size = CHUNK_SIZE
        
        self.seed = seed if seed is not None else random.randint(1, 999999)

        self.background_assets = {}
        self._load_assets()

        self.chunks : dict[tuple[int, int], Chunk] = {}
        self.chunks_raws : dict[tuple[int, int], npt.NDArray] = {}
        

    

        self.clock = pygame.time.Clock().tick(FPS)

        self.season = "summer"
        self.season_update_time = pygame.time.get_ticks()
        self.season_cooldown = 5 * 60 * 1000 * 6

        self.is_day = True
        self.day_update_time = pygame.time.get_ticks()
        self.day_cooldown = 5 * 60 * 1000
        self.day_mask = pygame.Surface((SCREENW, SCREENH), pygame.SRCALPHA)

        self.water_update_time = pygame.time.get_ticks()
        self.water_cooldown = 250
        self.water_frame = 0

        self.animal_manager = AnimalManager(self.chunks)

        self._create_initial_world()
        for index, chunk in self.chunks.items():
            self.chunks_raws[index] = chunk.chunk_raw

    def _load_assets(self) -> None:
        for img in os.listdir(ASSET_PATH_BACKGROUND):
            load_img = pygame.image.load(f"{ASSET_PATH_BACKGROUND}\\{img}").convert_alpha()
            load_img = pygame.transform.scale_by(load_img, SCALE)
            name = img.replace(".png", "")
            self.background_assets[name] = load_img


    # -- Chunk Generation -- #

    def _build_neighbor_dict(self, chunk_index: tuple[int, int]) -> dict[tuple[int, int], Chunk]:
        y0, x0 = chunk_index
        neighbors = {}

        for dy, dx in [
            (-1, 0), (1, 0), (0, -1), (0, 1),(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            nidx = (y0 + dy * self.chunk_size,
                    x0 + dx * self.chunk_size)

            
            if nidx not in self.chunks:
                chunk = Chunk(nidx, self.seed,   self.background_assets)
                self.chunks[nidx] = chunk

                # Only generate raw here

            neighbors[nidx] = self.chunks[nidx]

        return neighbors

    def _generate_chunk(self, chunk_index: tuple[int, int]) -> None:
        chunk = Chunk(chunk_index, self.seed, self.background_assets)

        self.chunks[chunk_index] = chunk

        # water collapse needs neighbors, so redo it now that chunk is registered
        chunk.chunk = chunk.chunk_raw.copy()
        chunk.finalize_chunk_creation(self._build_neighbor_dict(chunk_index))

    def _create_initial_world(self) -> None:
        for y in range(0, self.gridh, self.chunk_size):
            for x in range(0, self.gridw, self.chunk_size):
                self._generate_chunk((y, x))


    # -- Rendering -- #
    def _get_drawable_chunks(self, chunk_index: tuple[int, int]) -> list:
        out = []
        y, x = chunk_index
        for offset in DRAWABLE_CHUNKS:
            dy, dx = offset
            ny, nx = y + dy * CHUNK_SIZE, x + dx * CHUNK_SIZE

            out.append((ny, nx))

        return out

    def _get_chunks_from_indices(self, chunk_indices: list[tuple[int, int]]) -> list[Chunk]:
        out = []

        for index in chunk_indices:
            if index not in self.chunks:
                self._generate_chunk(index)

            chunk = self.chunks[index]

            if not chunk.image["summer"]:  
                chunk.chunk = chunk.chunk_raw.copy()
                chunk.finalize_chunk_creation(self._build_neighbor_dict(index))

            out.append(chunk)

        return out

    def _get_chunk_from_camera_pos(self, camera_pos: tuple[int, int]) -> tuple[int, int]:
        cam_x, cam_y = camera_pos
        half_w = (32 * SCALE) // 2
        half_h = (16 * SCALE) // 2

        world_x = SCREENW // 2 + cam_x + half_w
        world_y = SCREENH // 2 + cam_y + half_h

        tile_x = int((world_x / half_w + world_y / half_h) / 2 - CHUNK_SIZE / 2)
        tile_y = int((world_y / half_h - world_x / half_w) / 2 - CHUNK_SIZE / 2)

        chunk_x = (tile_x // CHUNK_SIZE) * CHUNK_SIZE
        chunk_y = (tile_y // CHUNK_SIZE) * CHUNK_SIZE
        return (chunk_y, chunk_x)

    def _sort_chunks(self, chunks: list[Chunk]) -> list[Chunk]:
        return sorted(chunks, key=lambda c: c.index[0] + c.index[1])

    def _draw_background_layer(self, screen, camera_pos, drawable_chunks) -> None:
        for chunk in self._sort_chunks(drawable_chunks):
            chunk.draw_background_layer(screen, camera_pos, self.season, self.water_frame)

    def _draw_tree_layer(self, screen, camera_pos, drawable_chunks) -> None:
        for chunk in self._sort_chunks(drawable_chunks):
            chunk.draw_tree_layer(screen, camera_pos, self.season)

    def _draw_animals(self, screen, camera_pos, drawable_chunks) -> None:
        for chunk in self._sort_chunks(drawable_chunks):
            chunk.draw_animals(screen, camera_pos)

    def _draw_chunk_debug(self, screen, camera_pos) -> None:
        cam_x, cam_y = camera_pos
        TILE_W = 32 * SCALE
        TILE_H = 16 * SCALE
        half_w = TILE_W // 2
        half_h = TILE_H // 2
        TREE_OVERHEAD = 96

        for chunk in self.chunks.values():
            y0, x0 = chunk.index

            iso_x = (x0 - y0) * half_w - half_w
            iso_y = (x0 + y0) * half_h

            draw_x = iso_x - cam_x
            draw_y = iso_y - cam_y

            # Use raw unscaled steps (16, 8) matching _generate_chunk_image exactly
            corners = []
            for ty, tx in [(0, 0), (0, CHUNK_SIZE), (CHUNK_SIZE, CHUNK_SIZE), (CHUNK_SIZE, 0)]:
                local_x = half_w + (32 * CHUNK_SIZE) // 2 + tx * 16 - ty * 16
                local_y = tx * 8 + ty * 8 + TREE_OVERHEAD
                corners.append((draw_x + local_x, draw_y + local_y))

            pygame.draw.lines(screen, (255, 0, 0), True, corners, 1)

    def _draw(self, screen, camera_pos: tuple[int, int]) -> None:
        selected_chunk = self._get_chunk_from_camera_pos(camera_pos)
        drawable_chunks = self._get_chunks_from_indices(self._get_drawable_chunks(selected_chunk))
        
        self._draw_background_layer(screen, camera_pos, drawable_chunks)
        # animals drawn here: z-layer above background, below trees
        
        self._draw_animals(screen, camera_pos, drawable_chunks)
        
        self._draw_tree_layer(screen, camera_pos, drawable_chunks)
        screen.blit(self.day_mask, (0, 0))
        #print(f"Visible chunks: {len(drawable_chunks)}")
        #self._draw_chunk_debug(screen, camera_pos)


    # -- Update -- #

    def _get_mask_color(self, percent: float) -> tuple[int,int,int,int]:
        '''
        Returns the interpolated RGBA color for a given percentage of the day.
        '''
        percent = percent % 1.0

        for i in range(len(MASK_COLOR) - 1):
            start_time, start_color = MASK_COLOR[i]
            end_time,   end_color   = MASK_COLOR[i + 1]

            if start_time <= percent <= end_time:
                t = (percent - start_time) / (end_time - start_time)
                
                r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
                g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
                b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
                a = int(start_color[3] + (end_color[3] - start_color[3]) * t)
                
                return (r, g, b, a)
        
        return MASK_COLOR[-1][1]

    def _update_day(self):
        current_time = pygame.time.get_ticks()
        percentage = current_time / self.day_cooldown
        color = self._get_mask_color(percentage)
        self.day_mask.fill(color)

    def _update_season(self):
        if pygame.time.get_ticks() - self.season_update_time >= self.season_cooldown:
            self.season_update_time = pygame.time.get_ticks()
            match self.season:
                case "summer":
                    self.season = "autumn"
                case "autumn":
                    self.season = "winter"
                case "winter":
                    self.season = "summer"

    def _update_water_animation(self):
        if pygame.time.get_ticks() - self.water_update_time >= self.water_cooldown:
            self.water_update_time = pygame.time.get_ticks()
            self.water_frame = (self.water_frame + 1) % 8


    # -- Public Methods -- #

    def update(self, screen, camera_pos):
        self.animal_manager._update_chunks()
        self._update_day()
        self._update_season()
        self._update_water_animation()
        self._draw(screen, camera_pos)


#FIXME change some trees (large ones) being rendered too high (sometimes on water)


if __name__ == "__main__":
    import cProfile
    import pstats

    





