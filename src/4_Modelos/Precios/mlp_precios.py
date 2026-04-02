"""
Dado precios.parquet crea diferentes modelos de MLP para predecir en que rango 
de precio se sitúa un juego según sus características.
"""

from src.utils.config import prices
from src.utils.files import read_file
from utils_modelo_precios.preprocesamiento import get_metrics

from sklearn.preprocessing import StandardScaler, PowerTransformer, OneHotEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neural_network import MLPClassifier

from pandas import DataFrame, concat, Series

def _preprocess(df):
    """Función para transformar los datos para realiza MLP

    Args:
        df (DataFrame): Datos iniciales del modelo que van a ser procesados.
    
    Returns:
        DataFrame: Datos que contienen las variables regresoras.
        DataFrame: Datos que contienen las variables respuesta.
    """
    df = df.drop(columns=['price_overview'])

    # Separación de DataFrames en diferentes tipos de variables
    y = DataFrame(df['price_range'])
    X_num_log = df[['num_languages', 'total_games_by_publisher', 'total_games_by_developer']]
    X_num_std = df[['description_len', 'release_year', 'brillo']]
    X_trans = df.drop(columns=['price_range', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'description_len', 'release_year', 'brillo'])

    # Transformación de variables
    pt = PowerTransformer(method='yeo-johnson')
    X_num_log_trans = pt.fit_transform(X_num_log)

    std = StandardScaler()
    X_num_std_trans = std.fit_transform(X_num_std)

    ohe = OneHotEncoder(sparse_output=False)
    y_trans = ohe.fit_transform(y)

    # Unificar datos transformados
    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_y_trans = DataFrame(y_trans, columns = ohe.get_feature_names_out())

    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)

    # Variables eliminadas por poca relevancia (el estudio está en el notebook de MLP)
    df2 = df2.drop(columns=['Family Sharing'], errors='ignore')

    # Variables no usadas en el análisis
    df2 = df2.drop(columns=['id', 'name'], errors='ignore')

    return df2, df_y_trans

def _model_no_img(df):
    param_grid = {
        'hidden_layer_sizes': [(64,32), (100,), (80,60), (70,35)],
        'activation': ['relu', 'tanh'],
        'alpha': [0.0001, 0.01, 0.1],
        'learning_rate_init': [0.001, 0.01]
    }

    X_train, X_test, Y_train, Y_test = train_test_split(df_X, df_Y, test_size=0.3, random_state=42)

    grid = GridSearchCV(MLPClassifier(max_iter=5000, random_state=42), param_grid=param_grid, cv=5, n_jobs=-1)
    grid.fit(X_train, Y_train)

    mlp_mejor_modelo = grid.best_estimator_
    params_mejor_modelo = grid.best_params_
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    Y_pred = mlp_mejor_modelo.predict(X_test)
    get_metrics(Y_test, Y_pred, classes=list(Y_test.columns),  confusion_m=False)


if __name__ == '__main__':
    print('Reading...')
    df = read_file(prices)
    
    print('Preprocessing...')
    df_X, df_Y = _preprocess(df)

    print('Creating MLP without images...')
    _model_no_img(df)
