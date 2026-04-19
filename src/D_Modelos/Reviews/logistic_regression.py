"""
Dado resenyas.parquet crea un modelo de Regresión Logística para predecir 
si la review es positiva o negativa en base al texto de esta. Utiliza TF-IDF
para la transformación de texto a vectores numéricos.
"""
import wandb
import optuna
import numpy as np
import os

from src.utils.config import reviews
from src.utils.files import read_file, write_to_file
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from src.utils.config import reviews_logistic_regression_gridsearch_file, reviews_logistic_regression_optuna_file, models_reviews_path

from nltk.stem import PorterStemmer
from nltk.corpus import stopwords

from tqdm import tqdm

from src.D_Modelos.Reviews.utils.preprocesamiento import clean_text_stem, train_val_test_split
from src.utils.config import seed

from src.D_Modelos.Reviews.utils.utils import get_metrics

class_names = ["Negativo", "Positivo"]

def preprocess(df):
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
    X = df["text"].progress_apply(lambda x : clean_text_stem(x))
    
    return X, y

def build_objective(X_train, y_train, X_val, y_val):
    '''
    Función que se encarga de encontrar los mejores hiperparámetros
    a partir de la función objective de Optuna.
    
    Args:
        - X_train (pd.Series) : Conjunto de textos de entrenamiento.
        - y_train (pd.Series) : Etiquetas asociadas al conjunto entrenamiento.
        - X_val (pd.Series) : Conjunto de textos de validación.
        - y_val (pd.Series) : Etiquetas asociadas al conjunto validación.
        
    Returns:
        - objective (function) : Función que recibe objeto `trial` de Optuna y 
        se encarga de la optimización de hiperparámetros.
    '''
    
    # Función de optimización usada por Optuna para encontrar los mejores hiperparámetros
    def objective(trial):
        tfidf = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1,2),
            min_df=trial.suggest_int("min_df", 1, 5),
            max_df=trial.suggest_float("max_df", 0.7, 1.0),
            max_features=trial.suggest_categorical("max_features", [20000, 40000, 60000, None]),
            sublinear_tf=trial.suggest_categorical("sublinear_tf", [True, False]),
            strip_accents="unicode",
            lowercase=True,
        )

        clf = LogisticRegression(
            solver="saga",
            C=trial.suggest_float("C", 1e-2, 20.0, log=True),
            class_weight=trial.suggest_categorical("class_weight", [None, "balanced"]),
            max_iter=3000,
            random_state=seed
        )

        pipe = Pipeline([
            ("tfidf", tfidf),
            ("clf", clf),
        ])
        
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_val)
        
        score = balanced_accuracy_score(y_val, y_pred)
        
        return score

    return objective

def best_model_optuna(best_params):
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

def train_optuna(minio):
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

    study.optimize(build_objective(X_train, y_train, X_val, y_val), n_trials=20, show_progress_bar= True)
    
    best_logistic_model = best_model_optuna(study.best_params)

    X_train_val = np.concatenate([X_train, X_val])
    y_train_val = np.concatenate([y_train, y_val])

    best_logistic_model.fit(X_train_val, y_train_val)
    
    y_pred_test = best_logistic_model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred_test)
    f1 = f1_score(y_test, y_pred_test)
    balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
    recall= recall_score(y_test, y_pred_test)
    precision=  precision_score(y_test, y_pred_test)
    
    run.config.update(study.best_params)
    run.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })
    run.finish()

    os.makedirs(models_reviews_path(), exist_ok=True)
    write_to_file(best_logistic_model, reviews_logistic_regression_optuna_file, minio)
    print(f"Modelo guardado en {reviews_logistic_regression_optuna_file}")
    
    print(f"Valor de accuracy: {accuracy}")
    print(f"Valor de f1: {f1}")
    print(f"Valor de balanced_accuracy: {balanced_accuracy}")
    print(f"Valor de recall: {recall}")
    print(f"Valor de precision: {precision}")
    
def train_gridsearch(minio):
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
    
    X_train_val = np.concatenate([X_train, X_val])
    y_train_val = np.concatenate([y_train, y_val])

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
    
    grid.fit(X_train_val, y_train_val)
    
    best_params = grid.best_params_
    
    y_pred_test = grid.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred_test)
    f1 = f1_score(y_test, y_pred_test)
    balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
    recall= recall_score(y_test, y_pred_test)
    precision=  precision_score(y_test, y_pred_test)
    
    run.config.update(best_params)
    run.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })
    run.finish()

    os.makedirs(models_reviews_path(), exist_ok=True)
    write_to_file(grid, reviews_logistic_regression_gridsearch_file, minio)
    print(f"Modelo guardado en {reviews_logistic_regression_gridsearch_file}")
    
    print(f"Valor de accuracy: {accuracy}")
    print(f"Valor de f1: {f1}")
    print(f"Valor de balanced_accuracy: {balanced_accuracy}")
    print(f"Valor de recall: {recall}")
    print(f"Valor de precision: {precision}")
    

def main(minio = {"minio_write": False, "minio_read": False}):
    tqdm.pandas(desc="Limpiando texto")
    print("Leyendo Datos")
    df = read_file(reviews, minio)

    print("Preprocesado de los datos")
    X, y = preprocess(df)

    global X_train, X_val, X_test, y_train, y_val, y_test
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    use_optuna = True

    if use_optuna:
        train_optuna(minio)
    else:
        train_gridsearch(minio)

if __name__ == "__main__":
    main()
