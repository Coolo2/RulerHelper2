
import io

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle

matplotlib.use('Agg') 
mplstyle.use('fast')
matplotlib.interactive(True)

from itertools import islice
import setup as s

from matplotlib.ticker import MaxNLocator

import datetime

import client
import os

from shapely import Point

def save_graph(data : dict, title : str, x : str, y : str, chartType, highlight : int = None, y_formatter = None):
    
    color = "silver"

    matplotlib.rcParams['text.color'] = color
    matplotlib.rcParams['axes.labelcolor'] = color
    matplotlib.rcParams['xtick.color'] = color
    matplotlib.rcParams['ytick.color'] = color
    matplotlib.rcParams["axes.edgecolor"] = color
    matplotlib.rcParams["xtick.labelsize"] = 7

    if chartType == plt.pie:
        def my_autopct(pct):
            return ('%.1f' % pct) + "%" if pct > 3 else ''

        barlist, labels, pct_texts = plt.pie(data.values(), labels=data.keys(), autopct=my_autopct, textprops={'fontsize': 7, "color":"white"}, rotatelabels=True, radius=1, startangle=160)
        
        for label, pct_text in zip(labels, pct_texts):
            pct_text.set_rotation(label.get_rotation())
    else:
        
    
        # Add ticks if not pie
        start_date : datetime.date = None
        xticks = {}
        keys = []
        for i, tick_raw in enumerate(data.keys()):
            try:
                date = datetime.datetime.strptime(tick_raw, "%Y-%m-%d").date()
            except:
                date = None
            if date:
                if i == 0:
                    start_date = date

                xticks[tick_raw] = (date-start_date).days
                keys.append(xticks[tick_raw])
            else:
                xticks[tick_raw] = i
                keys.append(i)

        fig, gnt = plt.subplots()
        if chartType == plt.bar:
            chartType = gnt.bar 
        else:
            chartType = gnt.plot 
        
        barlist = chartType(keys, data.values(), color=s.bar_color if chartType == gnt.bar else s.line_color)

        gnt.set_xticks(list(xticks.values()))
        gnt.set_xticklabels(list(xticks.keys()))

        gnt.axes.yaxis.set_major_locator(MaxNLocator(integer=True))

        if y_formatter:
            y_ticks = []
            for tick in gnt.get_yticks():
                y_ticks.append(y_formatter(tick))
            gnt.set_yticklabels(y_ticks)

    plt.title(title, y=1.2 if chartType == plt.pie else 1)
    plt.xlabel(x)
    plt.ylabel(y)

    plt.xticks(rotation=270)

    if highlight:
        barlist[highlight].set_color('r')

    buf = io.BytesIO()
    plt.savefig(buf, dpi=s.IMAGE_DPI_GRAPH, transparent=True, bbox_inches="tight")
    buf.seek(0)

    plt.close()

    return buf

def save_timeline(data : dict, title : str, booly=False):

    # Convert to date ranges
    ranges : dict[str, list[datetime.date, datetime.date]] = {}
    start_date = datetime.datetime.strptime(list(data.keys())[0], "%Y-%m-%d").date() if len(data) > 0 else datetime.date.today()
    end_date = datetime.date.today()

    xticks = {start_date.strftime("%Y-%m-%d"):0, end_date.strftime("%Y-%m-%d"):(end_date-start_date).days}

    color = "silver"

    matplotlib.rcParams['text.color'] = color
    matplotlib.rcParams['axes.labelcolor'] = color
    matplotlib.rcParams['xtick.color'] = color
    matplotlib.rcParams['ytick.color'] = color
    matplotlib.rcParams["axes.edgecolor"] = color
    matplotlib.rcParams["xtick.labelsize"] = 7

    last_date = None
    last_str = None
    
    for i, date_str in enumerate(data):
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        xticks[date_str] = (date-start_date).days

        if not last_date:
            last_date = date
            last_str = date_str
            if len(data) == 1:
                ranges[data[date_str]] = [[0, 1]]
            continue
        
        if data[last_str] not in ranges:
            ranges[data[last_str]] = []
        ranges[data[last_str]].append([(last_date-start_date).days, (date-last_date).days])
        if i == len(data)-1:
            if data[date_str] not in ranges:
                ranges[data[date_str]] = []
            ranges[data[date_str]].append([(date-start_date).days, (datetime.date.today()-date).days])
        
        last_date = date
        last_str = date_str

    fig, gnt = plt.subplots()
    
    gnt.set_ylim(0, len(ranges))

    plt.xticks(rotation=270)
    plt.title(title)
    
    # Setting ticks on y-axis
    start_y = 1
    add_end_y = 1

    gnt.set_yticks([start_y+i+0.5 for i in range(len(ranges))] + [len(ranges)+0.5+start_y+add_end_y])
    gnt.set_yticklabels(list(ranges.keys()) + [""])

    gnt.set_xticks(list(xticks.values()))
    gnt.set_xticklabels(list(xticks.keys()))

    colors = s.timeline_colors
    if booly:
        colors = s.timeline_colors_bool if list(ranges.keys())[0] == "True" else list(reversed(s.timeline_colors_bool))
 
    for i, item in enumerate(ranges):
        
        gnt.broken_barh(ranges[item], (start_y+i, 1), facecolors =(f'tab:{colors[i%len(s.timeline_colors)]}'))

    buf = io.BytesIO()
    plt.savefig(buf, dpi=s.IMAGE_DPI_GRAPH, transparent=True, bbox_inches="tight")
    buf.seek(0)

    plt.close()

    return buf

def check_cache(cache_name : str, cache_id : str):
    cache_files = [file_name for file_name in os.listdir('./cache') if file_name.endswith(".png")]
    
    n = None
    for name in cache_files:
        if name == f"{cache_name}_{cache_id}.png":
            #with open(f"cache/{cache_name}_{cache_id}.png", "rb") as f:
            n = f"./cache/{cache_name}_{cache_id}.png"
        elif cache_name in name:
            os.remove(f"./cache/{name}")
    
    return n

def plot_towns(towns : list[client.object.Town], outposts=True, show_earth="auto", plot_spawn=True, dot_size=None, whole=False, players : list[client.object.Player] = None, cache_name : str = None, cache_id : int = None, cache_checked=False, dimmed_towns : list[client.object.Town]=[]):

    # Cache_checked can be False if not checked, None if doesn't exists, str if does exist

    bg_path = s.earth_bg_path
    if cache_name and cache_id and cache_checked == False:
        n = check_cache(cache_name, cache_id)
        if n:
            return n
    
    if players and cache_name and cache_id:
        if not cache_checked:
            plot_towns(towns, outposts, show_earth, plot_spawn, dot_size, whole, None, cache_name, cache_id)
        bg_path = f"./cache/{cache_name}_{cache_id}.png"
        towns = None

    xw = 36865
    yw = 18432

    fig = plt.figure()
    fig.patch.set_facecolor('#2F3136')

    if towns:
        for town in towns:
            
            for i, polygon in enumerate(town.locations.geoms):
                if not outposts and not polygon.contains(Point(town.spawn.x, town.spawn.z)):
                    continue

                plt.fill(*polygon.exterior.xy, fc=town.fill_color + "20", ec=town.border_color, zorder=3, rasterized=True, lw=0.5)

    ax = plt.gca()
    ax.set_aspect('equal', adjustable='box')

    x_lim = ax.get_xlim()
    y_lim = ax.get_ylim()

    if dimmed_towns:
        for town in dimmed_towns:
            for i, polygon in enumerate(town.locations.geoms):

                plt.fill(*polygon.exterior.xy, fc=s.map_bordering_town_fill_colour + f"{s.map_bordering_town_opacity:02}", ec=town.border_color + f"{s.map_bordering_town_opacity//2:02}", zorder=2, rasterized=True, lw=0.5)

    if whole or (show_earth == "auto" and (x_lim[1]-x_lim[0] > 2000 or y_lim[1]-y_lim[0] > 2000)):
        show_earth = True

    if plot_spawn and towns:
        
        for town in towns:
        
            plt.scatter([town.spawn.x], [town.spawn.z], color=town.border_color, zorder=3, s=dot_size or 10)

    if show_earth == True:
        img = plt.imread(bg_path)
        plt.imshow(img, extent=[0-xw, xw, 0-yw, yw], origin='lower')
    
    if players:
        x_online = []
        z_online = []

        x_offline = []
        z_offline = []

        for player in players:
            if player.online:
                x_online.append(player.location.x)
                z_online.append(player.location.z)
            else:
                x_offline.append(player.location.x)
                z_offline.append(player.location.z)

        plt.scatter(x_online, z_online, color="white", s=dot_size or 10, zorder=5)
        plt.scatter(x_offline, z_offline, color="#707070", s=dot_size or 1, zorder=4)
    
    if not whole:
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

    ax.invert_yaxis()

    plt.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, dpi=s.IMAGE_DPI_DRAWING, transparent=True, bbox_inches="tight", pad_inches = 0)
   

    if cache_name and cache_id:
        with open(f"./cache/{cache_name}_{cache_id}.png", "wb") as f:
            f.write(buf.getbuffer())
    
    buf.seek(0)
    
    plt.close()

    return buf





def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))