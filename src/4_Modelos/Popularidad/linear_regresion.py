from numpy import sqrt
import pandas as pd
import wandb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.utils.config import popularity
from src.utils.files import read_file

def create_linear_model_popularity():
    None