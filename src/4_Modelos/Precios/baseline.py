"""
Baseline para predecir la categoría de precio en la que se encuentra un 
juego. Se crea un modelo que utiliza la moda (la clase mayoritaria) para 
realizar las predicciones. 

Las métricas se registran en Weights & Biases (wandb).
"""

from utils_modelo_precios.preprocesamiento import get_metrics, read_prices, train_val_test_split
from pandas import DataFrame, concat

import wandb

def create_price_mode_baseline():
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name="baseline-mode",
        job_type="baseline"
    )
        
    df = read_prices()

    y_all = DataFrame(df['price_range'])
    X_all = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X_all, y_all)

    # Para la calcular la moda no nos hacen falta datos de validación, por lo que los vamos
    # a unir a los de entrenamiento para un cálculo más exacto de la moda
    X_train = concat([X_train, X_val], axis=0)
    y_train = concat([y_train, y_val], axis=0)
    
    mode = y_train["price_range"].value_counts().idxmax()
    run.config.update({'mode': mode})
    
    y_pred = [mode] * len(y_test)
  
    metricas = get_metrics(y_test.values.flatten(), y_pred, classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'])

    run.log(metricas)
    
    run.finish()


if __name__ == "__main__":
    create_price_mode_baseline()