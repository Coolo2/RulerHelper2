from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    import client as client_pre
    

import datetime
from shapely.geometry import Polygon, Point

from client import funcs
from matplotlib.patches import Polygon as MPolygon



class Area():
    def __init__(self, town : client_pre.objects.Town, verticies : list, name : str = None):
        self.__town = town 
        self.__verticies = verticies
        self.__name = name

        self.__polygon_cache = None
    
    @property 
    def name(self):
        return self.__name
    
    @property 
    def town(self):
        return self.__town

    @property 
    def raw_verticies(self) -> list[float]:
        return self.__verticies
    
    def set_verticies(self, verticies : list[tuple[float]]):
        self.__verticies = verticies

    @property 
    def polygon(self):
        if not self.__polygon_cache:
            self.__polygon_cache = Polygon(self.__verticies)
        return self.__polygon_cache
    
    @property 
    def matpolygon(self):
        return MPolygon(self.__verticies)
    
    
    @property 
    def outpost_spawn(self) -> Point:

        for outpost_spawn in self.__town.outpost_spawns:
            if self.polygon.contains(Point(outpost_spawn.x, outpost_spawn.z)):
                return self.polygon
        
        return None 

    @property 
    def is_outpost(self) -> bool:
        if not self.outpost_spawn or len(self.town.areas) == 1:
            return False 
        return True

    @property 
    def is_mainland(self) -> bool:
        return not self.is_outpost

    def is_point_in_area(self, point : Point) -> bool:
        try:
            return self.polygon.contains(Point(point.x, point.z))
        except:
            return False
    
    @property 
    def fill_color(self):
        return self.__town.fill_color
    
    @property 
    def border_color(self):
        return self.__town.border_color
     
    def __eq__(self, other):
        if type(other) == Area and other.name == self.__name:
            return True 
        return False


class Activity():
    def __init__(self, total : int = 0, last : datetime.datetime = datetime.datetime.now(), town : client_pre.objects.Town|str = None, player : client_pre.objects.Player|str = None, nation : client_pre.objects.Nation|str = None):
        self.total = total 
        self.last = last

        self.town = town
        self.player = player
        self.nation = nation
    
    def from_record(record, town : client_pre.objects.Town = None):
        a = Activity()
        if record:
            a.total = record[0]
            a.last = record[1]
        
        a.town = town

        return a
    
    def str_no_timestamp(self, show_minutes=True):
        return funcs.generate_time(self.total, show_minutes)

    def __add__(self, other):
        return Activity(self.total + (other.total if hasattr(other, "total") else other), max(self.last, (other.last if hasattr(other, "last") else datetime.datetime(2000, 1, 1))), self.town)

    __radd__ = __add__

    def __str__(self):
        return f"{funcs.generate_time(self.total)}" + (f" <t:{round(self.last.timestamp())}:R>" if self.total > 0 else '')
    
    def __int__(self):
        return self.total 

    def __float__(self):
        return float(self.total)
    
    def __round__(self, *args):
        return self


class Tax():
    def __init__(self, amount : float, tax_type : str):
        self.amount = amount 
        self.tax_type = tax_type 
    
    def __float__(self):
        return float(self.amount)

    def __int__(self):
        return int(self.amount)
    
    def __add__(self, other):
        return Tax(self.amount + (other.amount if hasattr(other, "amount") else other), self.tax_type)
    
    def __round__(self, *args):
        return self

    __radd__ = __add__

    def __str__(self):
        if self.tax_type == "%":
            return f"{self.amount:,.2f}%"
        return f"${self.amount:,.2f}"

    def for_record(self):
        return self.amount if self.tax_type == "%" else 0




