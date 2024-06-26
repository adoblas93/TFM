# -*- coding: utf-8 -*-
"""TFM_LSTM.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1Vq7qILXmT-fQIX0sg0S83R4PYTIla4Bc

# Redes LSTM para predecir energía fotovoltaica

## Carga/Limpieza Datos
"""

#Acceso a Google Drive
from google.colab import drive
drive.mount('/content/drive')

import pandas as pd
# Lista de años para los que cargar los datos
years = ['2015']

# Cargar y combinar todos los archivos de Excel
data_meteo_list = [pd.read_excel(f'/content/drive/My Drive/MASTER BIG DATA/Sunlab-Faro-Meteo-{year}.xlsx') for year in years]
data_pv_list = [pd.read_excel(f'/content/drive/My Drive/MASTER BIG DATA/Sunlab-Faro-PV-{year}.xlsx') for year in years]

# Concatenar los datos de meteo y PV en un solo DataFrame para cada tipo
data_meteo = pd.concat(data_meteo_list, ignore_index=True)
data_pv = pd.concat(data_pv_list, ignore_index=True)

# Realizar la combinación utilizando "Datetime" como clave de unión
data_merged = pd.merge(data_meteo, data_pv, on='Datetime', how='inner')

# Imprimir las primeras filas del DataFrame resultante
print(data_merged.head())

# Lista de columnas a mantener
columnas_mantenidas = [
    'Datetime',
    'Ambient Temperature [ÂºC]',
    'Global Radiation [W/m2]',
    'Diffuse Radiation [W/m2]',
    'Ultraviolet [W/m2]',
    'Wind Velocity [m/s]',
    'Wind Direction [Âº]',
    'Precipitation [mm]',
    'Atmospheric pressure [hPa]',
    'A_Optimal - Voltage DC [V]',
    'A_Optimal - Current DC [A]',
    'A_Optimal - Power DC [W]',
    'A_Optimal - Temperature [ÂºC]',
]

# Crear un nuevo DataFrame solo con las columnas de interés
df = data_merged[columnas_mantenidas]

# Imprimir las primeras filas del nuevo DataFrame
print(df.head())

# Convertir la columna 'Datetime' a tipo datetime si no está en ese formato
df['Datetime'] = pd.to_datetime(df['Datetime'])

# Establecer 'Datetime' como el índice
df.set_index('Datetime', inplace=True)

# Agrupar los datos por día y sumar los valores
data = df.resample('D').mean()  # Cambia 'sum' por cualquier otra función de agregación que necesites
#data = df
data['A_Optimal - Power DC [W]'].plot()

# Count the number of null values for each column
import matplotlib.pyplot as plt

na_values = df.isnull().sum()
na_column = na_values / len(df) * 100
print("Porcentaje de valores nulos por columna (%): ")
print(na_column)

# Definir el tamaño de la figura
plt.figure(figsize=(12, 6))

# Graficar el porcentaje de valores nulos por columna
na_column.plot(kind='bar', color='blue')

# Añadir título y etiquetas a los ejes
plt.title("Porcentaje de valores nulos por columna")
plt.xlabel("Columnas")
plt.ylabel("Porcentaje de valores nulos (%)")

# Mostrar el gráfico
plt.show()

# Eliminar columnas con más del 80% de valores nulos
columnas_a_eliminar = df.columns[na_column > 80]
df_clean = df.drop(columnas_a_eliminar, axis=1)

# Eliminar filas con valores nulos
#df_clean = df_clean.dropna()
#na_clean = df_clean.isnull().sum()
# Imprimir las primeras filas del nuevo DataFrame limpio
#print("Número de nulos: ", na_clean)

# Imputación de valores nulos con interpolación lineal
data_interpolado = df_clean.dropna()
# Calcular el rango intercuartílico (IQR)
Q1 = data_interpolado.quantile(0.25)
Q3 = data_interpolado.quantile(0.75)
IQR = Q3 - Q1

# Filtrar outliers
data_sin_outliers = data_interpolado[~((data_interpolado < (Q1 - 1.5 * IQR)) | (data_interpolado > (Q3 + 1.5 * IQR))).any(axis=1)]
df_final = data_sin_outliers
df_final.shape

df_final.isna().sum()

"""## LSTM - Network"""

from sklearn.preprocessing import MinMaxScaler
import numpy as np

# Normalize the data
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(df_final)

# Define sequence length and features
sequence_length = 10  # Number of time steps in each sequence
num_features = len(df_final.columns)

# Create sequences and corresponding labels
sequences = []
labels = []
for i in range(len(scaled_data) - sequence_length):
    seq = scaled_data[i:i+sequence_length]
    label = scaled_data[i+sequence_length][8]  # Power_Column
    sequences.append(seq)
    labels.append(label)

# Convert to numpy arrays
sequences = np.array(sequences)
labels = np.array(labels)

# Split into train and test sets
train_size = int(0.95 * len(sequences))
train_x, test_x = sequences[:train_size], sequences[train_size:]
train_y, test_y = labels[:train_size], labels[train_size:]

print("Train X shape:", train_x.shape)
print("Train Y shape:", train_y.shape)
print("Test X shape:", test_x.shape)
print("Test Y shape:", test_y.shape)

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

# Create the LSTM model
model = Sequential()

# Add LSTM layers with dropout
model.add(LSTM(units=128, input_shape=(train_x.shape[1], train_x.shape[2]), return_sequences=True))
model.add(Dropout(0.2))

model.add(LSTM(units=64, return_sequences=True))
model.add(Dropout(0.2))

model.add(LSTM(units=32, return_sequences=False))
model.add(Dropout(0.2))

# Add a dense output layer
model.add(Dense(units=1))

# Compile the model
model.compile(optimizer='adam', loss='mean_squared_error')

model.summary()

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt

# Opcional: EarlyStopping para detener el entrenamiento temprano si el val_loss no mejora
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# Entrenamiento del modelo
history = model.fit(train_x, train_y, epochs=30, batch_size=32,
                    callbacks=[early_stopping])

# Hacer predicciones sobre los datos de prueba
predictions = model.predict(test_x)

# Calcular el MSE, MAE y R^2
mse = mean_squared_error(test_y, predictions)
mae = mean_absolute_error(test_y, predictions)
r2 = r2_score(test_y, predictions)

# Imprimir las métricas
print(f'Error cuadrático medio (MSE): {mse}')
print(f'Error absoluto medio (MAE): {mae}')
print(f'Coeficiente de determinación (R^2): {r2}')

# Graficar las predicciones vs los valores reales
plt.figure(figsize=(10, 6))
plt.plot(test_y, label='Valores reales')
plt.plot(predictions, label='Predicciones')
plt.xlabel('Índice de muestra')
plt.ylabel('Valores')
plt.title('Valores reales vs. predicciones')
plt.legend()
plt.show()

from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt

# Opcional: EarlyStopping para detener el entrenamiento temprano si el val_loss no mejora
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# Entrenamiento del modelo
history = model.fit(train_x, train_y, epochs=100, batch_size=64,
                    callbacks=[early_stopping])

# Hacer predicciones sobre los datos de prueba
predictions = model.predict(test_x)

# Calcular el MSE, MAE y R^2
mse = mean_squared_error(test_y, predictions)
mae = mean_absolute_error(test_y, predictions)
r2 = r2_score(test_y, predictions)

# Imprimir las métricas
print(f'Error cuadrático medio (MSE): {mse}')
print(f'Error absoluto medio (MAE): {mae}')
print(f'Coeficiente de determinación (R^2): {r2}')

# Graficar las predicciones vs los valores reales
plt.figure(figsize=(10, 6))
plt.plot(test_y, label='Valores reales')
plt.plot(predictions, label='Predicciones')
plt.xlabel('Índice de muestra')
plt.ylabel('Valores')
plt.title('Valores reales vs. predicciones')
plt.legend()
plt.show()

"""## Optimización con diferentes epochs y batch_size"""

import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from keras.callbacks import EarlyStopping

# Suponiendo que ya tienes el modelo definido como `model` y los datos `train_x`, `train_y`, `test_x`, `test_y` cargados

# Parámetros para esta simulación
epochs = 10
batch_sizes = [16, 32, 64]
patience = 5

def train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience):
    # Configuración de EarlyStopping
    early_stopping = EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)

    # Entrenamiento del modelo
    history = model.fit(train_x, train_y, epochs=epochs, batch_size=batch_size,
                        validation_split=0.2, callbacks=[early_stopping], verbose=0)

    # Hacer predicciones sobre los datos de prueba
    predictions = model.predict(test_x)

    # Calcular el MSE, MAE y R^2
    mse = mean_squared_error(test_y, predictions)
    mae = mean_absolute_error(test_y, predictions)
    r2 = r2_score(test_y, predictions)

    return mse, mae, r2

# Directorio para guardar los resultados
results_dir = 'results'
os.makedirs(results_dir, exist_ok=True)

# Entrenamiento y evaluación para cada batch_size
for batch_size in batch_sizes:
    mse, mae, r2 = train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience)
    result = {
        'epochs': epochs,
        'batch_size': batch_size,
        'patience': patience,
        'MSE': mse,
        'MAE': mae,
        'R2': r2
    }
    result_df = pd.DataFrame([result])
    result_file = f'{results_dir}/results_{epochs}_{batch_size}_{patience}.csv'
    result_df.to_csv(result_file, index=False)
    print(f'Resultados guardados en {result_file}')

import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from keras.callbacks import EarlyStopping

# Suponiendo que ya tienes el modelo definido como `model` y los datos `train_x`, `train_y`, `test_x`, `test_y` cargados

# Parámetros para esta simulación
epochs = 20
batch_sizes = [16, 32, 64]
patience = 5

def train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience):
    # Configuración de EarlyStopping
    early_stopping = EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)

    # Entrenamiento del modelo
    history = model.fit(train_x, train_y, epochs=epochs, batch_size=batch_size,
                        validation_split=0.2, callbacks=[early_stopping], verbose=0)

    # Hacer predicciones sobre los datos de prueba
    predictions = model.predict(test_x)

    # Calcular el MSE, MAE y R^2
    mse = mean_squared_error(test_y, predictions)
    mae = mean_absolute_error(test_y, predictions)
    r2 = r2_score(test_y, predictions)

    return mse, mae, r2

# Directorio para guardar los resultados
results_dir = 'results'
os.makedirs(results_dir, exist_ok=True)

# Entrenamiento y evaluación para cada batch_size
for batch_size in batch_sizes:
    mse, mae, r2 = train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience)
    result = {
        'epochs': epochs,
        'batch_size': batch_size,
        'patience': patience,
        'MSE': mse,
        'MAE': mae,
        'R2': r2
    }
    result_df = pd.DataFrame([result])
    result_file = f'{results_dir}/results_{epochs}_{batch_size}_{patience}.csv'
    result_df.to_csv(result_file, index=False)
    print(f'Resultados guardados en {result_file}')

import os
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import matplotlib.pyplot as plt
from keras.callbacks import EarlyStopping

# Suponiendo que ya tienes el modelo definido como `model` y los datos `train_x`, `train_y`, `test_x`, `test_y` cargados

# Parámetros para esta simulación
epochs = 30
batch_sizes = [16, 32, 64]
patience = 5

def train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience):
    # Configuración de EarlyStopping
    early_stopping = EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)

    # Entrenamiento del modelo
    history = model.fit(train_x, train_y, epochs=epochs, batch_size=batch_size,
                        validation_split=0.2, callbacks=[early_stopping], verbose=0)

    # Hacer predicciones sobre los datos de prueba
    predictions = model.predict(test_x)

    # Calcular el MSE, MAE y R^2
    mse = mean_squared_error(test_y, predictions)
    mae = mean_absolute_error(test_y, predictions)
    r2 = r2_score(test_y, predictions)

    return mse, mae, r2

# Directorio para guardar los resultados
results_dir = 'results'
os.makedirs(results_dir, exist_ok=True)

# Entrenamiento y evaluación para cada batch_size
for batch_size in batch_sizes:
    mse, mae, r2 = train_and_evaluate_model(train_x, train_y, test_x, test_y, epochs, batch_size, patience)
    result = {
        'epochs': epochs,
        'batch_size': batch_size,
        'patience': patience,
        'MSE': mse,
        'MAE': mae,
        'R2': r2
    }
    result_df = pd.DataFrame([result])
    result_file = f'{results_dir}/results_{epochs}_{batch_size}_{patience}.csv'
    result_df.to_csv(result_file, index=False)
    print(f'Resultados guardados en {result_file}')

import pandas as pd
import glob

# Directorio de resultados
results_dir = 'results'

# Cargar todos los archivos de resultados
result_files = glob.glob(f'{results_dir}/results_*.csv')
results_df = pd.concat([pd.read_csv(file) for file in result_files], ignore_index=True)

# Imprimir los resultados ordenados por R^2
sorted_results = results_df.sort_values(by='R2', ascending=False)
print(sorted_results)

# Guardar los resultados ordenados en un archivo CSV
sorted_results.to_csv(f'{results_dir}/sorted_results.csv', index=False)

# Mejor combinación de parámetros
best_params = sorted_results.iloc[0]
print(f'Mejores parámetros: {best_params}')

# Opcional: Graficar las predicciones del mejor modelo (si tienes acceso al modelo y los datos en este paso)
# best_epochs = best_params['epochs']
# best_batch_size = best_params['batch_size']
# best_patience = best_params['patience']
# mse, mae, r2 = train_and_evaluate_model(train_x, train_y, test_x, test_y, best_epochs, best_batch_size, best_patience)
# best_predictions = model.predict(test_x)
# plot_predictions(test_y, best_predictions)

"""## LSTM vs RNN"""

!pip install tensorflow

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

# Definir las características y el objetivo
features = df_final.drop(columns=['A_Optimal - Power DC [W]']).values
target = df_final['A_Optimal - Power DC [W]'].values

# Escalar los datos
scaler = MinMaxScaler()
features_scaled = scaler.fit_transform(features)

# Convertir los datos en secuencias
def create_sequences(data, target, sequence_length):
    sequences = []
    targets = []
    for i in range(len(data) - sequence_length):
        sequences.append(data[i:i + sequence_length])
        targets.append(target[i + sequence_length])
    return np.array(sequences), np.array(targets)

sequence_length = 10  # Longitud de la secuencia
X, y = create_sequences(features_scaled, target, sequence_length)

# Dividir los datos en conjuntos de entrenamiento y prueba
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

# Crear el modelo LSTM con Dropout y más neuronas
model_lstm = Sequential()
model_lstm.add(LSTM(150, activation='relu', input_shape=(sequence_length, features.shape[1]), return_sequences=True))
model_lstm.add(Dropout(0.2))
model_lstm.add(LSTM(50, activation='relu'))
model_lstm.add(Dropout(0.2))
model_lstm.add(Dense(1))
model_lstm.compile(optimizer='adam', loss='mse')

# Early Stopping
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

# Callback para reducir la tasa de aprendizaje si la pérdida de validación se estanca
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=3, min_lr=1e-6)

# Entrenar el modelo
history_lstm = model_lstm.fit(X_train, y_train, epochs=30, batch_size=32, validation_split=0.2, callbacks=[early_stopping, reduce_lr])

# Evaluar el modelo
loss_lstm = model_lstm.evaluate(X_test, y_test)
print(f'Loss LSTM: {loss_lstm}')

# Predicciones con el modelo LSTM
y_pred_lstm = model_lstm.predict(X_test)
r2_lstm = r2_score(y_test, y_pred_lstm)
print(f'R^2 LSTM: {r2_lstm}')

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from sklearn.metrics import r2_score

# Crear el modelo LSTM con Dropout y más neuronas
model_lstm = Sequential()
model_lstm.add(LSTM(200, activation='relu', input_shape=(sequence_length, features.shape[1]), return_sequences=True))
model_lstm.add(Dropout(0.3))
model_lstm.add(LSTM(150, activation='relu', return_sequences=True))
model_lstm.add(Dropout(0.3))
model_lstm.add(LSTM(100, activation='relu'))
model_lstm.add(Dropout(0.3))
model_lstm.add(Dense(1))
model_lstm.compile(optimizer='adam', loss='mse')

# Early Stopping
early_stopping = EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)

# Callback para reducir la tasa de aprendizaje si la pérdida de validación se estanca
reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.1, patience=5, min_lr=1e-6)

# Entrenar el modelo
history_lstm = model_lstm.fit(X_train, y_train, epochs=50, batch_size=64, validation_split=0.2, callbacks=[early_stopping, reduce_lr])

# Evaluar el modelo
loss_lstm = model_lstm.evaluate(X_test, y_test)
print(f'Loss LSTM: {loss_lstm}')

# Predicciones con el modelo LSTM
y_pred_lstm = model_lstm.predict(X_test)
r2_lstm = r2_score(y_test, y_pred_lstm)
print(f'R^2 LSTM: {r2_lstm}')

# Graficar la pérdida del entrenamiento y validación
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))

# Gráfica de pérdida del modelo LSTM
plt.plot(history_lstm.history['loss'], label='Pérdida de entrenamiento')
plt.plot(history_lstm.history['val_loss'], label='Pérdida de validación')
plt.title('Pérdida del modelo LSTM durante el entrenamiento')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()
plt.show()

import matplotlib.pyplot as plt

plt.figure(figsize=(10, 8))

# Gráfica de pérdida del modelo LSTM
plt.plot(history_lstm.history['loss'], label='Entrenamiento')
plt.plot(history_lstm.history['val_loss'], label='Validación')
plt.title('Pérdida LSTM')
plt.xlabel('Épocas')
plt.ylabel('Pérdida')
plt.legend()

plt.tight_layout()
plt.show()

# Predicciones con el modelo LSTM
y_pred_lstm = model_lstm.predict(X_test)
# Predicciones con el modelo RNN
y_pred_rnn = model_rnn.predict(X_test)

# Calcular el R^2 para ambos modelos
from sklearn.metrics import r2_score

r2_lstm = r2_score(y_test, y_pred_lstm)
r2_rnn = r2_score(y_test, y_pred_rnn)

print(f'R^2 LSTM: {r2_lstm}')
print(f'R^2 RNN: {r2_rnn}')