import pygame
import cProfile
import pstats

from world import World
from config import *
from animal import Animal, Stag, Badger, Wolf, Boar



if __name__ == "__main__":
    screen = pygame.display.set_mode((SCREENW, SCREENH))
    
    w = World(seed=69)
    clock = pygame.time.Clock()

    camerax, cameray = 0, 0

    is_moving_left = is_moving_right = is_moving_up = is_moving_down = False

    is_running = True
    animals = [Stag(w.chunks_raws) for _ in range(100)]
    for animal in animals:
        w.animal_manager.animals.add(animal)
        

    while is_running:
        #clock.tick(60)
        
        screen.fill((0, 0, 0))
        
        for animal in animals:
            animal.update()
        w.update(screen, (camerax, cameray))

        

        if is_moving_left:
            camerax -= 2
        if is_moving_right:
            camerax += 2
        if is_moving_up:
            cameray -= 2
        if is_moving_down:
            cameray += 2

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                is_running = False
                
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    is_running = False

                if event.key == pygame.K_a:
                    is_moving_left = True
                elif event.key == pygame.K_d:
                    is_moving_right = True                
                if event.key == pygame.K_w:
                    is_moving_up = True
                elif event.key == pygame.K_s:
                    is_moving_down = True

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_a:
                    is_moving_left = False
                elif event.key == pygame.K_d:
                    is_moving_right = False                
                if event.key == pygame.K_w:
                    is_moving_up = False
                elif event.key == pygame.K_s:
                    is_moving_down = False

        pygame.display.update()
