import logging
import sys
import os
from datetime import datetime
import json
import argparse

sys.path.append('scripts')
from transform import MoroccoTourismTransformer
from validate import DataValidator
from load import DatabaseLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/etl_main.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class ETLOrchestrator:
    def __init__(self, config_path='config/config.json'):
        self.config_path = config_path
        self.start_time = datetime.now()
        self.execution_log = {
            'start_time': self.start_time.isoformat(),
            'phases': {},
            'overall_status': 'RUNNING'
        }
        os.makedirs('data/raw', exist_ok=True)
        os.makedirs('data/processed', exist_ok=True)
        os.makedirs('data/logs', exist_ok=True)
        os.makedirs('config', exist_ok=True)
        
    def print_banner(self):
        banner = """
        ╔════════════════════════════════════════════════════════════╗
        ║     MOROCCO TOURISM DATA - ETL PIPELINE                    ║
        ║     Extract → Transform → Load                             ║
        ╚════════════════════════════════════════════════════════════╝
        """
        print(banner)
        logging.info("ETL Pipeline Starting...")
    
    def run_transform_phase(self):
        phase_name = 'TRANSFORM'
        logging.info("\n" + "="*60)
        logging.info(f"PHASE 1: {phase_name}")
        logging.info("="*60)
        
        phase_start = datetime.now()
        
        try:
            transformer = MoroccoTourismTransformer()
            results = transformer.run_all_transformations()
            
            success_count = sum(1 for v in results.values() if v)
            failure_count = sum(1 for v in results.values() if not v)
            
            phase_end = datetime.now()
            duration = (phase_end - phase_start).total_seconds()
            
            status = 'SUCCESS' if failure_count == 0 else 'PARTIAL_SUCCESS'
            
            self.execution_log['phases'][phase_name] = {
                'status': status,
                'start_time': phase_start.isoformat(),
                'end_time': phase_end.isoformat(),
                'duration_seconds': duration,
                'files_processed': len(results),
                'successful': success_count,
                'failed': failure_count,
                'details': results
            }
            
            logging.info(f"\n{phase_name} Phase Summary:")
            logging.info(f"  Status: {status}")
            logging.info(f"  Duration: {duration:.2f} seconds")
            logging.info(f"  Successful: {success_count}/{len(results)}")
            logging.info(f"  Failed: {failure_count}/{len(results)}")
            
            return status != 'FAILED'
            
        except Exception as e:
            logging.error(f"Critical error in {phase_name} phase: {str(e)}")
            self.execution_log['phases'][phase_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    def run_validate_phase(self):
        phase_name = 'VALIDATE'
        logging.info("\n" + "="*60)
        logging.info(f"PHASE 2: {phase_name}")
        logging.info("="*60)
        
        phase_start = datetime.now()
        
        try:
            validator = DataValidator()
            validation_report = validator.validate_all_files()
            validator.generate_quality_report()
            
            phase_end = datetime.now()
            duration = (phase_end - phase_start).total_seconds()
            
            status = validation_report['overall_status']
            
            self.execution_log['phases'][phase_name] = {
                'status': status,
                'start_time': phase_start.isoformat(),
                'end_time': phase_end.isoformat(),
                'duration_seconds': duration,
                'files_validated': len(validation_report['files_validated']),
                'validation_report': validation_report
            }
            
            logging.info(f"\n{phase_name} Phase Summary:")
            logging.info(f"  Status: {status}")
            logging.info(f"  Duration: {duration:.2f} seconds")
            logging.info(f"  Files Validated: {len(validation_report['files_validated'])}")
            
            return status == 'PASSED'
            
        except Exception as e:
            logging.error(f"Critical error in {phase_name} phase: {str(e)}")
            self.execution_log['phases'][phase_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    def run_load_phase(self):
        phase_name = 'LOAD'
        logging.info("\n" + "="*60)
        logging.info(f"PHASE 3: {phase_name}")
        logging.info("="*60)
        
        phase_start = datetime.now()
        
        try:
            loader = DatabaseLoader(self.config_path)
            success = loader.run_full_load()
            
            phase_end = datetime.now()
            duration = (phase_end - phase_start).total_seconds()
            
            status = 'SUCCESS' if success else 'FAILED'
            
            self.execution_log['phases'][phase_name] = {
                'status': status,
                'start_time': phase_start.isoformat(),
                'end_time': phase_end.isoformat(),
                'duration_seconds': duration
            }
            
            logging.info(f"\n{phase_name} Phase Summary:")
            logging.info(f"  Status: {status}")
            logging.info(f"  Duration: {duration:.2f} seconds")
            
            return success
            
        except Exception as e:
            logging.error(f"Critical error in {phase_name} phase: {str(e)}")
            self.execution_log['phases'][phase_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    def run_full_pipeline(self):
        self.print_banner()
        
        transform_success = self.run_transform_phase()
        if not transform_success:
            logging.error("Transform phase failed. Stopping pipeline.")
            self.execution_log['overall_status'] = 'FAILED'
            self.save_execution_log()
            return False
        
        validate_success = self.run_validate_phase()
        if not validate_success:
            logging.warning("Validation phase found issues. Review quality report before loading.")
            user_input = input("\nContinue with load phase? (yes/no): ")
            if user_input.lower() != 'yes':
                logging.info("Pipeline stopped by user.")
                self.execution_log['overall_status'] = 'STOPPED'
                self.save_execution_log()
                return False
        
        load_success = self.run_load_phase()
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        self.execution_log['end_time'] = self.end_time.isoformat()
        self.execution_log['total_duration_seconds'] = total_duration
        self.execution_log['overall_status'] = 'SUCCESS' if load_success else 'FAILED'
        
        self.print_final_summary()
        self.save_execution_log()
        
        return load_success
    
    def run_phase_only(self, phase):
        self.print_banner()
        
        phase = phase.upper()
        success = False
        
        if phase == 'TRANSFORM':
            success = self.run_transform_phase()
        elif phase == 'VALIDATE':
            success = self.run_validate_phase()
        elif phase == 'LOAD':
            success = self.run_load_phase()
        else:
            logging.error(f"Unknown phase: {phase}")
            return False
        
        self.end_time = datetime.now()
        total_duration = (self.end_time - self.start_time).total_seconds()
        
        self.execution_log['end_time'] = self.end_time.isoformat()
        self.execution_log['total_duration_seconds'] = total_duration
        self.execution_log['overall_status'] = 'SUCCESS' if success else 'FAILED'
        
        self.save_execution_log()
        return success
    
    def print_final_summary(self):
        summary = f"""
        ╔════════════════════════════════════════════════════════════╗
        ║                  ETL PIPELINE SUMMARY                      ║
        ╚════════════════════════════════════════════════════════════╝
        
        Overall Status: {self.execution_log['overall_status']}
        Total Duration: {self.execution_log['total_duration_seconds']:.2f} seconds
        
        Phase Results:
        """
        
        for phase_name, phase_data in self.execution_log['phases'].items():
            status = phase_data.get('status', 'UNKNOWN')
            duration = phase_data.get('duration_seconds', 0)
            summary += f"  - {phase_name}: {status} ({duration:.2f}s)\n"
        
        summary += f"""
        Logs Location: data/logs/
        Report Location: data/logs/validation_report.json
        
        ╔════════════════════════════════════════════════════════════╗
        """
        
        print(summary)
        logging.info("Pipeline execution completed")
    
    def save_execution_log(self):
        log_file = f"data/logs/execution_log_{self.start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
        logging.info(f"Execution log saved to: {log_file}")


def main():
    parser = argparse.ArgumentParser(description='Morocco Tourism ETL Pipeline')
    parser.add_argument(
        '--phase',
        choices=['transform', 'validate', 'load', 'full'],
        default='full',
        help='ETL phase to run (default: full)'
    )
    parser.add_argument(
        '--config',
        default='config/config.json',
        help='Path to configuration file (default: config/config.json)'
    )
    
    args = parser.parse_args()
    
    orchestrator = ETLOrchestrator(config_path=args.config)
    
    if args.phase == 'full':
        success = orchestrator.run_full_pipeline()
    else:
        success = orchestrator.run_phase_only(args.phase)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
