# testing to move and delete a figure(s) on a graph widget

import PySimpleGUI as sg
import random
import time
import os.path 


gold = 100
stuff_to_buy = {"simple tower": 50 ,
                "ice tower" : 65, 
                "sniper tower": 75, 
                "minelayer tower": 75,
                }
flamefigures = []
arrowfigures = []
circles = []  # container for shooting radius of towers
towers = []   # container for towers
my_towers = []
end_fire = 0
sell_factor = 0.5

layout = [
            [sg.Text("testing graph"), #sg.Button("click me", key="button1"), sg.Button("kill"),
             sg.Button("fire")],
            [sg.Text("gold:"), sg.Text(gold, key="gold_text")],
            [sg.Text("shopping:"), 
             sg.Table(stuff_to_buy.items(), headings=["name","price"], key="shopping", size=(20,5), select_mode=sg.TABLE_SELECT_MODE_BROWSE),
             sg.Column(layout=[
                [sg.Button("buy")],
                [sg.Button("sell")],
                ]),
             sg.Table(my_towers, headings=["name", "buy $", "sell $"], col_widths=(25,5,5), key="my_towers", size=(40,5)),
             ],


            [sg.Checkbox("show radius", default=False, key="show_radius" ), sg.Text("status: "), sg.Text("buy something", key="status_text")],
            [sg.Graph(canvas_size=(400,400), 
                    graph_bottom_left=(0,0),
                    graph_top_right=(400,400),
                    key="canvas",
                    background_color = "purple", ),
            ],
            [sg.Text("xxx", key="circles_display")],
        ]
        
flamenames = [os.path.join("data", "flame1.png"),
              os.path.join("data", "flame2.png"),
              os.path.join("data", "flame3.png"),
              os.path.join("data", "flame4.png"),
              os.path.join("data", "flame5.png"),
              os.path.join("data", "flame6.png"),
              os.path.join("data", "flame7.png"),
              os.path.join("data", "flame8.png"),
              ]




window = sg.Window("hallo",layout=layout, size=(800,600))

window.finalize() # now we can draw on graph


#circles.append(window["canvas"].draw_circle(center_location=(400,100), radius=5))

tower_stay = window["canvas"].draw_image(filename = os.path.join("data","helmet1.png"), location = (350,100))
tower_shoot = window["canvas"].draw_image(filename = os.path.join("data", "helmet2.png"), location = (8000,100))

towers.append(tower_stay)
circles.append(window["canvas"].draw_circle(center_location=(350,100), radius=100))

for i,filename in enumerate(flamenames):
    flamefigures.append(window["canvas"].draw_image(filename = filename, location = (8000,100)))
window["canvas"].relocate_figure(flamefigures[0], 200, 100)
end_flame = time.time() + 0.5/len(flamefigures) #full animation in 1 second
i = 0 #which picture is actual


Ice_Golem = window["canvas"].draw_image(filename = os.path.join("data", "golem.png"), location = (100,350))




while True:
    event, values = window.read(timeout=100)
    
    if event == sg.TIMEOUT_EVENT:
        print("tick-tack")
        window["circles_display"].update(str(circles))
        #for c in circles:
        #    window["canvas"].move_figure(c, -5, 0)
        for a in arrowfigures:
            window["canvas"].move_figure(a, -5, 2)
        #flame animation
        if time.time() > end_flame:
            end_flame = time.time() + 1/len(flamefigures)
            window["canvas"].relocate_figure(flamefigures[i],1800, 100)
            i +=1
            if i == len(flamefigures):
                i = 0
            window["canvas"].relocate_figure(flamefigures[i],200, 100)
            
        #archer reset
        if time.time() > end_fire:
            window["canvas"].relocate_figure(tower_stay, 350, 100)
            window["canvas"].relocate_figure(tower_shoot,1800, 100)
    if event == sg.WINDOW_CLOSED:
        break
    #if event == "button1":
    #    y = random.randint(10, 390)
    #    circles.append(window["canvas"].draw_circle(center_location=(400,y), radius=5))
    #if event == "kill":
    #    if len(circles) > 0:
    #        window["canvas"].delete_figure(circles[0])
    #        circles.pop(0)
    if event == "fire":
        window["canvas"].relocate_figure(tower_stay, 1800, 100)
        window["canvas"].relocate_figure(tower_shoot, 350, 100)
        end_fire = time.time() +0.5
        #arrow
        arrowfigures.append(window["canvas"].draw_image(filename = os.path.join("data", "arrow.png"), location = (350,100)))
    
    if event == "buy":
        # what kind of tower is selected in the shop_list? 
        tower_to_buy = values["shopping"][0] # is index of row
        print("selected index:", tower_to_buy)
        print(list(window["shopping"].get())[tower_to_buy])
        what = list(window["shopping"].get())[tower_to_buy]
        #my_towers.append(what)
        
        buy_price = int(what[1])
        if gold - buy_price < 0:
            sg.PopupError("you can not afford to buy this")
            continue
        gold -= buy_price
        window["gold_text"].update(gold)
        sell_price = round(buy_price * sell_factor, 0)
        what = [what[0], what[1], sell_price]
        my_towers.append(what)
        window["my_towers"].update(values = my_towers)
        #break



    

window.close()
                    
