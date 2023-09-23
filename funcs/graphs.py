
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
import matplotlib.dates as mdates

import datetime

import client

def save_graph(data : dict, title : str, x : str, y : str, chartType, highlight : int = None):
    
    color = "silver"

    matplotlib.rcParams['text.color'] = color
    matplotlib.rcParams['axes.labelcolor'] = color
    matplotlib.rcParams['xtick.color'] = color
    matplotlib.rcParams['ytick.color'] = color
    matplotlib.rcParams["axes.edgecolor"] = color
    matplotlib.rcParams["xtick.labelsize"] = 7

    ax = plt.axes()
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    if chartType == plt.pie:
        def my_autopct(pct):
            return ('%.1f' % pct) + "%" if pct > 3 else ''

        barlist, labels, pct_texts = plt.pie(data.values(), labels=data.keys(), autopct=my_autopct, textprops={'fontsize': 7, "color":"white"}, rotatelabels=True, radius=1, startangle=160)
        
        for label, pct_text in zip(labels, pct_texts):
            pct_text.set_rotation(label.get_rotation())
    else:
        barlist = chartType(data.keys(), data.values(), color=s.bar_color)

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

def save_timeline(data : dict, title : str):

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

    for i, item in enumerate(ranges):
        
        gnt.broken_barh(ranges[item], (start_y+i, 1), facecolors =(f'tab:{s.timeline_colors[i%len(s.timeline_colors)]}'))

    buf = io.BytesIO()
    plt.savefig(buf, dpi=s.IMAGE_DPI_GRAPH, transparent=True, bbox_inches="tight")
    buf.seek(0)

    plt.close()

    return buf
        
def plot_towns(towns : list[client.object.Town], outposts=True, show_earth="auto", plot_spawn=True, dot_size=None, whole=True, players : list[client.object.Player] = None):

    xw = 36865
    yw = 18432

    fig = plt.figure()
    fig.patch.set_facecolor('#2F3136')

    for town in towns:
        
        for i, polygon in enumerate(town.locations.geoms):
            if not outposts and i > 0:
                continue

            plt.fill(*polygon.exterior.xy, fc=town.fill_color + "20", ec=town.border_color, zorder=3, rasterized=True, lw=0.5)

    ax = plt.gca()
    ax.set_aspect('equal', adjustable='box')

    x_lim = ax.get_xlim()
    y_lim = ax.get_ylim()

    
    if show_earth == "auto" and x_lim[1]-x_lim[0] > 2000 or y_lim[1]-y_lim[0] > 2000:
        show_earth = True

    if plot_spawn:
        
        for town in towns:
        
            plt.scatter([town.spawn.x], [town.spawn.z], color=town.border_color, zorder=3, s=dot_size or 10)

    if show_earth == True:
        img = plt.imread("earth.png")
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
    buf.seek(0)

    plt.close()

    return buf





def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))