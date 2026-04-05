import pandas as pd
import wandb
import optuna
import numpy as np

from src.utils.config import reviews
from src.utils.files import read_file
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score,f1_score
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from nltk.stem import PorterStemmer
from nltk.corpus import stopwords

from tqdm import tqdm

from utils_modelo_reviews.preprocesamiento import clean_text, train_val_test_split

def _preprocess(df):
    stop_words = set(stopwords.words("english"))
    ps = PorterStemmer()

    y = df["is_positive"]
    X = df["text"].progress_apply(lambda x : clean_text(x,ps,stop_words))
    
    return X, y


def build_objective(X_train, y_train, X_val, y_val):
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
            random_state=42
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

def best_model(best_params):
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
            random_state=42
    )
    
    return Pipeline([("tfidf", tfidf),("clf", clf)])

if __name__ == "__main__":
    tqdm.pandas(desc="Limpiando texto")
    print("Leyendo Datos")
    df = read_file(reviews)
    
    print("Preprocesado de los datos")
    X, y = _preprocess(df)
    
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
            direction="maximize",
            sampler=optuna.samplers.TPESampler(seed=42)
        )

    study.optimize(build_objective(X_train, y_train, X_val, y_val), n_trials=20, show_progress_bar= True)
    
    best_logistic_model = best_model(study.best_params)

    X_train_val = np.concatenate([X_train, X_val])
    y_train_val = np.concatenate([y_train, y_val])

    best_logistic_model.fit(X_train_val, y_train_val)
    
    y_pred_test = best_logistic_model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred_test)
    f1 = f1_score(y_test, y_pred_test)
    balanced_accuracy = balanced_accuracy_score(y_test, y_pred_test)
    recall= recall_score(y_test, y_pred_test)
    precision=  precision_score(y_test, y_pred_test)

    print(f"Valor de accuracy: {accuracy}")
    print(f"Valor de f1: {f1}")
    print(f"Valor de balanced_accuracy: {balanced_accuracy}")
    print(f"Valor de recall: {recall}")
    print(f"Valor de precision: {precision}")