
import io

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle

matplotlib.use('Agg') 
mplstyle.use('fast')
#matplotlib.interactive(True)

from itertools import islice
import setup as s

from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle

import datetime

import client
import os

from shapely import Point
import math
import itertools
import numpy as np

import warnings
warnings.filterwarnings("ignore")

def floor(num, zoomed_scale):
    return zoomed_scale * math.floor(num / zoomed_scale)

def ceil(num, zoomed_scale):
    return zoomed_scale * math.ceil(num / zoomed_scale)

def save_graph(data : dict, title : str, x : str, y : str, chartType, highlight : int = None, y_formatter = None, multi_data : dict[str, list] = None, ticks : list[str]= None, colors : list[str] = None, adjust_missing=False, jump=True):
    
    color = "silver"

    plt.rcParams["figure.figsize"] = [6.4*1.6, 4.8]

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

        times = ticks or list(data.keys())
        time_idx = list(np.round(np.linspace(0, len(times) - 1, len(times) if len(times) < 60 else 60 )).astype(int))
        added_i = []
        
        for _, data_group in enumerate([list(data.values())]) if data != None else enumerate(multi_data.values()): 
            max_i = data_group.index(max(data_group))
            min_i = data_group.index(min(data_group))

            if max_i not in time_idx: 
                to_remove = min(time_idx, key=lambda x:abs(x-max_i))
                to_remove = to_remove if to_remove not in added_i else time_idx[time_idx.index(to_remove)+(1 if time_idx[time_idx.index(to_remove)] < max_i and time_idx.index(to_remove)+1 < len(time_idx) else -1)]
                time_idx.remove(to_remove)
                time_idx.append(max_i)
                added_i.append(max_i)
            if min_i not in time_idx: 
                to_remove = min(time_idx, key=lambda x:abs(x-min_i))
                to_remove = to_remove if to_remove not in added_i else time_idx[time_idx.index(to_remove)+(1 if time_idx[time_idx.index(to_remove)] < min_i else -1)]
                time_idx.remove(to_remove)
                time_idx.append(min_i)
                added_i.append(min_i)
       
        times = [times[i] for i in time_idx]
        
        # Add ticks if not pie
        start_time : datetime.datetime = None
        xticks = {}
        keys = []
        added_times = []
        for i, tick_raw in enumerate(times):
            is_date = False
            try:
                time = datetime.datetime.strptime(tick_raw, "%Y-%m-%d")
                is_date = True 
            except:
                try:
                    time = datetime.datetime.fromisoformat(tick_raw)
                except:
                    time = None
            if time:
                if i == 0:
                    start_time = time

                time_str = time.strftime('%b %d %Y') if is_date else time.strftime('%b %d %Y %H:%M')
                xticks[time_str] = int((time-start_time).total_seconds()/60)
                keys.append(xticks[time_str])

                if jump and adjust_missing and xticks[time_str] -1 not in keys and xticks[time_str]-1 > 0:
                    time = time-datetime.timedelta(minutes=s.today_tracking_period.seconds//60, days=1 if is_date else 0)
                    if time > start_time:
                        time_str = time.strftime('%b %d %Y') if is_date else time.strftime('%b %d %Y %H:%M')
                        added_times.append(time)
                        keys.append(int((time-start_time).total_seconds()/60))
                        time_idx.append(i-1)

            else:
                xticks[tick_raw] = i
                keys.append(i)
        
        time_idx = sorted(time_idx)
        
        
        if jump and adjust_missing and len(added_times) > 0 and data:
            # Add in days where there is a gap so that slope isn't gradual
            last_time = None
            dates_start = [str(d)[:16] for d in data]
            for i, time in enumerate(data.copy().keys()):
                is_date = False
                try:
                    t = datetime.datetime.strptime(tick_raw, "%Y-%m-%d")
                    is_date = True 
                except:
                    t = datetime.datetime.fromisoformat(tick_raw)

                for added_time in added_times.copy():
                    
                    if last_time and added_time+datetime.timedelta(minutes=s.today_tracking_period.seconds//60, days=1 if is_date else 0) == t:
                        
                        copy_to = str(added_time.date()) if is_date else str(added_time)
                        copy_from = str(last_time.date()) if is_date else str(last_time)
                        
                        if str(copy_to)[:16] in dates_start:
                            continue
                        
                        data[copy_to] = data[copy_from]
                        added_times.remove(added_time)

                last_time = t
            
            def sort(x):
                if client.funcs.validate_datetime(x[0], "%Y-%m-%d"):
                    return datetime.datetime.strptime(x[0], "%Y-%m-%d")
                else:
                    return datetime.datetime.fromisoformat(x[0])
            data = dict(sorted(data.items(), key=sort))

        fig, gnt = plt.subplots()
        if chartType == plt.bar:
            chartType = gnt.bar 
        else:
            chartType = gnt.plot 
        
        if not multi_data or len(multi_data) == 0:
            multi_data = {"default":data.values()}
        
        
        xticks = dict(sorted(xticks.items(), key = lambda x:x[1]))
        keys = sorted(keys)
        
        for i, (name, plot) in enumerate(multi_data.items()):
            plot = [list(plot)[i] for i in time_idx]
            
            prev = None 
            for i_, v in enumerate(plot):
                if v != v and prev:
                    plot[i_] = prev 
                else:
                    prev = v

            color_i = ((colors if colors else s.bar_color) if chartType == gnt.bar else s.line_color) if data != None else colors[i%len(colors)] if colors else None
            plot_nonan = [p for p in plot if p != None and p == p]
            if len(plot_nonan) == 1: # Remove nan and count
                gnt.scatter(x=keys[-1] if len(keys) > 0 else 0, y=list(plot_nonan)[0], color=color_i, label=name)
            else:
                
                barlist : list[Rectangle] = chartType(keys, plot, color=color_i, label=name, alpha=0.75 if colors else 1)
                
        
        if len(multi_data) > 1:
            plt.legend(bbox_to_anchor=(0, 1.05, 1, 0.2), loc="lower left", prop={'size':10}, frameon=False, mode="expand", borderaxespad=0, ncol=3)

        gnt.set_xticks(list(xticks.values()))
        gnt.set_xticklabels(list(xticks.keys()))

        gnt.axes.yaxis.set_major_locator(MaxNLocator(integer=True))
        
        y_ticks = []
        for tick in gnt.get_yticks():
            y_ticks.append((y_formatter or (lambda x: f"{int(x):,}" if type(x) != str else x))(tick))
        gnt.set_yticklabels(y_ticks)
        
        if highlight:
            highlight = highlight.replace("_", " ").title()
            if highlight in list(xticks):
                barlist[list(xticks).index(highlight)].set_color('r')
    
    plt.title(title, y=1.2 if chartType == plt.pie else 1)
    plt.xlabel(x)
    plt.ylabel(y)

    plt.xticks(rotation=270)
    buf = io.BytesIO()
    plt.savefig(buf, dpi=s.IMAGE_DPI_GRAPH, transparent=True, bbox_inches="tight")
    buf.seek(0)

    plt.close()

    return buf

def save_timeline(data : dict, title : str, booly=False):

    # Convert to date ranges
    ranges : dict[str, list[datetime.date, datetime.date]] = {}
    start_date = datetime.datetime.strptime(list(data.keys())[0], "%Y-%m-%d").date() if len(data) > 0 else datetime.date.today()
    
    end_date = datetime.datetime.strptime(list(data.keys())[-1], "%Y-%m-%d").date() if len(data) > 0 else datetime.date.today()

    xticks = {start_date.strftime("%Y-%m-%d"):0, end_date.strftime("%Y-%m-%d"):(end_date-start_date).days}

    color = "silver"

    matplotlib.rcParams['text.color'] = color
    matplotlib.rcParams['axes.labelcolor'] = color
    matplotlib.rcParams['xtick.color'] = color
    matplotlib.rcParams['ytick.color'] = color
    matplotlib.rcParams["axes.edgecolor"] = color
    matplotlib.rcParams["xtick.labelsize"] = 7
    plt.rcParams["figure.figsize"] = [6.4*1.6, 4.8]

    last_date = None
    last_str = None
    
    for i, date_str in enumerate(data):
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()

        xticks[date.strftime('%b %d %Y')] = (date-start_date).days

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
            ranges[data[date_str]].append([(date-start_date).days, (end_date-date).days])
        
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

def plot_towns(towns : list[client.object.Town], outposts="retain", show_earth="auto", plot_spawn=True, dot_size=None, whole=False, players : list[client.object.Player] = None, cache_name : str = None, cache_id : int = None, cache_checked=False, dimmed_towns : list[client.object.Town]=[], connect_spawns:list[client.object.Town]=False, maintain_aspect=True, journey:list[list[int]]=None):

    # Cache_checked can be False if not checked, None if doesn't exists, str if does exist
    matplotlib.rcParams['text.color'] = "silver"

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

    ax = plt.gca()
    ax.set_aspect('equal', adjustable='box')
    
    if towns:
        for town in towns:
            for i, polygon in enumerate(town.locations.geoms):
                if journey:
                    add = False 
                    for p_raw in journey:
                        if polygon.contains(Point(p_raw[0], p_raw[1])):
                            add = True
                else:
                    add = True

                if polygon.contains(Point(town.spawn.x, town.spawn.z)) and add == True:
                    plt.fill(*polygon.exterior.xy, fc=town.fill_color + "20", ec=town.border_color, zorder=3, rasterized=True, lw=0.2 if whole == True else 0.5, animated=True)
        
        if outposts == "retain":
            x_lim = ax.get_xlim()
            y_lim = ax.get_ylim()
            

        for town in towns:
            if outposts or journey:
                
                det = town.detached_locations
                for polygon in det.geoms if hasattr(det, "geoms") else [det]:
                    if journey:
                        add = False 
                        for p_raw in journey:
                            if polygon.contains(Point(p_raw[0], p_raw[1])):
                                add = True
                    else:
                        add = True
                    
                    if add:
                        plt.fill(*polygon.exterior.xy, fc=town.fill_color + "20", ec=town.border_color, zorder=3, rasterized=True, lw=0.2 if whole == True else 0.5, animated=True)
    

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

        plt.scatter(x_online, z_online, color="white", s=dot_size or 10, zorder=6)
        plt.scatter(x_offline, z_offline, color="#707070", s=dot_size/10 or 1, zorder=5)

    if dimmed_towns:
        for town in dimmed_towns:
            for i, polygon in enumerate(town.locations.geoms):

                plt.fill(*polygon.exterior.xy, fc=s.map_bordering_town_fill_colour + f"{s.map_bordering_town_opacity:02}", ec=town.border_color + f"{s.map_bordering_town_opacity//2:02}", zorder=2, rasterized=True, lw=0.5)

    if plot_spawn:

        if connect_spawns:
            done = []
            for i, ts in enumerate(itertools.product(connect_spawns, repeat=2)):
                if ts[0].name == ts[1].name or [ts[0].name, ts[1].name] in done:
                    continue 
                
                distance = math.sqrt((ts[0].spawn.x-ts[1].spawn.x)**2 + (ts[0].spawn.z-ts[1].spawn.z)**2)
                plt.plot([t.spawn.x for t in ts], [t.spawn.z for t in ts], color=s.connection_line_colours[i%len(s.connection_line_colours)], zorder=4, lw=0.5, label=f"{int(distance):,} blocks ({ts[0].name[:2]}->{ts[1].name[:2]})")
                done.append([ts[0].name, ts[1].name])
                done.append([ts[1].name, ts[0].name])
            plt.legend(loc="upper left", prop={'size':5}, frameon=False)
        
        if journey:
            for i in range(len(journey)):
                if i == 0:
                    continue 
                
                prev, current = journey[i-1], journey[i]
                d = [current[0]-prev[0], current[1]-prev[1]]

                plt.arrow(prev[0], prev[1], d[0], d[1], length_includes_head=True, head_width=5, head_length=10, color="#FFFFFFB4", zorder=5, lw=0.5, linestyle='dashed')
    
    if outposts != "retain" or journey:
        x_lim = ax.get_xlim()
        y_lim = ax.get_ylim()
    
    dpi = s.IMAGE_DPI_DRAWING

    if whole or (show_earth == "auto" and (x_lim[1]-x_lim[0] > s.show_earth_bg_if_over or y_lim[1]-y_lim[0] > s.show_earth_bg_if_over)):
        show_earth = True
        
        if (whole or (x_lim[1]-x_lim[0] > xw*1.7 or y_lim[1]-y_lim[0] > yw*1.5)):
            if bg_path == s.earth_bg_path:
                bg_path = s.earth_bg_path_whole
            dpi = s.IMAGE_DPI_DRAWING_BIG

    if show_earth == True:
        
        img = plt.imread(bg_path)
        plt.imshow(img, extent=[0-xw, xw, 0-yw, yw], origin='lower')
        
    
    if not whole:
        if maintain_aspect and (x_lim[1]-x_lim[0]) < 2*(y_lim[1]-y_lim[0]) :
            x_lim_centre = (x_lim[1]+x_lim[0])/2
            y_lim_mag_from_centre = (y_lim[1]-y_lim[0])/2

            x_lim = (x_lim_centre-y_lim_mag_from_centre*2, x_lim_centre+y_lim_mag_from_centre*2)

            shift_x = ((xw-x_lim[1]) if x_lim[1] > xw else 0) + (0-((0-xw)-(0-x_lim[0])) if x_lim[0] < 0-xw else 0)
            x_lim = x_lim[0]+shift_x, x_lim[1]+shift_x
        
        if maintain_aspect and (y_lim[1]-y_lim[0]) < 0.3*(x_lim[1]-x_lim[0]) :
            y_lim_centre = (y_lim[1]+y_lim[0])/2
            x_lim_mag_from_centre = (x_lim[1]-x_lim[0])/2

            y_lim = (y_lim_centre-x_lim_mag_from_centre*0.3, y_lim_centre+x_lim_mag_from_centre*0.3)

            shift_y = ((yw-y_lim[1]) if y_lim[1] > yw else 0) + (0-((0-yw)-(0-y_lim[0])) if y_lim[0] < 0-yw else 0)
            y_lim = y_lim[0]+shift_y, y_lim[1]+shift_y
        
        if connect_spawns:
            x_lim = x_lim[1]-((x_lim[1]-x_lim[0])*1.25), x_lim[1]
            y_lim = y_lim[0], (y_lim[0]+((0.92+(0.08*len(connect_spawns)))*(y_lim[1]-y_lim[0])))

        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
    
    if plot_spawn and towns:
        if not dot_size:
            dot_size = 10

        x_lim = ax.get_xlim()
        y_lim = ax.get_ylim()
        biggest_boundary = max(x_lim[1]-x_lim[0], y_lim[1]-y_lim[0])
        
        for town in towns:
            plt.scatter([town.spawn.x], [town.spawn.z], color=town.border_color, zorder=3, s=(min(1000/biggest_boundary, 1))*dot_size)
    

    ax.invert_yaxis()

    plt.axis('off')

    buf = io.BytesIO()
    plt.savefig(buf, dpi=dpi, transparent=True, bbox_inches="tight", pad_inches = 0)

    if cache_name and cache_id and not players:
        with open(f"./cache/{cache_name}_{cache_id}.png", "wb") as f:
            f.write(buf.getbuffer())
    
    buf.seek(0)
    plt.close()

    return buf


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))