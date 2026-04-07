from utils_modelo_reviews.preprocesamiento import read_reviews, train_val_test_split, clean_text_lemma
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score
import optuna
import nltk
import wandb
import os
import joblib
import json
nltk.download('stopwords')
tqdm.pandas(desc="Limpiando texto")

def preprocesar_texto(X_train, X_val, X_test):
    X_train = [clean_text_lemma(review) for review in tqdm(X_train, desc = "Preprocesando entrenamiento")]
    X_val = [clean_text_lemma(review) for review in tqdm(X_val, desc = "Preprocesando validacion")]
    X_test = [clean_text_lemma(review) for review in tqdm(X_test, desc = "Preprocesando prueba")]
    return X_train, X_val, X_test

def entrenar_modelo_con_gridsearch(X_train, X_val, y_train, y_val):
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val
    pipeline = Pipeline([
        ('vect', TfidfVectorizer()),
        ('clf', ComplementNB())
    ])

    param_grid = {
        'vect__ngram_range': [(1, 1), (1, 2)],
        'vect__min_df': [1, 2, 5],
        'vect__max_df': [0.8, 1.0],
        'vect__sublinear_tf': [True, False],
        'vect__norm': ['l1', 'l2'],
        'clf__alpha': [0.1, 0.5, 1.0, 2.0]
    }

    grid_search = GridSearchCV(
        pipeline, 
        param_grid, 
        cv=5, 
        scoring='balanced_accuracy',
        n_jobs=-1, 
        verbose=2
    )

    grid_search.fit(X_train_full, y_train_full)
    final_model = Pipeline([
        ('vect', TfidfVectorizer(
            ngram_range=grid_search.best_params_['vect__ngram_range'],
            min_df=grid_search.best_params_['vect__min_df'],
            max_df=grid_search.best_params_['vect__max_df'],
            sublinear_tf=grid_search.best_params_['vect__sublinear_tf'],
            norm=grid_search.best_params_['vect__norm']
        )),
        ('clf', ComplementNB(alpha=grid_search.best_params_['clf__alpha']))
    ])
    
    final_model.fit(X_train, y_train)
    return final_model, grid_search.best_params_


def entrenar_modelo_con_optuna(X_train, X_val, y_train, y_val, n_trials=50):
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val
    def objective(trial):
        ngram_max = trial.suggest_int('ngram_max', 1, 2)
        
        param_grid = {
            'vect__ngram_range': (1, ngram_max),
            'vect__min_df': trial.suggest_int('min_df', 1, 5),
            'vect__max_df': trial.suggest_float('max_df', 0.7, 1.0),
            'vect__sublinear_tf': trial.suggest_categorical('sublinear_tf', [True, False]),
            'vect__norm': trial.suggest_categorical('norm', ['l1', 'l2']),
            'clf__alpha': trial.suggest_float('alpha', 0.01, 2.0, log=True)
        }

        pipeline = Pipeline([
            ('vect', TfidfVectorizer(
                ngram_range=param_grid['vect__ngram_range'],
                min_df=param_grid['vect__min_df'],
                max_df=param_grid['vect__max_df'],
                sublinear_tf=param_grid['vect__sublinear_tf'],
                norm=param_grid['vect__norm']
            )),
            ('clf', ComplementNB(alpha=param_grid['clf__alpha']))
        ])

        score = cross_val_score(pipeline, X_train_full, y_train_full, n_jobs=-1, cv=5, scoring='balanced_accuracy')
        return score.mean()


    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    final_model = Pipeline([
        ('vect', TfidfVectorizer(
            ngram_range=(1, best_params['ngram_max']),
            min_df=best_params['min_df'],
            max_df=best_params['max_df'],
            sublinear_tf=best_params['sublinear_tf'],
            norm=best_params['norm']
        )),
        ('clf', ComplementNB(alpha=best_params['alpha']))
    ])
    
    final_model.fit(X_train, y_train)
    
    return final_model, best_params

def calcular_metricas(y_true, y_pred):
    accuracy = accuracy_score(y_true, y_pred)
    balanced_accuracy = balanced_accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)

    print("Accuracy:", accuracy)
    print("Balanced accuracy:", balanced_accuracy)
    print("Precision:", precision)
    print("Recall:", recall)
    print("F1-score:", f1)
    return accuracy, balanced_accuracy, precision, recall, f1

def best_standard_params(score_grid, params_grid,score_optuna, params_optuna):
    if score_grid > score_optuna:
        best_params = params_grid.copy()
        best_params["ngram_range"] = best_params.pop("vect__ngram_range")
        best_params["min_df"] = best_params.pop("vect__min_df")
        best_params["max_df"] = best_params.pop("vect__max_df")
        best_params["alpha"] = best_params.pop("clf__alpha")
        best_params["sublinear_tf"] = best_params.pop("vect__sublinear_tf")
        best_params["norm"] = best_params.pop("vect__norm")
    else:
        best_params = params_optuna.copy()
        ngram_range = (1, 1) if best_params["ngram_max"] == 1 else (1,2)
        best_params.pop("ngram_max")
        best_params["ngram_range"] = ngram_range
    return best_params

def _gridsearch(X_train, X_val, X_test, y_train, y_val, y_test):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "naive-bayes-tfidf-gridsearch",
        job_type='naive-bayes-tfidf'
    )

    modelo, mejores_params = entrenar_modelo_con_gridsearch(X_train, X_val, y_train, y_val)
    y_pred = modelo.predict(X_test)
    accuracy, balanced_accuracy, precision, recall, f1 = calcular_metricas(y_test, y_pred)

    run.config.update(mejores_params)
    run.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })
    run.finish()

    return balanced_accuracy, mejores_params

def _optuna(X_train, X_val, X_test, y_train, y_val, y_test):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "naive-bayes-tfidf-optuna",
        job_type='naive-bayes-tfidf'
    )
    
    modelo, mejores_params = entrenar_modelo_con_optuna(X_train, X_val, y_train, y_val)
    y_pred = modelo.predict(X_test)
    accuracy, balanced_accuracy, precision, recall, f1 = calcular_metricas(y_test, y_pred)

    run.config.update(mejores_params)
    run.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })

    run.finish()

    return balanced_accuracy, mejores_params

def train_best_model(X_train, y_train):
    path = "models/reviews/naivebayes_tfidf_hyperparameters.json"
    with open(path, "r") as f:
        model_params = json.load(f)
        
    final_model = Pipeline([
        ('vect', TfidfVectorizer(
            ngram_range=tuple(model_params["ngram_range"]),
            min_df=model_params['min_df'],
            max_df=model_params['max_df'],
            sublinear_tf=model_params['sublinear_tf'],
            norm=model_params['norm']
        )),
        ('clf', ComplementNB(alpha=model_params['alpha']))
    ])
    
    final_model.fit(X_train, y_train)
    return final_model



def main():
    df = read_reviews()
    reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
    labels = df["is_positive"].to_list()

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)
    X_train, X_val, X_test = preprocesar_texto(X_train, X_val, X_test)


    score_grid, params_grid = _gridsearch(X_train, X_val, X_test, y_train, y_val, y_test)
    score_optuna, params_optuna = _optuna(X_train, X_val, X_test, y_train, y_val, y_test)

    best_params = best_standard_params(score_grid, params_grid,score_optuna, params_optuna)


    os.makedirs('models/reviews', exist_ok=True)
    with open("models/reviews/naivebayes_tfidf_hyperparameters.json", "w") as f:
        json.dump(best_params, f, indent=4)

if __name__ == "__main__":
    main()
