import pygame
import PySimpleGUI as sg
from PIL import Image, ImageTk
import base64
from io import BytesIO
import random
#import time
import os.path
import pathlib
from dataclasses import dataclass

# import platform
import xml.etree.ElementTree as ET

# helper functions

def pygame2tk(pygameimage):
    """converts a pygame surface to an Tkinter image,
       usable as a data source for PySimpleGUI Image widgets (tkinter)

    returns a Tkinter image
    """
    #pygameimage = pygame.image.load(IMAGEPATH)
    w, h = pygameimage.get_rect().width, pygameimage.get_rect().height
    pygame_surface = pygame.transform.smoothscale(pygameimage, (w, h))
    image_str = pygame.image.tostring(pygame_surface, 'RGBA')
    img = Image.frombytes('RGBA', (w, h), image_str)
    tkimage = ImageTk.PhotoImage(img)
    return tkimage

def pygame2base64(pygameimage):
    """takes pygame image, returns base64 string to use inside pysimplegui graph element"""
    w, h = pygameimage.get_rect().width, pygameimage.get_rect().height
    pygame_surface = pygame.transform.smoothscale(pygameimage, (w, h))
    image_str = pygame.image.tostring(pygame_surface, 'RGBA')
    img = Image.frombytes('RGBA', (w, h), image_str)
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    byte_data = img_buffer.getvalue()
    base64_str = base64.b64encode(byte_data)
    return base64_str

def tk2pygame(tkimage):
    """converts a tkinter image into an pygame surface"""
    img = ImageTk.getimage(tkimage)
    # img = Image.open(IMAGEPATH)
    w, h = img.width, img.height
    pygameimage = pygame.image.frombuffer(img.tobytes(), (w, h), "RGBA")
    return pygameimage

# ---------------------------

class Game:
    gold = 1400
    towerdata = {}  # name: dataclass-instance
    sell_factor = 0.5
    #stuff_to_buy = {
    #    "simple tower": 50,
    #    "ice tower": 65,
    #    "sniper tower": 75,
    #    "minelayer tower": 75,
    #}
    my_towers = {}
    level = 1


@dataclass
class Tower:
    name: str
    sprite_name: str = None # name of sprite for tower
    barrel_name: str = None # name of barrel sprite expected to look north, rotation point is at south
    bullet_name: str = None # name of bullet sprite
    bullet_type: str = None # bullet, rocket, laser, ice etc.
    sprite_size: int = None # pixel width == height of sprite in pixel, will be transformed to this width
    barrels: int = 1  # how many barrels
    damage: int = 100
    splash_radius = 1       # pixel
    range_min: int = 25
    range_max: int = 150
    reload_time: float = 2.5 # seconds
    rotation_speed: float = 90.0 # degrees / second
    bullet_speed: float = 100  # pixcel / second
    bullet_error: float = 1.0 # degrees
    salvo: int = 1 # how many bullets per salvo per barrel
    salvo_delay: float = 0.1 # time between bullets of a salvo from the same barrel
    price: int = 100
    upgrade_name: str = None # can be upgraded to this name
    upgrade_time: float = 5.0 # seconds to upgrade
    hitpoints = 200

    def __post_init__(self):
        Game.towerdata[self.name] = self

# --------- define Tower types ------------
Tower(name="simple",
      sprite_name="barrelGreen_top.png",
      barrel_name="tankGreen_barrel2.png",
      bullet_name="bulletGreen3_outline.png",
      bullet_type="bullet",
      price = 100,
      range_min = 25,
      range_max = 100,
      )

Tower(name="medium",
      sprite_name="barrelRed_top.png",
      barrel_name="tankGreen_barrel2.png",
      bullet_name="bulletRed3_outline.png",
      bullet_type="bullet",
      price = 200,
      range_min = 50,
      range_max = 200,
      )

#print("towerdata:", Game.towerdata)

class Viewer:
    # source_path = pathlib.Path.cwd() # get current work directory
    resolution = (1024, 800)  # pygame window size in pixel.
    backgroundimage = None
    #maskimage = None  # test maskgroup instead
    # flamenames = []
    # flamefigures = []
    flame_images = []
    pause = False  # amount of seconds when pygame can not update because a popup is blocking etc
    # arrowfigures = []
    # OUT_OF_SIGHT = (-200,-200)

    # circles = []  # container for shooting radius of towers
    # towers = []   # container for towers
    my_towers = []
    # towernames = []
    # ------- pygame -----
    # ---- pygame sprite groups ----
    allgroup = pygame.sprite.LayeredUpdates()
    tankgroup = pygame.sprite.Group()
    towergroup = pygame.sprite.Group()
    shellgroup = pygame.sprite.Group()
    cursorgroup = pygame.sprite.GroupSingle()
    maskgroup = pygame.sprite.GroupSingle()
    placemodusgroup = pygame.sprite.GroupSingle()
    images = {}
    # -------- gui --------
    layout = [
        [
            #sg.Text(
            #    "testing graph"
            #),  # sg.Button("click me", key="button1"), sg.Button("kill"),
            #sg.Button("fire"),
            sg.Text(
                "play the game",
                size=(20, 1),
                text_color="yellow",
                key="hint",
                font=("Arial", 17, "bold"),
            ),
            sg.Column([
                [sg.Text("waypoints:"), ],
                [sg.Button("click to set waypoints", key="waypointbutton", size=(18, 1)),],
                [sg.Button("delete waypoint"),],
                [sg.Button("export waypoints")],
            ]),
            sg.Column([

                [sg.Listbox(values=[], size=(10, 5), key="waypointliste"),],
            ]),
            sg.Graph(
                canvas_size=(200, 100),
                key="canvas1",
                graph_bottom_left=(0, 100),
                graph_top_right=(200, 0),
                enable_events=True,
                background_color="purple",
            ),

        ],
        [

            sg.Text("shopping:"),
            sg.Checkbox("show radius", default=False, key="show_radius"),
            sg.Text("status: "),
            sg.Text("buy something", key="status_text"),
        ],
        [
            sg.Image(key="towerimage", size=(200, 200)),
            sg.Table(
                #Game.stuff_to_buy.items(),
                [[tower.name, tower.price] for tower in Game.towerdata.values() ],
                headings=["turret name", "price"],
                key="shopping",
                size=(20, 5),
                select_mode=sg.TABLE_SELECT_MODE_BROWSE,
            ),
            sg.Button("load image"),
            sg.Column(
                layout=[
                    [sg.Text("$:"),
                     sg.Text(Game.gold, key="gold_text"),],
                    [sg.Button("buy")],
                    [sg.Button("sell")],
                    [sg.Checkbox("pause", key="pause", enable_events=True)],
                ]
            ),
            sg.Table(
                my_towers,
                headings=["turret name", "buy $", "sell $"],
                #col_widths=(35, 5, 5),
                key="my_towers",
                size=(50, 5),
                select_mode=sg.TABLE_SELECT_MODE_BROWSE,
            ),
        ],
        [
            sg.Text("xxx", key="circles_display"),
            sg.Text("pygame mouse xy: "),
            sg.Text("", key="show_mouse_pos_pygame"),
            sg.Text("absolute mouse xy: "),
            sg.Text("", key="show_mouse_pos_absolute"),
            sg.Text("time.playtime: "),
            sg.Text("0", size=(10, 1), key="playtime1"),
            sg.Text("pygame.playtime: "),
            sg.Text("0", size=(10, 1), key="playtime2"),
        ],
        # [ sg.Graph(canvas_size=resolution,
        #          graph_bottom_left=(0,resolution[1]),  # use pygame coordinate system with topleft = (0,0)
        #          graph_top_right=(resolution[0],0),
        #          enable_events=True, # to get mouse coordinates from Tkinter
        #          motion_events=True, # create graph key + '+MOVE' event when mouse moves
        #          drag_submits=True, # super important!!!!
        #          key = "canvas2",)
        #
        # ],
    ]

    def __init__(self):
        self.window = sg.Window(
            "hallo",
            layout=Viewer.layout,
            size=(800, 300),
            location=(200, 20),  # absolute coordinate topleft corner of GUI window
            return_keyboard_events=True,
            finalize=True,
        )

        os.environ[
            "SDL_VIDEO_WINDOW_POS"
        ] = "200,250"  # this is the ABSOLUTE position of the pygame window

        # ----
        if sg.running_linux():
            os.environ["SDL_VIDEODRIVER"] = "x11"  # linux needs x11 here
        elif sg.running_windows():
            os.environ["SDL_VIDEODRIVER"] = "windib"
        else:
            print("error - only tested for Linux and Windows.trying out linux code... ")
            os.environ["SDL_VIDEODRIVER"] = "x11"  # linux needs x11 here
        # ----------------------------- PyGame Code -----------------------------
        # pygame display set_mode flags. combine using the pipe |
        # --------------- this does the pygame init? --------------------
        self.screen = pygame.display.set_mode(
            size=Viewer.resolution,
            # flags=pygame.NOFRAME,
            depth=0,
            display=0,
            vsync=0,
        )
        self.mysurface = pygame.display.get_surface()
        self.my_id = pygame.display.get_wm_info()
        #print("surface:", self.mysurface)
        #print("id:", self.my_id)
        self.screen.fill(pygame.Color(255, 255, 255))

        pygame.fastevent.init()  # use fast event instead of pygame event
        # pygame.init()
        # pygame.display.init() # already done by display.set_mode?

        Tank.groups = Viewer.allgroup, Viewer.tankgroup
        PlacemodusTower.groups = Viewer.allgroup, Viewer.placemodusgroup
        MaskSprite.groups = Viewer.maskgroup

        self.load_resources()
        # ----- sprite groups ----
        # self.allgroup = pygame.sprite.LayeredUpdates()  # for drawing with layers
        # self.tankgroup = pygame.sprite.Group()
        # set waypoints
        self.waypoints = []
        # ---- test tank ---
        self.enemy1 = Tank(
            image_name="tank_sand.png",
            correction_angle=90,
            move_speed=0,
            acceleration=2,
        )
        # the tower image should be appear in the pygame window (canvas2) as well as in the pysimplegui graph (canvas1)
        self.tower_image = Viewer.images["barrelRust_top.png"][0]
        # tower_image_tk = pathlib.Path(""barrelRust_top.png"
        self.window["canvas1"].draw_circle(
            center_location=(50, 50), radius=40, line_color="yellow"
        )
        self.window["canvas1"].draw_image(
            data=pygame2base64(Viewer.images["barrelRust_top.png"][0]),
            #filename="data/tanks/PNG/Retina/barrelRust_top.png",    ## works but needs file
            #data=pygame2tk(Viewer.images["barrelRust_top.png"][1]), ## does nothing
            location=(50, 50),
        )
        #self.window["towerimage"].update(data = pygame2tk(Viewer.images["barrelRust_top.png"][0]))

        # ----- clock etc ---
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.playtime1 = 0.0  # tkinter
        self.playtime2 = 0.0  # pygame
        duration_all_flames = 1.0
        self.duration_one_flame_frame = duration_all_flames / len(Viewer.flame_images)
        # self.end_flame = time.time() + duration_all_flames/len(Viewer.flamenames) #full animation in 1 second
        self.run()

    def load_resources(self):
        """load all Images from data/tanks/Spritesheet/allSprites_retina.png
         as described in allSprites_retina.xml into pygame image objects
        """
        # load pygame stuff
        # gather all flame pictures into Viewer.flameimages list
        # ------------- load maps ---------
        Viewer.backgroundimage = pygame.image.load("data/maps/petermap2.png")
        #Viewer.maskimage = pygame.image.load("data/maps/petermap2_mask.png")
        # create mask sprite:
        MaskSprite(image=pygame.image.load("data/maps/petermap2_mask.png"))


        #-------------- load tileset, sprites etc ------------

        p = pathlib.Path("data")
        for file in p.iterdir():
            # print(file, file.stem, file.suffix)
            if file.stem.startswith("flame") and file.suffix == ".png":
                Viewer.flame_images.append(pygame.image.load(str(file)).convert_alpha())

        source_xml = pathlib.Path(
            "data", "tanks", "Spritesheet", "allSprites_retina.xml"
        )
        source_png = pathlib.Path(
            "data", "tanks", "Spritesheet", "allSprites_retina.png"
        )
        Viewer.big_image = pygame.image.load(str(source_png)).convert_alpha()
        # for texture in root.iter("SubTexture"):
        tree = ET.parse(source_xml)
        root = tree.getroot()
        # Viewer.images = {}
        for texture in root.iter("SubTexture"):
            # print(texture.attrib)
            # xml file:: <SubTexture name="barrelBlack_side.png" x="1016" y="510" width="40" height="56"/>
            # texture.attrib:  {name:"barrelBlack_side.png", x:"1016", ... }
            raw = texture.attrib
            cropped_image = Viewer.big_image.subsurface(
                pygame.Rect(
                    int(raw["x"]), int(raw["y"]), int(raw["width"]), int(raw["height"])
                )
            )  #  {"x":raw["x"], "y":raw["y"], "width":raw["width"], "height":raw["height"]}
            # resize the cropped image to half the original size
            half_image = pygame.transform.scale(
                cropped_image, (int(raw["width"]) // 2, int(raw["height"]) // 2)
            )
            Viewer.images[raw["name"]] = (half_image, cropped_image)

        # print(Viewer.images)
        # test blit tank into pygame
        # pygame.display.update()  # need to be called each loop
        # -------------   load pygame images ----
        # for i in range(1,9):
        #    Viewer.flame_images.append(pygame.image.load(os.path.join("data", f"flame{i}.png")))

    def run(self):
        i = 0
        end_fire = 0
        # now = time.time()
        # next_frame = time.time() + self.duration_one_flame_frame
        next_frame = self.playtime2 + self.duration_one_flame_frame
        running = True
        waypointmodus = False
        place_tower_modus = False
        my_tower = None
        backgroundfile = None
        red_cross = True
        bigmask = Viewer.maskgroup.sprite

        while running:
            # pysimpleGui
            # -------------- tkinter / pysimplegui mainloop ------------------------
            event, values = self.window.read(timeout=1)

            if event == "delete waypoint":
                # waypoints = self.window["waypointliste"].get_list_values()
                selected = self.window["waypointliste"].get_indexes()
                for i in selected:
                    self.waypoints.pop(i)
                self.window["waypointliste"].update(values=self.waypoints)
                for tank in Viewer.tankgroup:
                    tank.waypoints = self.waypoints
                    if len(self.waypoints) > 0:
                        tank.waypoint = self.waypoints[0]
                    else:
                        tank.waypoint = None
                    tank.i = 0
            if event == "load image":
                backgroundfile = sg.popup_get_file("please choose background image file")
                if backgroundfile is None:
                    continue
                Viewer.backgroundimage = pygame.image.load(backgroundfile)
                Viewer.maskimage = pygame.image.load(backgroundfile[:-4]+"_mask.png")
            if event == "export waypoints":
                # get values of Listbox "waypointliste"
                my_waypoints = self.window["waypointliste"].get_list_values() # list
                if backgroundfile is None:
                    sg.PopupError("please select backgroundimage before exporting waypoints")
                    continue
                pathlib.Path(backgroundfile).stem
                waypointfilename = "data/maps/" + pathlib.Path(backgroundfile).stem + ".txt"
                with open(waypointfilename, "w") as myfile:
                    for line in my_waypoints:
                        x,y = line
                        myfile.write( f"{x},{y}\n")
                sg.PopupOK("waypointfile written")



            if event == "waypointbutton":
                if not waypointmodus:
                    waypointmodus = True
                    self.window["waypointbutton"].update(text="done")
                else:
                    waypointmodus = False
                    self.window["waypointbutton"].update(text="set waypoints")
                    # done wurde geklickt
                    # alle tanks sollen diese waypoints übernehmen
                    for tank in Viewer.tankgroup:
                        tank.waypoints = self.waypoints
                        if len(self.waypoints) > 0:
                            tank.waypoint = self.waypoints[0]

            if event == "pause":
                Viewer.pause = values["pause"]
                print("pause is now", Viewer.pause)

            #if event == "canvas1":
                #print("canvas 1 click: ", values["canvas1"])

            if event == "buy":
                # what kind of tower is selected in the shop_list?
                tower_to_buy = values["shopping"][0]  # is index of row, first column = name
                # print("selected index:", tower_to_buy)
                # print(list(self.window["shopping"].get())[tower_to_buy])
                what = list(self.window["shopping"].get())[tower_to_buy]
                # my_towers.append(what)

                buy_price = int(what[1])
                if Game.gold - buy_price < 0:
                    # Viewer.pause = True
                    sg.PopupError("you can not afford to buy this", non_blocking=True)
                    # Viewer.pause = False
                    continue
                Game.gold -= buy_price

                self.window["gold_text"].update(Game.gold)
                sell_price = round(buy_price * Game.sell_factor, 0)
                what = [what[0], what[1], sell_price]
                Viewer.my_towers.append(what)
                self.window["my_towers"].update(values=Viewer.my_towers)
                place_tower_modus = True
                #my_tower = Tower(image_name="barrelBlack_top.png" )
                # ----- my tower for pygame
                #my_tower = Game.towerdata[what[0]]  # the dataclass instance
                my_data = Game.towerdata[what[0]]
                my_tower = PlacemodusTower(image_name=my_data.sprite_name)

                # break

            if event == "sell":
                what = values["my_towers"]
                #print(what)

            # --------- timeout event, does the pygame loop ---------------
            if event == sg.TIMEOUT_EVENT:

                # get mouse location: window.mouse_location() returns ABSOLUTE mouse position of whole screen!
                self.window["show_mouse_pos_absolute"].update(
                    self.window.mouse_location()
                )
                self.window["show_mouse_pos_pygame"].update(pygame.mouse.get_pos())
                # for event in pygame.event.get():
                # print("pygame_event:", event)
                #    if event in

                # ---- pygame part (mainloop ) ----------
                pygame_events = pygame.event.get()
                for e in pygame_events:
                    #if e.type == pygame.WINDOWENTER:
                    #    print("-----------------------------------------------------")
                    #    print("----------- mouse entered pygame window -------------")
                    #    print("-----------------------------------------------------")
                    #if e.type == pygame.WINDOWLEAVE:
                    #    print("============ mouse left pygame window =============")
                    if e.type == pygame.QUIT:
                        print("bye bye says pygame")
                        running = False
                    #if e.type == pygame.WINDOWMOVED:
                    #    print("** ** ** window moved ** * ** ** **")
                    #if e.type == pygame.MOUSEWHEEL:
                    #    print(
                    #        "wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwheeeeeeeeeeeeeeeeeeeeeeeeeeelllllllllllllll"
                    #    )
                    if (e.type == pygame.MOUSEBUTTONUP) and waypointmodus:
                        # put the pygame mouse position into the waypointlist
                        # waypoints = self.window["waypointliste"].get_list_values()
                        self.waypoints.append(pygame.mouse.get_pos())
                        self.window["waypointliste"].update(values=self.waypoints)

                    if (e.type == pygame.MOUSEBUTTONDOWN):

                        # ---------- place tower --------------
                        if my_tower is not None:
                            if not red_cross:
                                #place_tower_modus = False
                                my_tower.placemodus = False
                                # create Tower here
                                my_tower.kill()
                                my_tower = None
                                red_cross = False


                    # print("xx",e)
                    # print("dict:", e.dict)
                    # print("type:", e.type)

                pressed_keys = pygame.key.get_pressed()
                #if any(pressed_keys):
                    #print([k for k in pressed_keys if k])
                    #if pressed_keys[pygame.K_a]:
                    #    print("aaaaaaaaaaaaaaaa is pressed")

                # pygame_fast_events = pygame.fastevent.get()
                # print(pygame_fast_events)
                # if "Mouse" in pygame_fast_events:
                #    break

                pygame.display.set_caption(
                    f"mousepos: {pygame.mouse.get_pos()} tank speed: {self.enemy1.move_speed}"
                )

                # ----- pygame clock tick ----
                milliseconds = self.clock.tick(self.fps)  #
                if Viewer.pause:
                    seconds = 0
                    # print("in pause.......")
                else:
                    # print("not in pause")
                    seconds = milliseconds / 1000
                self.playtime2 += seconds

                # update both times
                # self.window["playtime1"].update(self.playtime1)
                self.window["playtime2"].update(self.playtime2)

                # =================================== CLEAR SCREEN ===========================
                # -----pygame clear screen -----
                if Viewer.backgroundimage is None:
                    self.screen.fill((255, 255, 255)) # fill screen white
                else:
                    self.screen.blit(Viewer.backgroundimage, (0,0))
                # mousepointer is circle ?
                if my_tower is not None:
                    if bigmask:
                        # if Viewer.maskgroup(): # any strite at all inside maskgropu?
                        collisions = pygame.sprite.collide_mask(bigmask, my_tower)
                        if collisions is None:
                            red_cross = False
                        else:
                            red_cross = True
                    #print(red_cross)
                    color = (random.randint(0,255),random.randint(0,255),random.randint(0,255) )
                    pygame.draw.circle(self.screen, color, pygame.mouse.get_pos(), 50,2)
                    if red_cross:
                        pygame.draw.line(self.screen, (255,0,0),
                                         pygame.mouse.get_pos()+pygame.Vector2(-50,-50),
                                         pygame.mouse.get_pos()+pygame.Vector2(50,50),
                                         4)
                        pygame.draw.line(self.screen, (255, 0, 0),
                                         pygame.mouse.get_pos() + pygame.Vector2(-50, 50),
                                         pygame.mouse.get_pos() + pygame.Vector2(50, -50),
                                         4)





                # ----- draw waypoint circles and lines ------
                if len(self.waypoints) == 1:
                    pygame.draw.circle(self.screen, (255, 0, 255), self.waypoints[0], 5)
                elif len(self.waypoints) > 1:
                    for wp in self.waypoints:
                        pygame.draw.circle(self.screen, (255, 0, 255), wp, 5)
                    for j, wp in enumerate(self.waypoints[1:], 1):
                        old = self.waypoints[j - 1]
                        pygame.draw.line(self.screen, (128, 0, 128), old, wp, 2)
                #  ----------- draw flame ----
                self.screen.blit(Viewer.flame_images[i], (200, 200))
                # ------ draw fixed test tower -----
                self.screen.blit(self.tower_image, (400, 100))
                # self.screen.blit(self.photo1, (100,350)) # works perfect

                # blit big tank
                # self.screen.blit(Viewer.images["tankBody_blue.png"][0] , (400,300))
                # --------- update all sprites ----------------
                self.allgroup.update(seconds)

                # ---------- blit all sprites --------------
                self.allgroup.draw(self.screen)
                # ---- special for tanks only -----
                # --- blit red line from each tank to his next waypoint
                for tank in Viewer.tankgroup:
                    if tank.waypoint is not None:
                        # print("line from", tank.pos, "to", tank.waypoint)
                        pygame.draw.line(
                            self.screen, (255, 0, 0), tank.pos, tank.waypoint, 1
                        )

                ## doenst not work: print(pygame.mouse.get_pos())
                pygame.display.update()  # need to be called each loop
                # pygame.display.flip()

                # -----flame animation-------
                # if now > next_frame:
                #    next_frame = now + self.duration_one_flame_frame
                if self.playtime2 > next_frame:
                    next_frame = self.playtime2 + self.duration_one_flame_frame
                    i += 1
                    if i == len(Viewer.flame_images):
                        i = 0

            if event == sg.WINDOW_CLOSED:
                break

        self.window.close()

class MaskSprite(pygame.sprite.Sprite):
    """A bitmap with the same size as the background.
       with visible pixels wehere building is forbidden (rivers, streets etc).
       Is used as a pygame sprite in collision detection when placing towers.
       Is never blitted to screen.
    """

    def __init__(self, image):
        pygame.sprite.Sprite.__init__(self, self.groups )
        self.image = image
        self.rect = self.image.get_rect()
        self.mask =  pygame.mask.from_surface(self.image)


class VectorSprite(pygame.sprite.Sprite):
    """base class for sprites. this class inherits from pygame sprite class"""

    number = 0  # unique number for each sprite
    # images = []
    # book = {} # { number, Sprite }

    def __init__(
        self,
        image_name = None,
        image = None,
        correction_angle=0,  # if the images originally "looks" at right, this remains 0. if it looks "up", must be -90 etc.
        pos=None,
        move_direction=None,
        move_speed=0.0,
        move_speed_max=150,  # pixel/second
        rotation_speed=0,
        rotation_speed_max=90,  # grad/second
        acceleration=0,
        boss_number=None,
        _layer=0,
        look_angle=0,  # degrees
        radius=0,
        hitpoints=100,
        hitpointsfull=100,
        age=0,
        max_age=None,
        max_distance=None,
        area=None,  # pygame.Rect,
        animation_images=None,
        time_for_each_frame=None,
        animation_index=None,
        **kwargs,
    ):
        # self._default_parameters(**kwargs)
        # copy every named argument into an attribute
        _locals = locals().copy()  # copy locals() so that it does not updates itself
        for key in _locals:
            if (
                key != "self" and key != "kwargs"
            ):  # iterate over all named arguments, including default values
                setattr(self, key, _locals[key])
        # copy every **kwargs pair into an attribute
        for key, arg in kwargs.items():  # iterate over all **kwargs arguments
            setattr(self, key, arg)
        if pos is None:
            self.pos = pygame.math.Vector2(200, 200)
        if move_direction is None:
            self.move_direction = pygame.math.Vector2(1, 0)
        # print("self move_directoin:", self.move_direction)
        self.time_for_next_frame = 0
        # self._overwrite_parameters()
        pygame.sprite.Sprite.__init__(
            self, self.groups
        )  # call parent class. NEVER FORGET !
        self.number = VectorSprite.number  # unique number for each sprite
        # VectorSprite.book[self.number] = self
        VectorSprite.number += 1
        # self.visible = False
        self.create_image()
        self.distance_traveled = 0  # in pixel
        # animation
        if self.time_for_each_frame is not None:
            self.time_for_next_frame = self.age + self.time_for_each_frame
        else:
            self.time_for_next_frame = None
        # self.rect.center = (-300,-300) # avoid blinking image in topleft corner
        if self.look_angle != 0:
            self.set_angle(self.angle)
        self.__post_init__()

    def __post_init__(self):
        """change parameters before create_image is called"""
        pass

    def kill(self):
        # check if this is a boss and kill all his underlings as well
        # a sprite is a boss if any other sprite has this sprite number as boss number
        # kill also delete a sprite in all spritegroups
        tokill = [s for s in Viewer.allgroup if "boss" in s.__dict__ and s.boss == self]
        for s in tokill:
            s.kill()
        # if self.number in self.numbers:
        #   del VectorSprite.numbers[self.number] # remove Sprite from numbers dict
        pygame.sprite.Sprite.kill(self)

    def create_image(self):
        """either an ready-to-use pygame image is given as image argument, or an image name to lookup"""
        # i assume that in Viewer.images is a key with self.imagename and the value is a tuple,
        # consisting of normal_sized image ("half") and double_sized image ( for higher quality)
        # i assume the Viewer.images are already convert_alpha() processed
        # ---- if image_name is given:
        if (self.image is None) and (self.image_name is not None):
            self.image = Viewer.images[self.image_name][0].copy()
            self.image0 = Viewer.images[self.image_name][1].copy()  # for rotation in better quality, use the bigger image
        #elif self.image is not None:
        #    self.image = image

        if self.correction_angle != 0:
            self.image = pygame.transform.rotate(self.image, self.correction_angle)
            self.image0 = pygame.transform.rotate(self.image0, self.correction_angle)
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.center = (int(round(self.pos[0], 0)), int(round(self.pos[1], 0)))

    def rotate(self, by_degree):
        """rotates a sprite and changes it's look angle by by_degree"""
        self.look_angle += by_degree
        self.look_angle = self.look_angle % 360
        if self.look_angle > 180:
            self.look_angle -= 360
        oldcenter = self.rect.center
        # self.image = pygame.transform.rotate(self.image0, -self.angle)
        self.image = pygame.transform.rotozoom(
            self.image0, -self.look_angle, 0.5
        )  # image0 is in double size
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.center = oldcenter

    def rotate_with_roation_speed(self, seconds, clockwise=True, stop_angle=None):
        """rotates a sprite using its rotation_speed and changes it's look angle"""
        angle_old = self.look_angle
        self.rotate(self.rotation_speed * seconds * -1 if clockwise else 1)

    def set_angle(self, degree):
        """rotates a sprite and changes it's angle to degree"""
        self.look_angle = degree
        self.look_angle = self.look_angle % 360
        if self.look_angle > 180:
            self.look_angle -= 360
        oldcenter = self.rect.center
        # self.image = pygame.transform.rotate(self.image0, -self.angle)
        self.image = pygame.transform.rotozoom(self.image0, -self.look_angle, 0.5)
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.center = oldcenter

    def get_next_waypoint(self):
        pass

    def update(self, seconds):
        """calculate movement, position and bouncing on edge"""
        self.get_next_waypoint()
        self.age += seconds
        # do nothing if negative age ( sprite will appear in the future, not yet)
        if self.age < 0:
            return
        # update animation if sprite has an animation_images list.
        if self.time_for_next_frame is not None:
            if self.age > self.time_for_next_frame:
                self.animation_index += 1
                if self.animation_index >= len(self.animation_images):
                    self.animation_index = 0
                self.time_for_next_frame = self.age + self.time_for_each_frame
                self.image = self.animation_images[self.animation_index]

        # self.visible = True
        self.distance_traveled += self.move_speed * seconds
        # ----- kill because... ------
        if self.hitpoints <= 0:
            self.kill()
        if self.max_age is not None and self.age > self.max_age:
            self.kill()
        if self.max_distance is not None and self.distance_traveled > self.max_distance:
            self.kill()
        # ---- movement with/without boss ----
        if self.boss_number and self.move_with_boss:
            bosslist = [
                sprite
                for sprite in Viewer.allgroup
                if sprite.number == self.boss_number
            ]
            if len(bosslist) < 1:
                print("boss not found in allgroup error:", self.boss_number)
            else:
                self.pos = bosslist[0].pos
            # self.move = self.boss.move
            # self
        else:
            # move independent of boss
            # acceleration
            self.move_speed += self.acceleration * seconds
            # print(self.move_speed)
            self.move_speed = min(self.move_speed, self.move_speed_max)
            if (
                (self.waypoint is not None)
                and (self.move_speed > 0)
                and (self.move_direction.length() > 0)
            ):
                self.pos += self.move_direction.normalize() * self.move_speed * seconds
            # self.wallcheck()
        # print("rect:", self.pos.x, self.pos.y)
        self.rect.center = (int(round(self.pos.x, 0)), int(round(self.pos.y, 0)))


class PlacemodusTower(VectorSprite):
    def __post_init__(self):
        self.placemodus = True

    def update(self, seconds):
        if self.placemodus:
            self.pos = pygame.Vector2(pygame.mouse.get_pos())
            self.rect.center = self.pos

class TowerSprite(VectorSprite):

    def __post_init__(self):
        pass
        # create sprite from self.towerdata including barrel(s)


class Tank(VectorSprite):
    near_enough = 10  # pixel

    def __post_init__(self):
        print("tank post init")
        self.waypoints = []
        self.waypoint = None
        self.i = 0


    def get_next_waypoint(self):
        if self.waypoint is None:
            return
        self.move_direction = self.waypoint - self.pos
        flipped = pygame.Vector2(self.move_direction.x, -self.move_direction.y)
        self.set_angle(flipped.angle_to(pygame.Vector2(1, 0)))
        if self.move_direction.length() < Tank.near_enough:
            self.i += 1
            if self.i == len(self.waypoints):
                self.i = 0
            self.waypoint = self.waypoints[self.i]


# def motion(window):
#    #x, y = event.x, event.y
#    #print('{}, {}'.format(x, y))
#    #print(f'X, Y = {window.user_bind_event.x, window.user_bind_event.y}')
#    return f'X, Y = {window.user_bind_event.x, window.user_bind_event.y}'


if __name__ == "__main__":
    mygame = Viewer()