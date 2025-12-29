import pandas as pd
import psycopg2
from psycopg2 import sql, extras
import json
import logging
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/load.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DatabaseLoader:
    def __init__(self, config_path='config/config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        self.db_config = self.config['database']
        self.processed_path = self.config['paths']['processed_data']
        self.conn = None
        self.cursor = None
        
        os.makedirs('data/logs', exist_ok=True)
    
    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            self.cursor = self.conn.cursor()
            logging.info("[OK] Database connection established")
            return True
        except Exception as e:
            logging.error(f"✗ Database connection failed: {str(e)}")
            return False
    
    def disconnect(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logging.info("Database connection closed")
    
    def execute_query(self, query, params=None):
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            logging.error(f"Query execution failed: {str(e)}")
            return False
    
    def log_etl_execution(self, phase, status, table_name=None, rows_affected=0, error_message=None, exec_time=0):
        query = """
            INSERT INTO etl_execution_log 
            (phase, status, table_name, rows_affected, error_message, execution_time_seconds)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        try:
            self.cursor.execute(query, (phase, status, table_name, rows_affected, error_message, exec_time))
            self.conn.commit()
        except Exception as e:
            logging.warning(f"Failed to log ETL execution: {str(e)}")
    
    def load_dimension(self, table_name, data, unique_columns, return_id_column=None):
        try:
            start_time = datetime.now()
            id_map = {}
            
            select_query = f"SELECT * FROM {table_name}"
            existing_df = pd.read_sql(select_query, self.conn)
            
            rows_inserted = 0
            for _, row in data.iterrows():
                where_clause = " AND ".join([f"{col} = %s" for col in unique_columns])
                check_query = f"SELECT {return_id_column} FROM {table_name} WHERE {where_clause}"
                values = tuple(row[col] for col in unique_columns)
                
                self.cursor.execute(check_query, values)
                result = self.cursor.fetchone()
                
                if result:
                    id_map[tuple(values)] = result[0]
                else:
                    columns = list(row.index)
                    placeholders = ', '.join(['%s'] * len(columns))
                    insert_query = f"""
                        INSERT INTO {table_name} ({', '.join(columns)})
                        VALUES ({placeholders})
                        RETURNING {return_id_column}
                    """
                    self.cursor.execute(insert_query, tuple(row.values))
                    new_id = self.cursor.fetchone()[0]
                    id_map[tuple(values)] = new_id
                    rows_inserted += 1
            
            self.conn.commit()
            exec_time = (datetime.now() - start_time).total_seconds()
            
            logging.info(f"[OK] {table_name}: {rows_inserted} new rows inserted")
            self.log_etl_execution('LOAD', 'SUCCESS', table_name, rows_inserted, None, exec_time)
            
            return id_map
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"[ERROR] Failed to load {table_name}: {str(e)}")
            self.log_etl_execution('LOAD', 'FAILED', table_name, 0, str(e), 0)
            return {}
    
    def bulk_insert(self, table_name, df, batch_size=1000):
        try:
            start_time = datetime.now()
            
            df = df.copy()
            for col in df.columns:
                if df[col].dtype == 'int64':
                    df[col] = df[col].astype(int)
                elif df[col].dtype == 'float64':
                    df[col] = df[col].astype(float)
            
            df = df.where(pd.notnull(df), None)
            
            columns = list(df.columns)
            values = [tuple(row) for row in df.values]
            
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """
            
            total_rows = 0
            for i in range(0, len(values), batch_size):
                batch = values[i:i+batch_size]
                extras.execute_batch(self.cursor, insert_query, batch)
                total_rows += len(batch)
                logging.info(f"  Inserted {total_rows}/{len(values)} rows into {table_name}")
            
            self.conn.commit()
            exec_time = (datetime.now() - start_time).total_seconds()
            
            logging.info(f"[OK] {table_name}: {total_rows} rows loaded in {exec_time:.2f}s")
            self.log_etl_execution('LOAD', 'SUCCESS', table_name, total_rows, None, exec_time)
            
            return total_rows
            
        except Exception as e:
            self.conn.rollback()
            logging.error(f"[ERROR] Failed to bulk insert into {table_name}: {str(e)}")
            self.log_etl_execution('LOAD', 'FAILED', table_name, 0, str(e), 0)
            return 0
    
    def load_dim_temps(self):
        logging.info("[OK] dim_temps: Already initialized in schema")
        return True
    
    def load_dim_destinations(self):
        try:
            destinations = set()
            
            files = [
                'nuitees_destination_clean.csv',
                'taux_occupation_clean.csv',
                'top_destinations_clean.csv'
            ]
            
            for file in files:
                filepath = f'{self.processed_path}{file}'
                if os.path.exists(filepath):
                    df = pd.read_csv(filepath)
                    if 'destination' in df.columns:
                        destinations.update(df['destination'].dropna().unique())
            
            dest_df = pd.DataFrame({'nom_destination': list(destinations)})
            dest_df = dest_df[dest_df['nom_destination'].str.strip() != '']
            
            self.load_dimension('dim_destinations', dest_df, ['nom_destination'], 'destinations_id')
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load destinations: {str(e)}")
            return False
    
    def load_dim_nationalites(self):
        try:
            nationalites = set()
            
            files = [
                'arrivees_nationalite_clean.csv',
                'nuitees_nationalite_clean.csv'
            ]
            
            for file in files:
                filepath = f'{self.processed_path}{file}'
                if os.path.exists(filepath):
                    df = pd.read_csv(filepath)
                    col = 'pays' if 'pays' in df.columns else 'nationalite'
                    if col in df.columns:
                        nationalites.update(df[col].dropna().unique())
            
            nat_df = pd.DataFrame({'nom_pays': list(nationalites)})
            nat_df = nat_df[nat_df['nom_pays'].str.strip() != '']
            
            self.load_dimension('dim_nationalites', nat_df, ['nom_pays'], 'nationalites_id')
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load nationalites: {str(e)}")
            return False
    
    def load_dim_voies_acces(self):
        try:
            filepath = f'{self.processed_path}voies_acces_clean.csv'
            if not os.path.exists(filepath):
                logging.warning("voies_acces_clean.csv not found")
                return False
            
            df = pd.read_csv(filepath)
            voies_df = df[['voie_acces', 'point_entree']].drop_duplicates()
            voies_df.columns = ['type_voie', 'point_entree']
            
            self.load_dimension('dim_voies_acces', voies_df, ['type_voie', 'point_entree'], 'voie_id')
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load voies_acces: {str(e)}")
            return False
    
    def get_temps_id(self, annee, mois=None):
        if mois:
            query = "SELECT temps_id FROM dim_temps WHERE annee = %s AND mois = %s"
            self.cursor.execute(query, (annee, mois))
        else:
            query = "SELECT temps_id FROM dim_temps WHERE annee = %s AND mois IS NULL"
            self.cursor.execute(query, (annee,))
        
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_foreign_key_id(self, table, column, value):
        query = f"SELECT {table.replace('dim_', '')}_id FROM {table} WHERE {column} = %s"
        self.cursor.execute(query, (value,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def load_fact_arrivees(self):
        try:
            files = ['arrivees_type_clean.csv', 'arrivees_nationalite_clean.csv']
            
            for file in files:
                filepath = f'{self.processed_path}{file}'
                if not os.path.exists(filepath):
                    continue
                
                df = pd.read_csv(filepath)
                fact_data = []
                
                for _, row in df.iterrows():
                    temps_id = self.get_temps_id(row['annee'])
                    if not temps_id:
                        continue
                    
                    nationalites_id = None
                    if 'pays' in row:
                        nationalites_id = self.get_foreign_key_id('dim_nationalites', 'nom_pays', row['pays'])
                    
                    type_touriste = row.get('type_touriste', None)
                    arrivees = row.get('arrivees', 0)
                    variation = row.get('variation_22_21_pct', None)
                    
                    fact_data.append({
                        'temps_id': temps_id,
                        'nationalites_id': nationalites_id,
                        'type_touriste': type_touriste,
                        'nombre_arrivees': arrivees,
                        'variation_annuelle_pct': variation
                    })
                
                if fact_data:
                    fact_df = pd.DataFrame(fact_data)
                    self.bulk_insert('fact_arrivees', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_arrivees: {str(e)}")
            return False
    
    def load_fact_nuitees(self):
        try:
            files = ['nuitees_destination_clean.csv', 'nuitees_nationalite_clean.csv']
            
            for file in files:
                filepath = f'{self.processed_path}{file}'
                if not os.path.exists(filepath):
                    continue
                
                df = pd.read_csv(filepath)
                fact_data = []
                
                for _, row in df.iterrows():
                    temps_id = self.get_temps_id(row['annee'])
                    if not temps_id:
                        continue
                    
                    destinations_id = None
                    if 'destination' in row:
                        destinations_id = self.get_foreign_key_id('dim_destinations', 'nom_destination', row['destination'])
                    
                    nationalites_id = None
                    if 'nationalite' in row:
                        nationalites_id = self.get_foreign_key_id('dim_nationalites', 'nom_pays', row['nationalite'])
                    
                    type_touriste = row.get('type_touriste', None)
                    nuitees = row.get('nuitees', 0)
                    variation = row.get('variation_22_21_pct', None)
                    taux_recup = row.get('taux_recup_vs_2019_pct', None)
                    
                    fact_data.append({
                        'temps_id': temps_id,
                        'destinations_id': destinations_id,
                        'nationalites_id': nationalites_id,
                        'type_touriste': type_touriste,
                        'nombre_nuitees': nuitees,
                        'variation_annuelle_pct': variation,
                        'taux_recuperation_vs_2019_pct': taux_recup
                    })
                
                if fact_data:
                    fact_df = pd.DataFrame(fact_data)
                    self.bulk_insert('fact_nuitees', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_nuitees: {str(e)}")
            return False
    
    def load_fact_recettes(self):
        try:
            filepath = f'{self.processed_path}recettes_mensuelles_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            fact_data = []
            
            for _, row in df.iterrows():
                temps_id = self.get_temps_id(row['annee'], row.get('mois'))
                if not temps_id:
                    continue
                
                fact_data.append({
                    'temps_id': temps_id,
                    'montant_recettes': row['recettes'],
                    'variation_annuelle_pct': row.get('variation_22_21_pct', None)
                })
            
            if fact_data:
                fact_df = pd.DataFrame(fact_data)
                self.bulk_insert('fact_recettes', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_recettes: {str(e)}")
            return False
    
    def load_fact_capacite_hoteliere(self):
        try:
            filepath = f'{self.processed_path}capacite_hoteliere_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            fact_data = []
            
            for _, row in df.iterrows():
                temps_id = self.get_temps_id(row['annee'])
                if not temps_id:
                    continue
                
                categories_hotel_id = self.get_foreign_key_id('dim_categories_hotel', 'nom_categorie', row['categorie'])
                
                fact_data.append({
                    'temps_id': temps_id,
                    'categories_hotel_id': categories_hotel_id,
                    'nombre_unites': row['units'],
                    'nombre_chambres': row['chambres'],
                    'nombre_lits': row['lits']
                })
            
            if fact_data:
                fact_df = pd.DataFrame(fact_data)
                self.bulk_insert('fact_capacite_hoteliere', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_capacite_hoteliere: {str(e)}")
            return False
    
    def load_fact_taux_occupation(self):
        try:
            filepath = f'{self.processed_path}taux_occupation_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            fact_data = []
            
            for _, row in df.iterrows():
                temps_id = self.get_temps_id(row['annee'])
                if not temps_id:
                    continue
                
                destinations_id = self.get_foreign_key_id('dim_destinations', 'nom_destination', row['destination'])
                
                fact_data.append({
                    'temps_id': temps_id,
                    'destinations_id': destinations_id,
                    'taux_occupation_pct': row['taux_occupation'],
                    'ecart_annuel_points': row.get('ecart_22_21_points', None)
                })
            
            if fact_data:
                fact_df = pd.DataFrame(fact_data)
                self.bulk_insert('fact_taux_occupation', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_taux_occupation: {str(e)}")
            return False
    
    def load_fact_voies_acces(self):
        try:
            filepath = f'{self.processed_path}voies_acces_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            fact_data = []
            
            for _, row in df.iterrows():
                voie_query = "SELECT voie_id FROM dim_voies_acces WHERE type_voie = %s AND point_entree = %s"
                self.cursor.execute(voie_query, (row['voie_acces'], row['point_entree']))
                result = self.cursor.fetchone()
                voie_id = result[0] if result else None
                
                fact_data.append({
                    'voie_id': voie_id,
                    'total_passages': row['total'],
                    'mre_passages': row.get('mre', None),
                    'touristes_etrangers': row.get('touristes_etrangers', None)
                })
            
            if fact_data:
                fact_df = pd.DataFrame(fact_data)
                self.bulk_insert('fact_voies_acces', fact_df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load fact_voies_acces: {str(e)}")
            return False
    
    def load_ref_agences_voyage(self):
        try:
            filepath = f'{self.processed_path}agences_voyage_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            self.bulk_insert('ref_agences_voyage', df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load ref_agences_voyage: {str(e)}")
            return False
    
    def load_ref_guides_touristiques(self):
        try:
            filepath = f'{self.processed_path}guides_touristiques_clean.csv'
            if not os.path.exists(filepath):
                return False
            
            df = pd.read_csv(filepath)
            self.bulk_insert('ref_guides_touristiques', df)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to load ref_guides_touristiques: {str(e)}")
            return False
    
    def run_full_load(self):
        logging.info("=" * 60)
        logging.info("Starting Data Loading to PostgreSQL")
        logging.info("=" * 60)
        
        if not self.connect():
            return False
        
        success = True
        
        try:
            logging.info("\n--- Loading Dimension Tables ---")
            self.load_dim_temps()
            self.load_dim_destinations()
            self.load_dim_nationalites()
            self.load_dim_voies_acces()
            
            logging.info("\n--- Loading Fact Tables ---")
            
            try:
                self.load_fact_arrivees()
            except Exception as e:
                logging.error(f"Error in load_fact_arrivees: {str(e)}")
                success = False
            
            try:
                self.load_fact_nuitees()
            except Exception as e:
                logging.error(f"Error in load_fact_nuitees: {str(e)}")
                success = False
            
            try:
                self.load_fact_recettes()
            except Exception as e:
                logging.error(f"Error in load_fact_recettes: {str(e)}")
                success = False
            
            try:
                self.load_fact_capacite_hoteliere()
            except Exception as e:
                logging.error(f"Error in load_fact_capacite_hoteliere: {str(e)}")
                success = False
            
            try:
                self.load_fact_taux_occupation()
            except Exception as e:
                logging.error(f"Error in load_fact_taux_occupation: {str(e)}")
                success = False
            
            try:
                self.load_fact_voies_acces()
            except Exception as e:
                logging.error(f"Error in load_fact_voies_acces: {str(e)}")
                success = False
            
            logging.info("\n--- Loading Reference Tables ---")
            try:
                self.load_ref_agences_voyage()
            except Exception as e:
                logging.error(f"Error in load_ref_agences_voyage: {str(e)}")
            
            try:
                self.load_ref_guides_touristiques()
            except Exception as e:
                logging.error(f"Error in load_ref_guides_touristiques: {str(e)}")
            
            logging.info("\n" + "=" * 60)
            if success:
                logging.info("[OK] Data Loading Completed Successfully")
            else:
                logging.warning("[WARNING] Data Loading Completed with Some Errors")
            logging.info("=" * 60)
            
            return success
            
        except Exception as e:
            logging.error(f"[ERROR] Data loading failed: {str(e)}")
            return False
        finally:
            self.disconnect()


if __name__ == "__main__":
    loader = DatabaseLoader()
    loader.run_full_load()
