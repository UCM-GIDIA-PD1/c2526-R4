import pandas as pd
import wandb

from src.utils.config import prices
from src.utils.files import read_file
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

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
  
    report = classification_report(y_true, y_pred)

    wandb.log({
        "report": report
    })
    
    print(report)
    
    run.finish()



if __name__ == "__main__":
    create_price_mode_baseline()