import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import statsmodels.api as sm
import wandb
from math import sqrt
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.utils.config import popularity
from src.utils.files import read_file

def transform_for_linear_regresion(df):
    df_clean = df.copy()
    errase_columns = ['id', 'name', 'price_range', 'v_resnet', 'v_convnext']
    df_clean = df_clean.drop(columns=[col for col in errase_columns if col in df_clean.columns])

    # PCA de vector de emmbedings
    zero_vector = np.zeros(512)
    df_clean['v_clip'] = df_clean['v_clip'].apply(
        lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
    )
    
    clip_matrix = np.vstack(df_clean['v_clip'].values)
    
    pca = PCA(n_components=10, random_state=42)
    clip_pca = pca.fit_transform(clip_matrix)
    
    for i in range(10):
        df_clean[f'clip_pca_{i}'] = clip_pca[:, i]
    
    # Ya con el PCA la columna de CLIP no es necesaria
    df_clean = df_clean.drop(columns=['v_clip'])

    variables_to_scale = [col for col in df_clean.columns if col != 'recomendaciones_totales']
    
    scaler = StandardScaler()
    df_clean[variables_to_scale] = scaler.fit_transform(df_clean[variables_to_scale])

    # Forzamos a todos los datos a ser numéricos
    obj_cols = df_clean.select_dtypes(include=['object']).columns
    for col in obj_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Solo nos quedamos con columnas numéricas y por si hay algún nulo ponemos 0s
    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.fillna(0)

    return df_clean

def forward_selection(train_df, test_df, y_variable, selection_method="AIC", use_log=False):
    initial_variables = [c for c in train_df.columns if c != y_variable]
    selected_variables = []
    
    current_score = float('inf') 
    
    if use_log:
        y_train_target = np.log1p(train_df[y_variable])
    else:
        y_train_target = train_df[y_variable]
        
    y_test_real = test_df[y_variable]

    step = 0

    while initial_variables:
        scores_with_candidates = []
        
        for candidate in initial_variables:
            variables = selected_variables + [candidate]
            X_train = sm.add_constant(train_df[variables])
            
            model = sm.OLS(y_train_target, X_train).fit()
            scores_with_candidates.append((getattr(model, selection_method.lower()), candidate))
            
        best_new_score, best_candidate = min(scores_with_candidates) 
        
        if best_new_score < current_score:
            selected_variables.append(best_candidate)
            initial_variables.remove(best_candidate)
            current_score = best_new_score
            step += 1

            X_train_final = sm.add_constant(train_df[selected_variables])
            best_model_step = sm.OLS(y_train_target, X_train_final).fit()

            X_test = sm.add_constant(test_df[selected_variables])
            y_pred_raw = best_model_step.predict(X_test)
            
            if use_log:
                y_pred = np.expm1(y_pred_raw)
            else:
                y_pred = y_pred_raw
            
            mae = mean_absolute_error(y_test_real, y_pred)
            rmse = sqrt(mean_squared_error(y_test_real, y_pred))
            r2 = r2_score(y_test_real, y_pred)

            wandb.log({
                "iteration": step,
                "score": current_score,
                "test_mae": mae,
                "test_rmse": rmse,
                "test_r2": r2,
                "num_variables": len(selected_variables),
                "current_variables": ", ".join(selected_variables) 
            })
            
            print(f"Añadida {best_candidate} con {selection_method}: {current_score:.2f} y MAE: {mae:.2f}")
        else:
            break 
            
def create_linear_model_popularity(selection_method, use_log):
    run_name = f"linear-regression-log-{selection_method.lower()}" if use_log else f"linear-regression-{selection_method.lower()}"
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name=run_name,
        job_type="model-training"
    )

    df = read_file(popularity)
    y_variable = "recomendaciones_totales"
    
    df = transform_for_linear_regresion(df)

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)

    forward_selection(train_df, test_df, y_variable, selection_method, use_log)

    run.finish()

if __name__ == "__main__":
    # Con AIC Normal
    create_linear_model_popularity(selection_method="AIC", use_log=False)

    # Con AIC Logarítmico
    create_linear_model_popularity(selection_method="AIC", use_log=True)

    # Parece que en este caso AIC y BIC hacen lo mismo así que nos quedamos solo con AIC

    # Con BIC Normal
    #create_linear_model_popularity(selection_method="BIC", use_log=False)
    # Con BIC Logarítmico
    #create_linear_model_popularity(selection_method="BIC", use_log=True)