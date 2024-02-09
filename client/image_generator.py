from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre
    from client import object as o_pre

import setup as s
import client.object

import io
import os
import itertools 
import math
import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle

matplotlib.use('Agg') 
mplstyle.use('fast')
matplotlib.rcParams['text.color'] = "silver"

CACHE_SPLIT_STRING = "_+_"

class CacheItem():
    def __init__(self, name : str, id : str, extra : str = None):

        self.checked = False

        self.name = name 
        self.id = id 
        self.extra = extra 

        self.valid : bool = None
        self.path : str = None
        """
        Cache file names have three parts:
        1. Name - A name of the object. Only one cache should exist for each name
        2. ID - Something to identify the cache and compare to see if it needs to be updated
        3. Extra - Extra data which is used

        These are split by "_+_"
        """
    
    def check_cache(self):
        self.checked = True
        cache_files = [file_name for file_name in os.listdir('./cache') if file_name.endswith(".png")]
    
        for fname in cache_files:
            path = f"./cache/{fname}"

            if fname.startswith(f"{self.name}{CACHE_SPLIT_STRING}{self.id}") and "png" in fname:
                self.extra = fname.replace(f"{self.name}{CACHE_SPLIT_STRING}{self.id}", "").replace(".png", "").replace(CACHE_SPLIT_STRING, "")
                self.valid = True
                self.path = path
            elif self.name in fname:
                os.remove(path)
        
        return self
    
    async def save(self, buf):
        with open(f"./cache/{self.name}{CACHE_SPLIT_STRING}{self.id}{CACHE_SPLIT_STRING}{self.extra}.png", "wb") as f:
            f.write(buf.getbuffer())


class ImageGenerator():
    def __init__(self, client : client_pre.Client):
        self.client = client 

        self.map_width, self.map_height = 36864, 18400
    
    class Vertex():
        def __init__(self, x : typing.Union[datetime.datetime, int], y : float):
            self.x = x
            self.__y = y
        
        @property 
        def x_num(self):
            if type(self.x) == datetime.datetime:
                return self.x.timestamp()
            elif type(self.x) == datetime.date:
                return datetime.datetime.fromisoformat(self.x.isoformat()).timestamp()
            elif type(self.x) == datetime.timedelta:
                return self.x.total_seconds()
            return self.x
        
        @property 
        def y(self):
            return self.__y.total_seconds() if type(self.__y) == datetime.timedelta else self.__y
        
        def make_relative(self, minimum : ImageGenerator.Vertex):
            return (self.x_num - minimum.x_num, self.y)
            #return (self.x_num - minimum.x_num, self.y) if type(self.x) not in [datetime.datetime, datetime.timedelta, datetime.date] else ((self.x_num - minimum.x_num)//60, self.y)

        def __repr__(self):
            return f"<Vertex {self.x} {self.y}>"
        
    class Line():
        def __init__(self, points : list[ImageGenerator.Vertex], name : str = None, remove_none = True):
            self.raw_points = [p for p in points if p.y != None] if remove_none else points
            self.name = name
        
        @property 
        def min_max_x(self):
            return min(self.raw_points, key=lambda k: k.x), max(self.raw_points, key=lambda k: k.x)
        
        @property 
        def sorted_points(self):
            return sorted(self.raw_points, key=lambda p: p.x)

        @property 
        def abstracted_points(self):
            return self.sorted_points
        
        def decode_points(self, line_graph : client_pre.image_generator.ImageGenerator.LineGraph):
            
            abstracted = self.abstracted_points

            points = []
            for i, point in enumerate(abstracted):
                points.append(point.make_relative(line_graph.min_max_x[0]))
            
            return points

    class XTickFormatter:
        DATETIME = lambda initial, x: datetime.datetime.strftime(initial + datetime.timedelta(seconds=x), "%b %d %Y %H:%M")
        DATE = lambda initial, x: datetime.datetime.strftime(initial + datetime.timedelta(seconds=x), "%b %d %Y")
        NUMBER = lambda initial, x: str(x)
    
    class YTickFormatter:
        TIME = lambda y: client.funcs.generate_time(y)
        DEFAULT = lambda x: str(int(x))

    class LineGraph():
        def __init__(self, x_tick_formatter : ImageGenerator.XTickFormatter, y_tick_formatter = None, colors : list[str] = None):
            self.lines : list[ImageGenerator.Line] = [] 
            self.colors = colors

            if not y_tick_formatter:
                y_tick_formatter = ImageGenerator.YTickFormatter.DEFAULT

            self.__min_x, self.__max_x = None, None 
            self.__x_tick_formatter, self.__y_tick_formatter = x_tick_formatter, y_tick_formatter
        
        def add_line(self, line : ImageGenerator.Line):
            self.lines.append(line)
        
        @property 
        def min_max_x(self):

            if not self.__min_x and not self.__max_x:
            
                _ = [l.min_max_x for l in self.lines]
                mins, maxes = [mm[0] for mm in _], [mm[1] for mm in _]

                self.__min_x, self.__max_x = min(mins, key=lambda k: k.x), max(maxes, key=lambda k: k.x) 
            
            return self.__min_x, self.__max_x

        def format_x(self, ticks : list[plt.Text]):
            return [self.__x_tick_formatter(self.min_max_x[0].x, t) for t in ticks]
        
        def format_y(self, ticks : list[plt.Text]):
            return [str(self.__y_tick_formatter(t)) for t in ticks]
        
        def calculate_x_gap(self):

            if self.__x_tick_formatter == ImageGenerator.XTickFormatter.DATETIME:
                return None
            
            difference_seconds = (self.min_max_x[1].x_num-self.min_max_x[0].x_num)
            difference_days = difference_seconds/60/60/60/24 
            gap_days = int(max(round(difference_days), 1))
            
            return gap_days*60*60*24
        
        def get_xlim(self, x_gap : float = 0):
            pad = 0.85
            return [0-(pad*x_gap), self.min_max_x[1].x_num-self.min_max_x[0].x_num+(pad*x_gap)]
        
        @property 
        def x_formatter(self):
            return self.__x_tick_formatter
    
    

    async def plot_linegraph(self, lg : LineGraph, title : str, x_label : str, y_label : str):
        color = "silver"
        plt.rcParams["figure.figsize"] = [6.4*1.6, 4.8]
        matplotlib.rcParams['text.color'] = color
        matplotlib.rcParams['axes.labelcolor'] = color
        matplotlib.rcParams['xtick.color'] = color
        matplotlib.rcParams['ytick.color'] = color
        matplotlib.rcParams["axes.edgecolor"] = color
        matplotlib.rcParams["xtick.labelsize"] = 7

        plt.title(title, y=1)
        plt.xlabel(x_label)
        plt.ylabel(y_label)
        plt.xticks(rotation=270)

        if not lg.colors:
            lg.colors = s.compare_line_colors

        for i, line in enumerate(lg.lines):
            color_i = s.line_color if len(lg.lines) == 1 else lg.colors[i%len(lg.colors)]
            points = line.decode_points(lg)

            if len(points) == 1: # Remove nan and count
                plt.scatter(x=points[-1][0] if len(points) > 0 else 0, y=points[-1][1], color=color_i, label=line.name)
            else:
                plt.plot([p[0] for p in points], [p[1] for p in points], color=color_i, label=line.name, alpha=1 if len(lg.lines) == 1 else 0.75)

        gca = plt.gca()
        
        x_gap = lg.calculate_x_gap()
        gca.set_xlim(lg.get_xlim(x_gap or 0))
        
        gca.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        if x_gap:
            gca.xaxis.set_major_locator(plt.MultipleLocator(x_gap))

        xticks, yticks = gca.get_xticks(), gca.get_yticks()
        gca.set_xticklabels(lg.format_x(list(xticks)))
        gca.set_yticklabels(lg.format_y(list(yticks)))

        if len(lg.lines) > 1:
            plt.legend(bbox_to_anchor=(0, 1.05, 1, 0.2), loc="lower left", prop={'size':10}, frameon=False, mode="expand", borderaxespad=0, ncol=3)


    
    class MapBackground:
        AUTO = "auto" 
        ON = True 
        OFF = False
    
    def __plot_area(self, area : client_pre.object.Area, dimmed : bool, show_whole_earth : bool):

        if not dimmed:
            plt.fill(
                *area.polygon.exterior.xy, 
                fc=area.fill_color + "20", 
                ec=area.border_color, 
                zorder=3, 
                lw=0.2 if show_whole_earth == True else 0.3,
                rasterized=True
            )
        else:
            plt.fill(
                *area.polygon.exterior.xy, 
                fc=s.map_bordering_town_fill_colour + f"{s.map_bordering_town_opacity:02}", 
                ec=area.border_color + f"{s.map_bordering_town_opacity//2:02}", 
                zorder=2, 
                lw=0.2 if show_whole_earth == True else 0.3,
                rasterized=True
            )

    def town_cache_item(self, name : str, towns : list[client_pre.object.Town]):
        total_vertex_count = total_area = 0
        for town in towns:
            total_vertex_count += town.vertex_count
            total_area += town.area

        return CacheItem(name, f"{total_vertex_count}{CACHE_SPLIT_STRING}{total_area}")

    def __calculate_limits(self, main_lim : tuple[float], other_lim : tuple[float], main_width : int, r : float) -> tuple[float]:

        if (main_lim[1]-main_lim[0]) >= r*(other_lim[1]-other_lim[0]):
            return main_lim

        x_lim_centre = (main_lim[1]+main_lim[0])/2
        y_lim_mag_from_centre = (other_lim[1]-other_lim[0])/2

        x_lim = (x_lim_centre-y_lim_mag_from_centre*r, x_lim_centre+y_lim_mag_from_centre*r)

        shift_x = ((main_width-x_lim[1]) if x_lim[1] > main_width else 0) + (0-((0-main_width)-(0-x_lim[0])) if x_lim[0] < 0-main_width else 0)
        x_lim = x_lim[0]+shift_x, x_lim[1]+shift_x

        return x_lim

    async def init_map(self):
        ax = plt.gca()
        ax.set_aspect('equal', adjustable='box')
        plt.axis('off')
        return ax
    
    def __expand_limits(self, x_lim, y_lim, expand_limits_multiplier):
        x_lim = x_lim[1]-((x_lim[1]-x_lim[0])*expand_limits_multiplier[0]), x_lim[1]
        y_lim = y_lim[0], (y_lim[0]+(expand_limits_multiplier[1]*(y_lim[1]-y_lim[0])))
        return x_lim, y_lim

    async def generate_area_map(
            self, 
            areas : list[typing.Union[o_pre.Area, o_pre.Town, o_pre.Object]],
            town_spawn_dot : typing.Union[int, bool],
            show_outposts : bool,
            show_background : MapBackground,
            show_whole_earth : bool,
            cache_item : CacheItem,
            dimmed_areas : list[typing.Union[o_pre.Area, o_pre.Town, o_pre.Object]] = [],
            maintain_aspect_ratio : bool = True,
            expand_limits_multiplier : tuple[float] = (1, 1)
    ):
        bg_path = s.earth_bg_path

        towns : list[client.object.Town] = []

        ax = await self.init_map()

        if cache_item and not cache_item.checked:
            cache_item.check_cache()

        if cache_item and cache_item.valid:
            dpi = int(cache_item.extra.split("+")[0])
            lims = [float(n) for n in cache_item.extra.split("+")[1:]]
            img = plt.imread(cache_item.path)
            plt.imshow(img, extent=[lims[0], lims[1], lims[2], lims[3]], origin='lower')
        else:
            # Plot towns and dimmed towns
            for o in areas :
                _areas = [o] if type(o) == client.object.Area else o.areas
                for area in _areas:
                    if area.town not in towns:
                        towns.append(area.town)
                    if area.is_mainland or show_outposts:
                        self.__plot_area(area, False, show_whole_earth)

            x_lim, y_lim = ax.get_xlim(), ax.get_ylim()

            # Plot dimmed areas after getting limits
            for o in dimmed_areas:
                _areas = [o] if type(o) == client.object.Area else o.areas
                for area in _areas:
                    if area.is_mainland or show_outposts:
                        self.__plot_area(area, True, show_whole_earth)
            
            if not show_whole_earth:
                if maintain_aspect_ratio:
                    x_lim = self.__calculate_limits(x_lim, y_lim, self.map_width, 2)
                    y_lim = self.__calculate_limits(y_lim, x_lim, self.map_height, 0.3)
            
            x_lim, y_lim = (max(x_lim[0], 0-self.map_width), min(x_lim[1], self.map_width)), (max(y_lim[0], 0-self.map_height), min(y_lim[1], self.map_height))
            
            if town_spawn_dot:
                if town_spawn_dot == True: town_spawn_dot : int = 7
                biggest_boundary = max(x_lim[1]-x_lim[0], y_lim[1]-y_lim[0])
                for town in towns:
                    plt.scatter([town.spawn.x], [town.spawn.z], color=town.border_color, zorder=3, s=(min(1000/biggest_boundary, 1))*town_spawn_dot)

            if show_background == self.MapBackground.AUTO:
                show_background = x_lim[1]-x_lim[0] > s.show_earth_bg_if_over or y_lim[1]-y_lim[0] > s.show_earth_bg_if_over

            if (show_whole_earth or (x_lim[1]-x_lim[0] > self.map_width*1.7 or y_lim[1]-y_lim[0] > self.map_height*1.5)):
                bg_path = s.earth_bg_path_whole
                dpi = s.IMAGE_DPI_DRAWING_BIG
            else:
                dpi = s.IMAGE_DPI_DRAWING
        
            if show_background == True:
                plt.imshow(plt.imread(bg_path), extent=[0-self.map_width, self.map_width, 0-self.map_height, self.map_height], origin='lower')
            
            x_lim, y_lim = self.__expand_limits(x_lim, y_lim, expand_limits_multiplier)
            
            if not show_whole_earth:
                ax.set_xlim(x_lim)
                ax.set_ylim(y_lim)
            
            if cache_item:
                cache_item.extra = f"{dpi}+{x_lim[0]:.2f}+{x_lim[1]:.2f}+{y_lim[0]:.2f}+{y_lim[1]:.2f}"
        
        ax.invert_yaxis()
        

        return dpi
    
    async def layer_player_locations(
                self, 
                primary_players : list[o_pre.Player], 
                secondary_players : list[o_pre.Player], 
                primary_dot_size : int = 8, 
                secondary_dot_size : float = 0.5, 
                show_background: MapBackground=False, 
                expand_limits_multiplier : tuple[float] = (1, 1)
    ):

        ax = plt.gca()

        x_online, z_online, x_offline, z_offline = [], [], [], []

        for player in primary_players:
            x_online.append(player.location.x)
            z_online.append(player.location.z)
        for player in secondary_players:
            x_offline.append(player.location.x)
            z_offline.append(player.location.z)
        
        plt.scatter(x_online, z_online, color="white", s=primary_dot_size, zorder=6)
        plt.scatter(x_offline, z_offline, color="#707070", s=secondary_dot_size, zorder=5)
        
        x_lim, y_lim = ax.get_xlim(), ax.get_ylim()
        if show_background == self.MapBackground.AUTO:
            show_background = x_lim[1]-x_lim[0] > s.show_earth_bg_if_over or y_lim[1]-y_lim[0] > s.show_earth_bg_if_over
        if show_background == True:
            plt.imshow(plt.imread(s.earth_bg_path_whole), extent=[0-self.map_width, self.map_width, 0-self.map_height, self.map_height], origin='lower')
        
        x_lim, y_lim = self.__expand_limits(x_lim, y_lim, expand_limits_multiplier)

        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)

        if show_background == True:
            ax.invert_yaxis()

    async def layer_journey(self, journey : list[list[int]]):
        for i in range(len(journey)):
            if i == 0:
                continue 
            
            prev, current = journey[i-1], journey[i]
            d = [current[0]-prev[0], current[1]-prev[1]]

            plt.arrow(prev[0], prev[1], d[0], d[1], length_includes_head=True, head_width=5, head_length=10, color="#FFFFFFB4", zorder=5, lw=0.5, linestyle='dashed')
    
    async def layer_spawn_connections(self, towns : list[client.object.Town]):
        done = []
        for i, ts in enumerate(itertools.product(towns, repeat=2)):
            if ts[0].name == ts[1].name or [ts[0].name, ts[1].name] in done:
                continue 
            
            distance = math.sqrt((ts[0].spawn.x-ts[1].spawn.x)**2 + (ts[0].spawn.z-ts[1].spawn.z)**2)
            plt.plot([t.spawn.x for t in ts], [t.spawn.z for t in ts], color=s.connection_line_colours[i%len(s.connection_line_colours)], zorder=4, lw=0.5, label=f"{int(distance):,} blocks ({ts[0].name[:2]}->{ts[1].name[:2]})")
            done.append([ts[0].name, ts[1].name])
            done.append([ts[1].name, ts[0].name])
        plt.legend(loc="upper left", prop={'size':5}, frameon=False)
    
    async def render_plt(self, dpi : int, cache_item : CacheItem = None, dont_close = False, pad : bool = False):
        buf = io.BytesIO()
        plt.savefig(buf, dpi=dpi, transparent=True, bbox_inches="tight", pad_inches = None if pad else 0 )

        if cache_item and not cache_item.valid:
            await cache_item.save(buf)
        
        if not dont_close:
            plt.close()
        
        buf.seek(0)

        return buf
    

        

