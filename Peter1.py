import pygame
import PySimpleGUI as sg
from PIL import Image, ImageTk
import base64
from io import BytesIO
import random
# import time
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
    # pygameimage = pygame.image.load(IMAGEPATH)
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
    # stuff_to_buy = {
    #    "simple tower": 50,
    #    "ice tower": 65,
    #    "sniper tower": 75,
    #    "minelayer tower": 75,
    # }
    my_towers = {}
    level = 1
    tanks_total = 0
    tanks_killed = 0
    tanks_passed = 0



@dataclass
class Tower:
    name: str
    sprite_name: str = None  # name of sprite for tower
    # name of barrel sprite expected to look north, rotation point is at south
    barrel_name: str = None
    bullet_name: str = None  # name of bullet sprite
    bullet_type: str = None  # bullet, rocket, laser, ice etc.
    # pixel width == height of sprite in pixel, will be transformed to this width
    sprite_size: int = None
    barrels: int = 1  # how many barrels
    damage: int = 1
    splash_radius = 1  # pixel
    range_min: int = 25
    range_max: int = 150
    reload_time: float = 2.5  # seconds
    rotation_speed: float = 90.0  # degrees / second
    bullet_speed: float = 100  # pixcel / second
    bullet_error: float = 1.0  # degrees
    salvo: int = 1  # how many bullets per salvo per barrel
    salvo_delay: float = 0.25  # time between bullets of a salvo from the same barrel
    price: int = 100
    upgrade_name: str = None  # can be upgraded to this name
    upgrade_time: float = 5.0  # seconds to upgrade
    hitpoints = 200

    def __post_init__(self):
        Game.towerdata[self.name] = self
    

    

# --------- define Tower types ------------
Tower(name="simple",
      sprite_name="barrelGreen_top.png",
      barrel_name="tankGreen_barrel2.png",
      bullet_name="bulletGreen3_outline.png",
      bullet_type="bullet",
      price=100,
      range_min=25,
      range_max=150,
      salvo=4,
      bullet_speed = 225
      )

Tower(name="medium",
      sprite_name="barrelRed_top.png",
      barrel_name="tankGreen_barrel2.png",
      bullet_name="bulletRed3_outline.png",
      bullet_type="bullet",
      price=200,
      range_min=50,
      range_max=200,
      bullet_speed = 225
      )

Tower(name="laser",
      sprite_name="barrelBlack_top.png",
      barrel_name="tankDark_barrel2.png",
      bullet_type="laser",
      damage = 0.05, # hitpoins per second
      price=400,
      range_min=40,
      range_max=250,
      )

Tower(name="rocket",
      sprite_name="barrelRust_top.png",
      barrel_name="specialBarrel5.png",
      bullet_name="bulletDark2_outline.png",
      bullet_type="rocket",
      price=500,
      range_min=100,
      range_max=200,
      salvo=4,
      salvo_delay = 0.25,
      reload_time=5,
      damage=8,
      bullet_speed = 66,
      bullet_error = 30,
     )

# print("towerdata:", Game.towerdata)

class Viewer:
    # source_path = pathlib.Path.cwd() # get current work directory
    resolution = (1024, 800)  # pygame window size in pixel.
    backgroundimage = None
    # maskimage = None  # test maskgroup instead
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
    bulletgroup = pygame.sprite.Group()
    cursorgroup = pygame.sprite.GroupSingle()
    maskgroup = pygame.sprite.GroupSingle()
    placemodusgroup = pygame.sprite.GroupSingle()
    bargroup = pygame.sprite.Group()  # will be updated AFTER allgroup
    fxgroup = pygame.sprite.Group() # will be drawn on top # TODO: use _layer instead?
    images = {}
    # -------- gui --------
    layout = [
        [
            # sg.Text(
            #    "testing graph"
            # ),  # sg.Button("click me", key="button1"), sg.Button("kill"),
            # sg.Button("fire"),
            sg.Text(
                "play the game",
                size=(20, 1),
                text_color="yellow",
                key="hint",
                font=("Arial", 17, "bold"),
            ),
            sg.Column([
                [sg.Text("waypoints:"), ],
                [sg.Button("click to set waypoints",
                           key="waypointbutton", size=(18, 1)), ],
                [sg.Button("delete waypoint"), ],
                [sg.Button("export waypoints")],
                [sg.Button("spawn"), sg.Button("play")],
            ]),
            sg.Column([

                [sg.Listbox(values=[], size=(10, 5), key="waypointliste"), ],
                [sg.Text("Tanks total: "),sg.Text("0", key="tanks_total") ],
                [sg.Text("Tanks killed: "),sg.Text("0", key="tanks_killed") ],
                [sg.Text("Tanks passed: "),sg.Text("0", key="tanks_passed") ],

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
                # Game.stuff_to_buy.items(),
                [[tower.name, tower.price]
                    for tower in Game.towerdata.values()],
                headings=["turret name", "price"],
                key="shopping",
                size=(20, 5),
                select_mode=sg.TABLE_SELECT_MODE_BROWSE,
            ),
            sg.Button("load image"),
            sg.Column(
                layout=[
                    [sg.Text("$:"),
                     sg.Text(Game.gold, key="gold_text"), ],
                    [sg.Button("buy")],
                    [sg.Button("sell")],
                    [sg.Checkbox("pause", key="pause", enable_events=True)],
                ]
            ),
            sg.Table(
                my_towers,
                headings=["turret name", "buy $", "sell $"],
                # col_widths=(35, 5, 5),
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
            # absolute coordinate topleft corner of GUI window
            location=(200, 20),
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
        # print("surface:", self.mysurface)
        # print("id:", self.my_id)
        self.screen.fill(pygame.Color(255, 255, 255))

        pygame.fastevent.init()  # use fast event instead of pygame event
        # pygame.init()
        # pygame.display.init() # already done by display.set_mode?
        TowerSprite.groups = Viewer.allgroup, Viewer.towergroup
        Tank.groups = Viewer.allgroup, Viewer.tankgroup
        PlacemodusTower.groups = Viewer.allgroup, Viewer.placemodusgroup
        MaskSprite.groups = Viewer.maskgroup
        BulletSprite.groups = Viewer.allgroup, Viewer.bulletgroup
        RocketSprite.groups = Viewer.allgroup, Viewer.bulletgroup
        # NOT allgroup! TODO: check if there is wiggling hp-bar problem if bar is in allgroup
        HealthBarSprite.groups = Viewer.bargroup
        Spark.groups = Viewer.fxgroup
        SmokeSprite.groups = Viewer.allgroup

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
            waypoint = None,
            waypoints = None
        )
        # the tower image should be appear in the pygame window (canvas2) as well as in the pysimplegui graph (canvas1)
        self.tower_image = Viewer.images["barrelRust_top.png"][0]
        # tower_image_tk = pathlib.Path(""barrelRust_top.png"
        self.window["canvas1"].draw_circle(
            center_location=(50, 50), radius=40, line_color="yellow"
        )
        self.window["canvas1"].draw_image(
            data=pygame2base64(Viewer.images["barrelRust_top.png"][0]),
            # filename="data/tanks/PNG/Retina/barrelRust_top.png",    ## works but needs file
            # data=pygame2tk(Viewer.images["barrelRust_top.png"][1]), ## does nothing
            location=(50, 50),
        )
        # self.window["towerimage"].update(data = pygame2tk(Viewer.images["barrelRust_top.png"][0]))

        # ----- clock etc ---
        self.clock = pygame.time.Clock()
        self.fps = 60
        self.playtime1 = 0.0  # tkinter
        self.playtime2 = 0.0  # pygame
        duration_all_flames = 1.0
        self.duration_one_flame_frame = duration_all_flames / \
            len(Viewer.flame_images)
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
        # Viewer.maskimage = pygame.image.load("data/maps/petermap2_mask.png")
        # create mask sprite:
        MaskSprite(image=pygame.image.load("data/maps/petermap2_mask.png"))

        # -------------- load tileset, sprites etc ------------

        p = pathlib.Path("data")
        for file in p.iterdir():
            # print(file, file.stem, file.suffix)
            if file.stem.startswith("flame") and file.suffix == ".png":
                Viewer.flame_images.append(
                    pygame.image.load(str(file)).convert_alpha())

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
                    int(raw["x"]), int(raw["y"]), int(
                        raw["width"]), int(raw["height"])
                )
            )  # {"x":raw["x"], "y":raw["y"], "width":raw["width"], "height":raw["height"]}
            # resize the cropped image to half the original size
            half_image = pygame.transform.scale(
                cropped_image, (int(raw["width"]) // 2,
                                int(raw["height"]) // 2)
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

            if event == "spawn":
                Tank(image_name="tank_sand.png",
                correction_angle=90,
                move_speed = 0,
                acceleration=2,
                waypoints=self.waypoints,
                waypoint=self.waypoints[0])

            if event=="play":
                Game.tanks_total = 25
                Game.tanks_killed = 0
                Game.tanks_passed = 0
                self.window["tanks_total"].update(Game.tanks_total)
                

            if event == "load image":
                backgroundfile = sg.popup_get_file(
                    "please choose background image file")
                if backgroundfile is None:
                    continue
                Viewer.backgroundimage = pygame.image.load(backgroundfile)
                Viewer.maskimage = pygame.image.load(
                    backgroundfile[:-4] + "_mask.png")
                waypointfilename = "data/maps/" + \
                    pathlib.Path(backgroundfile).stem + ".txt"
                #-----load waypoints from waypointfile? -----
                wp = pathlib.Path(waypointfilename)
                if pathlib.Path.exists(wp):
                    with open(waypointfilename) as myfile:
                        lines = myfile.readlines()
                    my_waypoints = []
                    for line in lines:
                        before_comma,after_comma = line.split(",")
                        x = int(before_comma.strip())
                        y = int(after_comma.strip())
                        my_waypoints.append((x,y))
                    self.window["waypointliste"].update(values=my_waypoints)
                    self.waypoints = my_waypoints 
                    # all tanks should obey this waypoints
                    for tank in Viewer.tankgroup:
                        tank.waypoints = self.waypoints
                        if len(self.waypoints) > 0:
                            tank.waypoint = self.waypoints[0]

            if event == "export waypoints":
                # get values of Listbox "waypointliste"
                # list
                my_waypoints = self.window["waypointliste"].get_list_values()
                if backgroundfile is None:
                    sg.PopupError(
                        "please select backgroundimage before exporting waypoints")
                    continue
                pathlib.Path(backgroundfile).stem
                waypointfilename = "data/maps/" + \
                    pathlib.Path(backgroundfile).stem + ".txt"
                with open(waypointfilename, "w") as myfile:
                    for line in my_waypoints:
                        x, y = line
                        myfile.write(f"{x},{y}\n")
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

            # if event == "canvas1":
            # print("canvas 1 click: ", values["canvas1"])

            if event == "buy":
                # what kind of tower is selected in the shop_list?
                # is index of row, first column = name
                tower_to_buy = values["shopping"][0]
                # print("selected index:", tower_to_buy)
                # print(list(self.window["shopping"].get())[tower_to_buy])
                what = list(self.window["shopping"].get())[tower_to_buy]
                # my_towers.append(what)

                buy_price = int(what[1])
                if Game.gold - buy_price < 0:
                    # Viewer.pause = True
                    sg.PopupError(
                        "you can not afford to buy this", non_blocking=True)
                    # Viewer.pause = False
                    continue
                Game.gold -= buy_price

                self.window["gold_text"].update(Game.gold)
                sell_price = round(buy_price * Game.sell_factor, 0)
                what = [what[0], what[1], sell_price]
                Viewer.my_towers.append(what)
                self.window["my_towers"].update(values=Viewer.my_towers)
                place_tower_modus = True
                # my_tower = Tower(image_name="barrelBlack_top.png" )
                # ----- my tower for pygame
                # my_tower = Game.towerdata[what[0]]  # the dataclass instance
                my_data = Game.towerdata[what[0]]
                my_tower = PlacemodusTower(image_name=my_data.sprite_name)

                # break

            if event == "sell":
                what = values["my_towers"]
                # print(what)

            # --------- timeout event, does the pygame loop ---------------
            if event == sg.TIMEOUT_EVENT:

                # get mouse location: window.mouse_location() returns ABSOLUTE mouse position of whole screen!
                self.window["show_mouse_pos_absolute"].update(
                    self.window.mouse_location()
                )
                self.window["show_mouse_pos_pygame"].update(
                    pygame.mouse.get_pos())
                # for event in pygame.event.get():
                # print("pygame_event:", event)
                #    if event in

                # ---- pygame part (mainloop ) ----------
                pygame_events = pygame.event.get()
                for e in pygame_events:
                    # if e.type == pygame.WINDOWENTER:
                    #    print("-----------------------------------------------------")
                    #    print("----------- mouse entered pygame window -------------")
                    #    print("-----------------------------------------------------")
                    # if e.type == pygame.WINDOWLEAVE:
                    #    print("============ mouse left pygame window =============")
                    if e.type == pygame.QUIT:
                        print("bye bye says pygame")
                        running = False
                    # if e.type == pygame.WINDOWMOVED:
                    #    print("** ** ** window moved ** * ** ** **")
                    # if e.type == pygame.MOUSEWHEEL:
                    #    print(
                    #        "wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwheeeeeeeeeeeeeeeeeeeeeeeeeeelllllllllllllll"
                    #    )
                    if (e.type == pygame.MOUSEBUTTONUP) and waypointmodus:
                        # put the pygame mouse position into the waypointlist
                        # waypoints = self.window["waypointliste"].get_list_values()
                        self.waypoints.append(pygame.mouse.get_pos())
                        self.window["waypointliste"].update(
                            values=self.waypoints)

                    if (e.type == pygame.MOUSEBUTTONDOWN):

                        # ---------- place tower --------------
                        if my_tower is not None:
                            if not red_cross:
                                # place_tower_modus = False
                                my_tower.placemodus = False
                                # create Tower here
                                my_tower.kill()
                                # create towersprite
                                # print("mydata:\n", my_data)  # this is the dataclass instance
                                TowerSprite(#image_name=my_tower.image_name,
                                            #image=my_tower.image,
                                            pos=my_tower.pos, towerdata=my_data)

                                # kill placeholders
                                my_tower = None
                                red_cross = False

                pressed_keys = pygame.key.get_pressed()

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
                    self.screen.fill((255, 255, 255))  # fill screen white
                else:
                    self.screen.blit(Viewer.backgroundimage, (0, 0))
                # -------- edit mousepointer when in place-tower-mode -----------------
                if my_tower is not None:
                    if bigmask:
                        # if Viewer.maskgroup(): # any strite at all inside maskgropu?
                        collisions = pygame.sprite.collide_mask(
                            bigmask, my_tower)
                        if collisions is None:
                            red_cross = False
                        else:
                            red_cross = True
                    #color = (random.randint(0, 255), random.randint(
                    #    0, 255), random.randint(0, 255))
                    pygame.draw.circle(self.screen, (255, 94, 0), pygame.mouse.get_pos(), my_data.range_min,
                                       2)  # minrange orange
                    pygame.draw.circle(self.screen, (234, 18, 217), pygame.mouse.get_pos(), my_data.range_max,
                                       2)  # maxrange purple
                    if red_cross:
                        pygame.draw.line(self.screen, (255, 0, 0),
                                         pygame.mouse.get_pos() + pygame.Vector2(-50, -50),
                                         pygame.mouse.get_pos() + pygame.Vector2(50, 50),
                                         4)
                        pygame.draw.line(self.screen, (255, 0, 0),
                                         pygame.mouse.get_pos() + pygame.Vector2(-50, 50),
                                         pygame.mouse.get_pos() + pygame.Vector2(50, -50),
                                         4)
                # ----- draw pink waypoint dots and lines ------
                if len(self.waypoints) == 1:
                    pygame.draw.circle(
                        self.screen, (255, 0, 255), self.waypoints[0], 5)
                elif len(self.waypoints) > 1:
                    for wp in self.waypoints:
                        pygame.draw.circle(self.screen, (255, 0, 255), wp, 5)
                    for j, wp in enumerate(self.waypoints[1:], 1):
                        old = self.waypoints[j - 1]
                        pygame.draw.line(
                            self.screen, (128, 0, 128), old, wp, 2)
                # -----------------Show-Radius-mode-----------------------------
                if values["show_radius"]:
                    for t in Viewer.towergroup:
                        pygame.draw.circle(self.screen, (255, 94, 0), t.pos, t.towerdata.range_min,
                                           2)  # minrange orange
                        pygame.draw.circle(self.screen, (234, 18, 217), t.pos, t.towerdata.range_max,
                                           2)  # maxrange purple
                #  ----------- draw flame animation ----
                self.screen.blit(Viewer.flame_images[i], (200, 200))
                # --------- update all sprites ----------------
                self.allgroup.update(seconds)
                self.bargroup.update(seconds)
                self.fxgroup.update(seconds)
               

                       
                # ===========================================================
                # ----------- collision detection ---------------------------
                # ===========================================================
                # ----- Bullet vs. Tank
                for enemy in Viewer.tankgroup:
                    crashgroup = pygame.sprite.spritecollide(
                        sprite=enemy,
                        group=Viewer.bulletgroup,
                        dokill=False,  # TODO: fix
                        collided=pygame.sprite.collide_rect_ratio(0.7)
                    )
                    for bullet in crashgroup:
                        #print("hitpoints before", enemy.hitpoints)
                        enemy.hitpoints -= bullet.damage
                        #print("hitpoints after", enemy.hitpoints)
                        for _ in range(8):
                            Spark(pos=pygame.Vector2(bullet.pos.x, bullet.pos.y))
                        bullet.kill()

                # ---------- blit all sprites --------------
                self.allgroup.draw(self.screen)
                self.bargroup.draw(self.screen)
                self.fxgroup.draw(self.screen)
                # ---- special for tanks only -----
                # --- blit red line from each tank to his next waypoint
                for tank in Viewer.tankgroup:
                    if tank.waypoint is not None:
                        # print("line from", tank.pos, "to", tank.waypoint)
                        pygame.draw.line(
                            self.screen, (255, 0,
                                          0), tank.pos, tank.waypoint, 1
                        )

                # ---------- turret shooting at tanks -------------
                if len(Viewer.tankgroup) > 0:
                    for t in Viewer.towergroup:
                        # ---- aim at closest enemy ----
                        best_distance, closest_enemy = None, None
                        for enemy in Viewer.tankgroup:  # e for enemy
                            distance = t.pos - enemy.pos
                            if (best_distance is None) or (distance.length() < best_distance.length()):
                                best_distance = distance
                                closest_enemy = enemy
                        t.rotate_towards(seconds, closest_enemy)
                        # bullet turrets fire automatically
                        # --- fire laser turret ? 
                        if t.towerdata.bullet_type == "laser":
                            if t.towerdata.range_min < best_distance.length() < t.towerdata.range_max:
                                red = (random.randint(222,255),0,0)
                                width = random.randint(1,3)
                                pygame.draw.line(self.screen, red, t.pos, closest_enemy.pos, width)
                                if random.random() < 0.2:
                                    Spark(pos=pygame.Vector2(closest_enemy.pos.x, closest_enemy.pos.y))
                                closest_enemy.hitpoints -= t.towerdata.damage

                            


                # ----------- blit screen -------------------------
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
            # ================== end of pygame (=TIMEOUT) event =============
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
        pygame.sprite.Sprite.__init__(self, self.groups)
        self.image = image
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)


class VectorSprite(pygame.sprite.Sprite):
    """base class for sprites. this class inherits from pygame sprite class"""

    number = 0  # unique number for each sprite

    # images = []
    # book = {} # { number, Sprite }

    def __init__(
            self,
            image_name=None,
            image=None,
            correction_angle=0,
            # if the images originally "looks" at right, this remains 0. if it looks "up", must be -90 etc.
            pos=None,
            move_direction=None,
            move_speed=0.0,
            move_speed_max=150,  # pixel/second
            move_speed_min=0,
            rotation_speed=0,
            rotation_speed_max=90,  # grad/second
            acceleration=0,
            boss_number=None,
            boss_delta=None,  # Vector2, relative to boss.pos
            _layer=0,
            look_angle=0,  # degrees
            radius=0,
            hitpoints=100,
            hitpoints_full=100,
            waypoint = None,
            age=0,
            alpha = 0,
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
            self.pos = pygame.Vector2(200, 200)
        if move_direction is None:
            self.move_direction = pygame.Vector2(1, 0)
        self.time_for_next_frame = 0

        # ------------- assign sprite groups ---- (don't forget to code Tank.groups = allgroup, Tankgroup etc )
        pygame.sprite.Sprite.__init__(
            self, self.groups
        )  # call parent class. NEVER FORGET !
        self.number = VectorSprite.number  # unique number for each sprite
        # VectorSprite.book[self.number] = self
        VectorSprite.number += 1
        # self.visible = False

        # ------------ execute create_image --------
        self.create_image()
        # ------------ execute __post_init__ -----------------
        self.__post_init__()
        self.distance_traveled = 0  # in pixel
        # animation
        if self.time_for_each_frame is not None:
            self.time_for_next_frame = self.age + self.time_for_each_frame
        else:
            self.time_for_next_frame = None
        # self.rect.center = (-300,-300) # avoid blinking image in topleft corner
        if self.look_angle != 0:
            self.set_angle(self.look_angle)

    def __post_init__(self):
        """change parameters before create_image is called"""
        pass

    def kill(self):
        # check if this is a boss and kill all his underlings as well
        # a sprite is a boss if any other sprite has this sprite number as boss number
        # kill also delete a sprite in all spritegroups
        #tokill = [s for s in Viewer.allgroup if "boss" in s.__dict__ and s.boss == self]
        tokill = [s for s in Viewer.bargroup if s.boss == self]
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
        if self.image is None:
            if self.image_name is None:
                return
            self.image = Viewer.images[self.image_name][0].copy()
            self.image0 = Viewer.images[self.image_name][
                1].copy()  # for rotation in better quality, use the bigger image
        # elif self.image is not None:
        #    self.image = image

        if self.correction_angle != 0:
            self.image = pygame.transform.rotate(
                self.image, self.correction_angle)
            self.image0 = pygame.transform.rotate(
                self.image0, self.correction_angle)
        #if self.image is not None:
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.center = (
            int(round(self.pos[0], 0)), int(round(self.pos[1], 0)))

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
        #angle_old = self.look_angle
        new_angle = self.look_angle + self.rotation_speed * \
            seconds * -1 if clockwise else 1
        new_angle = new_angle % 360
        if new_angle > 180:
            new_angle -= 360
        if stop_angle is not None:
            if clockwise:
                if self.look_angle > stop_angle and new_angle < stop_angle:
                    new_angle = stop_angle
            else:
                if self.look_angle < stop_angle and new_angle > stop_angle:
                    new_angle = stop_angle
        #self.rotate(self.rotation_speed * seconds * -1 if clockwise else 1)
        self.set_angle(new_angle)

    def set_angle(self, degree):
        """rotates a sprite and changes it's angle to degree"""
        self.look_angle = degree
        self.look_angle = self.look_angle % 360
        if self.look_angle > 180:
            self.look_angle -= 360
        oldcenter = self.rect.center
        # self.image = pygame.transform.rotate(self.image0, -self.angle)
        self.image = pygame.transform.rotozoom(
            self.image0, -self.look_angle, 0.5)
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.center = oldcenter

    def get_next_waypoint(self):
        pass

    def update(self, seconds):
        """calculate movement, position and bouncing on edge"""

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
        #print("move_speed,", self.move_speed, "seconds:", seconds)
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
            #    bosslist = [
            #        sprite
            #        for sprite in Viewer.allgroup
         #       if sprite.number == self.boss_number
            #    ]
            #    if len(bosslist) < 1:
            #        print("boss not found in allgroup error:", self.boss_number)
            #    else:
            #        boss = bosslist[0]
            # assert that self.boss exist if self.boss_number exist
            self.pos = self.boss.pos + self.boss_delta
        else:  # ----------- move independent of boss
            # acceleration
            self.move_speed += self.acceleration * seconds
            self.move_speed = min(
                self.move_speed, self.move_speed_max)  # speed limit
            self.move_speed = max(
                self.move_speed, self.move_speed_min)  # speed limit
            if (
                    #(self.waypoint is not None)
                    #and 
                    (self.move_speed != 0) and (self.move_direction.length() > 0)
            ):
                self.pos += self.move_direction.normalize() * self.move_speed * seconds
            # self.wallcheck()
        self.rect.center = (int(round(self.pos.x, 0)),
                            int(round(self.pos.y, 0)))


class PlacemodusTower(VectorSprite):
    def __post_init__(self):
        self.placemodus = True

    def update(self, seconds):
        if self.placemodus:
            self.pos = pygame.Vector2(pygame.mouse.get_pos())
            self.rect.center = self.pos


class TowerSprite(VectorSprite):
    # in attribute .towerdata is the instance of the Tower Dataclass

    def __post_init__(self):
        self.waypoint = None
        self.ready_to_fire = 0  # age when tower will be ready to fire.
        self.rotation_speed = self.towerdata.rotation_speed
        self.compose_image()

    def compose_image(self):
        """merge tower and barrel image(s)"""
        self.image = Viewer.images[self.towerdata.sprite_name][1].copy()
        self.image.blit(Viewer.images[self.towerdata.barrel_name][1], (0,0))
        self.image = pygame.transform.rotozoom(self.image, 90, 1.0)
        self.image0 = self.image.copy()
        self.rect = self.image.get_rect()
        self.rect.center = self.pos


    def rotate_towards(self, seconds, enemy):
        # rotate clockwise or counteclockwise?
        tower2enemy = enemy.pos - self.pos 
        angle = tower2enemy.angle_to(pygame.Vector2(1,0))
        #print("angle", angle, enemy.pos, self.pos)
        self.set_angle(-angle)
        self.enemy = enemy
        # clockwise or counterclockwise? 
        
        #diffvector = pygame.Vector2(1,0)
        #diffvector.rotate_ip(angle)
        #diff = diffvector.angle_to(pygame.Vector2(1,0))
        #self.rotate_with_roation_speed(seconds, True if diff>0 else False, stop_angle=angle)
        # fire whole salvo:
        distance = self.pos - enemy.pos
        if self.towerdata.range_min < distance.length() < self.towerdata.range_max:
            if self.ready_to_fire < self.age:
                self.fire() # salvo!


    def fire(self):
        if self.towerdata.bullet_type == "bullet":
            start_time = 0
            for b in range(self.towerdata.salvo):
                start_time =  b*self.towerdata.salvo_delay
                BulletSprite(turret = self, age= -start_time)
                #BulletSprite(image_name=self.towerdata.bullet_name,
                #     correction_angle=-90,
                #     pos=pygame.Vector2(self.pos.x, self.pos.y),
                #     #waypoint=pygame.Vector2(enemy.pos.x, enemy.pos.y),
                #     turret = self,
                #     damage=self.towerdata.damage,
                #     speed=self.towerdata.bullet_speed,
                #     error=self.towerdata.bullet_error,
                #     age=-start_time,
                #     max_distance = self.towerdata.range_max)
        
        elif self.towerdata.bullet_type == "laser":
            pass # laser drawing and damage is handled in Viewer.run (Timeout event)

        elif self.towerdata.bullet_type == "rocket":
            start_time = 0
            for b in range(self.towerdata.salvo):
                start_time =  b*self.towerdata.salvo_delay
                RocketSprite(turret=self, age=-start_time, enemy=self.enemy)
                #RocketSprite(image_name=self.towerdata.bullet_name,
                #     correction_angle=-90,
                #     pos=pygame.Vector2(self.pos.x, self.pos.y),
                #     #waypoint=pygame.Vector2(enemy.pos.x, enemy.pos.y),
                #     turret = self,
                #     damage=self.towerdata.damage,
                #     speed=self.towerdata.bullet_speed,
                #     error=self.towerdata.bullet_error,
                #     age=-start_time,
                #     max_distance = self.towerdata.range_max,
                #     enemy=self.enemy)


        self.ready_to_fire = self.age + self.towerdata.reload_time


class HealthBarSprite(VectorSprite):

    def __post_init__(self):
        try:
            self.boss = [s for s in Viewer.allgroup if s.number ==
                         self.boss_number][0]
        except IndexError as e:
            raise("boss Sprite not found error", e)
        self.old_hp = self.boss.hitpoints

    def update(self, seconds):
        if self.boss.hitpoints != self.old_hp:
            self.create_image()
        self.rect.center = self.boss.pos + self.boss_delta

    def create_image(self):
        width = self.boss.image0.get_rect().width // 2
        height = 10
        percent = self.boss.hitpoints / self.boss.hitpoints_full
        self.image = pygame.Surface((width, height))
        pygame.draw.rect(self.image, (0, 128, 0),
                         (0, 0, width, height), 1)  # outer border
        pygame.draw.rect(self.image, (0, 255, 0),
                         (1, 1, int(width * percent)-2, height-2))
        self.image.set_colorkey((0, 0, 0))  # black is transparent
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        boss_w, boss_h = self.boss.image.get_rect().width, self.boss.image.get_rect().height
        self.boss_delta = pygame.Vector2(0, -int(boss_h/2) - 20)



class Spark(VectorSprite):

    def __post_init__(self):
        # TODO: fine tune spark parameters
        c = random.randint(200,255)
        self.color = (c,c,0) # yellow?
        self.move_speed = random.uniform(20,50)
        self.move_speed_max = 160
        self.max_age = random.uniform(0.2,0.5)
        self.max_distance = random.uniform(30,50)
        self.acceleration = 20
        self.move_direction = pygame.Vector2(1,0)
        self.angle = random.randint(0,360)
        self.move_direction.rotate_ip(self.angle)
        self.zoom = random.uniform(1.0,1.0)
        self.create_image2()
    
    def create_image2(self):
        self.image = pygame.Surface((24,12))
        pygame.draw.line(self.image, self.color, (13,3), (17,3),1)
        pygame.draw.line(self.image, self.color, (17,3), (22,3),2)
        self.image = pygame.transform.rotozoom(self.image,-self.angle, self.zoom)
        self.image.set_colorkey((0,0,0)) # black is transparent
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        #self.rect.center = self.pos
        self.rect.center = (
                int(round(self.pos.x, 0)), int(round(self.pos.y, 0)))


class SmokeSprite(VectorSprite):

    def __post_init__(self):
        self.radius = 1
        self.max_age = random.uniform(1,2)
        self.alpha = 0

    def create_image(self):
        self.image=pygame.surface.Surface((20,20))
        pygame.draw.circle(self.image, (255,255,255), (10,10), self.radius)
        self.image.set_colorkey((0,0,0))
        self.image.set_alpha(self.alpha)
        self.image.convert_alpha()
        self.rect = self.image.get_rect()
        self.rect.center = (int(round(self.pos.x, 0)),
                            int(round(self.pos.y, 0)))

    def update(self, seconds):
        self.age += seconds
        if self.age > self.max_age:
            self.kill()
        self.alpha = 255 * self.age / self.max_age
        self.radius = int(round(10*self.age/self.max_age,0))
        self.create_image()
        




class RocketSprite(VectorSprite):
    """A self-guiding rocket, flying in a curvy path, tracking a tank"""
    
    def __post_init__(self):
        self.correction_angle = -90
        self.pos = pygame.Vector2(self.turret.pos.x, self.turret.pos.y)
        self.damage = self.turret.towerdata.damage
        self.move_speed = self.turret.towerdata.bullet_speed
        self.max_distance = self.turret.towerdata.range_max
        self.image_name = self.turret.towerdata.bullet_name
        self.max_age = 25
        self.create_image()
        self.fly_straight_duration = random.uniform(1,2)
        #self.enemy = None
        self.move = None
        self.speed_max = 200
        self.rotation_speed = 90 # grad/seconds
        # ---
        self.move_direction = pygame.Vector2(1,0)
        self.aim_with_error()
        
    def aim_with_error(self):
        error = random.uniform(-self.turret.towerdata.bullet_error,self.turret.towerdata.bullet_error)
        self.move_direction = pygame.Vector2(1,0) # must be reset!!
        self.move_direction.rotate_ip(self.turret.look_angle + error)
        self.set_angle(self.turret.look_angle + error)
        self.move = self.move_direction
        
    def aim_at_enemy(self,seconds):
        #if self.enemy is not None:
        dist = self.enemy.pos - self.pos
        self.e_angle = dist.angle_to(pygame.math.Vector2(1,0))
        
        self.set_angle(-self.e_angle)
        self.move = pygame.Vector2(dist.x, dist.y)
        # -- slow turn?
        ##self.move = pygame.Vector2(1,0)
        #self.e_angle = dist.angle_to(self.move_direction)
        #print("look, e:", self.look_angle, self.e_angle)
        #if self.look_angle == self.e_angle:
        #    return
        #elif self.look_angle < self.e_angle:
        #    clockwise = True
        #else: 
        #    clockwise = False
        #self.move.rotate_ip(-self.rotation_speed * seconds * clockwise)
        #self.set_angle(-self.move.angle_to(pygame.Vector2(1,0)))
        
    
    def update(self, seconds):
        """calculate movement, position and re-aming"""
        self.old_age = self.age
        self.age += seconds
        # do nothing if negative age ( sprite will appear in the future, not yet)
        if self.age < 0:
            self.visible = False
            return
        elif self.old_age <0 and self.age >= 0:
            self.aim_with_error()
            self.visible = True
        
        if random.random() < 0.1:
            SmokeSprite(pos=pygame.Vector2(self.pos.x, self.pos.y))
       
        #self.distance_traveled += self.move_speed * seconds
        # ----- kill because... ------
       
        #if self.max_distance is not None and self.distance_traveled > self.max_distance:
        #    self.kill()
        if self.age > self.max_age:
            self.kill()

        #print("enemy:", self.enemy)
        # update aiming  (if enemy exist)
        # do NOT aim in the first second
        if self.age > self.fly_straight_duration:
            self.aim_at_enemy(seconds) # create self.move
            #self.set_angle()
            # self.e_angle is now set towards enemy
            #self.move = pygame.math.Vector2(1,0)
            
            #if self.e_angle < self.look_angle:
            #    self.rotate_with_roation_speed(seconds, False, self.e_angle)
            #elif self.e_angle > self.look_angle:
            #    self.rotate_with_roation_speed(seconds, True, self.e_angle)
            #self.set_angle(self.look_angle)
            #self.move.rotate_ip(self.look_angle)


            
        # first move ? 
        #if self.move is None:
        #    self.pos += self.move_direction.normalize() * self.move_speed * seconds
        #else:
        #    print("updating aim...")
            #self.move = self.move_direction.normalize() * self.move_speed * seconds
        #self.move_direction = self.move_direction * 0.9 * self.move_speed * seconds +  self.move * self.move_speed * seconds           
        self.move_direction = self.move.normalize() * self.move_speed * seconds
        self.pos += self.move_direction 
        # acceleration
        #self.move_speed += self.acceleration * seconds
        #self.move_speed = min(
        #    self.move_speed, self.move_speed_max)  # speed limit
        #self.move_speed = max(
        #    self.move_speed, self.move_speed_min)  # speed limit
        #self.pos += self.move_direction.normalize() * self.move_speed * seconds
        
        self.rect.center = (int(round(self.pos.x, 0)),
                            int(round(self.pos.y, 0)))


class BulletSprite(VectorSprite):
    """A bullet flys in a straith line until max_distance is reached"""

    def __post_init__(self):
        """bullet flying from pos to waypoint"""
        #self.image_name = "bulletDark1.png"
        ##self.move_speed = self.speed
        #self.move_speed_max = self.speed
        #self.move_speed_min = self.speed
        # self.correction_angle=-90
        #self.waypoint = pygame.Vector2(self.waypoint.x, self.waypoint.y)
        #self.max_distance = self.range_max
        # ---
        self.correction_angle = -90
        self.pos = pygame.Vector2(self.turret.pos.x, self.turret.pos.y)
        self.damage = self.turret.towerdata.damage
        self.move_speed = self.turret.towerdata.bullet_speed
        self.max_distance = self.turret.towerdata.range_max
        self.image_name = self.turret.towerdata.bullet_name
        self.create_image()
        # ---
        self.move_direction = pygame.Vector2(1,0)
        self.aim()
        
    def aim(self):
        self.move_direction = pygame.Vector2(1,0) # must be reset!!
        self.move_direction.rotate_ip(self.turret.look_angle)
        self.set_angle(self.turret.look_angle)
        #self.move_direction = self.waypoint - self.pos
        #self.move_direction.rotate_ip(random.uniform(-self.error,self.error))
        #self.angle = -self.move_direction.angle_to(pygame.Vector2(1,0))
        #flipped = pygame.Vector2(self.move_direction.x, -self.move_direction.y)
        #self.set_angle(flipped.angle_to(pygame.Vector2(1, 0)))

    def update(self, seconds):
        """calculate movement, position and bouncing on edge"""
        self.old_age = self.age
        self.age += seconds
        # do nothing if negative age ( sprite will appear in the future, not yet)
        if self.age < 0:
            return
        elif self.old_age <0 and self.age >= 0:
            self.aim()
       
        self.distance_traveled += self.move_speed * seconds
        # ----- kill because... ------
       
        if self.max_distance is not None and self.distance_traveled > self.max_distance:
            self.kill()
        # ----------- move independent of boss
        # acceleration
        #self.move_speed += self.acceleration * seconds
        #self.move_speed = min(
        #    self.move_speed, self.move_speed_max)  # speed limit
        #self.move_speed = max(
        #    self.move_speed, self.move_speed_min)  # speed limit
        self.pos += self.move_direction.normalize() * self.move_speed * seconds
        self.rect.center = (int(round(self.pos.x, 0)),
                            int(round(self.pos.y, 0)))



        

class Tank(VectorSprite):
    near_enough = 10  # pixel

    def __post_init__(self):
        #print("tank post init")
        #self.waypoints = []
        #self.waypoint = None
        self.i = 0
        HealthBarSprite(boss_number=self.number, boss=self)
        self.hitpoints = 25
        self.hitpoints_full = 25
        # for collision_detection
        #w,h = self.rect.size()
        #self.radius = min(w,h)/2

    def update(self, seconds):
        self.get_next_waypoint()
        super().update(seconds)

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

# TODO: method to cancel tower placement / get "normal" mousepointer back (after interacting with tkinter while tower placement is active)
# TODO: fix chrash when just clicking "buy" without selecting tower first


if __name__ == "__main__":
    mygame = Viewer()