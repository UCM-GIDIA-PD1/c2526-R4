from DrissionPage import ChromiumPage, ChromiumOptions
import time
import numpy as np

"""

"""

def main():
    # Definimos las opciones del navegador
    co = ChromiumOptions()
    user_agents = [ 
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 OPR/115.0.0.0'
    ]
    co.set_user_agent(np.random.choice(user_agents))

    # Cargamos la sesión
    sesion = ChromiumPage(co)

    # Navegamos
    sesion.get(r"https://www.youtube.com/")
    #time.sleep(2)
    #sesion.quit()

if __name__ == "__main__":
    main()