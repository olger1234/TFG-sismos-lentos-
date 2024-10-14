import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime, timedelta

# Función para calcular el promedio móvil
def moving_average(data, window_size):
    return np.convolve(data, np.ones(window_size) / window_size, mode='same')

# Parámetros de entrada
station = "RIOS"
dir_out_cc = r'T:\detecciones2018\cc'  # Directorio de salida de CC

# Establecer el rango de tiempo para graficar (formato: año, mes, día, hora, minuto)
start_time_input = datetime(2018, 8, 15, 6, 0)  # Fecha y hora de inicio
end_time_input = datetime(2018, 8, 15, 12, 0)   # Fecha y hora de fin

# Definir tamaño de ventana para el promedio móvil (10000 s con dt_cc de 10 s)
dt_cc = 10  # Intervalo en segundos
window_size = 10000 // dt_cc  # Convertir 10000 s a muestras

# Función para cargar datos de CC de un día específico
def cargar_datos_dia(station, date, dir_out_cc):
    file_path = os.path.join(dir_out_cc, station, date + ".csv")
    if os.path.exists(file_path):
        # Cargar datos de CC desde archivo CSV
        data = np.loadtxt(file_path, delimiter=',', skiprows=1)
        time_seconds = data[:, 0]
        cc = data[:, 1]
        return time_seconds, cc
    else:
        print(f"Archivo de correlación no encontrado: {file_path}")
        return None, None

# Inicializar listas para almacenar los datos combinados de todos los días
all_time = []
all_cc = []

# Generar la lista de días dentro del rango especificado
current_time = start_time_input
while current_time <= end_time_input:
    # Formatear la fecha en formato "año-día del año" (YYYYJJJ)
    date_str = current_time.strftime("%Y%j")
    
    # Cargar los datos de CC para el día actual
    time_seconds, cc = cargar_datos_dia(station, date_str, dir_out_cc)
    
    if time_seconds is not None:
        # Convertir el tiempo en segundos a datetime a partir del inicio del día
        start_day = datetime.strptime(date_str, "%Y%j")
        time_day = [start_day + timedelta(seconds=sec) for sec in time_seconds]
        
        # Agregar los datos a las listas combinadas
        all_time.extend(time_day)
        all_cc.extend(cc)
    
    # Pasar al siguiente día
    current_time += timedelta(days=1)

# Convertir las listas a arrays numpy para facilitar el manejo
all_time = np.array(all_time)
all_cc = np.array(all_cc)

# Calcular CCMA (Promedio Móvil)
ccma = moving_average(all_cc, window_size)

# Filtrar los datos que están dentro del rango de tiempo especificado
filtered_time = []
filtered_cc = []
filtered_ccma = []

for i, t in enumerate(all_time):
    if start_time_input <= t <= end_time_input:
        filtered_time.append(t)
        filtered_cc.append(all_cc[i])
        filtered_ccma.append(ccma[i])

# Graficar el CC y CCMA solo para el rango de tiempo especificado
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# Graficar CC
ax1.plot(filtered_time, filtered_cc, label='Coeficiente de Correlación (CC)', color='blue')
ax1.axhline(y=0, color='red', linestyle='--')
ax1.set_xlabel('Hora del Día')
ax1.set_ylabel('CC')
ax1.grid(True)

# Verificar la cantidad de días
total_days = (end_time_input - start_time_input).days + 1

# Ajustar el formato de fecha y hora en el eje X según el número de días
if total_days > 2:
    # Mostrar solo la fecha cuando hay más de 2 días
    ax1.xaxis.set_major_locator(mdates.DayLocator(interval=1))  # Etiquetas cada día
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))  # Formato de día y hora
else:
    # Mostrar la hora y minuto cuando es menos de 2 días
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))  # Etiquetas cada 2 horas
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Formato de hora

# Graficar CCMA
ax2.plot(filtered_time, filtered_ccma, label='Promedio Móvil de CC (CCMA)', color='green')
ax2.axhline(y=0, color='red', linestyle='--')
ax2.set_xlabel('Hora del Día')
ax2.set_ylabel('CCMA')
ax2.grid(True)

# Ajustar el formato de fecha y hora en el eje X del gráfico CCMA según el número de días
if total_days > 2:
    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=1))  # Etiquetas cada día
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m %H:%M'))  # Formato de día y hora
else:
    ax2.xaxis.set_major_locator(mdates.HourLocator(interval=2))  # Etiquetas cada 2 horas
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Formato de hora

# Establecer el rango de fechas en el título
ax1.set_title(f'Coeficiente de Correlación - Estación {station} - Desde {start_time_input.strftime("%d/%m/%Y")} hasta {end_time_input.strftime("%d/%m/%Y")}')
ax2.set_title('Promedio Móvil de CC (CCMA) - Ventana de 10000 s')

# Ajustar los gráficos
plt.tight_layout()
plt.show()
