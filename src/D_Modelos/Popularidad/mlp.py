"""
Dado popularidad.parquet, ejecuta el modelo de Late Fusion.
No se reduce la dimensionalidad de las imagenes.
"""
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['CUDA_VISIBLE_DEVICES'] = '' # Ejecución en CPU (estable y sin límite de memoria VRAM)

import numpy as np
import optuna
import warnings

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import PowerTransformer, QuantileTransformer, MinMaxScaler, StandardScaler, FunctionTransformer
from sklearn.model_selection import StratifiedKFold, cross_validate

import keras
from keras.models import Model
from keras.layers import Input, Dense, Dropout, Concatenate
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from keras.regularizers import l2
from scikeras.wrappers import KerasRegressor

from src.utils.files import read_file
from src.utils.config import popularity, popularidad_mlp_file, seed
from src.D_Modelos.Popularidad.popularity_model import PopularityModel

warnings.filterwarnings('ignore')

def get_image_matrix(X):
    """Extrae los embeddings puros de 512 dimensiones sin comprimir"""
    return np.vstack(X.iloc[:, 0].values).astype(np.float32)

def cast_to_float32(X):
    return X.astype(np.float32)

def safe_expm1(y):
    return np.expm1(np.clip(y, a_min=0, a_max=16))

def build_keras_heavyweight(hidden_layer_sizes=(256, 128, 64), activation='swish', learning_rate_init=0.001, alpha=0.0001, drop_rate=0.4, image_features=512, meta=None):
    keras.utils.set_random_seed(seed)
    
    n_features = meta["n_features_in_"]
    inputs = Input(shape=(n_features,))

    if image_features > 0:
        image_inputs = inputs[:, :image_features]
        tabular_inputs = inputs[:, image_features:]

        # BRAZO VISUAL
        v = Dense(256, activation=activation, kernel_regularizer=l2(alpha * 5))(image_inputs)
        v = Dropout(drop_rate)(v)
        v = Dense(64, activation=activation, kernel_regularizer=l2(alpha))(v)
        v = Dropout(drop_rate / 2)(v) # Menos dropout según se comprime
        v = Dense(16, activation=activation)(v)

        # BRAZO TABULAR 
        t = Dense(hidden_layer_sizes[0], activation=activation, kernel_regularizer=l2(alpha))(tabular_inputs)
        if len(hidden_layer_sizes) > 1:
            t = Dense(hidden_layer_sizes[1], activation=activation)(t)
        if len(hidden_layer_sizes) > 2:
            t = Dense(hidden_layer_sizes[2], activation=activation)(t)

        # FUSIÓN
        merged = Concatenate()([v, t])
        z = Dense(64, activation=activation)(merged)
        z = Dense(16, activation=activation)(z)
        outputs = Dense(1)(z)
        
    else:
        t = Dense(hidden_layer_sizes[0], activation=activation, kernel_regularizer=l2(alpha))(inputs)
        for size in hidden_layer_sizes[1:]:
            t = Dense(size, activation=activation)(t)
        outputs = Dense(1)(t)

    model = Model(inputs=inputs, outputs=outputs)
    opt = keras.optimizers.Adam(learning_rate=learning_rate_init)
    model.compile(optimizer=opt, loss='mse') 
    
    return model

class MLPPopularity(PopularityModel):
    def __init__(self, minio: dict):
        super().__init__(
            run_name="mlp-keras-heavyweight-nolimits",
            model_path=popularidad_mlp_file,
            minio=minio
        )

    def _build_pipeline(self, hyperparameters, config, X_train):
        mlp_params = {k: v for k, v in hyperparameters.items()}
        transformer_name = mlp_params.pop('transformer', 'power')
        skew_transformer = PowerTransformer(method='yeo-johnson') if transformer_name == 'power' else QuantileTransformer(output_distribution='normal', random_state=seed)

        has_image = 'v_clip' in X_train.columns
        image_dim = 512 if has_image else 0

        cols_minmax = [c for c in self.COLS_ACOTADAS if c in X_train.columns]
        cols_sesgadas = [c for c in self.COLS_SESGADAS if c in X_train.columns]
        cols_binarias = [c for c in self.COLS_BINARIAS if c in X_train.columns]
        cols_normales = [c for c in X_train.columns if c not in cols_minmax + cols_sesgadas + cols_binarias and c != 'v_clip']
        
        transformers = []

        if has_image:
            clip_pipe = Pipeline([
                ('extractor', FunctionTransformer(get_image_matrix, validate=False)),
                ('scale', MinMaxScaler()) 
            ])
            transformers.append(('clip_raw', clip_pipe, ['v_clip']))

        if cols_minmax: transformers.append(('minmax', MinMaxScaler(), cols_minmax))
        if cols_sesgadas: transformers.append(('sesgadas', skew_transformer, cols_sesgadas))
        if cols_binarias: transformers.append(('binarias', 'passthrough', cols_binarias))
        if cols_normales: transformers.append(('normales', StandardScaler(), cols_normales))

        preprocessor = ColumnTransformer(transformers=transformers, remainder='drop')

        early_stopping = EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)
        reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=15, min_lr=1e-6, verbose=0)

        keras_mlp = KerasRegressor(
            model=build_keras_heavyweight,
            model__image_features=image_dim,
            model__hidden_layer_sizes=mlp_params.get('hidden_layer_sizes', (256, 128, 64)),
            model__activation=mlp_params.get('activation', 'swish'),
            model__drop_rate=mlp_params.get('drop_rate', 0.4),
            model__learning_rate_init=mlp_params.get('learning_rate_init', 0.001),
            model__alpha=mlp_params.get('alpha', 0.0001),
            epochs=10000,
            batch_size=128,
            validation_split=0.1,
            callbacks=[reduce_lr, early_stopping],
            verbose=0,
            random_state=seed
        )

        pipeline = Pipeline([
            ('prep', preprocessor),
            ('cast', FunctionTransformer(cast_to_float32)),
            ('mlp', keras_mlp)
        ])

        return TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=safe_expm1)

    def _optimize_hyperparameters(self, data_splits, config):
        X_train = data_splits["X_train"]
        y_train = data_splits["y_train"]
        y_binned_train = data_splits["y_binned_train"]

        def objective(trial):
            params = {
                'hidden_layer_sizes': trial.suggest_categorical('hidden_layer_sizes', [
                    (256, 128, 64), 
                    (512, 256, 128),
                    (128, 64, 32), 
                    (256, 128)
                ]),
                'activation': trial.suggest_categorical('activation', ['swish', 'relu', 'elu']),
                'drop_rate': trial.suggest_categorical('drop_rate', [0.3, 0.4, 0.5]),
                'alpha': trial.suggest_categorical('alpha', [0.0001, 0.001, 0.01, 0.1]),
                'learning_rate_init': trial.suggest_categorical('learning_rate_init', [0.001, 0.0005]),
                'transformer': trial.suggest_categorical('transformer', ['power', 'quantile'])
            }

            model = self._build_pipeline(params, config, X_train)
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
            
            scores = cross_validate(
                model, X_train, y_train, 
                cv=list(cv.split(X_train, y_binned_train)), 
                scoring='neg_mean_absolute_error', 
                n_jobs=1, 
                error_score='raise'
            )
            return -scores['test_score'].mean()
        
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=100) 
        
        return study.best_params

def main(minio={"minio_write": False, "minio_read": False}):
    df_raw = read_file(popularity, minio)
    modelo_mlp = MLPPopularity(minio=minio)
    modelo_mlp.run_experiment(df_raw, config={"avoid_multicol": False, "use_log": False})

if __name__ == "__main__":
    main()