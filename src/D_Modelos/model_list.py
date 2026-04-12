from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, popularidad_mlp_file
from src.utils.config import popularidad_linear_regression_file, popularidad_linear_regression_log_file, popularidad_knn_log_file

from src.D_Modelos.Popularidad.baseline import transform_baseline, predict_baseline_median, predict_baseline_mean
from src.D_Modelos.Popularidad.linear_regresion_log import transform_for_linear_regresion, predict_linear_regresion, predict_linear_regresion_log
from src.D_Modelos.Popularidad.xgboost_popularidad import transform_for_xgboost, predict_xgboost, predict_xgboost_log
from src.D_Modelos.Popularidad.mlp_popularidad import transform_mlp, predict_mlp
from src.D_Modelos.Popularidad.knn_popularidad import transform_for_knn, predict_knn

# POPULARIDAD
models_popularidad = {
        "Baseline (Median)": {
            "transform_function": transform_baseline,
            "model_path": None,
            "prediction_function": predict_baseline_median,
        },
        "Baseline (Mean)": {
            "transform_function": transform_baseline,
            "model_path": None,
            "prediction_function": predict_baseline_mean,
        },
        "Linear Regression (Normal)": { 
            "transform_function": transform_for_linear_regresion,
            "model_path": popularidad_linear_regression_file,
            "prediction_function": predict_linear_regresion,
        },
        "Linear Regression (Log)": {
            "transform_function": transform_for_linear_regresion,
            "model_path": popularidad_linear_regression_log_file,
            "prediction_function": predict_linear_regresion_log,
        },
        "XGBoost (Normal)": {
            "transform_function": transform_for_xgboost,
            "model_path": popularidad_xgboost_file,
            "prediction_function": predict_xgboost,
        },
        "XGBoost (Log)": {
            "transform_function": transform_for_xgboost,
            "model_path": popularidad_xgboost_log_file,
            "prediction_function": predict_xgboost_log,
        },
        "MLP": {
            "transform_function": transform_mlp,
            "model_path": popularidad_mlp_file,
            "prediction_function": predict_mlp,
        },
        "KNN (Log)": {
            "transform_function": transform_for_knn,
            "model_path": popularidad_knn_log_file,
            "prediction_function": predict_knn,
        }
}

# PRECIOS
models_precios = {
        
}

# RESEÑAS
models_reviews = {
        
}