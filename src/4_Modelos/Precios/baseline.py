import pandas as pd
import wandb

from src.utils.config import prices
from src.utils.files import read_file
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score, precision_score, recall_score,f1_score # para las métricas de evaluación

def create_price_mode_baseline():
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name="baseline-mode",
        job_type="baseline"
    )
        
    df = read_file(prices)
    y_column = "price_range"
    
    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42)
    
    mode = train_df[y_column].value_counts().idxmax()
    
    y_true = test_df[y_column]
    y_pred = [mode] * len(y_true)
  
    conf_matrix = confusion_matrix(y_true, y_pred)

    precision = precision_score(y_true, y_pred, average='weighted')
    recall = recall_score(y_true, y_pred, average='weighted')
    f1 = f1_score(y_true, y_pred, average='weighted')
    accuracy = accuracy_score(y_true, y_pred)

    run.log({
        'accuracy' : accuracy,
        'precision' : precision,
        'Recall' : recall,
        'f1-score' : f1,
        'confusion-matrix' : conf_matrix
    })
    
    
    run.finish()



if __name__ == "__main__":
    create_price_mode_baseline()