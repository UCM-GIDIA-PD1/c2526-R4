from src.utils.files import write_to_file
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix 
from sklearn.metrics import ConfusionMatrixDisplay, classification_report

import os
import joblib

import matplotlib.pyplot as plt
import wandb

def get_metrics(y_test, y_pred, classes=None, img_path=None, download_images=False):
    """Calcula y muestra las métricas de rendimiento para un modelo de clasificación.

    Args:
        y_test (pd.Dataframe): Etiquetas reales del conjunto de prueba.
        y_pred (pd.Dataframe): Etiquetas predichas por el modelo.
        classes (list, optional): Nombres de las categorías para el informe de 
            clasificación. Por defecto es None.
        img_path (str | Path, optional): ruta en donde guardar la imagen
        download_images (bool, optional): booleano que indica si guardar la imagen localmente

    Returns:
        dict: Diccionario con las métricas calculadas:
            - 'accuracy': Exactitud global.
            - 'precision': Precisión media ponderada.
            - 'recall': Sensibilidad media ponderada.
            - 'f1': Puntuación F1 media ponderada.
    """
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted')
    rec = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')

    print(f'Accuracy:  {acc}')
    print(f'Precision: {prec}')
    print(f'Recall:    {rec}')
    print(f'F1 Score:  {f1}')
    print(classification_report(y_test, y_pred, target_names=classes))

    cm = confusion_matrix(y_test, y_pred)
    print(cm)

    wandb_matrix = None
    if classes:
        fig, ax = plt.subplots(figsize=(10,6))
        disp = ConfusionMatrixDisplay.from_predictions(
            y_test, y_pred,
            display_labels=classes,
            cmap='Blues',
            ax=ax,
            xticks_rotation=45
        )

        wandb_matrix = wandb.Image(fig)

        if img_path and download_images:
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            write_to_file(data=disp.figure_, filepath=img_path)
        else:
            plt.close()

    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1-score': f1, 
            'confusion_matrix': wandb_matrix }

def save_model(output_file, final_model):
    os.makedirs('models/precios', exist_ok=True)
    joblib.dump(final_model, f"models/precios/{output_file}")
    print(f"Modelo guardado en models/precios/{output_file}")