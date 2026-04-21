import os
import wandb
import numpy as np
from abc import ABC, abstractmethod
from src.utils.files import read_file, write_to_file

class BaseModel(ABC):
    def __init__(self, project_name: str, run_name: str, model_path, minio: dict, entity: str = "pd1-c2526-team4"):
        self.project_name = project_name
        self.run_name = run_name
        self.model_path = model_path
        self.minio = minio
        self.entity = entity

    # MÉTODOS ABSTRACTOS
    @abstractmethod
    def _preprocess_data(self, df_raw, config):
        pass

    @abstractmethod
    def _split_data(self, df_prep):
        """Debe retornar un dict con al menos: X_train, X_test, y_train, y_test"""
        pass

    @abstractmethod
    def _optimize_hyperparameters(self, data_splits, config):
        pass

    @abstractmethod
    def _build_pipeline(self, hyperparameters, config, X_train):
        pass

    @abstractmethod
    def _calculate_metrics(self, y_true, y_pred) -> dict:
        pass
    
    def _predict(self, model, X_test, X_train=None):
        preds = model.predict(X_test)
        return np.maximum(preds, 0)

    def run_experiment(self, df_raw, config, hyperparameters=None):
        """Flujo de ejecución de un modelo"""
        
        run = wandb.init(
            entity=self.entity, 
            project=self.project_name, 
            name=self.run_name,
            job_type="model-training",
            config=config
        )
        print(f"\nIniciando experimento: {self.run_name} ---")

        # Preparación de datos
        df_prep = self._preprocess_data(df_raw, config)
        data_splits = self._split_data(df_prep)
        
        X_train, X_test = data_splits["X_train"], data_splits["X_test"]
        y_train, y_test = data_splits["y_train"], data_splits["y_test"]

        # Intentamos cargar hiperparámetros en caso de que ya se hayan encontrado los óptimos
        model_data = None
        try:
            model_data = read_file(self.model_path, self.minio)
        except Exception:
            pass
        
        if model_data is not None:
            print(f"Cargando modelo existente de {self.model_path}...")
            modelo_final = model_data["model"]
            best_params = model_data.get("hyperparameters", {})
        else:
            print("No se encontró pkl. Iniciando entrenamiento...")
            if hyperparameters:
                best_params = hyperparameters.copy()
            else:
                best_params = self._optimize_hyperparameters(data_splits, config)

            modelo_final = self._build_pipeline(best_params, config, X_train)
            modelo_final.fit(X_train, y_train)

            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            write_to_file({"model": modelo_final, "hyperparameters": best_params}, self.model_path, self.minio)
            print(f"Modelo guardado exitosamente en {self.model_path}")

        # Predicción, Métricas y WandB
        wandb.config.update({"params": best_params})
        
        preds = self._predict(modelo_final, X_test, X_train)
        metrics = self._calculate_metrics(y_test, preds)
        
        print(f"Resultados de {self.run_name}: MAE: {metrics['mae']:.4f} | RMSE: {metrics['rmse']:.4f} | R2: {metrics['r2']:.4f}")
        wandb.log({f"test_{k}": v for k, v in metrics.items()}) # Logueamos estandarizado
        
        run.finish()
        return modelo_final

    # Evaluación para Z_evaluaciones.py
    def evaluate(self, df_raw, config) -> dict:
        """Hace todo el pipeline de datos y predice cargando los hiperparámetros óptimos"""
        df_prep = self._preprocess_data(df_raw, config)
        data_splits = self._split_data(df_prep)
        
        model_data = read_file(self.model_path, self.minio)
        if model_data is None:
            raise FileNotFoundError(f"No se encontró el modelo en {self.model_path} para evaluación.")
            
        modelo_final = model_data["model"]
        preds = self._predict(modelo_final, data_splits["X_test"], data_splits["X_train"])
        
        return self._calculate_metrics(data_splits["y_test"], preds)