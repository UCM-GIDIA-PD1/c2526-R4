import pandas as pd

def price_range(x):
    if x == 0:
        return 'Free'
    elif x > 0 and x < 5:
        return '[0.01,4.99]'
    elif x >= 5 and x < 10:
        return '[5.00,9.99]'
    elif x >= 10 and x < 15:
        return '[10.00,14.99]'
    elif x >= 15 and x < 20:
        return '[15.00,19.99]'
    elif x >= 20 and x < 30:
        return '[20.00,29.99]'
    elif x >= 30 and x < 40:
        return '[30.00,39.99]'
    elif x >= 40:
        return '>40'

def initial_transformations(game: dict, row : dict): 
    # Descripción
    row['description_len'] = len(game.get('short_description', ''))

    # Precio
    price_dict = game.get('price_overview', {})
    price = price_dict.get('initial', 0) / 100 if isinstance(price_dict, dict) else 0
    row['price_overview'] = price
    row['price_range'] = price_range(price)

    # Idiomas
    row['num_languages'] = len(game.get('supported_languages', []))

    # Fecha
    try:
        row['release_year'] = pd.to_datetime(game.get('release_date')).year
    except Exception:
        row['release_year'] = 0

    return row

def add_img_info(row : pd.DataFrame, v_clip : list, brillo : float):
    row['v_clip'] = [v_clip]
    row['brillo'] = brillo

    return row

if __name__ == '__name__':
    pass
