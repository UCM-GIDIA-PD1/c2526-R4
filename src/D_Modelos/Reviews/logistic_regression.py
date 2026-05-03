"""
Dado resenyas.parquet crea un modelo de Regresión Logística para predecir 
si la review es positiva o negativa en base al texto de esta. Utiliza TF-IDF
para la transformación de texto a vectores numéricos.
"""
import numpy as np
import os

from src.utils.config import reviews
from src.utils.files import read_file, write_to_file
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split, cross_val_score
from src.utils.config import reviews_logistic_regression_gridsearch_file, reviews_logistic_regression_optuna_file, reviews_logistic_regression_optuna_retrained_file,  models_reviews_path
from src.D_Modelos.Reviews.utils.preprocesamiento import clean_text_stem
from src.D_Modelos.Reviews.utils.utils import get_metrics
from src.utils.config import seed

class_names = ["Negativo", "Positivo"]

def transform_logistic_regression(df):
    return df

def predict_logistic_regression(model_data, test_df, train_df):
    X_test, _ = _preprocess(test_df)
    
    
    y_pred = model_data.predict(X_test)
    return y_pred

def _preprocess(df):
    '''
    Función que se encarga del preprocesado del texto.
    
    Args:
        - df (pd.DataFrame) : DataFrame con el que se realizará el modelo.
    Returns:
        - X (pd.Series) : Contiene la columna de los comentarios tras las transformaciones realizadas (eliminación
        de stopwords y aplicación de stemming).
        
        - y (pd.Series) : Contiene la variable respuesta que puede tomar 2 valores: 0 (negativo), 1 (positivo).
    '''

    y = df["is_positive"]
    X = df["text"].apply(lambda x : clean_text_stem(x))
    
    return X, y

def build_objective(X_train, y_train, cv=5):
    '''
    Función que se encarga de encontrar los mejores hiperparámetros
    usando validación cruzada en lugar de conjunto de validación fijo.
    
    Args:
        - X_train (pd.Series): Textos de entrenamiento.
        - y_train (pd.Series): Etiquetas.
        - cv (int): Número de folds para cross-validation.
        
    Returns:
        - objective (function): Función para Optuna.
    '''
    
    def objective(trial):
        params = {
            "min_df": trial.suggest_int("min_df", 1, 5),
            "max_df": trial.suggest_float("max_df", 0.7, 1.0),
            "max_features": trial.suggest_categorical("max_features", [20000, 40000, 60000, None]),
            "sublinear_tf": trial.suggest_categorical("sublinear_tf", [True, False]),
            "C": trial.suggest_float("C", 1e-2, 20.0, log=True),
            "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
        }
        pipe = _build_pipeline(params)
        scores = cross_val_score(pipe, X_train, y_train, cv=cv,
                                scoring="balanced_accuracy", n_jobs=-1)
        return scores.mean()

    return objective

def _build_pipeline(best_params):
    '''
    Función que se encarga de la creación del modelo a partir de los mejores
    parámetros obtenidos con Optuna.
    
    Args:
        - best_params (dict) : Diccionario con los mejores hiperparámetros encontrados
        por Optuna.
    Returns:
        - modelo (sklearn.pipeline.Pipeline) : Pipeline que contiene tanto un objeto
        TfidfVectorizer para la transformación del texto a vectores numéricos, como un
        objeto LogisticRegression correspondiente a la regresión logística. Ambos ajustados
        a los mejores hiperparámetros.
    '''
    
    tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1,2),
            min_df= best_params["min_df"],
            max_df= best_params["max_df"],
            max_features= best_params["max_features"],
            sublinear_tf=best_params["sublinear_tf"],
            strip_accents="unicode",
            lowercase=True,
        )
    clf = LogisticRegression(
        solver="saga",
            C= best_params["C"],
            class_weight= best_params["class_weight"],
            max_iter=3000,
            random_state=seed
    )
    
    return Pipeline([("tfidf", tfidf),("clf", clf)])

def train_optuna(X_train, X_test, y_train, y_test, minio):
    import wandb
    import optuna
    '''
    Función para el entrenamiento del modelo usando Optuna para la
    búsqueda de los mejores hiperparámetros.
    '''
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "logistic-regression_optuna",
        job_type='logistic-regression'
    )
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42)
        )

    study.optimize(build_objective(X_train, y_train), n_trials=20, show_progress_bar= True)
    
    best_params = study.best_params
    model = _build_pipeline(best_params)
    
    model.fit(X_train, y_train)
    
    y_pred_test = model.predict(X_test)

    metricas = get_metrics(y_test, y_pred_test, class_names)
    
    run.config.update(study.best_params)
    run.log({
        "Accuracy": metricas["accuracy"],
        "Balanced accuracy": metricas["balanced_accuracy"],
        "Precision": metricas["precision"],
        "Recall": metricas["recall"],
        "F1-score": metricas["f1-score"]
    })
    run.finish()

    os.makedirs(models_reviews_path(), exist_ok=True)
    write_to_file(model, reviews_logistic_regression_optuna_file, minio)
    print(f"Modelo guardado en {reviews_logistic_regression_optuna_file}")
    
    return best_params
    
def train_gridsearch(X_train, X_test, y_train, y_test, minio):
    import wandb
    '''
    Función para el entrenamiento del modelo usando GridSearchCV para la
    búsqueda de los mejores hiperparámetros.
    '''
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "logistic-regression_gridsearch",
        job_type='logistic-regression'
    )
    
    pipe = Pipeline([("tfidf", TfidfVectorizer(
            analyzer="word",
            ngram_range=(1,2),
            strip_accents="unicode",
            lowercase=True,
        )),("clf", LogisticRegression(
            solver= "saga",
            max_iter = 3000,
            random_state=seed
        ))])

    # Valores sobre los que probará GridSearch,
    # debido a que suele tardar más que con optuna
    # el número de valores para los parámetros a probar es inferior
    param_grid = {
    "tfidf__min_df": [1, 2],
    "tfidf__max_df": [0.8, 1.0],
    "clf__C": [0.1, 1, 10],
    }
    
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)
    
    grid = GridSearchCV(
        pipe,
        param_grid,
        cv=cv,
        scoring="balanced_accuracy",
        verbose=1,
        n_jobs=-1
    )
    
    grid.fit(X_train, y_train)
    
    best_params = grid.best_params_
    
    y_pred_test = grid.predict(X_test)

    metricas = get_metrics(y_test, y_pred_test, class_names)
    
    run.config.update(best_params)
    run.log({
        "Accuracy": metricas["accuracy"],
        "Balanced accuracy": metricas["balanced_accuracy"],
        "Precision": metricas["precision"],
        "Recall": metricas["recall"],
        "F1-score": metricas["f1-score"],
        "Confusion maxtrix": metricas["confusion_matrix"]
    })
    run.finish()

    os.makedirs(models_reviews_path(), exist_ok=True)
    write_to_file(grid, reviews_logistic_regression_gridsearch_file, minio)
    print(f"Modelo guardado en {reviews_logistic_regression_gridsearch_file}")
    
    return best_params
    

def retrain_final_model(X, y, best_params, minio):
    """
    Reentrena el modelo con todos los datos disponibles (train + test)
    usando los mejores hiperparámetros ya encontrados.

    Args:
        X:           Todos los textos preprocesados.
        y:           Todas las etiquetas.
        best_params: Mejores parámetros devueltos por .
        minio:       Configuración de MinIO para guardar el modelo.
    """
    print("Reentrenando modelo final con todos los datos...")
    model = _build_pipeline(best_params)
    model.fit(X, y)

    os.makedirs(models_reviews_path(), exist_ok=True)
    write_to_file(model, reviews_logistic_regression_optuna_retrained_file, minio)
    print(f"Modelo final guardado en {reviews_logistic_regression_optuna_retrained_file}")


def main(minio = {"minio_write": False, "minio_read": False}):
    from tqdm import tqdm
    tqdm.pandas(desc="Limpiando texto")
    print("Leyendo Datos")
    df = read_file(reviews, minio)

    print("Preprocesado de los datos")
    X, y = _preprocess(df)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)

    use_optuna = True
    if use_optuna:
       best_params =  train_optuna(X_train, X_test, y_train, y_test, minio)
       retrain_final_model(X, y, best_params, minio)
    else:
        best_params = train_gridsearch(X_train, X_test, y_train, y_test, minio)

if __name__ == "__main__":
    main()
