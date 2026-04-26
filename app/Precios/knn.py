
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
import numpy as np
import pandas as pd

class ClusterEmbeddingsTransformer(BaseEstimator, TransformerMixin):
    """
    Clase para tener la función ClusterEmbeddings en el pipeline y no tener que luego que volver
    entrenar el algoritmo de clustering.

    Realiza el fit de kmeans y almacena el los datos para ser reutilizados.
    """
    def __init__(self, emb_col='v_clip', n_clusters=8, seed = 42):
        self.emb_col = emb_col
        self.n_clusters = n_clusters
        self.seed = seed
        self.kmeans_ = None

    def fit(self, X, y=None):
        embeddings = np.stack(X[self.emb_col].values)
        self.kmeans_ = KMeans(n_clusters=self.n_clusters, random_state=self.seed)
        self.kmeans_.fit(embeddings)
        return self

    def transform(self, X):
        X = X.copy()
        embeddings = np.stack(X[self.emb_col].values)
        X['cluster'] = self.kmeans_.predict(embeddings)
        X = X.drop(columns=[self.emb_col])
        return X
