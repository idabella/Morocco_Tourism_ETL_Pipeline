import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/transform.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class MoroccoTourismTransformer:
    def __init__(self, raw_data_path='data/raw/', processed_data_path='data/processed/'):
        self.raw_path = raw_data_path
        self.processed_path = processed_data_path
        os.makedirs(self.processed_path, exist_ok=True)
        os.makedirs('data/logs', exist_ok=True)
        
    def clean_numeric_columns(self, df, columns):
        for col in columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(' ', '').str.replace(',', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    
    def standardize_column_names(self, df):
        df.columns = df.columns.str.strip().str.lower()
        df.columns = df.columns.str.replace(' ', '_').str.replace('é', 'e').str.replace('è', 'e')
        df.columns = df.columns.str.replace('ô', 'o').str.replace('û', 'u').str.replace('î', 'i')
        df.columns = df.columns.str.replace('à', 'a').str.replace('ç', 'c')
        return df
    
    def find_file(self, *possible_names):
        for name in possible_names:
            filepath = f'{self.raw_path}{name}'
            if os.path.exists(filepath):
                return filepath
        return None
    
    def transform_arrivees_type(self):
        try:
            logging.info("Transforming arrivees_type data...")
            filepath = self.find_file('01_arrivees_type.csv', 'arrivees_type.csv')
            if not filepath:
                logging.warning("Arrivees type file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            df = self.clean_numeric_columns(df, ['arrivees'])
            df['annee'] = pd.to_numeric(df['annee'], errors='coerce')
            
            df = df.drop_duplicates()
            
            df = df.dropna(subset=['annee', 'type_touriste', 'arrivees'])
            
            df['annee'] = df['annee'].astype(int)
            df['type_touriste'] = df['type_touriste'].str.strip()
            
            df.to_csv(f'{self.processed_path}arrivees_type_clean.csv', index=False)
            logging.info(f"SUCCESS: Arrivees type transformed: {len(df)} rows")
            return df
            
        except Exception as e:
            logging.error(f"Error transforming arrivees_type: {str(e)}")
            return None
    
    def transform_arrivees_nationalite(self):
        try:
            logging.info("Transforming arrivees_nationalite data...")
            filepath = self.find_file('02_arrivees_nationalite.csv', 'arrivees_nationalite.csv')
            if not filepath:
                logging.warning("Arrivees nationalite file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and col != 'pays']
            variation_cols = [col for col in df.columns if 'variation' in col]
            
            df = self.clean_numeric_columns(df, year_cols + variation_cols)
            
            id_vars = ['pays'] + variation_cols
            df_melted = df.melt(id_vars=id_vars, value_vars=year_cols, 
                                var_name='annee', value_name='arrivees')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            
            df_melted = df_melted.dropna(subset=['arrivees'])
            df_melted['pays'] = df_melted['pays'].str.strip()
            
            df_melted.to_csv(f'{self.processed_path}arrivees_nationalite_clean.csv', index=False)
            logging.info(f"SUCCESS: Arrivees nationalite transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming arrivees_nationalite: {str(e)}")
            return None
    
    def transform_nuitees_destination(self):
        try:
            logging.info("Transforming nuitees_destination data...")
            filepath = self.find_file('03_nuitees_destination.csv', 'nuitees_destination.csv')
            if not filepath:
                logging.warning("Nuitees destination file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col]
            metric_cols = [col for col in df.columns if 'variation' in col or 'taux' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['destination'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='nuitees')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['nuitees'])
            df_melted['destination'] = df_melted['destination'].str.strip()
            
            df_melted.to_csv(f'{self.processed_path}nuitees_destination_clean.csv', index=False)
            logging.info(f"SUCCESS: Nuitees destination transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming nuitees_destination: {str(e)}")
            return None
    
    def transform_nuitees_nationalite(self):
        try:
            logging.info("Transforming nuitees_nationalite data...")
            filepath = self.find_file('04_nuitees_nationalite.csv', 'nuitees_nationalite.csv')
            if not filepath:
                logging.warning("Nuitees nationalite file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and 'variation' not in col]
            metric_cols = [col for col in df.columns if 'variation' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['nationalite'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='nuitees')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['nuitees'])
            
            df_melted.to_csv(f'{self.processed_path}nuitees_nationalite_clean.csv', index=False)
            logging.info(f"SUCCESS: Nuitees nationalite transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming nuitees_nationalite: {str(e)}")
            return None
    
    def transform_recettes_mensuelles(self):
        try:
            logging.info("Transforming recettes_mensuelles data...")
            filepath = self.find_file('05_recettes_mensuelles.csv', 'recettes_mensuelles.csv')
            if not filepath:
                logging.warning("Recettes mensuelles file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and 'variation' not in col]
            metric_cols = [col for col in df.columns if 'variation' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['mois'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='recettes')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['recettes'])
            df_melted['mois'] = df_melted['mois'].str.strip()
            
            month_map = {'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 
                        'Mai': 5, 'Juin': 6, 'Juillet': 7, 'Août': 8, 
                        'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
                        'Fevrier': 2, 'Aout': 8}
            df_melted['mois_num'] = df_melted['mois'].map(month_map)
            
            df_melted.to_csv(f'{self.processed_path}recettes_mensuelles_clean.csv', index=False)
            logging.info(f"SUCCESS: Recettes mensuelles transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming recettes_mensuelles: {str(e)}")
            return None
    
    def transform_capacite_hoteliere(self):
        try:
            logging.info("Transforming capacite_hoteliere data...")
            filepath = self.find_file('06_capacite_hoteliere.csv', 'capacite_hoteliere.csv')
            if not filepath:
                logging.warning("Capacite hoteliere file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            years = []
            for year in [2019, 2021, 2022]:
                year_cols = [col for col in df.columns if str(year) in col]
                if year_cols:
                    df_year = df[['categorie'] + year_cols].copy()
                    df_year['annee'] = year
                    
                    for col in year_cols:
                        new_name = col.replace(f'annee_{year}_', '')
                        df_year.rename(columns={col: new_name}, inplace=True)
                    
                    years.append(df_year)
            
            df_combined = pd.concat(years, ignore_index=True)
            
            numeric_cols = ['units', 'chambres', 'lits']
            df_combined = self.clean_numeric_columns(df_combined, numeric_cols)
            
            df_combined = df_combined.dropna(subset=numeric_cols)
            df_combined['categorie'] = df_combined['categorie'].str.strip()
            
            df_combined.to_csv(f'{self.processed_path}capacite_hoteliere_clean.csv', index=False)
            logging.info(f"SUCCESS: Capacite hoteliere transformed: {len(df_combined)} rows")
            return df_combined
            
        except Exception as e:
            logging.error(f"Error transforming capacite_hoteliere: {str(e)}")
            return None
    
    def transform_taux_occupation(self):
        try:
            logging.info("Transforming taux_occupation data...")
            filepath = self.find_file('07_taux_occupation.csv', 'taux_occupation.csv')
            if not filepath:
                logging.warning("Taux occupation file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and 'ecart' not in col]
            metric_cols = [col for col in df.columns if 'ecart' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['destination'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='taux_occupation')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['taux_occupation'])
            
            df_melted.to_csv(f'{self.processed_path}taux_occupation_clean.csv', index=False)
            logging.info(f"SUCCESS: Taux occupation transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming taux_occupation: {str(e)}")
            return None
    
    def transform_arrivees_mensuelles(self):
        try:
            logging.info("Transforming arrivees_mensuelles data...")
            filepath = self.find_file('08_arrivees_mensuelles.csv', 'arrivees_mensuelles.csv')
            if not filepath:
                logging.warning("Arrivees mensuelles file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and 'variation' not in col]
            metric_cols = [col for col in df.columns if 'variation' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['mois'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='arrivees')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['arrivees'])
            
            month_map = {'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 
                        'Mai': 5, 'Juin': 6, 'Juillet': 7, 'Août': 8, 
                        'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
                        'Fevrier': 2, 'Aout': 8}
            df_melted['mois_num'] = df_melted['mois'].map(month_map)
            
            df_melted.to_csv(f'{self.processed_path}arrivees_mensuelles_clean.csv', index=False)
            logging.info(f"SUCCESS: Arrivees mensuelles transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming arrivees_mensuelles: {str(e)}")
            return None
    
    def transform_nuitees_mensuelles(self):
        try:
            logging.info("Transforming nuitees_mensuelles data...")
            filepath = self.find_file('09_nuitees_mensuelles.csv', 'nuitees_mensuelles.csv')
            if not filepath:
                logging.warning("Nuitees mensuelles file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col and 'variation' not in col]
            metric_cols = [col for col in df.columns if 'variation' in col]
            
            df = self.clean_numeric_columns(df, year_cols + metric_cols)
            
            df_melted = df.melt(id_vars=['mois', 'type_touriste'] + metric_cols, 
                                value_vars=year_cols, 
                                var_name='annee', value_name='nuitees')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['nuitees'])
            
            month_map = {'Janvier': 1, 'Février': 2, 'Mars': 3, 'Avril': 4, 
                        'Mai': 5, 'Juin': 6, 'Juillet': 7, 'Août': 8, 
                        'Septembre': 9, 'Octobre': 10, 'Novembre': 11, 'Décembre': 12,
                        'Fevrier': 2, 'Aout': 8}
            df_melted['mois_num'] = df_melted['mois'].map(month_map)
            
            df_melted.to_csv(f'{self.processed_path}nuitees_mensuelles_clean.csv', index=False)
            logging.info(f"SUCCESS: Nuitees mensuelles transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming nuitees_mensuelles: {str(e)}")
            return None
    
    def transform_voies_acces(self):
        try:
            logging.info("Transforming voies_acces data...")
            filepath = self.find_file('10_voies_acces.csv', 'voies_acces.csv')
            if not filepath:
                logging.warning("Voies acces file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            numeric_cols = ['total', 'mre', 'touristes_etrangers']
            df = self.clean_numeric_columns(df, numeric_cols)
            
            df = df.dropna(subset=numeric_cols)
            df['voie_acces'] = df['voie_acces'].str.strip()
            df['point_entree'] = df['point_entree'].str.strip()
            
            df.to_csv(f'{self.processed_path}voies_acces_clean.csv', index=False)
            logging.info(f"SUCCESS: Voies acces transformed: {len(df)} rows")
            return df
            
        except Exception as e:
            logging.error(f"Error transforming voies_acces: {str(e)}")
            return None
    
    def transform_indicateurs_globaux(self):
        try:
            logging.info("Transforming indicateurs_globaux data...")
            filepath = self.find_file('11_indicateurs_globaux.csv', 'indicateurs_globaux.csv')
            if not filepath:
                logging.warning("Indicateurs globaux file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            year_cols = [col for col in df.columns if 'annee' in col]
            df = self.clean_numeric_columns(df, year_cols)
            
            df_melted = df.melt(id_vars=['indicateur'], 
                                value_vars=year_cols, 
                                var_name='annee', value_name='valeur')
            
            df_melted['annee'] = df_melted['annee'].str.extract(r'(\d{4})').astype(int)
            df_melted = df_melted.dropna(subset=['valeur'])
            
            df_melted.to_csv(f'{self.processed_path}indicateurs_globaux_clean.csv', index=False)
            logging.info(f"SUCCESS: Indicateurs globaux transformed: {len(df_melted)} rows")
            return df_melted
            
        except Exception as e:
            logging.error(f"Error transforming indicateurs_globaux: {str(e)}")
            return None
    
    def transform_top_destinations(self):
        try:
            logging.info("Transforming top_destinations data...")
            filepath = self.find_file('12_top_destinations.csv', 'top_destinations.csv')
            if not filepath:
                logging.warning("Top destinations file not found")
                return None
                
            df = pd.read_csv(filepath)
            df = self.standardize_column_names(df)
            
            numeric_cols = ['non_residents', 'residents', 'total', 'taux_occupation_pct']
            df = self.clean_numeric_columns(df, numeric_cols)
            
            df = df.dropna(subset=['destination', 'total'])
            df['destination'] = df['destination'].str.strip()
            
            df.to_csv(f'{self.processed_path}top_destinations_clean.csv', index=False)
            logging.info(f"SUCCESS: Top destinations transformed: {len(df)} rows")
            return df
            
        except Exception as e:
            logging.error(f"Error transforming top_destinations: {str(e)}")
            return None
    

    def run_all_transformations(self):
        logging.info("=" * 60)
        logging.info("Starting Morocco Tourism Data Transformation")
        logging.info("=" * 60)
        
        transformations = [
            self.transform_arrivees_type,
            self.transform_arrivees_nationalite,
            self.transform_nuitees_destination,
            self.transform_nuitees_nationalite,
            self.transform_recettes_mensuelles,
            self.transform_capacite_hoteliere,
            self.transform_taux_occupation,
            self.transform_arrivees_mensuelles,
            self.transform_nuitees_mensuelles,
            self.transform_voies_acces,
            self.transform_indicateurs_globaux,
            self.transform_top_destinations
        ]
        
        results = {}
        for transform_func in transformations:
            try:
                result = transform_func()
                results[transform_func.__name__] = result is not None
            except Exception as e:
                logging.error(f"Failed to execute {transform_func.__name__}: {str(e)}")
                results[transform_func.__name__] = False
        
        logging.info("=" * 60)
        logging.info("Transformation Summary:")
        for func_name, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logging.info(f"{func_name}: {status}")
        logging.info("=" * 60)
        
        return results


if __name__ == "__main__":
    transformer = MoroccoTourismTransformer()
    transformer.run_all_transformations()
