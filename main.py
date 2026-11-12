import os
from random import randint, uniform

from kivy import platform
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
from kivy.metrics import dp
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivymd.app import MDApp
from kivymd.uix.dialog import (
    MDDialog,
    MDDialogButtonContainer,
    MDDialogHeadlineText,
    MDDialogSupportingText,
)
from kivymd.uix.button import MDButton, MDButtonText
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.widget import MDWidget


FPS = 60
SHIP_SPEED = dp(5)
PLAYER_BULLET_SPEED = dp(10)
ENEMY_BULLET_SPEED = dp(5)
ENEMY_SPEED = dp(2)
ENEMY_SPAWN_INTERVAL = 1.5
DIR_UP = 1
DIR_DOWN = -1


class Starfield(Widget):
    """Lightweight animated starfield drawn without extra image assets."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stars = []
        with self.canvas:
            Color(0.35, 0.75, 1, 0.8)
            self.star_shapes = [Ellipse(size=(dp(1.5), dp(1.5))) for _ in range(65)]
        self.bind(size=self._place_stars, pos=self._place_stars)
        self._place_stars()
        self._event = Clock.schedule_interval(self._tick, 1 / 30)

    def _place_stars(self, *_args):
        if not self.width or not self.height:
            return
        self.stars = [
            [uniform(0, self.width), uniform(0, self.height), uniform(dp(12), dp(55)), uniform(0.7, 2.2)]
            for _ in self.star_shapes
        ]
        self._sync_shapes()

    def _sync_shapes(self):
        for star, shape in zip(self.stars, self.star_shapes):
            shape.pos = (self.x + star[0], self.y + star[1])
            shape.size = (star[3], star[3])

    def _tick(self, dt):
        for star in self.stars:
            star[1] -= star[2] * dt
            if star[1] < 0:
                star[0] = uniform(0, self.width)
                star[1] = self.height
        self._sync_shapes()


class MainScreen(MDScreen):
    def start_game(self):
        game = self.manager.get_screen("game")
        game.reset_game()
        self.manager.current = "game"


class GameOverScreen(MDScreen):
    def retry(self):
        game = self.manager.get_screen("game")
        game.reset_game()
        self.manager.current = "game"

    def return_to_menu(self):
        game = self.manager.get_screen("game")
        game.reset_game()
        self.manager.current = "main"


class Shot(Image):
    def __init__(self, direction, owner, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.owner = owner


class EnemyShip(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.frame = 0
        self.game = None

    def update(self):
        self.y -= self.game.enemy_speed
        self.frame += 1
        if self.frame % 105 == 0 and self.game.running:
            bullet = Shot(DIR_DOWN, owner="enemy")
            bullet.center_x = self.center_x
            bullet.top = self.y
            self.game.add_bullet(bullet)


class GameScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.eventkeys = {}
        self.cartridge = []
        self.enemies = []
        self.lives = 5
        self.score = 0
        self.enemy_speed = ENEMY_SPEED
        self.running = False
        self.update_event = None
        self.spawn_event = None
        self.pause_dialog = None
        self._shot_cooldown = 0

    def on_enter(self, *_args):
        Window.bind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self._start_timers()

    def on_leave(self, *_args):
        Window.unbind(on_key_down=self._on_key_down, on_key_up=self._on_key_up)
        self.running = False
        self._stop_timers()

    def _on_key_down(self, _window, key, *_args):
        names = {276: "left", 275: "right", 273: "shot", 32: "shot", 97: "left", 100: "right"}
        if key in names:
            self.pressKey(names[key])
            return True
        return False

    def _on_key_up(self, _window, key, *_args):
        names = {276: "left", 275: "right", 273: "shot", 32: "shot", 97: "left", 100: "right"}
        if key in names:
            self.releaseKey(names[key])
            return True
        return False

    def _start_timers(self):
        if self.update_event is None:
            self.update_event = Clock.schedule_interval(self.update, 1 / FPS)
        if self.spawn_event is None:
            self.spawn_event = Clock.schedule_interval(self.spawn_enemy, ENEMY_SPAWN_INTERVAL)
        self.running = True

    def _stop_timers(self):
        if self.update_event is not None:
            self.update_event.cancel()
            self.update_event = None
        if self.spawn_event is not None:
            self.spawn_event.cancel()
            self.spawn_event = None

    def spawn_enemy(self, _dt):
        if not self.running or not self.ids.front.width:
            return
        enemy = EnemyShip()
        enemy.game = self
        enemy.x = randint(0, max(0, int(self.ids.front.width - enemy.width)))
        enemy.y = self.ids.front.height
        self.enemies.append(enemy)
        self.ids.front.add_widget(enemy)

    def add_bullet(self, bullet):
        self.cartridge.append(bullet)
        self.ids.front.add_widget(bullet)

    def update(self, dt):
        if not self.running:
            return
        self._shot_cooldown = max(0, self._shot_cooldown - dt)
        for key, pressed in tuple(self.eventkeys.items()):
            if pressed and key == "left":
                self.move_left()
            elif pressed and key == "right":
                self.move_right()
            elif pressed and key == "shot" and self._shot_cooldown == 0:
                self.shot()
                self._shot_cooldown = 0.22

        for bullet in self.cartridge[:]:
            speed = PLAYER_BULLET_SPEED if bullet.owner == "player" else ENEMY_BULLET_SPEED
            bullet.y += speed * bullet.direction
            if bullet.y > self.ids.front.height or bullet.top < 0:
                self.remove_bullet(bullet)

        for enemy in self.enemies[:]:
            enemy.update()
            if enemy.top < 0:
                self.remove_enemy(enemy)
                self.take_damage()
                if not self.running:
                    return

        for enemy in self.enemies[:]:
            if self.ids.ship.collide_widget(enemy):
                self.remove_enemy(enemy)
                self.take_damage()
                if not self.running:
                    return
        self.check_collisions()

    def check_collisions(self):
        for bullet in self.cartridge[:]:
            if bullet.owner == "player":
                for enemy in self.enemies[:]:
                    if enemy.collide_widget(bullet):
                        self.remove_enemy(enemy)
                        self.remove_bullet(bullet)
                        self.add_score(10)
                        if not self.running:
                            return
                        break
            elif self.ids.ship.collide_widget(bullet):
                self.remove_bullet(bullet)
                self.take_damage()
                if not self.running:
                    return

    def remove_bullet(self, bullet):
        if bullet in self.cartridge:
            self.cartridge.remove(bullet)
        if bullet.parent is not None:
            bullet.parent.remove_widget(bullet)

    def remove_enemy(self, enemy):
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        if enemy.parent is not None:
            enemy.parent.remove_widget(enemy)

    def add_score(self, points):
        self.score += points
        self._refresh_hud()
        if self.score >= 1000:
            self.win()

    def _refresh_hud(self):
        self.ids.score_label.text = f"SCORE  {self.score:04d}"
        self.ids.lives_label.text = f"LIVES  {self.lives}"

    def take_damage(self):
        self.lives = max(0, self.lives - 1)
        self._refresh_hud()
        if self.lives == 0:
            self.lose()

    def lose(self):
        self.finish_game("MISSION FAILED", (1, 0.35, 0.5, 1))

    def win(self):
        self.finish_game("MISSION COMPLETE", (0.3, 0.9, 0.65, 1))

    def finish_game(self, title, color):
        self.running = False
        self.eventkeys.clear()
        self._stop_timers()
        over = self.manager.get_screen("game_over")
        over.ids.result_title.text = title
        over.ids.result_title.text_color = color
        over.ids.final_score.text = f"SCORE  {self.score:04d}"
        self.manager.current = "game_over"

    def reset_game(self):
        self._stop_timers()
        for bullet in self.cartridge[:]:
            self.remove_bullet(bullet)
        for enemy in self.enemies[:]:
            self.remove_enemy(enemy)
        self.eventkeys.clear()
        self.lives = 5
        self.score = 0
        self.enemy_speed = ENEMY_SPEED
        self._shot_cooldown = 0
        self._refresh_hud()
        if "ship" in self.ids and "front" in self.ids:
            ship = self.ids.ship
            front = self.ids.front
            ship.x = max(0, (front.width - ship.width) / 2)
            ship.y = dp(105)

    def pressKey(self, key):
        self.eventkeys[key] = True

    def releaseKey(self, key):
        self.eventkeys[key] = False

    def move_left(self):
        ship = self.ids.ship
        ship.x = max(0, ship.x - SHIP_SPEED)

    def move_right(self):
        ship = self.ids.ship
        ship.x = min(max(0, self.ids.front.width - ship.width), ship.x + SHIP_SPEED)

    def shot(self):
        bullet = Shot(DIR_UP, owner="player")
        bullet.center_x = self.ids.ship.center_x
        bullet.y = self.ids.ship.top
        self.add_bullet(bullet)

    def show_pause(self):
        if not self.running:
            return
        self.running = False
        self._stop_timers()
        if self.pause_dialog is None:
            self.pause_dialog = MDDialog(
                MDDialogHeadlineText(text="PAUSED"),
                MDDialogSupportingText(text="Take a breath, pilot."),
                MDDialogButtonContainer(
                    MDWidget(),
                    MDButton(
                        MDButtonText(text="RESUME"),
                        style="text",
                        on_release=lambda *_: self.pause_dialog.dismiss(),
                    ),
                    spacing="8dp",
                ),
                on_dismiss=self.resume_game,
            )
        self.pause_dialog.open()

    def resume_game(self, *_args):
        if self.manager.current == "game":
            self._start_timers()


class ShooterApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        manager = MDScreenManager()
        manager.add_widget(MainScreen(name="main"))
        manager.add_widget(GameScreen(name="game"))
        manager.add_widget(GameOverScreen(name="game_over"))
        return manager


if platform != "android":
    Window.size = (400, 700)

os.chdir(os.path.dirname(os.path.abspath(__file__)))
ShooterApp().run()
