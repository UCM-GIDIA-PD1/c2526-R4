from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, popularidad_mlp_file
from src.utils.config import popularidad_linear_regression_file, popularidad_linear_regression_log_file, popularidad_knn_log_file
from src.utils.config import precios_xgboostumap_file, precios_knncompleteclusters_file, precios_mlp_file, precios_logistic_regression_file
from src.utils.config import reviews_logistic_regression_optuna_file

from src.D_Modelos.Popularidad.baseline import transform_baseline, predict_baseline_median, predict_baseline_mean
from src.D_Modelos.Popularidad.linear_regression import transform_for_linear_regresion, predict_linear_regresion, predict_linear_regresion_log
from src.D_Modelos.Popularidad.xgboost_model import transform_for_xgboost, predict_xgboost, predict_xgboost_log
from src.D_Modelos.Popularidad.mlp import transform_mlp, predict_mlp
from src.D_Modelos.Popularidad.knn import transform_for_knn, predict_knn

from src.D_Modelos.Precios.baseline import transform_baseline as transform_baseline_precios, predict_baseline_mode
from src.D_Modelos.Precios.xgboost_model import transform_xgboost as transform_xgboost_precios, predict_xgboost as predict_xgboost_precios
from src.D_Modelos.Precios.knn import transform_knn as transform_knn_precios, predict_knn as predict_knn_precios
from src.D_Modelos.Precios.mlp import transform_mlp as transform_mlp_precios, predict_mlp as predict_mlp_precios
from src.D_Modelos.Precios.logistic_regression import transform_logistic_regression as transform_logistic_regression_precios, predict_logistic_regression as predict_logistic_regression_precios

from src.D_Modelos.Reviews.baseline import transform_baseline as transform_baseline_reviews, predict_baseline_mode as predict_baseline_mode_reviews
#from src.D_Modelos.Reviews.logistic_regression import transform_logistic_regression as transform_logistic_regression_reviews, predict_logistic_regression as predict_logistic_regression_reviews

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
        "Baseline Mode": {
            "transform_function": transform_baseline_precios,
            "model_path": None,
            "prediction_function": predict_baseline_mode,
        },
        "XGBoost Umap": {
            "transform_function": transform_xgboost_precios,
            "model_path": precios_xgboostumap_file,
            "prediction_function": predict_xgboost_precios,
        },
        "K-NN Complete Clusters": {
            "transform_function": transform_knn_precios,
            "model_path": precios_knncompleteclusters_file,
            "prediction_function": predict_knn_precios,
        },
        "MLP GridSearchCV UMAP": {
            "transform_function": transform_mlp_precios,
            "model_path": precios_mlp_file,
            "prediction_function": predict_mlp_precios,
        },
        "Logistic Regression": {
            "transform_function": transform_logistic_regression_precios,
            "model_path": precios_logistic_regression_file,
            "prediction_function": predict_logistic_regression_precios,
        }
}

# RESEÑAS
models_reviews = {
        "Baseline Mode": {
            "transform_function": transform_baseline_reviews,
            "model_path": None,
            "prediction_function": predict_baseline_mode_reviews,
        },
}