from utils_modelo_reviews.preprocesamiento import read_reviews, train_val_test_split, clean_text_lemma
from tqdm import tqdm
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import ComplementNB
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GridSearchCV
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

def entrenar_modelo_con_gridsearch(X_train, y_train):
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

    grid_search.fit(X_train, y_train)

    return grid_search.best_estimator_, grid_search.best_params_

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
if __name__ == "__main__":
    df = read_reviews()
    df = read_reviews()
    reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
    labels = df["is_positive"].to_list()

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)

    X_train, X_val, X_test = preprocesar_texto(X_train, X_val, X_test)
    modelo, mejores_params = entrenar_modelo_con_gridsearch(X_train, y_train)
    y_pred = modelo.predict(X_val)
    calcular_metricas(y_val, y_pred)
    print(mejores_params)