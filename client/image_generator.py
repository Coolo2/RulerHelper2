from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre
    from client.objects import properties as o_pre

import io
import os
import itertools 
import math
import datetime

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.style as mplstyle
from matplotlib.collections import PatchCollection as MPatchCollection
from matplotlib.patches import Polygon as MPolygon

# SVG Conversion
from svgpath2mpl import parse_path
import xml.etree.ElementTree as etree

from client import funcs

matplotlib.use('Agg') 
mplstyle.use('fast')

color = "silver"
matplotlib.rcParams['text.color'] = color
matplotlib.rcParams['axes.labelcolor'] = color
matplotlib.rcParams['xtick.color'] = color
matplotlib.rcParams['ytick.color'] = color
matplotlib.rcParams["axes.edgecolor"] = color
matplotlib.rcParams["xtick.labelsize"] = 7

import warnings
warnings.filterwarnings("ignore")

CACHE_SPLIT_STRING = "_+_"

class XTickFormatter:
    DATETIME = lambda initial, x: datetime.datetime.strftime(initial + datetime.timedelta(seconds=x), "%b %d %Y %H:%M")
    DATE = lambda initial, x: datetime.datetime.strftime(initial + datetime.timedelta(seconds=x), "%b %d %Y")
    NUMBER = lambda initial, x: str(x)

class YTickFormatter:
    TIME = lambda y: funcs.generate_time(y)
    DEFAULT = lambda x: str(int(x))

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
    import setup as s
    def check_cache(self):
        if not self.s.CACHE_IMAGES:
            return self 
        
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
        if self.s.CACHE_IMAGES:
            with open(f"./cache/{self.name}{CACHE_SPLIT_STRING}{self.id}{CACHE_SPLIT_STRING}{self.extra}.png", "wb") as f:
                f.write(buf.getbuffer())


class ImageGenerator():
    def __init__(self, client : client_pre.Client):
        self.client = client 

        self.map_width, self.map_height = 36863, 18431

        self.__map_polys : list[MPolygon] = self.__load_map() 

    import setup as s
    
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
            sorted_points = self.sorted_points

            if len(sorted_points) > 0 and type(sorted_points[-1].x) == datetime.date:
                if sorted_points[-1].x < datetime.date.today():
                    self.raw_points.append(ImageGenerator.Vertex(datetime.date.today(), sorted_points[-1].y))

            return self.sorted_points
        
        def decode_points(self, line_graph : client_pre.image_generator.ImageGenerator.LineGraph):
            
            abstracted = self.abstracted_points

            points = []
            for i, point in enumerate(abstracted):
                points.append(point.make_relative(line_graph.min_max_x[0]))
            
            return points

    YTickFormatter = YTickFormatter
    XTickFormatter = XTickFormatter

    class LineGraph():
        def __init__(self, x_tick_formatter : XTickFormatter, y_tick_formatter = None, colors : list[str] = None):
            self.lines : list[ImageGenerator.Line] = [] 
            self.colors = colors

            if not y_tick_formatter:
                y_tick_formatter = YTickFormatter.DEFAULT

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
    
    def __config_graph_chart(self, title, x_label, y_label):
        plt.rcParams["figure.figsize"] = [6.4*1.6, 4.8]

        plt.title(title, y=1)
        if x_label: plt.xlabel(x_label)
        if y_label: plt.ylabel(y_label)
        plt.xticks(rotation=270)

    async def plot_linegraph(self, lg : LineGraph, title : str, x_label : str, y_label : str):
        plt.close()
        
        self.__config_graph_chart(title, x_label, y_label)

        if not lg.colors:
            lg.colors = self.s.compare_line_colors

        total_points = 0
        for i, line in enumerate(lg.lines):
            color_i = self.s.line_color if len(lg.lines) == 1 else lg.colors[i%len(lg.colors)]
            points = line.decode_points(lg)
            total_points += len(points)

            if len(points) == 1: # Remove nan and count
                plt.scatter(x=points[-1][0] if len(points) > 0 else 0, y=points[-1][1], color=color_i, label=line.name)
            else:
                plt.plot([p[0] for p in points], [p[1] for p in points], color=color_i, label=line.name, alpha=1 if len(lg.lines) == 1 else 0.75)
        
        gca = plt.gca()
        gca.set_facecolor("#00000000")

        gca.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        if total_points > 0:
            x_gap = lg.calculate_x_gap()
            gca.set_xlim(lg.get_xlim(x_gap or 0))

            if x_gap:
                gca.xaxis.set_major_locator(plt.MultipleLocator(x_gap))

            xticks, yticks = gca.get_xticks(), gca.get_yticks()
            gca.set_xticklabels(lg.format_x(list(xticks)))
            gca.set_yticklabels(lg.format_y(list(yticks)))

        if len(lg.lines) > 1:
            plt.legend(bbox_to_anchor=(0, 1.05, 1, 0.2), loc="lower left", prop={'size':10}, frameon=False, mode="expand", borderaxespad=0, ncol=3)
    
    async def plot_barchart(self, data : list[ImageGenerator.Vertex], title : str, x_label : str, y_label : str, y_formatter : YTickFormatter, highlight : str = None ):
        plt.close()
        if not y_formatter:
            y_formatter = YTickFormatter.DEFAULT
        
        self.__config_graph_chart(title, x_label, y_label)

        barlist = plt.bar([d.x for d in data], [d.y for d in data], color=self.s.bar_color)

        gca = plt.gca()
        gca.set_facecolor("#00000000")

        gca.yaxis.set_major_locator(plt.MaxNLocator(integer=True))

        yticks = gca.get_yticks()
        gca.set_yticklabels([y_formatter(t) for t in yticks])

        xticks = [d.x for d in data]

        if highlight:
            highlight = highlight.replace("_", " ")
            if highlight in list(xticks):
                barlist[list(xticks).index(highlight)].set_color('r')
    
    async def plot_piechart(self, data : list[ImageGenerator.Vertex], title : str ):
        plt.close()

        plt.rcParams["figure.figsize"] = [6.4*1.6, 4.8]
        plt.gca().set_facecolor("#00000000")

        def _autopct(pct):
            return ('%.1f' % pct) + "%" if pct > 3 else ''

        barlist, labels, pct_texts = plt.pie([d.y for d in data], labels=[d.x for d in data], autopct=_autopct, textprops={'fontsize': 7, "color":"white"}, rotatelabels=True, radius=1, startangle=160)
        
        for label, pct_text in zip(labels, pct_texts):
            pct_text.set_rotation(label.get_rotation())
        
        plt.title(title, y=1.2)
        plt.xticks(rotation=270)
    
    async def plot_timeline(self, points : list[ImageGenerator.Vertex], title : str, x_label : str = None, y_label : str = None, boolean_values : bool = False):
        plt.close()

        self.__config_graph_chart(title, x_label, y_label)
        
        minimum = min(points, key=lambda p: p.x_num)
        today = ImageGenerator.Vertex(datetime.date.today(), 1).make_relative(minimum)[0]
        gca = plt.gca()
        gca.set_facecolor("#00000000")

        last = None
        bar_spaces : dict[str, list[tuple[int, int]]]= {}
        x_ticks, x_ticklabels = [], []
        for i, point in enumerate(points):
            rel = point.make_relative(minimum)

            if last != None:
                if last[1] not in bar_spaces:
                    bar_spaces[last[1]] = []
                bar_spaces[last[1]].append((last[0], rel[0]-last[0] ))

            x_ticks.append(rel[0])
            x_ticklabels.append(ImageGenerator.XTickFormatter.DATE(minimum.x, rel[0]))
            
            last = rel 

        if point.y not in bar_spaces:
            bar_spaces[point.y] = []
        bar_spaces[point.y].append((last[0], today-last[0]))
        x_ticks.append(today)
        x_ticklabels.append(ImageGenerator.XTickFormatter.DATE(minimum.x, today))

        gca.set_ylim(0, len(bar_spaces))
        
        start_y = 1
        add_end_y = 1

        gca.set_yticks([start_y+i+0.5 for i in range(len(bar_spaces))] + [len(bar_spaces)+0.5+start_y+add_end_y])
        gca.set_yticklabels(list(bar_spaces) + [""])
        gca.set_xticks(x_ticks)
        gca.set_xticklabels(x_ticklabels)

        colors = self.s.timeline_colors
        if boolean_values:
            colors = self.s.timeline_colors_bool if points[0].y == True else list(reversed(self.s.timeline_colors_bool))

        for i, (name, spaces) in enumerate(bar_spaces.items()):
            plt.broken_barh(spaces, (start_y+i, 1), facecolors =(f'tab:{colors[i%len(colors)]}'))

    class MapBackground:
        AUTO = "auto" 
        ON = True 
        OFF = False

    def __load_map(self):
        
        tree = etree.parse("earth.svg")
        root = tree.getroot()

        ax = plt.gca()
        ax.set_aspect('equal', adjustable='box')

        path_elems = root.findall('.//{http://www.w3.org/2000/svg}path')

        polys = []
        for path in path_elems:

            if (not path.attrib.get("fill") or path.attrib["fill"] != "#000000") and path.get('d') and "cls-1" not in str(path.get("class")) and "010101" not in str(path.attrib.get("style")):
                path_parsed = parse_path(path.attrib['d'])
                coords = path_parsed.to_polygons()
                if coords:

                    coords[0] = coords[0]*(self.map_width/self.s.earth_svg_width)*2  
                    coords[0] = coords[0] - (self.map_width*self.s.stretch_earth_bg[0], self.map_height*self.s.stretch_earth_bg[1])
                    polys.append(MPolygon(coords[0]))
        
        return polys
    
    def __plot_map(self, ax):
        ax.set_facecolor("#1c1c1c")
        ax.add_collection(MPatchCollection(self.__map_polys, facecolor="#292929", zorder=-1))

    def town_cache_item(self, name : str, towns : list[client_pre.objects.Town]):
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
        plt.close()
        
        ax = plt.gca()
        ax.set_aspect('equal', adjustable='box')
        plt.axis('off')
        return ax
    

    def __add_margin(self, x_lim, y_lim, margin_amount):

        x_lim_centre = (x_lim[1]+x_lim[0])/2
        y_lim_centre = (y_lim[1]+y_lim[0])/2

        x_lim_distance = x_lim[1] - x_lim_centre
        y_lim_distance = y_lim[1] - y_lim_centre

        x_lim = x_lim_centre-(x_lim_distance*margin_amount), x_lim_centre+(x_lim_distance*margin_amount)
        y_lim = y_lim_centre-(y_lim_distance*margin_amount), y_lim_centre+(y_lim_distance*margin_amount)
        
        return x_lim, y_lim
    
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
            expand_limits_multiplier : tuple[float] = (1, 1),
            
    ):
        plt.close()

        towns : list[client_pre.objects.Town] = []

        ax = await self.init_map()

        if cache_item and not cache_item.checked:
            cache_item.check_cache()

        if cache_item and cache_item.valid:
            ax.set_facecolor("#00000000")

            dpi = int(cache_item.extra.split("+")[0])
            img = plt.imread(cache_item.path)

            if show_whole_earth:
                plt.imshow(img, extent=[0-self.map_width, self.map_width, 0-self.map_height, self.map_height], origin='lower')
            else:
                plt.imshow(img, extent=[float(n) for n in cache_item.extra.split("+")[1:]], origin='lower')
        else:

            polys = []
            facecolors = []
            edgecolors = []

            x_lim = [9999999, -999999]
            y_lim = [9999999, -999999]

            for o in areas :
                _areas = [o] if type(o) == self.client.objects.Area else o.areas
                for area in _areas:
                    if area.town not in towns:
                        towns.append(area.town)

                    if area.is_mainland or show_outposts:
                        
                        # Calculate drawing boundaries
                        bounds = area.polygon.bounds
                        if bounds[0] < x_lim[0]:
                            x_lim[0] = bounds[0]
                        if bounds[2] > x_lim[1]:
                            x_lim[1] = bounds[2]
                        if bounds[1] < y_lim[0]:
                            y_lim[0] = bounds[1]
                        if bounds[3] > y_lim[1]:
                            y_lim[1] = bounds[3]

                        polys.append(area.matpolygon)
                        facecolors.append(area.fill_color + "20")
                        edgecolors.append(area.border_color)

            # Add towns to drawing
            patches = MPatchCollection(polys, zorder=3, lw=0.2 if show_whole_earth == True else 0.3, )
            ax.add_collection(patches)
            patches.set_facecolor(facecolors)
            patches.set_edgecolor(edgecolors)
            
            if not show_whole_earth:
                x_lim, y_lim = self.__add_margin(x_lim, y_lim, 1.1) # Add margin to limits

                if maintain_aspect_ratio:
                    y_lim = self.__calculate_limits(y_lim, x_lim, self.map_height, 0.3)
                    x_lim = self.__calculate_limits(x_lim, y_lim, self.map_width, 2)
            
            x_lim, y_lim = (max(x_lim[0], 0-self.map_width), min(x_lim[1], self.map_width)), (max(y_lim[0], 0-self.map_height), min(y_lim[1], self.map_height))
            
            if town_spawn_dot:
                if town_spawn_dot == True: town_spawn_dot : int = 15 # if town spawn dot is enabled with no size then set to default 

                # Gather colours and points for spawn dots and put into dictionary
                colors_points = {}
                biggest_boundary = max(x_lim[1]-x_lim[0], y_lim[1]-y_lim[0]) if not show_whole_earth else self.map_width*2 # Calculate boundary to choose a more sutiable dot size
                for town in towns:
                    if town.border_color not in colors_points:
                        colors_points[town.border_color] = ([], [])
                    colors_points[town.border_color][0].append(town.spawn.x)
                    colors_points[town.border_color][1].append(town.spawn.z)
                
                # Scatter the gathered points 
                for color, points in colors_points.items():
                    plt.scatter(points[0], points[1], color=color, zorder=4, s=(min(3000/biggest_boundary, 2))*town_spawn_dot, linewidths=0)

            if show_background == self.MapBackground.AUTO:
                show_background = x_lim[1]-x_lim[0] > self.s.show_earth_bg_if_over or y_lim[1]-y_lim[0] > self.s.show_earth_bg_if_over

            dpi = self.s.IMAGE_DPI_DRAWING

            x_lim, y_lim = self.__expand_limits(x_lim, y_lim, expand_limits_multiplier)

            if show_background == True:
                self.__plot_map(ax)
            else:
                ax.set_facecolor("#00000000")
            
            if not show_whole_earth:
                ax.set_xlim(x_lim)
                ax.set_ylim(y_lim)
            else:
                ax.set_xlim((0-self.map_width, self.map_width))
                ax.set_ylim((0-self.map_height, self.map_height))
            
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
                expand_limits_multiplier : tuple[float] = (1, 1),
                maintain_aspect_ratio : bool = False
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
            show_background = x_lim[1]-x_lim[0] > self.s.show_earth_bg_if_over or y_lim[1]-y_lim[0] > self.s.show_earth_bg_if_over
        if show_background == True:
            self.__plot_map(ax)
        
        x_lim, y_lim = self.__expand_limits(x_lim, y_lim, expand_limits_multiplier)

        if maintain_aspect_ratio:
            y_lim = self.__calculate_limits(y_lim, x_lim, self.map_height, 0.3)
            x_lim = self.__calculate_limits(x_lim, y_lim, self.map_width, 2)

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
    
    async def layer_claim_circle(self, centre : tuple[int], radius : int):
        
        plt.gca().add_patch(plt.Circle(centre, radius, color='#FF0000', alpha=0.1, zorder=11))
    
    async def layer_spawn_connections(self, towns : list[client_pre.objects.Town]):
        done = []
        for i, ts in enumerate(itertools.product(towns, repeat=2)):
            if ts[0].name == ts[1].name or [ts[0].name, ts[1].name] in done:
                continue 
            
            distance = math.sqrt((ts[0].spawn.x-ts[1].spawn.x)**2 + (ts[0].spawn.z-ts[1].spawn.z)**2)
            plt.plot([t.spawn.x for t in ts], [t.spawn.z for t in ts], color=self.s.connection_line_colours[i%len(self.s.connection_line_colours)], zorder=4, lw=0.5, label=f"{int(distance):,} blocks ({ts[0].name[:2]}->{ts[1].name[:2]})")
            done.append([ts[0].name, ts[1].name])
            done.append([ts[1].name, ts[0].name])
        plt.legend(loc="upper left", prop={'size':5}, frameon=False)
    
    async def render_plt(self, dpi : int, cache_item : CacheItem = None, pad : bool = False):
        
        buf = io.BytesIO()
        plt.savefig(buf, dpi=dpi, transparent=True, bbox_inches="tight", pad_inches = None if pad else 0, facecolor=plt.gca().get_facecolor())

        if cache_item and not cache_item.valid:
            await cache_item.save(buf)
        
        buf.seek(0)

        return buf
