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

def forward_selection_aic(train_df, test_df, y_variable):
    initial_variables = [c for c in train_df.columns if c != y_variable]
    selected_variables = []
    current_aic = float('inf') # Representa infinito, para que cualquier AIC sea mejor que el inicial
    
    step = 0
    while initial_variables: # Mientras la lista no esté vacía
        aic_with_candidates = []
        
        # Probamos meter todas las variables y nos quedamos con la que mejor AIC tenga
        for candidate in initial_variables:
            variables = selected_variables + [candidate]
            X_train = sm.add_constant(train_df[variables])
            model = sm.OLS(train_df[y_variable], X_train).fit()
            aic_with_candidates.append((model.aic, candidate))
        aic_with_candidates.sort()
        best_new_aic, best_candidate = aic_with_candidates[0] 
        
        # Comprobamos si el mejor AIC es mejor que el que ya teníamos
        if best_new_aic < current_aic:
            selected_variables.append(best_candidate)
            initial_variables.remove(best_candidate)
            current_aic = best_new_aic
            step += 1

            # Calculamos métricas y las mandamos a W&B
            X_train_final = sm.add_constant(train_df[selected_variables])
            best_model_step = sm.OLS(train_df[y_variable], X_train_final).fit()

            X_test = sm.add_constant(test_df[selected_variables])
            y_pred = best_model_step.predict(X_test)
            
            mae = mean_absolute_error(test_df[y_variable], y_pred)
            rmse = sqrt(mean_squared_error(test_df[y_variable], y_pred))
            r2 = r2_score(test_df[y_variable], y_pred)

            wandb.log({
                "iteration": step,
                "aic": current_aic,
                "test_mae": mae,
                "test_rmse": rmse,
                "test_r2": r2,
                "num_variables": len(selected_variables),
                "current_variables": ", ".join(selected_variables) 
            })
            
            print(f"Añadida {best_candidate} con AIC: {current_aic:.2f} y MAE: {mae:.2f}")
        else:
            break # Si no encuentra un parámetro que mejore el AIC ha acabado
            
    return selected_variables

def forward_selection_bic(train_df, test_df, y_variable):
    initial_variables = [c for c in train_df.columns if c != y_variable]
    selected_variables = []
    current_bic = float('inf') # Representa infinito, para que cualquier BIC sea mejor que el inicial
    
    step = 0
    while initial_variables: # Mientras la lista no esté vacía
        bic_with_candidates = []
        
        # Probamos meter todas las variables y nos quedamos con la que mejor BIC tenga
        for candidate in initial_variables:
            variables = selected_variables + [candidate]
            X_train = sm.add_constant(train_df[variables])
            model = sm.OLS(train_df[y_variable], X_train).fit()
            bic_with_candidates.append((model.bic, candidate))
        bic_with_candidates.sort()
        best_new_bic, best_candidate = bic_with_candidates[0] 
        
        # Comprobamos si el mejor BIC es mejor que el que ya teníamos
        if best_new_bic < current_bic:
            selected_variables.append(best_candidate)
            initial_variables.remove(best_candidate)
            current_bic = best_new_bic
            step += 1

            # Calculamos métricas y las mandamos a W&B
            X_train_final = sm.add_constant(train_df[selected_variables])
            best_model_step = sm.OLS(train_df[y_variable], X_train_final).fit()

            X_test = sm.add_constant(test_df[selected_variables])
            y_pred = best_model_step.predict(X_test)
            
            mae = mean_absolute_error(test_df[y_variable], y_pred)
            rmse = sqrt(mean_squared_error(test_df[y_variable], y_pred))
            r2 = r2_score(test_df[y_variable], y_pred)

            wandb.log({
                "iteration": step,
                "bic": current_bic,
                "test_mae": mae,
                "test_rmse": rmse,
                "test_r2": r2,
                "num_variables": len(selected_variables),
                "current_variables": ", ".join(selected_variables) 
            })
            
            print(f"Añadida {best_candidate} con BIC: {current_bic:.2f} y MAE: {mae:.2f}")
        else:
            break # Si no encuentra un parámetro que mejore el BIC ha acabado
            
    return selected_variables

def train_linear(train_df, test_df, y_variable, selection_method="AIC"):
    if selection_method == "AIC":
        best_variables = forward_selection_aic(train_df, test_df, y_variable)
    else:
        best_variables = forward_selection_bic(train_df, test_df, y_variable)
    
    # Modelo con las mejores variables
    X_train = sm.add_constant(train_df[best_variables])
    model = sm.OLS(train_df[y_variable], X_train).fit()
    
    # Métricas finales
    X_test = sm.add_constant(test_df[best_variables])
    y_pred = model.predict(X_test)
    
    mae = mean_absolute_error(test_df[y_variable], y_pred)
    r2 = r2_score(test_df[y_variable], y_pred)
    
    return mae, r2, best_variables

def create_linear_model_popularity(selection_method="AIC"):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad",
        name=f"linear-regression-{selection_method.lower()}",
        job_type="model-training"
    )

    df = read_file(popularity)
    y_variable = "recomendaciones_totales"
    
    df = transform_for_linear_regresion(df)

    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)

    mae, r2, variables = train_linear(train_df, test_df, y_variable, selection_method)

    print(f"--- RESULTADOS {selection_method} ---")
    print(f"Variables finales ({len(variables)}): {variables}")
    print(f"R2 Final: {r2:.4f} \n MAE Final: {mae:.2f}\n")

    run.finish()

def transform_for_linear_regresion(df):
    df_clean = df.copy()
    errase_columns = ['id', 'name', 'price_range', 'v_resnet', 'v_convnext']
    df_clean = df_clean.drop(columns=[col for col in errase_columns if col in df_clean.columns])

    # Forzar a numérico columnas de texto (objetos) que deberían ser números
    obj_cols = df_clean.select_dtypes(include=['object']).columns
    for col in obj_cols:
        if col != 'v_clip':  # Dejamos v_clip tranquilo porque es una lista
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

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

    # Solo nos quedamos con columnas numéricas y por si hay algún nulo ponemos 0s
    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.fillna(0)

    return df_clean

if __name__ == "__main__":
    # Con AIC
    create_linear_model_popularity(selection_method="AIC")

    # Con BIC
    create_linear_model_popularity(selection_method="BIC")