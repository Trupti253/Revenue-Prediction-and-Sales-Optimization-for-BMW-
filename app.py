from flask import Flask, request, send_file, abort, render_template
import os
import json
import logging
from carprice.util.util import read_yaml_file, write_yaml_file, get_carlist
from carprice.config.configuration import Configuartion
from carprice.constant import CONFIG_DIR, get_current_time_stamp
from carprice.pipeline.pipeline import Pipeline
from carprice.entity.carprice_predictor import CarPricePredictor, CarPriceData
from carprice.logger import get_log_dataframe

ROOT_DIR = os.getcwd()
LOG_FOLDER_NAME = "logs"
PIPELINE_FOLDER_NAME = "carprice"
SAVED_MODELS_DIR_NAME = "saved_models"
MODEL_CONFIG_FILE_PATH = os.path.join(ROOT_DIR, CONFIG_DIR, "model.yaml")
LOG_DIR = os.path.join(ROOT_DIR, LOG_FOLDER_NAME)
PIPELINE_DIR = os.path.join(ROOT_DIR, PIPELINE_FOLDER_NAME)
MODEL_DIR = os.path.join(ROOT_DIR, SAVED_MODELS_DIR_NAME)

CAR_DATA_KEY = "carprice_data"
CAR_VALUE_KEY = "carprice_value"

app = Flask(__name__)

# Power BI Embed URL
POWER_BI_EMBED_URL = "https://app.powerbi.com/view?r=eyJrIjoiMTVmZWZiNTctNzkyMS00ZmFlLWE1ZDktNWViMGNhNGI4MWI4IiwidCI6ImRmODY3OWNkLWE4MGUtNDVkOC05OWFjLWM4M2VkN2ZmOTVhMCJ9"

# Ensure required directories are created
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(PIPELINE_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

@app.route('/artifact', defaults={'req_path': 'carprice'})
@app.route('/artifact/<path:req_path>')
def render_artifact_dir(req_path):
    abs_path = os.path.join(ROOT_DIR, req_path)
    if not os.path.exists(abs_path):
        logging.warning(f"Path not found: {abs_path}")
        return abort(404)

    if os.path.isfile(abs_path):
        if ".html" in abs_path:
            with open(abs_path, "r", encoding="utf-8") as file:
                content = file.read()
            return content
        return send_file(abs_path)

    files = {os.path.join(abs_path, file_name): file_name for file_name in os.listdir(abs_path) if "artifact" in file_name}
    result = {
        "files": files,
        "parent_folder": os.path.dirname(abs_path),
        "parent_label": abs_path
    }
    return render_template('files.html', result=result)


@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        logging.exception("Error rendering index page.")
        return str(e), 500


@app.route('/view_experiment_hist', methods=['GET', 'POST'])
def view_experiment_history():
    try:
        experiment_df = Pipeline.get_experiments_status()
        context = {
            "experiment": experiment_df.to_html(classes='table table-striped col-12')
        }
        return render_template('experiment_history.html', context=context)
    except Exception as e:
        logging.exception("Error retrieving experiment history.")
        return str(e), 500


@app.route('/train', methods=['GET', 'POST'])
def train():
    try:
        pipeline = Pipeline(config=Configuartion(current_time_stamp=get_current_time_stamp()))
        if not Pipeline.experiment.running_status:
            message = "Training started."
            pipeline.start()
        else:
            message = "Training is already in progress."

        context = {
            "experiment": pipeline.get_experiments_status().to_html(classes='table table-striped col-12'),
            "message": message
        }
        return render_template('train.html', context=context)
    except Exception as e:
        logging.exception("An error occurred during training.")
        return str(e), 500


@app.route('/predict', methods=['GET', 'POST'])
def predict():
    try:
        context = {
            CAR_DATA_KEY: None,
            CAR_VALUE_KEY: None
        }
        car_list = get_carlist()
        
        if request.method == "POST":
            car_name = request.form.get("car_name")
            vehicle_age = int(request.form.get("vehicle_age"))
            km_driven = int(request.form.get("km_driven"))
            seller_type = request.form.get("seller_type")
            fuel_type = request.form.get("fuel_type")
            transmission_type = request.form.get("transmission")
            mileage = float(request.form.get("mileage"))
            engine = int(request.form.get("engine"))
            max_power = float(request.form.get("max_power"))
            seats = int(request.form.get("seats"))

            carprice_data = CarPriceData(
                car_name=car_name, vehicle_age=vehicle_age, km_driven=km_driven, 
                seller_type=seller_type, fuel_type=fuel_type, transmission_type=transmission_type, 
                mileage=mileage, engine=engine, max_power=max_power, seats=seats
            )
            carprice_df = carprice_data.get_car_data_as_dict()
            carprice_predictor = CarPricePredictor(model_dir=MODEL_DIR)
            carprice_value = carprice_predictor.predict(X=carprice_df)
            
            context = {
                CAR_DATA_KEY: carprice_data.get_car_data_as_dict(),
                CAR_VALUE_KEY: round(carprice_value[0], 2),
            }
        return render_template("predict.html", context=context, car_list=car_list)
    except Exception as e:
        logging.exception("Error in prediction.")
        return str(e), 500


@app.route('/saved_models', defaults={'req_path': 'saved_models'})
@app.route('/saved_models/<path:req_path>')
def saved_models_dir(req_path):
    abs_path = os.path.join(ROOT_DIR, req_path)
    if not os.path.exists(abs_path):
        logging.warning(f"Path not found: {abs_path}")
        return abort(404)

    if os.path.isfile(abs_path):
        return send_file(abs_path)

    files = {os.path.join(abs_path, file): file for file in os.listdir(abs_path)}
    result = {
        "files": files,
        "parent_folder": os.path.dirname(abs_path),
        "parent_label": abs_path
    }
    return render_template('saved_models_files.html', result=result)


@app.route("/update_model_config", methods=['GET', 'POST'])
def update_model_config():
    try:
        if request.method == 'POST':
            model_config = request.form['new_model_config']
            model_config = json.loads(model_config.replace("'", '"'))
            write_yaml_file(file_path=MODEL_CONFIG_FILE_PATH, data=model_config)

        model_config = read_yaml_file(file_path=MODEL_CONFIG_FILE_PATH)
        return render_template('update_model.html', result={"model_config": model_config})
    except Exception as e:
        logging.exception("Error updating model configuration.")
        return str(e), 500


@app.route(f'/logs', defaults={'req_path': f'{LOG_FOLDER_NAME}'})
@app.route(f'/{LOG_FOLDER_NAME}/<path:req_path>')
def render_log_dir(req_path):
    abs_path = os.path.join(LOG_DIR, req_path)
    if not os.path.exists(abs_path):
        logging.warning(f"Path not found: {abs_path}")
        return abort(404)

    if os.path.isfile(abs_path):
        log_df = get_log_dataframe(abs_path)
        context = {"log": log_df.to_html(classes="table-striped", index=False)}
        return render_template('log.html', context=context)

    files = {os.path.join(abs_path, file): file for file in os.listdir(abs_path)}
    result = {
        "files": files,
        "parent_folder": os.path.dirname(abs_path),
        "parent_label": abs_path
    }
    return render_template('log_files.html', result=result)


@app.route('/analytics')
def analytics():
    return render_template('analytics.html', embed_url=POWER_BI_EMBED_URL)


if __name__ == "__main__":
    app.run(debug=True)
