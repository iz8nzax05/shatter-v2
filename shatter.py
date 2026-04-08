#!/usr/bin/env python3
"""
SHATTER - Fractal Crack Physics Simulator
MVP Version - Core physics and crack generation
"""

import pygame
import math
import random
import json
import os
from datetime import datetime

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Physics constants
GRAVITY = 1.0
ORB_SIZE = 30
FLOOR_Y = int(SCREEN_HEIGHT * 2/3)  # Floor at 2/3 of screen height

# Crack generation parameters - Organic straight cracks
CRACK_ANGLE = math.radians(25)  # Branch spread angle (narrower)
CRACK_FACTOR_MIN = 0.6  # Minimum length reduction
CRACK_FACTOR_MAX = 0.9  # Maximum length reduction (less aggressive)
MIN_CRACK_LENGTH = 3  # Minimum visible crack
MAX_CRACK_DEPTH = 15  # More depth but less branching
CRACK_BRANCH_PROBABILITY = 0.4  # Much lower chance to branch (40%)
CRACK_CONTINUE_PROBABILITY = 0.85  # High chance to just continue straight
CRACK_BRANCH_COUNT = [1, 2]  # Usually just 1-2 branches, not 3

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
DARK_GRAY = (30, 30, 30)
CRACK_COLOR = (200, 200, 200)

class Orb:
    """Physics-enabled falling orb"""
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.size = ORB_SIZE
        self.color = WHITE
    
    def update(self, gravity):
        """Update physics"""
        self.velocity.y += gravity
        self.pos += self.velocity
    
    def check_collision(self):
        """Check if orb hits the floor"""
        return self.pos.y + self.size >= FLOOR_Y
    
    def draw(self, screen):
        """Draw the orb"""
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.size, 0)  # 0 = filled circle

class Crack:
    """Recursive fractal crack (adapted from tree Branch)"""
    def __init__(self, start, angle, length, depth):
        self.start = pygame.Vector2(start)
        self.angle = angle
        self.length = length
        self.depth = depth
        self.children = []
        self.finished = False
    
    def get_end(self):
        """Calculate end point of crack"""
        return self.start + pygame.Vector2(
            math.cos(self.angle) * self.length,
            -math.sin(self.angle) * self.length  # Negative Y because pygame Y increases downward
        )
    
    def spawn_children(self):
        """Recursively spawn child cracks - organic straight-line behavior"""
        if self.finished or self.depth >= MAX_CRACK_DEPTH:
            return
        
        self.finished = True
        end = self.get_end()
        
        # Most of the time, just continue straight with minor deviation
        if random.random() < CRACK_CONTINUE_PROBABILITY:
            # Continue mostly straight - very small angle change
            delta = random.uniform(-math.radians(5), math.radians(5))
            
            # Length reduces slightly as crack propagates
            crack_factor = random.uniform(0.85, 0.95)
            new_length = self.length * crack_factor
            
            if new_length >= MIN_CRACK_LENGTH:
                child = Crack(
                    end, 
                    self.angle + delta,
                    new_length,
                    self.depth + 1
                )
                self.children.append(child)
                child.spawn_children()
        
        # Occasionally branch off
        elif random.random() < CRACK_BRANCH_PROBABILITY:
            num_branches = random.choice(CRACK_BRANCH_COUNT)
            
            for _ in range(num_branches):
                # Wider angle for actual branches
                delta = random.uniform(-CRACK_ANGLE, CRACK_ANGLE)
                
                # Branches are shorter
                crack_factor = random.uniform(CRACK_FACTOR_MIN, CRACK_FACTOR_MAX)
                new_length = self.length * crack_factor
                new_length *= random.uniform(0.7, 1.0)
                
                if new_length >= MIN_CRACK_LENGTH:
                    child = Crack(
                        end, 
                        self.angle + delta,
                        new_length,
                        self.depth + 1
                    )
                    self.children.append(child)
                    child.spawn_children()
        # Otherwise: crack just stops (dead end)

class Game:
    """Main game class"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SHATTER - Fractal Crack Simulator")
        self.clock = pygame.time.Clock()
        
        # Game state
        self.orbs = []
        self.floor_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.floor_surface.fill(DARK_GRAY)
        
        # Settings
        self.gravity = GRAVITY
        self.orb_size = ORB_SIZE
        self.crack_color = CRACK_COLOR
        
        # UI
        self.font = pygame.font.Font(None, 24)
        self.show_ui = True
        
    def spawn_orb(self, x, y):
        """Spawn a new orb at mouse position"""
        if y < FLOOR_Y - 50:  # Only in spawn zone (above floor)
            orb = Orb(x, y)
            orb.size = self.orb_size
            self.orbs.append(orb)
    
    def calculate_impact_force(self, orb):
        """Calculate impact force based on velocity and size"""
        return orb.velocity.length() * orb.size / 10
    
    def generate_cracks(self, impact_point, force):
        """Generate natural organic crack network from impact"""
        # Fewer main cracks - more like real fractures
        num_primary_cracks = min(5, max(3, int(force * 1.0)))
        base_length = min(120, max(40, force * 25))
        cracks = []
        
        # Create main cracks with RANDOM angles (not evenly distributed!)
        for i in range(num_primary_cracks):
            # Completely random angle - no circular symmetry
            angle = random.uniform(0, 2 * math.pi)
            
            # Vary initial length - some long, some short
            length_variation = random.uniform(0.6, 1.4)
            initial_length = base_length * length_variation
            
            crack = Crack(impact_point, angle, initial_length, 1)
            crack.spawn_children()
            cracks.append(crack)
        
        # Just a few tiny surface cracks at impact point
        num_micro_cracks = int(force * 1.5)
        for _ in range(num_micro_cracks):
            angle = random.uniform(0, 2 * math.pi)
            tiny_length = random.uniform(3, 10)
            micro_crack = Crack(impact_point, angle, tiny_length, MAX_CRACK_DEPTH)  # Max depth = no children
            cracks.append(micro_crack)
        
        return cracks
    
    def draw_crack_recursive(self, surface, crack):
        """Recursively draw crack and children with natural variation"""
        start = crack.start
        end = crack.get_end()
        
        # Thicker cracks near impact, thinner as they branch
        # depth 1-2: thick (3px), depth 3-5: medium (2px), depth 6+: thin (1px)
        if crack.depth <= 2:
            thickness = 3
        elif crack.depth <= 5:
            thickness = 2
        else:
            thickness = 1
        
        pygame.draw.line(surface, self.crack_color, start, end, thickness)
        
        # Draw children
        for child in crack.children:
            self.draw_crack_recursive(surface, child)
    
    def draw_crater(self, surface, center, force):
        """Draw impact crater"""
        crater_radius = int(force * 2)
        
        # Outer rim (darker)
        pygame.draw.circle(surface, (20, 20, 20), center, crater_radius + 5)
        
        # Inner depression (lighter)
        pygame.draw.circle(surface, (40, 40, 40), center, crater_radius)
    
    def handle_impact(self, orb):
        """Handle orb impact with floor"""
        # Calculate exact impact point on floor
        impact_x = int(orb.pos.x)
        impact_y = FLOOR_Y
        impact_point = (impact_x, impact_y)
        force = self.calculate_impact_force(orb)
        
        # Generate and draw cracks
        cracks = self.generate_cracks(impact_point, force)
        for crack in cracks:
            self.draw_crack_recursive(self.floor_surface, crack)
        
        # Crater disabled - just showing pure cracks
        # self.draw_crater(self.floor_surface, impact_point, force)
        
        # Remove orb
        self.orbs.remove(orb)
    
    def draw_ui(self):
        """Draw simple UI controls"""
        if not self.show_ui:
            return
        
        # Background panel
        ui_rect = pygame.Rect(10, 10, 250, 150)
        pygame.draw.rect(self.screen, (0, 0, 0, 128), ui_rect)
        pygame.draw.rect(self.screen, WHITE, ui_rect, 2)
        
        # Labels and values
        y_offset = 20
        labels = [
            f"Gravity: {self.gravity:.1f}",
            f"Orb Size: {self.orb_size}",
            f"Orbs: {len(self.orbs)}",
            "Click to spawn orb",
            "C to clear canvas",
            "TAB to toggle UI"
        ]
        
        for label in labels:
            text = self.font.render(label, True, WHITE)
            self.screen.blit(text, (20, y_offset))
            y_offset += 25
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.spawn_orb(event.pos[0], event.pos[1])
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c:
                    # Clear canvas
                    self.floor_surface.fill(DARK_GRAY)
                elif event.key == pygame.K_TAB:
                    # Toggle UI
                    self.show_ui = not self.show_ui
                elif event.key == pygame.K_UP:
                    # Increase gravity
                    self.gravity = min(5.0, self.gravity + 0.1)
                elif event.key == pygame.K_DOWN:
                    # Decrease gravity
                    self.gravity = max(0.1, self.gravity - 0.1)
                elif event.key == pygame.K_RIGHT:
                    # Increase orb size
                    self.orb_size = min(100, self.orb_size + 5)
                elif event.key == pygame.K_LEFT:
                    # Decrease orb size
                    self.orb_size = max(10, self.orb_size - 5)
        
        return True
    
    def update(self):
        """Update game state"""
        # Update orbs
        for orb in self.orbs[:]:  # Copy list to avoid modification during iteration
            orb.update(self.gravity)
            
            # Check for floor collision
            if orb.check_collision():
                self.handle_impact(orb)
    
    def draw(self):
        """Draw everything"""
        # Clear screen
        self.screen.fill(BLACK)
        
        # Draw visible floor line
        pygame.draw.line(self.screen, GRAY, (0, FLOOR_Y), (SCREEN_WIDTH, FLOOR_Y), 2)
        
        # Draw static floor with cracks (only the floor portion)
        floor_rect = pygame.Rect(0, FLOOR_Y, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y)
        self.screen.blit(self.floor_surface, (0, FLOOR_Y), floor_rect)
        
        # Draw active orbs
        for orb in self.orbs:
            orb.draw(self.screen)
        
        # Draw UI
        self.draw_ui()
        
        # Update display
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            # Handle events
            running = self.handle_events()
            
            # Update game state
            self.update()
            
            # Draw everything
            self.draw()
            
            # Cap frame rate
            self.clock.tick(FPS)
        
        pygame.quit()

def main():
    """Entry point"""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
