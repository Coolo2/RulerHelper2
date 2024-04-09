
import aiosqlite 
import os
import sqlite3 

class RawDatabase():
    def __init__(self, path : str):
        self.path = path 

        self._connection_store : aiosqlite.Connection = None
    
    @property 
    def filename(self):
        return os.path.basename(self.path)

    async def connect(self):
        self._connection_store = await aiosqlite.connect(self.path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES, check_same_thread=False) 
        return self._connection_store
    
    @property 
    def connection(self):
        return self._connection_store
