import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score, f1_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import ComplementNB
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import re
from src.utils.config import reviews
from tqdm import tqdm
import wandb
import nltk
from utils_modelo_reviews.preprocesamiento import clean_text

nltk.download('stopwords')

run = wandb.init(
        entity="pd1-c2526-team4",
        project="Reviews", 
        name="reviews-naivebayes-tfidf",
        job_type="model"
    )


tqdm.pandas(desc="Limpiando texto")

df = pd.read_parquet(reviews)

stop_words = set(stopwords.words("english"))
ps = PorterStemmer()

df["text"] = df["text"].progress_apply(lambda x : clean_text(x,ps,stop_words))

print("Entrenando modelo")
X_train, X_test, y_train, y_test = train_test_split(df["text"], df["is_positive"], train_size=0.8, random_state=42)

vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_df=0.9, min_df=5)
X_train = vectorizer.fit_transform(X_train) 
X_test = vectorizer.transform(X_test)       

classifier = ComplementNB()
classifier.fit(X_train, y_train)

y_pred = classifier.predict(X_test)

print("Calculando métricas")
accuracy = accuracy_score(y_test, y_pred)
balanced_accuracy = balanced_accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print("Accuracy:", accuracy)
print("Balanced accuracy:", balanced_accuracy)
print("Precision:", precision)
print("Recall:", recall)
print("F1-score:", f1)

wandb.log({
        "Accuracy": accuracy,
        "Balanced accuracy": balanced_accuracy,
        "Precision": precision,
        "Recall": recall,
        "F1-score": f1
    })

run.finish()