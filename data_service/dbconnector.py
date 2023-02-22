import psycopg2 as pg

class DBConnector:
    def __init__(self, database: str, 
                        user: str, 
                        password: str, 
                        host:str="localhost",
                        port:int=5432) -> None:
        self.conn_params = {}
        self.conn_params["host"] = host
        self.conn_params["database"] = database
        self.conn_params["user"] = user
        self.conn_params["password"] = password
        self.connection = None

    def connect(self):
        try:
            self.connection = pg.connect(database=self.conn_params["database"], 
                                    user=self.conn_params["user"], 
                                    password=self.conn_params["password"],
                                    host=self.conn_params["host"])

            cur = self.connection.cursor()
            print("Connected to PostgreSQL version:", end=" ")
            cur.execute("SELECT version()")
            db_version = cur.fetchone()
            print(db_version)
            cur.close()
        except (Exception, pg.DatabaseError) as error:
            print(error)

    def getConnection(self):
        return self.connection

    def __del__(self):
        if self.connection:
            self.connection.close()
