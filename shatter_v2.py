#!/usr/bin/env python3
"""
SHATTER V2 - Interactive Crack Simulator with Full UI
Phase 3: UI Framework Implementation
"""

import pygame
import math
import random
from datetime import datetime

# Initialize Pygame
pygame.init()

print("=" * 50)
print("SHATTER V2 - Interactive Crack Simulator")
print("=" * 50)
print("Controls:")
print("  Click         = Spawn orb")
print("  Click & Drag  = Move orb (glows yellow)")
print("  Release       = Apply momentum")
print("  TAB           = Toggle UI")
print("  D             = Toggle Debug Markers")
print("  C             = Clear canvas")
print("=" * 50)

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60
FLOOR_Y = int(SCREEN_HEIGHT * 2/3)  # Floor at 2/3 down
TOOLBAR_HEIGHT = 40

# Physics constants (now adjustable via UI)
GRAVITY = 1.0
ORB_SIZE = 30

# Crack parameters
CRACK_WOBBLE = 0.3
CRACK_BRANCH_CHANCE = 0.4
MAX_CRACK_DEPTH = 2

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
DARK_GRAY = (30, 30, 30)
CRACK_COLOR = (200, 200, 200)
UI_BG = (40, 40, 50)
UI_HOVER = (60, 60, 70)
UI_ACTIVE = (80, 80, 90)

class Orb:
    """Draggable rolling orb that interacts with terrain"""
    def __init__(self, x, y):
        self.pos = pygame.Vector2(x, y)
        self.velocity = pygame.Vector2(0, 0)
        self.size = ORB_SIZE
        self.color = WHITE
        self.dragging = False
        self.on_floor = False
        self.prev_on_floor = False  # Track previous frame for impact detection
        self.last_crack_pos = None
        self.crack_distance_threshold = 10
        self.prev_pos = pygame.Vector2(x, y)
        self.last_impact_speed = 0  # Store last impact velocity
        self.impact_cooldown = 0  # Frames since last impact
        self.frames_off_floor = 0  # Count frames not on floor
    
    def is_mouse_over(self, mouse_pos):
        dx = mouse_pos[0] - self.pos.x
        dy = mouse_pos[1] - self.pos.y
        distance = (dx * dx + dy * dy) ** 0.5
        return distance <= self.size
    
    def start_drag(self):
        self.dragging = True
        self.velocity = pygame.Vector2(0, 0)
        self.prev_pos = self.pos.copy()
    
    def stop_drag(self):
        self.dragging = False
        self.velocity = (self.pos - self.prev_pos) * 0.5
    
    def drag_to(self, mouse_pos):
        self.prev_pos = self.pos.copy()
        self.pos.x = mouse_pos[0]
        self.pos.y = mouse_pos[1]
    
    def update(self, gravity, floor_height_func):
        # Store previous floor state
        self.prev_on_floor = self.on_floor
        
        # Update cooldown timer
        if self.impact_cooldown > 0:
            self.impact_cooldown -= 1
        
        if not self.dragging:
            self.velocity.y += gravity
            self.pos += self.velocity
            
            # Get actual floor height at this X position (accounts for dents)
            floor_height = floor_height_func(self.pos.x)
            
            # Check floor collision
            if self.pos.y + self.size >= floor_height:
                # Only store impact speed on FIRST contact after being airborne AND cooldown expired
                if (not self.prev_on_floor and 
                    self.frames_off_floor >= 5 and  # Must be off floor for at least 5 frames (real fall)
                    self.impact_cooldown == 0):      # Cooldown must be fully expired
                    impact_speed = abs(self.velocity.y)
                    self.last_impact_speed = impact_speed  # Store for floor deformation
                    self.impact_cooldown = 60  # 60 frame cooldown (1 second) between impacts
                else:
                    self.last_impact_speed = 0  # Reset if already on floor or micro-bounce
                
                # Stop vertical movement - orb sits on deformed floor
                self.pos.y = floor_height - self.size
                self.velocity.y = 0
                
                # SIMPLE GRAVITY ON SLOPES: Gravity pulls down, slope redirects it sideways
                # Sample floor on both sides to detect slope angle
                sample_dist = 5
                left_x = max(0, self.pos.x - sample_dist)
                right_x = min(1280, self.pos.x + sample_dist)
                floor_left = floor_height_func(left_x)
                floor_right = floor_height_func(right_x)
                
                # Slope angle (higher Y = deeper, so flip the sign)
                # If left is deeper (higher Y), slope_angle should be negative (roll left)
                slope_angle = (floor_right - floor_left) / (2 * sample_dist)
                
                # Gravity component along slope (downward gravity creates sideways force on slope)
                # Simple: slope_angle directly translates to sideways acceleration
                self.velocity.x += slope_angle * gravity * 0.15  # Gravity pushes orb downhill
                
                # Rolling friction
                self.velocity.x *= 0.98
                
                # SLEEP THRESHOLD: Stop micro-vibrations when settled
                if abs(self.velocity.x) < 0.01:  # Only stop if BARELY moving
                    self.velocity.x = 0  # Come to complete rest
                
                self.on_floor = True
                self.frames_off_floor = 0
            else:
                self.on_floor = False
                self.last_impact_speed = 0
                self.frames_off_floor += 1
        else:
            # When dragging, still check floor height for positioning
            floor_height = floor_height_func(self.pos.x)
            self.on_floor = (self.pos.y + self.size >= floor_height)
            self.last_impact_speed = 0  # No impact while dragging
            self.frames_off_floor = 0
    
    def just_impacted(self):
        """Check if orb just hit the floor this frame (and cooldown allows it)"""
        return (self.on_floor and not self.prev_on_floor and 
                self.last_impact_speed > 1.0 and self.impact_cooldown == 60)  # Only on the frame cooldown was just set
    
    def should_create_crack(self):
        if self.pos.y + self.size < FLOOR_Y:
            return False
        
        if self.last_crack_pos is None:
            self.last_crack_pos = self.pos.copy()
            return True
        
        distance = (self.pos - self.last_crack_pos).length()
        if distance >= self.crack_distance_threshold:
            self.last_crack_pos = self.pos.copy()
            return True
        
        return False
    
    def collides_with(self, other_orb):
        """Check if this orb collides with another orb"""
        if other_orb is self:
            return False
        distance = (self.pos - other_orb.pos).length()
        return distance < (self.size + other_orb.size)
    
    def resolve_collision(self, other_orb):
        """Resolve collision with another orb (elastic collision with damping)"""
        if other_orb is self or self.dragging:
            return
        
        # Calculate collision normal
        delta = self.pos - other_orb.pos
        distance = delta.length()
        
        if distance == 0:  # Orbs exactly on top of each other
            delta = pygame.Vector2(1, 0)
            distance = 1
        
        # Normalize
        collision_normal = delta / distance
        
        # Separate overlapping orbs
        overlap = (self.size + other_orb.size) - distance
        if overlap > 0:
            # Push orbs apart (50/50 split unless one is dragging)
            if other_orb.dragging:
                self.pos += collision_normal * overlap
            else:
                separation = collision_normal * (overlap / 2)
                self.pos += separation
                other_orb.pos -= separation
        
        # Relative velocity
        relative_velocity = self.velocity - other_orb.velocity
        velocity_along_normal = relative_velocity.dot(collision_normal)
        
        # Don't resolve if velocities are separating
        if velocity_along_normal > 0:
            return
        
        # SLEEP CHECK: If both orbs are nearly still, don't bounce (prevents vibration)
        if abs(velocity_along_normal) < 0.02 and not self.dragging and not other_orb.dragging:
            return  # Both settled, just let separation handle it
        
        # Collision response (elastic with restitution)
        restitution = 0.6  # Bounciness (0 = inelastic, 1 = perfectly elastic)
        impulse = -(1 + restitution) * velocity_along_normal
        impulse /= 2  # Equal mass assumption
        
        # Apply impulse
        impulse_vector = collision_normal * impulse
        if not other_orb.dragging:
            self.velocity += impulse_vector
            other_orb.velocity -= impulse_vector
        else:
            # If other orb is dragging, this orb bounces off fully
            self.velocity += impulse_vector * 2
    
    def draw(self, screen):
        color = (255, 200, 0) if self.dragging else self.color
        pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), self.size, 0)

class FloorDeformation:
    """Persistent floor impact deformation - creates real dents"""
    def __init__(self, x, depth, radius):
        self.x = x
        self.depth = depth  # How deep the dent is (in pixels)
        self.radius = radius  # How wide the deformation spreads
    
    def get_offset_at(self, x):
        """Get the Y offset (downward) at a given X position"""
        # Distance from impact center
        dist = abs(x - self.x)
        if dist > self.radius:
            return 0
        
        # Smooth bowl-shaped falloff using cosine curve
        ratio = dist / self.radius
        falloff = (math.cos(ratio * math.pi) + 1) / 2
        return self.depth * falloff

class OrganicCrack:
    """Organic crack with curves and branches"""
    def __init__(self, start_x, start_y, angle, length, thickness=2, depth=0):
        self.start_x = start_x
        self.start_y = start_y
        self.angle = angle
        self.length = length
        self.thickness = thickness
        self.depth = depth
        self.segments = []
        self.branches = []
        
        self._generate_path()
        
        if depth < MAX_CRACK_DEPTH and random.random() < CRACK_BRANCH_CHANCE:
            self._create_branches()
    
    def _generate_path(self):
        num_segments = max(3, int(self.length / 10))
        current_x = self.start_x
        current_y = self.start_y
        current_angle = self.angle
        segment_length = self.length / num_segments
        
        self.segments.append((current_x, current_y))
        
        for i in range(num_segments):
            current_angle += random.uniform(-CRACK_WOBBLE, CRACK_WOBBLE)
            current_x += segment_length * math.cos(current_angle)
            current_y += segment_length * math.sin(current_angle)
            self.segments.append((current_x, current_y))
    
    def _create_branches(self):
        if len(self.segments) < 3:
            return
        
        branch_point_idx = len(self.segments) // 2 + random.randint(-1, 1)
        branch_x, branch_y = self.segments[branch_point_idx]
        
        num_branches = random.choice([1, 1, 2])
        for _ in range(num_branches):
            branch_angle = self.angle + random.uniform(-1.2, 1.2)
            branch_length = self.length * random.uniform(0.3, 0.6)
            branch_thickness = max(1, self.thickness - 1)
            
            branch = OrganicCrack(
                branch_x, branch_y, 
                branch_angle, branch_length, 
                branch_thickness, self.depth + 1
            )
            self.branches.append(branch)
    
    def draw(self, surface):
        if len(self.segments) >= 2:
            for i in range(len(self.segments) - 1):
                start = (int(self.segments[i][0]), int(self.segments[i][1]))
                end = (int(self.segments[i + 1][0]), int(self.segments[i + 1][1]))
                pygame.draw.line(surface, CRACK_COLOR, start, end, self.thickness)
        
        for branch in self.branches:
            branch.draw(surface)

def generate_instant_cracks(floor_surface, impact_x, impact_y, force):
    """Generate organic cracks instantly"""
    num_cracks = min(8, max(4, int(force * 1.2)))
    
    for _ in range(num_cracks):
        angle = random.uniform(0, 2 * math.pi)
        base_length = min(120, max(40, force * 25))
        length = base_length * random.uniform(0.6, 1.4)
        thickness = random.choice([2, 2, 3, 3, 4])
        
        crack = OrganicCrack(impact_x, impact_y, angle, length, thickness, depth=0)
        crack.draw(floor_surface)
    
    # Tiny hairline cracks
    num_tiny = int(force * 0.5)
    for _ in range(num_tiny):
        angle = random.uniform(0, 2 * math.pi)
        tiny_length = random.uniform(10, 25)
        tiny_crack = OrganicCrack(impact_x, impact_y, angle, tiny_length, 1, depth=MAX_CRACK_DEPTH)
        tiny_crack.draw(floor_surface)

class Slider:
    """UI Slider control"""
    def __init__(self, x, y, width, min_val, max_val, initial_val, label):
        self.x = x
        self.y = y
        self.width = width
        self.height = 20
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.label = label
        self.dragging = False
        self.font = pygame.font.Font(None, 20)
    
    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_mouse_over(mouse_pos):
                self.dragging = True
                self.update_value(mouse_pos[0])
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_value(mouse_pos[0])
    
    def update_value(self, mouse_x):
        rel_x = max(0, min(mouse_x - self.x, self.width))
        ratio = rel_x / self.width
        self.value = self.min_val + ratio * (self.max_val - self.min_val)
    
    def is_mouse_over(self, mouse_pos):
        return (self.x <= mouse_pos[0] <= self.x + self.width and
                self.y <= mouse_pos[1] <= self.y + self.height)
    
    def draw(self, screen):
        # Background
        pygame.draw.rect(screen, GRAY, (self.x, self.y, self.width, self.height))
        
        # Fill
        fill_width = int((self.value - self.min_val) / (self.max_val - self.min_val) * self.width)
        pygame.draw.rect(screen, (100, 150, 255), (self.x, self.y, fill_width, self.height))
        
        # Border
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 2)
        
        # Label
        text = self.font.render(f"{self.label}: {self.value:.2f}", True, WHITE)
        screen.blit(text, (self.x, self.y - 20))

class Button:
    """UI Button"""
    def __init__(self, x, y, width, height, text, callback):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.callback = callback
        self.hovered = False
        self.font = pygame.font.Font(None, 24)
    
    def handle_event(self, event, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            self.callback()
            return True
        return False
    
    def draw(self, screen):
        color = UI_HOVER if self.hovered else UI_BG
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, WHITE, self.rect, 2)
        
        text_surf = self.font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

class Game:
    """Main game with UI"""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("SHATTER V2 - Interactive Simulator")
        self.clock = pygame.time.Clock()
        
        # Game state
        self.orbs = []
        self.floor_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.floor_surface.fill(DARK_GRAY)
        self.floor_deformations = []  # Track floor impact dents
        self.dragged_orb = None
        
        # Settings
        self.gravity = GRAVITY
        self.orb_size = ORB_SIZE
        self.show_ui = True
        self.show_fps = False
        self.show_debug = False  # Toggle for debug markers (red dots, blue rings)
        
        # UI Components
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 20)
        
        # Sliders
        self.gravity_slider = Slider(50, 70, 200, 0.1, 5.0, self.gravity, "Gravity")
        self.orb_size_slider = Slider(50, 120, 200, 10, 100, self.orb_size, "Orb Size")
        self.sliders = [self.gravity_slider, self.orb_size_slider]
        
        # Buttons
        self.clear_button = Button(50, 170, 150, 35, "Clear Canvas", self.clear_canvas)
        self.fps_button = Button(210, 170, 100, 35, "Toggle FPS", self.toggle_fps)
        self.buttons = [self.clear_button, self.fps_button]
    
    def clear_canvas(self):
        self.floor_surface.fill(DARK_GRAY)
        self.orbs.clear()
        self.floor_deformations.clear()
        self.dragged_orb = None
        print("[CLEAR] Canvas cleared")
    
    def toggle_fps(self):
        self.show_fps = not self.show_fps
    
    def spawn_orb(self, x, y):
        orb = Orb(x, y)
        orb.size = self.orb_size
        self.orbs.append(orb)
        print(f"[SPAWN] Orb #{len(self.orbs)} at ({x}, {y})")
    
    def find_orb_at_position(self, pos):
        for orb in reversed(self.orbs):
            if orb.is_mouse_over(pos):
                return orb
        return None
    
    def calculate_impact_force(self, orb):
        speed = max(orb.velocity.length(), 2)
        return speed * orb.size / 10
    
    def get_floor_height(self, x):
        """Get the actual floor height at X position (including all deformations)"""
        floor_y = FLOOR_Y
        
        # Add all deformation offsets at this X position (dents go DOWN, so positive offset)
        for deform in self.floor_deformations:
            floor_y += deform.get_offset_at(x)
        
        return floor_y
    
    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            # UI interactions
            if self.show_ui:
                for slider in self.sliders:
                    slider.handle_event(event, mouse_pos)
                for button in self.buttons:
                    if button.handle_event(event, mouse_pos):
                        continue
            
            # Orb interactions
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Skip if clicking on UI
                if self.show_ui and mouse_pos[1] < 220:
                    continue
                
                orb = self.find_orb_at_position(event.pos)
                if orb:
                    orb.start_drag()
                    self.dragged_orb = orb
                else:
                    self.spawn_orb(event.pos[0], event.pos[1])
            
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.dragged_orb:
                    self.dragged_orb.stop_drag()
                    self.dragged_orb = None
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragged_orb:
                    self.dragged_orb.drag_to(event.pos)
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self.show_ui = not self.show_ui
                elif event.key == pygame.K_c:
                    self.clear_canvas()
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
                    print(f"[DEBUG] Markers {'ON' if self.show_debug else 'OFF'}")
        
        return True
    
    def update(self):
        # Update settings from sliders
        self.gravity = self.gravity_slider.value
        self.orb_size = self.orb_size_slider.value
        
        # Update orbs
        for orb in self.orbs:
            # Pass floor height function so orbs can follow terrain contours
            orb.update(self.gravity, self.get_floor_height)
            
            # Only process impacts, NOT rolling
            if orb.just_impacted():
                impact_force = orb.last_impact_speed * (orb.size / 20)  # Scale by size too
                floor_x = int(orb.pos.x)
                
                # Calculate the Y offset at this X position (how deep the floor is here)
                floor_y_offset = 0
                for deform in self.floor_deformations:
                    floor_y_offset += deform.get_offset_at(floor_x)
                floor_y_for_cracks = int(floor_y_offset)
                
                # Define impact thresholds - STRICT requirements for impacts!
                NO_EFFECT_THRESHOLD = 8.0      # Below this: nothing happens (must be real fall)
                TINY_IMPACT_THRESHOLD = 12.0   # Small dent, no cracks
                SMALL_IMPACT_THRESHOLD = 18.0  # Small dent + few cracks
                NORMAL_IMPACT_THRESHOLD = 30.0 # Normal dent + normal cracks
                BIG_IMPACT_THRESHOLD = 50.0    # Big dent + many cracks
                # Above BIG: Huge dent + maximum cracks
                
                if impact_force < NO_EFFECT_THRESHOLD:
                    # Too gentle - no effect
                    print(f"[IMPACT] Too gentle ({impact_force:.1f}) - No effect")
                
                elif impact_force < TINY_IMPACT_THRESHOLD:
                    # Tiny impact - only tiny dent, no cracks
                    depth = impact_force * 0.4
                    radius = orb.size * 1.8  # Close to orb size
                    deform = FloorDeformation(floor_x, depth, radius)
                    self.floor_deformations.append(deform)
                    print(f"[TINY IMPACT] Force: {impact_force:.1f} | Tiny dent depth={depth:.1f}px radius={radius:.0f}px | Total dents: {len(self.floor_deformations)}")
                
                elif impact_force < SMALL_IMPACT_THRESHOLD:
                    # Small impact - small dent + few cracks
                    depth = impact_force * 0.6
                    radius = orb.size * 2.0  # Orb footprint + slight spread
                    deform = FloorDeformation(floor_x, depth, radius)
                    self.floor_deformations.append(deform)
                    # Draw cracks at the NEW deformed position (floor_y_offset + new depth)
                    crack_y = floor_y_for_cracks + int(depth)
                    generate_instant_cracks(self.floor_surface, floor_x, crack_y, impact_force * 0.3)
                    print(f"[SMALL IMPACT] Force: {impact_force:.1f} | Dent: {depth:.1f}px deep, {radius:.0f}px wide + cracks | Total dents: {len(self.floor_deformations)}")
                
                elif impact_force < NORMAL_IMPACT_THRESHOLD:
                    # Normal impact - deeper dent with orb-shaped indent
                    depth = min(20, impact_force * 0.8)
                    radius = orb.size * 2.2  # Tight to orb shape
                    deform = FloorDeformation(floor_x, depth, radius)
                    self.floor_deformations.append(deform)
                    # Draw cracks at the NEW deformed position
                    crack_y = floor_y_for_cracks + int(depth)
                    generate_instant_cracks(self.floor_surface, floor_x, crack_y, impact_force * 0.5)
                    print(f"[NORMAL IMPACT] Force: {impact_force:.1f} | Dent: {depth:.1f}px deep, {radius:.0f}px wide + cracks | Total dents: {len(self.floor_deformations)}")
                
                elif impact_force < BIG_IMPACT_THRESHOLD:
                    # Big impact - DEEP orb-shaped indent
                    depth = min(35, impact_force * 1.0)
                    radius = orb.size * 2.5  # Orb shape + impact spread
                    deform = FloorDeformation(floor_x, depth, radius)
                    self.floor_deformations.append(deform)
                    # Draw cracks at the NEW deformed position
                    crack_y = floor_y_for_cracks + int(depth)
                    generate_instant_cracks(self.floor_surface, floor_x, crack_y, impact_force * 0.7)
                    print(f"[BIG IMPACT] Force: {impact_force:.1f} | Dent: {depth:.1f}px deep, {radius:.0f}px wide + many cracks | Total dents: {len(self.floor_deformations)}")
                
                else:
                    # HUGE impact - VERY DEEP orb-shaped crater
                    depth = min(60, impact_force * 1.2)  # Much deeper!
                    radius = orb.size * 3.0  # Still close to orb shape
                    deform = FloorDeformation(floor_x, depth, radius)
                    self.floor_deformations.append(deform)
                    # Draw cracks at the NEW deformed position
                    crack_y = floor_y_for_cracks + int(depth)
                    generate_instant_cracks(self.floor_surface, floor_x, crack_y, min(impact_force, 60))
                    print(f"[MASSIVE IMPACT] Force: {impact_force:.1f} | Dent: {depth:.1f}px deep, {radius:.0f}px wide + MAX cracks! | Total dents: {len(self.floor_deformations)}")
        
        # ORB-TO-ORB COLLISION DETECTION (after all orbs have updated)
        for i, orb1 in enumerate(self.orbs):
            for orb2 in self.orbs[i+1:]:  # Only check each pair once
                if orb1.collides_with(orb2):
                    orb1.resolve_collision(orb2)
    
    def draw(self):
        # Clear
        self.screen.fill(BLACK)
        
        # Floor with cracks - DRAW FIRST (background layer)
        floor_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT - FLOOR_Y)
        self.screen.blit(self.floor_surface, (0, FLOOR_Y), floor_rect)
        
        # Draw deformed floor line ON TOP - ALWAYS checking deformations
        points = []
        step = 2  # Sample every 2 pixels for very smooth curve
        for x in range(0, SCREEN_WIDTH + 1, step):
            y_offset = 0
            # Sum all deformations at this x position (dents push DOWN)
            for deform in self.floor_deformations:
                y_offset += deform.get_offset_at(x)
            points.append((x, FLOOR_Y + y_offset))
        
        # Draw the floor line itself (straight or deformed) - SHOWS CRACKS UNDERNEATH
        if len(points) > 1:
            pygame.draw.lines(self.screen, GRAY, False, points, 4)  # Thicker line for visibility
        
        # DEBUG: Draw deformation centers as markers (toggle with 'D' key)
        if self.show_debug:
            for deform in self.floor_deformations:
                # Calculate actual floor depth at this X (sum of all deformations)
                actual_floor_y = self.get_floor_height(deform.x)
                
                # Draw red circle at ACTUAL deformed depth
                pygame.draw.circle(self.screen, (255, 100, 100), (int(deform.x), int(actual_floor_y)), 5)
                # Draw deformation radius outline at actual depth too
                pygame.draw.circle(self.screen, (100, 100, 255), (int(deform.x), int(actual_floor_y)), int(deform.radius), 1)
        
        # Orbs
        for orb in self.orbs:
            orb.draw(self.screen)
        
        # UI
        if self.show_ui:
            self.draw_ui()
        
        # FPS
        if self.show_fps:
            fps_text = self.small_font.render(f"FPS: {int(self.clock.get_fps())}", True, WHITE)
            self.screen.blit(fps_text, (SCREEN_WIDTH - 80, 10))
        
        pygame.display.flip()
    
    def draw_ui(self):
        # Background panel
        pygame.draw.rect(self.screen, UI_BG, (0, 0, SCREEN_WIDTH, 230))
        pygame.draw.rect(self.screen, WHITE, (0, 0, SCREEN_WIDTH, 230), 2)
        
        # Title
        title = self.font.render("SHATTER CONTROLS", True, WHITE)
        self.screen.blit(title, (10, 10))
        
        # Instructions
        help_text = self.small_font.render("TAB=Toggle UI | D=Debug | Click=Spawn | Drag=Move Orb", True, (150, 150, 150))
        self.screen.blit(help_text, (10, 35))
        
        # Draw sliders
        for slider in self.sliders:
            slider.draw(self.screen)
        
        # Draw buttons
        for button in self.buttons:
            button.draw(self.screen)
        
        # Stats
        stats = self.small_font.render(f"Orbs: {len(self.orbs)}", True, WHITE)
        self.screen.blit(stats, (270, 70))
    
    def run(self):
        running = True
        print("[READY] Interactive simulator started!")
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        print("[EXIT] Simulation ended")
        pygame.quit()

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()
