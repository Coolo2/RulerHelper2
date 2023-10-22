
import typing
from db import types, wrapper

class CreationAttribute():

    def __init__(
            self, 
            name : str, 
            type : types.Type, 
            not_null : bool = False, 
            unique : bool = False, 
            primary_key : bool = False, 
            foreign_key : bool = False,
            autoincrement : bool = False
    ):
        self.name = name 
        self.type = type 
        self.not_null = not_null
        self.unique = unique 
        self.primary_key = primary_key	
        self.foreign_key = foreign_key
        self.autoincrement = autoincrement

    def for_table(self) -> str:
        flags = ""

        if self.primary_key:
            flags += " PRIMARY KEY"
        elif self.unique:
            flags += " UNIQUE"
        if self.foreign_key:
            flags += " FOREIGN KEY"
        if self.autoincrement:
            flags += " AUTOINCREMENT"

        return f"{self.name} {str(self.type)}{flags}"

    

class CreationCondition():
    def __init__(self, attribute : typing.Union[str, wrapper.Attribute], value : typing.Any, operator : str = None):
        self.attribute = attribute
        self.operator = operator if operator else "="
        self.value = value

        self.no_bindings = False 
        if type(self.value) in [wrapper.Attribute, tuple]:
            self.no_bindings = True
        
    
    @classmethod
    def OR(self):
        return "OR"
    

    @property
    def str_no_table(self):
        if not self.no_bindings:
            return f"{self.attribute.str_no_table if type(self.attribute) != str else self.attribute} {self.operator} ?"
        return f"{self.attribute.str_no_table if type(self.attribute) != str else self.attribute} {self.operator} {str(self.value)}"

    def __str__(self):
        if not self.no_bindings:
            return f"{str(self.attribute)} {self.operator} ?"
        return f"{str(self.attribute)} {self.operator} '{str(self.value)}'"


    def __repr__(self):
        return f"<Condition {str(self.attribute)} {self.operator} {self.value}>"

class CreationTableJoin(CreationCondition):
    def __init__(self, table : typing.Union[str, wrapper.Table], attribute1 : typing.Union[str, wrapper.Attribute], attribute2 : typing.Union[str, wrapper.Attribute]):
        self.attribute1 = attribute1 
        self.attribute2 = attribute2
        self.table = table
    
    def __str__(self):
        return f"{str(self.table)} ON {str(self.attribute1)} = {str(self.attribute2)}"

    def __repr__(self):
        return f"<TableJoin {str(self.table)} {str(self.attribute)} = {str(self.attribute2)}>"

class CreationField():
    def __init__(self, attribute_name : typing.Union[str, wrapper.Attribute], field_value : typing.Any):
        self.attribute_name = attribute_name
        self.field_value = field_value
        self.no_quotations = False
        self.operator = "="

        self._seperate_values = [self.field_value]
    
    def attribute_name_calc(self, name : typing.Union[str, wrapper.Attribute], no_table = False):
        return name if type(name) == str else name.str_no_table

    @classmethod
    def add(self, attribute_name : str, amount : int):
        attribute_name = self.attribute_name_calc(self, attribute_name)

        s = self(attribute_name, f"{attribute_name} + {amount}")
        s._seperate_values = []

        return s
    
    @classmethod
    def external_query(self, table : wrapper.Table, attribute : CreationAttribute|str, condition : CreationCondition|typing.List[CreationCondition], operator : str = "=", query_attribute:CreationAttribute|str=None):
        if type(condition) == list:
            conditions = condition
        else:
            conditions = [condition] if condition else []
        
        attribute_name = self.attribute_name_calc(self, str(attribute))
        attribute_name_val = self.attribute_name_calc(self, str(query_attribute or attribute))
        for condition in conditions:
            if type(condition) == CreationCondition:
                condition.no_bindings = True

        where = (f"WHERE " + " AND ".join(str(condition) for condition in conditions)) if len(conditions) > 0 else ""
        s = self(attribute_name, f"(SELECT {attribute_name_val} FROM {table.name if type(table) != str else table} {where})")
        s._seperate_values = []
        s.no_quotations = True
        s.operator = operator

        return s
    
    @property
    def str_no_table(self):
        attribute_name = self.attribute_name_calc(self.attribute_name)

        if len(self._seperate_values) == 0:
            return f"{attribute_name} {self.operator} {self.field_value}"
        else:
            return f"{attribute_name} {self.operator} ?"

    def __str__(self):
        attribute_name = self.attribute_name_calc(self.attribute_name)
        if len(self._seperate_values) == 0:
            return f"{attribute_name} {self.operator} {self.field_value}"
        else:
            return f"{attribute_name} {self.operator} ?"

class CreationTable():
    def __init__(self, name : str, attributes : typing.List[CreationAttribute]):
        self.name = name 
        self.attributes = attributes
    
    def create_in_db(self, db : wrapper.Database):
        db.create_table(self)

    def _create_table_query(self):
        attributes_as_string = ", ".join(a.for_table() for a in self.attributes)
        return f"CREATE TABLE {self.name} ({attributes_as_string});"

    def __eq__(self, other):
        if other.name == self.name:
            return True 
        return False

class CreationOrder():
    def __init__(self, attribute : typing.Union[str, wrapper.Attribute], order_type : typing.Union[types.OrderType, str] = None):
        self.attribute = attribute 
        self.type = order_type 

        self.__type__name = self.type if type(self.type) == str else self.type.name if self.type else "" 
    
    def __str__(self):
        return f"ORDER BY {str(self.attribute) } {self.__type__name}"

    def __repr__(self):
        return f"<Order by={str(self.attribute)} type={self.__type__name}>"
        
    
