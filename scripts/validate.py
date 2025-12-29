import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/validation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DataValidator:
    def __init__(self, processed_data_path='data/processed/'):
        self.processed_path = processed_data_path
        self.validation_report = {
            'timestamp': datetime.now().isoformat(),
            'files_validated': {},
            'overall_status': 'PASSED'
        }
        os.makedirs('data/logs', exist_ok=True)
    
    def check_file_exists(self, filename):
        filepath = f'{self.processed_path}{filename}'
        exists = os.path.exists(filepath)
        if not exists:
            logging.warning(f"File not found: {filename}")
        return exists
    
    def validate_no_nulls(self, df, columns, file_name):
        issues = []
        for col in columns:
            if col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    pct = (null_count / len(df)) * 100
                    issues.append(f"Column '{col}' has {null_count} nulls ({pct:.2f}%)")
                    logging.warning(f"{file_name}: {col} has {null_count} null values")
        return issues
    
    def validate_numeric_range(self, df, column, min_val=None, max_val=None, file_name=''):
        issues = []
        if column not in df.columns:
            return issues
        
        if min_val is not None:
            below_min = (df[column] < min_val).sum()
            if below_min > 0:
                issues.append(f"Column '{column}' has {below_min} values below {min_val}")
                logging.warning(f"{file_name}: {column} has values below minimum")
        
        if max_val is not None:
            above_max = (df[column] > max_val).sum()
            if above_max > 0:
                issues.append(f"Column '{column}' has {above_max} values above {max_val}")
                logging.warning(f"{file_name}: {column} has values above maximum")
        
        return issues
    
    def validate_duplicates(self, df, subset_cols, file_name):
        duplicates = df.duplicated(subset=subset_cols).sum()
        if duplicates > 0:
            logging.warning(f"{file_name}: Found {duplicates} duplicate rows")
            return [f"Found {duplicates} duplicate rows"]
        return []
    
    def validate_year_range(self, df, year_col, min_year=2010, max_year=2025, file_name=''):
        issues = []
        if year_col in df.columns:
            invalid_years = df[(df[year_col] < min_year) | (df[year_col] > max_year)]
            if len(invalid_years) > 0:
                issues.append(f"Found {len(invalid_years)} rows with invalid years")
                logging.warning(f"{file_name}: Invalid year values found")
        return issues
    
    def validate_percentage(self, df, pct_cols, file_name=''):
        issues = []
        for col in pct_cols:
            if col in df.columns:
                invalid = df[(df[col] < -100) | (df[col] > 2000)]
                if len(invalid) > 0:
                    issues.append(f"Column '{col}' has {len(invalid)} invalid percentage values")
                    logging.warning(f"{file_name}: {col} has invalid percentage values")
        return issues
    
    def generate_statistics(self, df, numeric_cols):
        stats = {}
        for col in numeric_cols:
            if col in df.columns:
                stats[col] = {
                    'count': int(df[col].count()),
                    'mean': float(df[col].mean()) if df[col].count() > 0 else None,
                    'min': float(df[col].min()) if df[col].count() > 0 else None,
                    'max': float(df[col].max()) if df[col].count() > 0 else None,
                    'std': float(df[col].std()) if df[col].count() > 0 else None
                }
        return stats
    
    def validate_arrivees_type(self):
        file_name = 'arrivees_type_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['annee', 'type_touriste', 'arrivees']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
        
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'arrivees', min_val=0, file_name=file_name))
        issues.extend(self.validate_duplicates(df, ['annee', 'type_touriste'], file_name))
        
        stats = self.generate_statistics(df, ['arrivees'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_arrivees_nationalite(self):
        file_name = 'arrivees_nationalite_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['pays', 'annee', 'arrivees']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'arrivees', min_val=0, file_name=file_name))
        
        var_cols = [col for col in df.columns if 'variation' in col]
        issues.extend(self.validate_percentage(df, var_cols, file_name))
        
        stats = self.generate_statistics(df, ['arrivees'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_nuitees_destination(self):
        file_name = 'nuitees_destination_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['destination', 'annee', 'nuitees']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'nuitees', min_val=0, file_name=file_name))
        
        var_cols = [col for col in df.columns if 'variation' in col or 'taux' in col]
        issues.extend(self.validate_percentage(df, var_cols, file_name))
        
        stats = self.generate_statistics(df, ['nuitees'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_nuitees_nationalite(self):
        file_name = 'nuitees_nationalite_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['nationalite', 'annee', 'nuitees']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'nuitees', min_val=0, file_name=file_name))
        
        var_cols = [col for col in df.columns if 'variation' in col]
        issues.extend(self.validate_percentage(df, var_cols, file_name))
        
        stats = self.generate_statistics(df, ['nuitees'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_recettes_mensuelles(self):
        file_name = 'recettes_mensuelles_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['mois', 'annee', 'recettes']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'recettes', min_val=0, file_name=file_name))
        
        if 'mois_num' in df.columns:
            issues.extend(self.validate_numeric_range(df, 'mois_num', min_val=1, max_val=12, file_name=file_name))
        
        stats = self.generate_statistics(df, ['recettes'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_capacite_hoteliere(self):
        file_name = 'capacite_hoteliere_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['categorie', 'annee', 'units', 'chambres', 'lits']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        
        for col in ['units', 'chambres', 'lits']:
            issues.extend(self.validate_numeric_range(df, col, min_val=0, file_name=file_name))
        
        stats = self.generate_statistics(df, ['units', 'chambres', 'lits'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_taux_occupation(self):
        file_name = 'taux_occupation_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['destination', 'annee', 'taux_occupation']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        issues.extend(self.validate_year_range(df, 'annee', file_name=file_name))
        issues.extend(self.validate_numeric_range(df, 'taux_occupation', min_val=0, max_val=100, file_name=file_name))
        
        stats = self.generate_statistics(df, ['taux_occupation'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_voies_acces(self):
        file_name = 'voies_acces_clean.csv'
        logging.info(f"Validating {file_name}...")
        
        if not self.check_file_exists(file_name):
            return {'status': 'FAILED', 'reason': 'File not found'}
        
        df = pd.read_csv(f'{self.processed_path}{file_name}')
        issues = []
        
        required_cols = ['voie_acces', 'point_entree', 'total']
        issues.extend(self.validate_no_nulls(df, required_cols, file_name))
        
        for col in ['total', 'mre', 'touristes_etrangers']:
            if col in df.columns:
                issues.extend(self.validate_numeric_range(df, col, min_val=0, file_name=file_name))
        
        stats = self.generate_statistics(df, ['total', 'mre', 'touristes_etrangers'])
        
        result = {
            'status': 'PASSED' if len(issues) == 0 else 'FAILED',
            'row_count': len(df),
            'issues': issues,
            'statistics': stats
        }
        
        self.validation_report['files_validated'][file_name] = result
        logging.info(f"[OK] {file_name}: {result['status']} ({len(df)} rows, {len(issues)} issues)")
        return result
    
    def validate_all_files(self):
        logging.info("=" * 60)
        logging.info("Starting Data Validation")
        logging.info("=" * 60)
        
        validation_functions = [
            self.validate_arrivees_type,
            self.validate_arrivees_nationalite,
            self.validate_nuitees_destination,
            self.validate_nuitees_nationalite,
            self.validate_recettes_mensuelles,
            self.validate_capacite_hoteliere,
            self.validate_taux_occupation,
            self.validate_voies_acces
        ]
        
        for validate_func in validation_functions:
            try:
                validate_func()
            except Exception as e:
                logging.error(f"Error in {validate_func.__name__}: {str(e)}")
                file_name = validate_func.__name__.replace('validate_', '') + '_clean.csv'
                self.validation_report['files_validated'][file_name] = {
                    'status': 'FAILED',
                    'error': str(e)
                }
        
        failed_files = [f for f, r in self.validation_report['files_validated'].items() 
                       if r.get('status') == 'FAILED']
        
        if failed_files:
            self.validation_report['overall_status'] = 'FAILED'
        
        report_path = 'data/logs/validation_report.json'
        with open(report_path, 'w') as f:
            json.dump(self.validation_report, f, indent=2)
        
        logging.info("=" * 60)
        logging.info("Validation Summary:")
        logging.info(f"Overall Status: {self.validation_report['overall_status']}")
        logging.info(f"Files Validated: {len(self.validation_report['files_validated'])}")
        logging.info(f"Failed Files: {len(failed_files)}")
        if failed_files:
            logging.info(f"Failed: {', '.join(failed_files)}")
        logging.info(f"Report saved to: {report_path}")
        logging.info("=" * 60)
        
        return self.validation_report
    
    def generate_quality_report(self):
        report_lines = [
            "=" * 70,
            "DATA QUALITY REPORT",
            f"Generated: {self.validation_report['timestamp']}",
            "=" * 70,
            ""
        ]
        
        for file_name, result in self.validation_report['files_validated'].items():
            report_lines.append(f"\n{file_name}")
            report_lines.append("-" * 70)
            report_lines.append(f"Status: {result['status']}")
            report_lines.append(f"Row Count: {result.get('row_count', 'N/A')}")
            
            if result.get('issues'):
                report_lines.append("\nIssues Found:")
                for issue in result['issues']:
                    report_lines.append(f"  - {issue}")
            
            if result.get('statistics'):
                report_lines.append("\nStatistics:")
                for col, stats in result['statistics'].items():
                    report_lines.append(f"  {col}:")
                    for stat_name, stat_value in stats.items():
                        if stat_value is not None:
                            report_lines.append(f"    {stat_name}: {stat_value:,.2f}")
        
        report_text = "\n".join(report_lines)
        
        with open('data/logs/quality_report.txt', 'w') as f:
            f.write(report_text)
        
        print(report_text)
        return report_text


if __name__ == "__main__":
    validator = DataValidator()
    validator.validate_all_files()
    validator.generate_quality_report()
