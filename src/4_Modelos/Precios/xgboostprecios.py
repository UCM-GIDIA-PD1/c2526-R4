from pathlib import Path
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.decomposition import PCA
from sklearn.preprocessing import LabelEncoder
import optuna
import xgboost as xgb
from src.utils.files import read_file
from src.utils.config import prices
import wandb
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_score, recall_score, f1_score

df = read_file(prices)
df_model1 = df.copy()

# Drop unused columns
df_model1.drop(columns=['id','name','price_overview','v_resnet','v_convnext'], inplace=True)

df_clip = df_model1['v_clip'].apply(pd.Series)
pca = PCA(n_components=0.9)
df_clip = pca.fit_transform(df_clip)
df_clip = pd.DataFrame(df_clip, index=df_model1.index)

# Combine PCA features
df_model1.drop(columns=['v_clip'], inplace=True, errors='ignore')
df_model1 = pd.concat([df_model1, df_clip], axis=1)
df_model1.columns = df_model1.columns.astype(str)


lb_year = LabelEncoder()
df_model1['release_year'] = lb_year.fit_transform(df_model1['release_year'])

lb_price = LabelEncoder()
df_model1['price_range'] = lb_price.fit_transform(df_model1['price_range'])


X = df_model1.drop(columns=['price_range'])
y = df_model1['price_range']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)


run = wandb.init(
    entity="pd1-c2526-team4",
    project="Precios", 
    name='XGBoost-PCA 0.9',
    job_type='xgboost'
)


# def objective(trial):
#     params = {
#         'max_depth':        trial.suggest_int('max_depth', 3, 7),
#         'n_estimators':     trial.suggest_int('n_estimators', 100, 500),
#         'learning_rate':    trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
#         'subsample':        trial.suggest_float('subsample', 0.7, 1.0),
#         'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 0.9),
#         'reg_alpha':        trial.suggest_float('reg_alpha', 1e-4, 1.0, log=True),
#         'reg_lambda':       trial.suggest_float('reg_lambda', 1e-4, 1.0, log=True),
#         'random_state':     42,
#         'tree_method':      'hist', 
#         'objective':        'multi:softprob',
#         'num_class':        len(y_train.unique()),
#         'eval_metric':      'mlogloss',
#         'verbosity':        0,
#         'n_jobs':           -1,
#     }

#     model = xgb.XGBClassifier(**params)
#     score = cross_val_score(
#         model, X_train, y_train, cv=5, scoring='f1_weighted', n_jobs=-1
#     ).mean()
#     return score

# study = optuna.create_study(direction='maximize')
# study.optimize(objective, n_trials=250, n_jobs=1, show_progress_bar=True)

# best_params = study.best_params
# print(f"\nBest parameters: {best_params}")

best_params = {'max_depth': 3,
            'n_estimators': 487,
            'learning_rate': 0.14536658290655233,
            'subsample': 0.8894780115676028,
            'colsample_bytree': 0.6451191817772451,
            'reg_alpha': 0.004060662145489121,
            'reg_lambda': 0.028027327514653633
        }

final_model = xgb.XGBClassifier(**best_params)
final_model.fit(X_train, y_train)


y_pred = final_model.predict(X_test)

print("Classification Report:")
cal = classification_report(y_test, y_pred)
print(cal)

print("Confusion Matrix:")
conf_matrix = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(conf_matrix)

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='weighted')
recall = recall_score(y_test, y_pred, average='weighted')
f1 = f1_score(y_test, y_pred, average='weighted')

run.log({
    'accuracy': accuracy,
    'precision': precision,
    'recall': recall,
    'f1-score': f1,
    'confusion-matrix': conf_matrix.tolist() 
    })

run.finish()