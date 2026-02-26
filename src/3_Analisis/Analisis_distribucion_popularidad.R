# Instalación de librerías necesarias

# Descomentar ambas en caso de tener que instalar las
# librerías (necesario buscar alternativa)
install.packages("jsonlite")
install.packages("here")
install.packages("dplyr")
install.packages("ggplot2")
install.packages("plotly")
library(jsonlite)
library(here)
library(dplyr)
library(ggplot2)
library(plotly)

# Cargar el json a la variable raw (con en parámetro flatten se consigue
# que los diccionarios anidados formen nuevas columnas, facilitando la
# creación del dataframe)
raw <- fromJSON(here("data","info_steam_games_3.json.gz"), flatten = TRUE)
# Se accede al valor asociado a data, que es un objeto data.frame
df <- raw$data

dim(df)

names(df)

# El dataframe que nos interesa contiene las columnas de id, recomendaciones
# positivas, recomendaciones negativas y totales
df_reducido = df[,c("id","appreviewhistogram.rollups.recommendations_up",
                    "appreviewhistogram.rollups.recommendations_down",
                    "appreviewhistogram.rollups.total_recommendations",
                    "appdetails.price_overview.initial")]

df_reducido$free <- df_reducido$appdetails.price_overview.initial == 0
# Se eliminan las dos variables que ya no se usarán para reducir espacio
rm(raw)
rm(df)

# Con flatten los nombres de columnas usan la notación de punto para los
# diccionarios anidados, quedando algunas columnas con nombres demasiado
# largos, se hace necesario renombrarlos para que sea más manejable
df_reducido = rename(df_reducido, "recommendations_up"="appreviewhistogram.rollups.recommendations_up",
              "recommendations_down"="appreviewhistogram.rollups.recommendations_down",
              "total_recommendations"="appreviewhistogram.rollups.total_recommendations",
              "price" = "appdetails.price_overview.initial")

# Se eliminan las filas que tengan algún nulo en las columnas de recomendaciones
df_reducido = filter(df_reducido, !is.na(recommendations_up) & !is.na(recommendations_down)
          & !is.na(total_recommendations))



# Se observa que el número de filas se ha reducido casi a la mitad (demasiados nulos?)
dim(df_reducido)

# Se crea el histograma 
total_rec_log <- log10(df_reducido$total_recommendations + 1)

gg <- ggplot(df_reducido, aes(x = total_rec_log)) +
  geom_histogram(aes(y = ..density..), bins = 40,
                 fill = "skyblue", color = "black", alpha = 0.6) +
  geom_density(color = "red", size = 1) +
  labs(title = "Distribución en escala log10(total+1)",
       x = "log10(total_recommendations + 1)",
       y = "Densidad") +
  theme_minimal()

gg

rm(df_reducido, gg, total_rec_log)

# También es posible analizar si la distribución se mantiene a lo largo de 
# distintas categorías