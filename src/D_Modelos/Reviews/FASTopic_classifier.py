"""
Requires the pretrained model
Given a text, classify it into one of the following topics:
topic_tags = {
    0: "Updates & Bugs",
    1: "Action & Combat",
    2: "Music & Atmosphere",
    3: "Story & Design",
    4: "Casual & Humor",
    5: "General Opinion",
}
"""
from src.utils.config import reviews_fastopic_file, reviews, reviews_en_core_web_sm
from src.utils.files import read_file
from fastopic import FASTopic
import re
import spacy

nlp = spacy.load(reviews_en_core_web_sm)
def spacy_tokenizer(text):
    doc = nlp(text)
    return [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop
        and not token.is_punct
        and not token.is_space
        and token.is_alpha
        and len(token.text) > 2
    ]

def load_topic_model():
    topic_model = FASTopic.from_pretrained(reviews_fastopic_file)
    # daba errores de tensores en distintos dispositivos (cuda, cpu), así que se asegura que todo esté en CPU para evitar esos problemas
    topic_model.model.to("cpu")
    topic_model.train_doc_embeddings = topic_model.train_doc_embeddings.to("cpu")
    if hasattr(topic_model.model, 'topic_embeddings'):
        topic_model.model.topic_embeddings = topic_model.model.topic_embeddings.to("cpu")
    return topic_model

def remove_hearts(text):
    text = re.sub(r'(hearts){2,}', '', text)
    text = re.sub('heartsheart', '', text)
    text = re.sub('heart', '', text)
    return text

def topic_predict(df, topic_model):
    topic_tags = {
        0: "Updates & Bugs",
        1: "Action & Combat",
        2: "Music & Atmosphere",
        3: "Story & Design",
        4: "Casual & Humor",
        5: "General Opinion",
    }
    df["text_clean"] = df["text"].apply(remove_hearts)
    # El modelo FASTopic ya se encarga del preprocesamiento del texto
    topic_distributions = topic_model.transform(df["text_clean"].tolist())
    df["predicted_topic"] = topic_distributions.argmax(axis=1)
    df["predicted_topic_label"] = df["predicted_topic"].map(topic_tags)
    return df

def return_statistics(df):
    counts = (
    df
    .groupby("predicted_topic_label")["is_positive"]
    .value_counts()
    .unstack(fill_value=0)
    )
    
    counts = counts.rename(columns={False: "negative", True: "positive"})
    counts["positive_ratio"] = counts["positive"] / (counts["positive"] + counts["negative"])
    counts = counts.sort_values("positive_ratio", ascending=False)
    print(counts)
    return counts

def pipeline(df):
    print("Cargando modelo FASTopic...")
    model = load_topic_model()

    print("Realizando predicciones de temas...")
    df = topic_predict(df, model)
    df_stats = return_statistics(df)
    return df_stats

if __name__ == "__main__":
    df = read_file(reviews)
    df = df.sample(frac=0.05, random_state=42)
    df_stats = pipeline(df)
    print(df_stats.loc["Music & Atmosphere", "positive"])
