import os
from os import path
import logging
import logging.config
import random
import pandas as pd
import psycopg2
import sqlalchemy
from sqlalchemy import create_engine
#import datetime
#from sqlalchemy.orm import sessionmaker
#from sqlalchemy.engine import URL

host = os.environ["DB_ADDR"]
db_name = os.environ["DB_DATABASE"]
passw = os.environ["DB_PASSWORD"]
port = os.environ["DB_PORT"]
db_user = os.environ["DB_USER"]

logger = logging.getLogger(__name__)
logger.propagate = False
#parent_path = Path(__file__).parent / 'logging.conf'
#root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print(root_dir)
#log_path = path.join(root_dir, 'log.config')
#print(log_path)
#logging.config.fileConfig(log_path)
#print("got here")


def dataframe_to_input_data(df, new_signal_id):
    # konvertera dataframe till input data format för tidsserie
    logging.info("Konverterar dataframe till rätt format...")
    try:
        timestamps = df.index.values
        values = df[df.columns[0]].values
        input_data = list(zip(timestamps.astype('M8[ms]').tolist(), values, [new_signal_id] * len(values)))
        logging.info("Dataframe konverterades till rätt format.")
        return input_data
    
    except Exception as Argument:
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument


def update_data():
    logging.info("Hämtar metadata...")
    try:
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=passw
        )
        cur = conn.cursor()

        # Query to select all rows from the table
        query = "SELECT * FROM public.acurve_meta;"

        cur.execute(query)
        rows = cur.fetchall()

        lat_range = (57.6, 57.8)  # Example latitude range
        lon_range = (11.9, 12.1)  # Example longitude range

        data = []
        for row in rows:
            # Generate random latitude and longitude values within the specified ranges
            latitude = round(random.uniform(lat_range[0], lat_range[1]), 8)
            longitude = round(random.uniform(lon_range[0], lon_range[1]), 8)

            data.append({
                'SubjectID': row[0],
                'name': row[1],
                'unit': row[2],
                'time_step': row[3],
                'beskrivning': row[4],
                'coordinates': (latitude, longitude)
            })

        logging.info("Metadata hämtades.")
        return pd.DataFrame(data)

    except Exception as Argument:
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument
    
    finally:
        cur.close()
        conn.close()

        
def get_flow_meta_data():
    logging.info("Hämtar metadata för beräkningar...")
    check_metadata = "SELECT * FROM flowcalc_schema.flow_meta;"

    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=passw
        )

        # Create a cursor object
        cur = conn.cursor()

        # Execute the SQL query
        cur.execute(check_metadata)

        # Fetch all rows from the result set
        rows = cur.fetchall()

        # Get column names from cursor description
        columns = [desc[0] for desc in cur.description]

        # Create a DataFrame from the retrieved data and column names
        df = pd.DataFrame(rows, columns=columns)
        logging.info("Metadata för beräkningar hämtades.")
        return df

    except Exception as Argument:
        logging.exception("Exception occured")
        raise ValueError(f"Error: {Argument}") from Argument

    finally:
        cur.close()
        conn.close()

        
def get_ts_from_id(selected_id, start_time, end_time, all_data=False, samples=None):
    logging.info("Hämtar tidsserie...")
    try:
        engine = create_engine(f"postgresql://{db_user}:{passw}@{host}:{port}/{db_name}")
        conn = engine.connect()

        if all_data:
            query = f"""
                SELECT * FROM public.acurve_ts
                WHERE signal IN ('{selected_id}')
                ;
            """

        elif samples:
            query = f"""
                SELECT * FROM public.acurve_ts
                WHERE signal IN ('{selected_id}')
                AND timestamp BETWEEN '{start_time.strftime("%Y-%m-%d %H:%M:%S")}' AND '{end_time.strftime("%Y-%m-%d %H:%M:%S")}'
                LIMIT {samples}
                ;
            """
        else:
            query = f"""
                SELECT * FROM public.acurve_ts
                WHERE signal IN ('{selected_id}')
                AND timestamp BETWEEN '{start_time.strftime("%Y-%m-%d %H:%M:%S")}' AND '{end_time.strftime("%Y-%m-%d %H:%M:%S")}'
                ;
            """

        df = pd.read_sql(sqlalchemy.text(query), conn).pivot(index='timestamp', columns=['signal'], values='value')

        logging.info("Tidsserie hämtades.")
        return df

    except Exception as Argument:
            logging.exception("Exception occured")
            raise ValueError(f"Error: {Argument}") from Argument

    finally:
        conn.close()
        engine.dispose()


def get_flow_ts_from_id(selected_id, start_time, end_time, all_data=False, samples=None):
    logging.info("Tidsserie hämtas...")
    try:
        engine = create_engine(f"postgresql://{db_user}:{passw}@{host}:{port}/{db_name}")
        conn = engine.connect()

        if all_data:
            query = f"""
                SELECT * FROM flowcalc_schema.flow_ts
                WHERE unique_id IN ('{selected_id}')
                ;
            """

        elif samples:
            query = f"""
                SELECT * FROM flowcalc_schema.flow_ts
                WHERE unique_id IN ('{selected_id}')
                AND time BETWEEN '{start_time.strftime("%Y-%m-%d %H:%M:%S")}' AND '{end_time.strftime("%Y-%m-%d %H:%M:%S")}'
                LIMIT {samples}
                ;
            """
        else:
            query = f"""
                SELECT * FROM flowcalc_schema.flow_ts
                WHERE unique_id IN ('{selected_id}')
                AND time BETWEEN '{start_time.strftime("%Y-%m-%d %H:%M:%S")}' AND '{end_time.strftime("%Y-%m-%d %H:%M:%S")}'
                ;
            """
        df = pd.read_sql(sqlalchemy.text(query), conn).pivot(index='time', columns=['unique_id'], values='value')

        logging.info("Tidsserie hämtades.")
        return df
    
    except Exception as Argument:
            logging.exception("Exception occured")
            raise ValueError(f"Error: {Argument}") from Argument

    finally:
        conn.close()
        engine.dispose()

def store_calc_metadata(unique_id, name, original_signal_id, calc_type, 
                        unit, parameters):
    """
    Insert metadata into the database.

    Parameters:
        unique_id (str): Unique ID.
        name (str): Name.
        original_signal_id (str): Original signal ID.
        calc_type (str): Calculation type. Either "overfall" or "rorberakning".
        unit (str): Unit. l/s or m3/s
        parameters (tuple): Calculation parameters. 
        Either (ski_width, ski_height) or (slope, diameter, roughness) depending on calc_type
    """
    logging.info("Skriver metadata till databas...")
    try:
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=passw
        )
        cur = conn.cursor()
        check_unique_id = "SELECT COUNT(*) FROM flowcalc_schema.flow_meta WHERE unique_id = %s;"
        cur.execute(check_unique_id, (unique_id,))
        count = cur.fetchone()[0]

        if count > 0:
            raise ValueError(f"Duplicate unique_id '{unique_id}'. Entry already exists in the table.")

        if calc_type == "overfall":
            
            ski_height, ski_width = parameters
            overfall_insert = """
                INSERT INTO flowcalc_schema.flow_meta (unique_id, name, original_signal_id, calc_type, unit, 
                ski_width, ski_height)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(overfall_insert, (str(unique_id), str(name), str(original_signal_id), str(calc_type), str(unit), float(ski_width), float(ski_height)))
            
            
        elif calc_type == "rorberakning":
            slope, diameter, roughness = parameters
            ror_insert = """
                INSERT INTO flowcalc_schema.flow_meta (unique_id, name, original_signal_id, calc_type, unit,
                slope, diameter, roughness)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(ror_insert, (unique_id, name, original_signal_id, calc_type, unit,
                                      slope, diameter, roughness))

        # Commit the transaction
        conn.commit()
        
        if cur.rowcount != 1:
            logging.error("Insertion failed")
            raise ValueError("Insertion failed.")

        df = get_flow_meta_data()
        logging.info("Metadata har skrivits till databas.")

    except Exception as Argument:
        logging.exception("Exception occured")
        conn.rollback()
        raise ValueError(f"Error during insertion: {Argument}") from Argument

    finally:
        cur.close()
        conn.close()
    

def store_calc_ts(data):
    """
    Store time-series data in the database.

    Parameters:
        data (list of tuples): Time-series data in the format (timestamp, value).
    """
    logging.info("Skriver tidsserie till databas...")
    try:
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=passw
        )
        cur = conn.cursor()

        def insert_data_batch(conn, cur, data):
            try:
                # Define the SQL statement for batch insertion
                insert_query = """
                INSERT INTO flowcalc_schema.flow_ts (time, value, unique_id)
                VALUES %s
                ON CONFLICT (time, unique_id) DO UPDATE
                SET value = EXCLUDED.value
                """
                psycopg2.extras.execute_values(cur, insert_query, data)

                # Commit the transaction
                conn.commit()
                logging.info("Batch skrevs till databas.")       

            except (Exception, psycopg2.Error) as Argument:
                logging.exception("Exception occured") 
                conn.rollback()

        # Define batch size for batch insertion
        batch_size = 100_000
        for i in range(0, len(data), batch_size):
            batch = data[i:i+batch_size]
            insert_data_batch(conn, cur, batch)

    except (Exception, psycopg2.Error) as Argument:
        logging.exception("Exception occured")

    finally:
        logging.info("Tidsserie skrevs till databas.")  
        cur.close()
        conn.close()


def delete_data_by_id(unique_id):
    """
    Delete all data for a given ID in the flowcalc_schema.flow_ts and flowcalc_schema.flow_meta tables.

    Parameters:
        unique_id (str): Unique ID to delete data for.
    """
    logging.info("Raderar beräkning från databas...")
    try:
        conn = psycopg2.connect(
            host=host,
            database=db_name,
            user=db_user,
            password=passw
        )
        cur = conn.cursor()

        # Define the SQL statement to delete data from flowcalc_schema.flow_ts
        delete_ts_query = """
        DELETE FROM flowcalc_schema.flow_ts
        WHERE unique_id = %s
        """
        
        # Execute the delete query for flowcalc_schema.flow_ts with the provided unique_id
        cur.execute(delete_ts_query, (unique_id,))
        
        # Define the SQL statement to delete data from flowcalc_schema.flow_meta
        delete_meta_query = """
        DELETE FROM flowcalc_schema.flow_meta
        WHERE unique_id = %s
        """

        # Execute the delete query for flowcalc_schema.flow_meta with the provided unique_id
        cur.execute(delete_meta_query, (unique_id,))

        # Commit the transaction
        conn.commit()
        logging.info("All data för vald beräkning har raderats.")
        #print(f"All data for ID '{unique_id}' deleted successfully.")

    except (Exception, psycopg2.Error) as Argument:
        logging.exception("Exception occured")

    finally:
        cur.close()
        conn.close()