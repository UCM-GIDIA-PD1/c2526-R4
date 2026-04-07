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
    reviews = df["text"].to_list() # minusculas y solo caracteres alphanumericos y signos comunes de puntuacion
    labels = df["is_positive"].to_list()

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(reviews, labels)

    X_train, X_val, X_test = preprocesar_texto(X_train, X_val, X_test)
    modelo, mejores_params = entrenar_modelo_con_optuna(X_train, y_train)
    y_pred = modelo.predict(X_val)
    calcular_metricas(y_val, y_pred)
    print(mejores_params)