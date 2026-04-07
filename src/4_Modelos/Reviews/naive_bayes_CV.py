from utils_modelo_reviews.preprocesamiento import read_reviews, train_val_test_split, clean_text_lemma
from tqdm import tqdm
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import ComplementNB
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
from sklearn.model_selection import cross_val_score
import optuna
import nltk
import wandb
nltk.download('stopwords')
tqdm.pandas(desc="Limpiando texto")
# run = wandb.init(
#         entity="pd1-c2526-team4",
#         project="Reviews", 
#         name="reviews-naivebayes-cv",
#         job_type="model"
#     )


def preprocesar_texto(X_train, X_val, X_test):
    X_train = [clean_text_lemma(review) for review in tqdm(X_train, desc = "Preprocesando entrenamiento")]
    X_val = [clean_text_lemma(review) for review in tqdm(X_val, desc = "Preprocesando validacion")]
    X_test = [clean_text_lemma(review) for review in tqdm(X_test, desc = "Preprocesando prueba")]
    return X_train, X_val, X_test

def entrenar_modelo(X_train, y_train):
    classifier = ComplementNB()
    classifier.fit(X_train, y_train)
    return classifier

def entrenar_modelo_con_gridsearch(X_train, X_val, y_train, y_val):
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val
    pipeline = Pipeline([
        ('vect', CountVectorizer()),
        ('clf', ComplementNB())
    ])

    param_grid = {
        'vect__ngram_range': [(1, 1), (1, 2)],
        'vect__min_df': [1, 2, 5],
        'vect__max_df': [0.8, 1.0],
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
        ('vect', CountVectorizer(
            ngram_range=grid_search.best_params_['vect__ngram_range'],
            min_df=grid_search.best_params_['vect__min_df'],
            max_df=grid_search.best_params_['vect__max_df']
        )),
        ('clf', ComplementNB(alpha=grid_search.best_params_['clf__alpha']))
    ])
    final_model.fit(X_train, y_train)
    return final_model, grid_search.best_params_


def entrenar_modelo_con_optuna(X_train,X_val, y_train,y_val, n_trials=30):
    X_train_full = X_train + X_val
    y_train_full = y_train + y_val
    def objective(trial):
        ngram_max = trial.suggest_int('ngram_max', 1, 2)
        
        param_grid = {
            'vect__ngram_range': (1, ngram_max),
            'vect__min_df': trial.suggest_int('min_df', 1, 5),
            'vect__max_df': trial.suggest_float('max_df', 0.7, 1.0),
            'clf__alpha': trial.suggest_float('alpha', 0.01, 2.0, log=True)
        }

        pipeline = Pipeline([
            ('vect', CountVectorizer(
                ngram_range=param_grid['vect__ngram_range'],
                min_df=param_grid['vect__min_df'],
                max_df=param_grid['vect__max_df']
            )),
            ('clf', ComplementNB(alpha=param_grid['clf__alpha']))
        ])

        score = cross_val_score(pipeline, X_train_full, y_train_full, n_jobs=-1, cv=5, scoring='balanced_accuracy')
        return score.mean()


    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    final_model = Pipeline([
        ('vect', CountVectorizer(
            ngram_range=(1, best_params['ngram_max']),
            min_df=best_params['min_df'],
            max_df=best_params['max_df']
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

# wandb.log({
#         "Accuracy": accuracy,
#         "Balanced accuracy": balanced_accuracy,
#         "Precision": precision,
#         "Recall": recall,
#         "F1-score": f1
#     })

# run.finish()

def _gridsearch(X_train, X_val, X_test, y_train, y_val, y_test):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "naive-bayes-cv-gridsearch",
        job_type='naive-bayes-cv'
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

def _optuna(X_train, X_val, X_test, y_train, y_val, y_test):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name= "naive-bayes-cv-optuna",
        job_type='naive-bayes-cv'
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

def handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Función que maneja la entrada. Por defecto la función siempre devuelve True.

    Args:
        initial_mensagge (str): mensaje inicial. 
        isResponseValid (function): función que verifica la validez de un input dado.

    Returns:
        bool: True si el input es correcto, False en caso contrario.
    """
    respuesta = input(initial_message).strip()

    # Hasta que no se dé una respuesta válida no se puede salir del bucle
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    
    return respuesta

if __name__ == "__main__":
    gridsearch_message = "Ejecutar gridsearch [Y/N]: "
    response = handle_input(gridsearch_message, lambda x: x.lower() in ["y", "n"])
    do_gridsearch = response.lower() == "y"

    optuna_message = "Ejecutar optuna [Y/N]: "
    response = handle_input(optuna_message, lambda x: x.lower() in ["y", "n"])
    do_optuna = response.lower() == "y"

    if do_gridsearch or do_optuna:
        df = read_reviews()
        reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
        labels = df["is_positive"].to_list()

        X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)
        X_train, X_val, X_test = preprocesar_texto(X_train, X_val, X_test)

    if do_gridsearch:
        _gridsearch(X_train, X_val, X_test, y_train, y_val, y_test)
    
    if do_optuna:
        _optuna(X_train, X_val, X_test, y_train, y_val, y_test)