from carprice.logger import logging
from carprice.exception import CarException
from carprice.entity.config_entity import DataValidationConfig
from carprice.entity.artifact_entity import DataIngestionArtifact, DataValidationArtifact
from carprice.constant import *
import os
import sys
import pandas as pd
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset
import json
from carprice.util.util import read_yaml_file

class DataValidation:

    def __init__(self, data_validation_config: DataValidationConfig,
                 data_ingestion_artifact: DataIngestionArtifact):
        try:
            logging.info(f"{'>>' * 30} Data Validation log started. {'<<' * 30} \n\n")
            self.data_validation_config = data_validation_config
            self.data_validation_info = read_yaml_file(self.data_validation_config.schema_file_path)
            self.data_ingestion_artifact = data_ingestion_artifact
        except Exception as e:
            raise CarException(e, sys) from e

    def get_train_and_test_df(self):
        try:
            train_df = pd.read_csv(self.data_ingestion_artifact.train_file_path)
            test_df = pd.read_csv(self.data_ingestion_artifact.test_file_path)
            return train_df, test_df
        except Exception as e:
            raise CarException(e, sys) from e

    def is_train_test_file_exists(self) -> bool:
        try:
            logging.info("Checking if training and test file is available")
            is_train_file_exist = os.path.exists(self.data_ingestion_artifact.train_file_path)
            is_test_file_exist = os.path.exists(self.data_ingestion_artifact.test_file_path)

            is_available = is_train_file_exist and is_test_file_exist
            logging.info(f"Is train and test file exists? -> {is_available}")

            if not is_available:
                message = f"Training file: {self.data_ingestion_artifact.train_file_path} or " \
                          f"Testing file: {self.data_ingestion_artifact.test_file_path} is not present"
                raise Exception(message)

            return is_available
        except Exception as e:
            raise CarException(e, sys) from e

    def data_validate(self, data):
        try:
            dataset_schema = self.data_validation_info[DATASET_SCHEMA_COLUMNS_KEY]
            column_list = list(dataset_schema.keys())
            if len(column_list) == len(list(data.columns)):
                pass
            else:
                return "Train data validation failed"
        except Exception as e:
            raise CarException(e, sys) from e

    def validate_dataset_schema(self) -> bool:
        """
        Performs data validation
        """
        try:
            train, test = self.get_train_and_test_df()
            error = self.data_validate(train)
            validation_status = False
            if not error:
                validation_status = True
            return validation_status
        except Exception as e:
            raise CarException(e, sys) from e

    def get_and_save_data_drift_report(self):
        try:
            # Create a report for data drift
            report = Report(metrics=[DataDriftPreset()])

            # Get the train and test data
            train_df, test_df = self.get_train_and_test_df()

            # Run the report calculation
            report.run(reference_data=train_df, current_data=test_df)

            # Save the report as JSON
            report_file_path = self.data_validation_config.report_file_path
            report_dir = os.path.dirname(report_file_path)
            os.makedirs(report_dir, exist_ok=True)

            # Save the report in JSON format
            report_json = report.json()

            with open(report_file_path, "w") as report_file:
                json.dump(report_json, report_file, indent=6)

            return report_json
        except Exception as e:
            raise CarException(e, sys) from e

    def save_data_drift_report_page(self):
        try:
            # Create a report for data drift
            report = Report(metrics=[DataDriftPreset()])

            # Get the train and test data
            train_df, test_df = self.get_train_and_test_df()

            # Run the report calculation
            report.run(reference_data=train_df, current_data=test_df)

            # Save the report as an HTML page
            report_page_file_path = self.data_validation_config.report_page_file_path
            report_page_dir = os.path.dirname(report_page_file_path)
            os.makedirs(report_page_dir, exist_ok=True)

            # Save the report as an HTML file
            with open(report_page_file_path, "w") as html_file:
                report.save_html(html_file)

        except Exception as e:
            raise CarException(e, sys) from e

    def is_data_drift_found(self) -> bool:
        try:
            report = self.get_and_save_data_drift_report()
            self.save_data_drift_report_page()
            return True
        except Exception as e:
            raise CarException(e, sys) from e

    def initiate_data_validation(self) -> DataValidationArtifact:
        try:
            self.is_train_test_file_exists()
            self.validate_dataset_schema()
            self.is_data_drift_found()

            data_validation_artifact = DataValidationArtifact(
                schema_file_path=self.data_validation_config.schema_file_path,
                report_file_path=self.data_validation_config.report_file_path,
                report_page_file_path=self.data_validation_config.report_page_file_path,
                is_validated=True,
                message="Data Validation performed successfully."
            )
            logging.info(f"Data validation artifact: {data_validation_artifact}")
            return data_validation_artifact
        except Exception as e:
            raise CarException(e, sys) from e

    def __del__(self):
        logging.info(f"{'>>' * 30} Data Validation log completed. {'<<' * 30} \n\n")
