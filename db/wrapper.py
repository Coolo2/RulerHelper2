from __future__ import annotations
import typing
if typing.TYPE_CHECKING:
    from db import wrapper

from db import database, creation, types
import datetime

SUPPORTED_ATTRIBUTE_FLAGS = [
 "NOT NULL", "UNIQUE", "PRIMARY KEY", "FOREIGN KEY", "AUTOINCREMENT"
]


class Attribute():

    def __init__(self, table : wrapper.Table, data: str):
        self.table = table
        self.raw = data

        self.name: str = None
        self.type: types.Type = None
        self.not_null: bool = False
        self.unique: bool = False
        self.primary_key: bool = False
        self.foreign_key: bool = False
        self.autoincrement : bool = False

        # Set flags from sql
        modified_raw = self.raw
        for flag in SUPPORTED_ATTRIBUTE_FLAGS:
            if flag in self.raw:
                modified_raw = modified_raw.replace(flag, "")
                self.__setattr__(flag.lower().replace(" ", "_"), True)

        self.flags = {"NOT NULL":self.not_null, "UNIQUE":self.unique, "PRIMARY KEY":self.primary_key, "FOREIGN KEY":self.foreign_key}
        
        self.name = modified_raw.split(" ")[0]
        self.type = types.from_str(modified_raw.split(" ")[1] if len(modified_raw.split(" ")) > 1 else "")

    @property
    def str_no_table(self):
        return self.name

    def __str__(self):
        return f"{self.table.name}.{self.name}"

    def __repr__(self):
        flags = ""
        for flag_name, flag_value in self.flags.items():
            if flag_value:
                flags += f" {flag_name}"
        return f"<Attribute '{self.name}'{flags}>"

    def sum(self, name : str = None):
        return f"SUM({self.table.name}.{self.name})" + (f" AS {name}" if name else "")

    def max(self, name : str = None):
        return f"MAX({self.table.name}.{self.name})" + (f" AS {name}" if name else "")


class Field():

    def __init__(self, record: wrapper.Record, attribute: Attribute,
                 value: typing.Any):
        self.record = record
        self.attribute = attribute
        self.value = value

    def __repr__(self):
        return f"<Field attribute={self.attribute.name if type(self.attribute) == Attribute else self.attribute} value={self.value}>"


class Record():

    def __init__(self, table: wrapper.Table, attributes: typing.List[Attribute],
                 values: typing.List[typing.Any]):
        self.table = table
        self.__raw_values = values
        self.__attributes = attributes
        self.fields: typing.List[Field] = []

        

        for i in range(len(values)):
            self.fields.append(Field(self, self.__attributes[i], self.__raw_values[i]))

    @property
    def key(self) -> typing.Optional[Field]:
        for field in self.fields:
            if field.attribute.primary_key:
                return field
        for field in self.fields:
            if field.attribute.unique:
                return field
        return None

    async def delete(self):
        await self.table.delete_record(self)
    
    async def update(self,
            *new_fields : typing.List[typing.Union[creation.CreationField, typing.Any]]
    ):
        return await self.table.update_records(self, *new_fields)

    def attribute(self, attribute : typing.Union[wrapper.Attribute, str]) -> typing.Optional[typing.Any]:
        for field in self.fields:
            if field.attribute == attribute or str(field.attribute) == attribute or (type(field.attribute) == Attribute and field.attribute.name == attribute):
                return field.value
        return None



    def __repr__(self):
        return f"<Record {self.__raw_values}>"
    
    @property
    def dict(self):
        return {f.attribute.name: f.value for f in self.fields}

    def to_dict(self):
        return self.dict

class MultiTableRecord(Record):
    def __init__(self, tables: typing.List[wrapper.Table], attributes: typing.List[Attribute], values: typing.List[typing.Any]):
        self.tables = tables
        self.__raw_values = values
        self.__attributes = attributes
        self.fields: typing.List[Field] = []

        # Change to variable names for AS
        for i in range(len(self.__attributes)):
            if type(self.__attributes[i]) == str and " AS " in self.__attributes[i]:
                self.__attributes[i] = self.__attributes[i].split(" AS ")[1]
        
        for i in range(len(values)):
            self.fields.append(Field(self, self.__attributes[i], self.__raw_values[i]))
    
    def __repr__(self):
        return f"<MultiTableRecord {self.__raw_values}>"
    
    @property 
    def dict(self):
        return {str(f.attribute): f.value for f in self.fields}
    def to_dict(self):
        return self.dict

class Table():

    def __init__(self, db: wrapper.Database, name: str, sql: str):
        self.name = name
        self.sql = sql
        self.db = db
        self.primary_key: Attribute = None

        self.attributes: typing.List[Attribute] = []

        # Process attributes
        attributes_string = sql[sql.index("(") + 1:sql.rfind(")") + 1]
        attributes_list = attributes_string.split(", ")
        for attribute_string in attributes_list:
            
            attr = Attribute(self, attribute_string)
            self.attributes.append(attr)
            if attr.primary_key:
                self.primary_key = attr

        self.__records: typing.List[Record] = None
    
    def attribute(self, *attribute_names : str) -> typing.Optional[typing.Union[Attribute, typing.List[Attribute]]]:
        returns = []
        for attr in self.attributes:
            if attr.name in attribute_names:
                returns.append(attr)
                
        if len(returns) == 1:
            return returns[0]
        elif len(returns) == 0:
            return None
        return returns

    async def delete(self):
        await self.db.delete_table(self)

    async def add_record(self,
            fields : typing.List[creation.CreationField, typing.Any]
    ):    
        if type(fields[0]) != list:
            fields : typing.List[typing.List[creation.CreationField, typing.Any]] = [fields]
        
        final_records : typing.List[typing.List[creation.CreationField]] = []
        

        for record in fields:
            record_send = []
            for i, field in enumerate(record):
                if type(field) == creation.CreationField:
                    record_send.append(field)
                else:
                    record_send.append(creation.CreationField(self.attributes[i].name, field))
            final_records.append(record_send)
        
        vals = []
        values = []
        for record in final_records:
            values_for_record = []
            values_for_query_record = []
            
            attributes = [f.attribute_name for f in record]
            
            for field in record:
                if field.no_quotations:
                    values_for_query_record.append(str(field.field_value))
                else:
                    values_for_record.append(str(field.field_value))
                    values_for_query_record.append(" ? ")
            
            vals.append("(" + ", ".join(values_for_query_record) + ")")
            values += values_for_record
        
        await self.db.connection.execute(f"INSERT INTO {self.name} ({', '.join(attributes)}) VALUES {', '.join(vals)}", tuple(values))
        await self.db.commit(True)

        

    async def get_records(
            self,
            conditions: typing.List[typing.Union[creation.CreationCondition,str]] = None,
            attributes: typing.List[typing.Union[str, Attribute]] = None,
            join : typing.Union[creation.CreationTableJoin, typing.List[creation.CreationTableJoin]] = None,
            order : creation.CreationOrder = None,
            limit : int = None,
            group: typing.List[typing.Union[str, Attribute]] = None
    ) -> typing.List[Record]:
        return await self.db.get_records(self, conditions, attributes, join, order, limit, group)

    async def get_record(
            self,
            conditions: typing.List[typing.Union[creation.CreationCondition,str]],
            attributes: typing.List[typing.Union[str, Attribute]] = None,
            group: typing.List[typing.Union[str, Attribute]] = None
    ) -> typing.Optional[Record]:
        records = await self.get_records(conditions=conditions, attributes=attributes, limit=1, group=group)
        return records[0] if len(records) > 0 else None

    async def total_column(
                self, 
                attribute : typing.Union[str, Attribute], 
                conditions : typing.List[typing.Union[creation.CreationAttribute, str]] = None,
                join : typing.Union[creation.CreationTableJoin, typing.List[creation.CreationTableJoin]] = None,
                group: typing.List[typing.Union[str, Attribute]] = None
        ) -> float:
        
        return (await self.db.get_record(self, conditions, [f"SUM({str(attribute)})"], join, group=group)).fields[0].value or 0

    async def max_column(
                self, 
                attribute : typing.Union[str, Attribute], 
                conditions : typing.List[typing.Union[creation.CreationAttribute, str]] = None,
                join : typing.Union[creation.CreationTableJoin, typing.List[creation.CreationTableJoin]] = None,
        ) -> typing.Any:
        return (await self.db.get_record(self, conditions, [f"MAX({str(attribute)})"], join)).fields[0].value

    async def count_rows(self, conditions : typing.List[typing.Union[creation.CreationAttribute, str]] = None,) -> int:
        return (await self.db.get_record(self, conditions, ["COUNT(*)"])).fields[0].value
        

    @property
    def records(self):
        return self.__records.copy() if self.__records else self.get_records()

    async def delete_records(self, *conditions : typing.List[typing.Union[creation.CreationCondition, str]]) -> int:
        if type(conditions[0]) == list:
            conditions = conditions[0]
        
        params = []
        conditions_str = f"DELETE FROM {self.name}"
        if len(conditions) > 0:
            conditions_str += " WHERE "

        for condition in conditions:
            if type(condition) == creation.CreationCondition:
                params.append(str(condition.value))

        conditions_str += " AND ".join(str(c) for c in conditions)

        cursor = await self.db.connection.execute(conditions_str, tuple(params))
        await self.db.commit(True)

        self.__records = None

        return cursor.rowcount
    
    async def delete_record(self, record : Record):
        
        delete_command = f"DELETE FROM {self.name} WHERE "
        conditions = []
        params = []
        for field in record.fields:
            c = creation.CreationCondition(field.attribute, field.value)
            params.append(c.value)
            conditions.append(c)
        
        delete_command += " AND ".join(str(c) for c in conditions)
        await self.db.connection.execute(delete_command, tuple(params))
        await self.db.commit(True)

        if self.__records:
            self.__records.remove(record)
        
    async def update_records(self,
            old_records : typing.Union[typing.List[typing.Union[Record, creation.CreationCondition]], Record, creation.CreationCondition],
            *new_fields : typing.List[typing.Union[creation.CreationField, typing.Any]]
    ) -> int: 
        conditions : typing.List[creation.CreationCondition] = []

        fields = []
        params = []

        if type(new_fields[0]) == list:
            new_fields = new_fields[0]
        for i, field in enumerate(new_fields):
            if type(field) == creation.CreationField:
                fields.append(field.str_no_table)
                params += field._seperate_values
            else:
                f = creation.CreationField(self.attributes[i].name, field)
                fields.append(f.str_no_table)
                params += f._seperate_values
        set_command = " , ".join(fields)

        if old_records:
            if type(old_records) == Record:
                old_records = [old_records]
            elif type(old_records) == creation.CreationCondition:
                conditions = [[old_records.str_no_table]]
                params = [old_records.value]
            else:
                creationconditions = []
                for condition in old_records:
                    if type(condition) == Record:
                        record_conditions = []
                        for field in condition.fields:
                            c = creation.CreationCondition(field.attribute, field.value)
                            params.append(str(c))
                            record_conditions.append(c.str_no_table)
                        conditions.append(record_conditions)

                    elif type(condition) == creation.CreationCondition:

                        creationconditions.append(condition.str_no_table)
                        params.append(condition.value)
                conditions.append(creationconditions)
        
        condition_str = ("WHERE (" + ") OR (".join(" AND ".join(str(condition) for condition in c) for c in conditions) + ")") if len(conditions) > 0 else ""
        command = f"UPDATE {self.name} SET {set_command} {condition_str} "
        
        cursor = await self.db.connection.execute(command, params)
        await self.db.commit(True)
        if self.__records:
            self.__records = None
        
        return cursor.rowcount
        
    async def update_record(self,
            record : typing.Union[Record,creation.CreationCondition],
            *new_fields : typing.List[typing.Union[creation.CreationField, typing.Any]]
    ):
        return await self.update_records(record, *new_fields)
    
    async def record_exists(self, *conditions : typing.List[typing.Union[creation.CreationCondition, creation.CreationField, typing.Any]]):

        if type(conditions[0]) == list:
            conditions = conditions[0]
        
        cds : typing.List[str] = []
        params = []
        for i, condition in enumerate(conditions):
            if type(condition) == creation.CreationCondition:
                cds.append(str(condition))
                params.append(condition.value)
            elif type(condition) == creation.CreationField:
                cds.append(str(condition))
                params.append(condition.field_value)
            else:
                condition = creation.CreationCondition(self.attributes[i], condition)
                cds.append(str(condition))
                params.append(condition.value)
        
        conditions_command = ("WHERE " + " AND ".join(cds)) if len(cds) > 0 else ""
        
        r = await (await self.db.connection.execute(f"SELECT EXISTS(SELECT * FROM {self.name} {conditions_command} )", params)).fetchone()
        return bool(r[0])

    async def add_record_if_not_exists(
                self, 
                fields : typing.List[creation.CreationField, typing.Any],
                conditions : typing.List[typing.Union[creation.CreationCondition, creation.CreationField, typing.Any]]
    ) -> typing.Optional[Record]:
        if await self.record_exists(*conditions):
            return None 
        
        await self.add_record(*fields)
        return True

    async def clear(self):
        await self.db.connection.execute(f"DELETE FROM {self.name}")

        
    def __str__(self):
        return self.name

    def __repr__(self):
        attrnames = ", ".join([a.name for a in self.attributes])
        return f"<Table name={self.name} attributes=[{attrnames}]>"

    def __eq__(self, other):
        if other.name == self.name and other.db == self.db:
            return True
        return False


class Database(database.RawDatabase):

    def __init__(self, path: str, auto_commit : typing.Union[bool, datetime.timedelta] = True):
        super().__init__(path)

        self.path = path
        self.auto_commit = auto_commit

        self.__tables = None
        self.__last_commit = datetime.datetime.now()

    async def get_tables(self) -> typing.List[Table]:
        cursor = await self.connection.execute("SELECT * FROM sqlite_master WHERE type='table'")
        self.__tables = [Table(self, t[1], t[4]) for t in await cursor.fetchall()]
        for table in self.__tables.copy():
            if table.name == "sqlite_sequence":
                self.__tables.remove(table)
        return self.__tables

    async def create_table(self, table: creation.CreationTable) -> Table:
        await self.connection.execute(table._create_table_query())
        table = await self.get_table(table.name)
        if self.__tables:
            self.__tables.append(table)
        await self.commit(True)
        return table

    async def get_table(self, name: str) -> Table:
        table_raw = await (await self.connection.execute("SELECT * FROM sqlite_master WHERE type='table' AND name= ?", (name, ))).fetchone()
        return Table(self, table_raw[1], table_raw[4])

    @property
    async def tables(self):
        return self.__tables.copy() if self.__tables else await self.get_tables()

    async def create_or_get_table(self, table: creation.CreationTable):
        
        for existing_table in (await self.tables):
            if table.name == existing_table.name:
                return existing_table

        return await self.create_table(table)

    async def delete_table(self, table: typing.Union[str, Table]):
        table_name = table.name if type(table) in [Table, creation.CreationTable] else table
        await self.connection.execute(f"DROP TABLE {table_name}")

        if self.__tables:
            if type(table) == str:
                del self.__tables[[t.name for t in self.__tables].index(table_name)]
            else:
                del self.__tables[(await self.tables).index(table)]

        await self.commit(True)
    
    async def get_records(
            self,
            table : typing.Union[str, Table],
            conditions: typing.List[typing.Union[creation.CreationCondition,str]] = None,
            attributes: typing.List[typing.Union[str, Attribute]] = None,
            join : typing.Union[creation.CreationTableJoin, typing.List[creation.CreationTableJoin]] = None,
            order : creation.CreationOrder = None,
            limit : int = None,
            group: typing.List[typing.Union[str, Attribute]] = None,
            distinct : bool = False
    ) -> typing.List[typing.Union[Record, MultiTableRecord]]:
        
        special = False
        table = table if type(table) == Table else self.get_table(table)
        tables = [table]

        attrs: typing.List[str] = []
        tab_attributes = [a.name.lower() for a in table.attributes]

        if attributes:
            for attribute in attributes:
                if type(attribute) == str:
                    real_attributes_matching = [a for a in table.attributes if a.name == attribute]
                    attrs.append(real_attributes_matching[0] if len(real_attributes_matching) > 0 else str(attribute))
                    if attribute.lower() not in tab_attributes:
                        special = True
                else:
                    attrs.append(attribute)
        else:
            attrs = table.attributes

        params = []
        conditions_str = ""
        
        if conditions:
            if type(conditions) == creation.CreationCondition:
                conditions = [conditions]
                
            if len(conditions) > 0: 
                conditions_str += " WHERE "

                if type(conditions[0]) == list:
                    conditions = conditions[0]

                for condition in conditions:
                    if type(condition) == creation.CreationCondition and not condition.no_bindings:
                        params.append(condition.value)
                conditions_str += " AND ".join(str(c) for c in conditions)
            conditions_str = conditions_str.replace("AND OR AND", "OR").replace("( AND", "(").replace("AND )", ")")
        
        group = [group] if type(group) in [str, Attribute] else None if not group else group

        if join:
            if type(join) != list:
                join = [join]
            for j in join:
                tables.append(j.table)

                found = False 
                for attribute in attrs:
                    if j.table.name in str(attribute):
                        found = True 
                if not found and len(attrs) == 0:
                    attrs += j.table.attributes
        join_command = (" JOIN " + " , ".join(str(j) for j in join)) if join else ""
        order_command = str(order) if order else ""
        limit_command = f" LIMIT {limit}" if limit else ""
        group_command = f" GROUP BY {', '.join(str(a) for a in group)}" if group and len(group) > 0 else ""
        distinct_command = f" DISTINCT" if distinct else ""
        
        selection = ", ".join(str(a) for a in attrs ) if len(attrs) != len(table.attributes) or join else "*"
        cursor = await self.connection.execute(f"SELECT{distinct_command} {selection} FROM {table.name}{join_command}{conditions_str}{group_command} {order_command}{limit_command}", tuple(params))
        fetched = await cursor.fetchall()

        resp = []
        for vals in fetched:
            if special or join:
                resp.append(MultiTableRecord(tables, attrs, vals))
            else:
                resp.append(Record(table, attrs, vals))

        if not attributes and not conditions and not order:
            table.__records = resp

        return resp

    async def get_record(
            self,
            table : typing.Union[str, Table],
            conditions: typing.List[typing.Union[creation.CreationCondition,str]],
            attributes: typing.List[typing.Union[str, Attribute]] = None,
            join : typing.Union[creation.CreationTableJoin, typing.List[creation.CreationTableJoin]] = None,
            group: typing.List[typing.Union[str, Attribute]] = None
    ) -> typing.Optional[typing.Union[Record, MultiTableRecord]]:
        rs = await self.get_records(table, conditions, attributes, join, limit=1, group=group)
        return rs[0] if len(rs) > 0 else None

    async def commit(self, auto=False):

        if (auto and self.auto_commit) or not auto:
            if type(self.auto_commit) == datetime.timedelta:
                if datetime.datetime.now() - self.__last_commit < self.auto_commit:
                    return
            await self.connection.commit()

    def __eq__(self, other):
        if other.path == self.path:
            return True 
        return False

