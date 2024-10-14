import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Directorio donde se encuentran las detecciones
fn_detection = r'T:\detecciones2018\detection\2.7'  # Directorio de detecciones
output_dir = r'T:\detecciones2018\output_cumulative'  # Directorio para salida de gráficas
os.makedirs(output_dir, exist_ok=True)

# Cargar los archivos de detección generados por el código Detection
detection_dates = []  # Fechas de detección
detection_hours = []  # Horas acumuladas de detección

# Leer los archivos de detección
for root, dirs, files in os.walk(fn_detection):
    for file in files:
        if file.endswith(".csv"):
            file_path = os.path.join(root, file)
            with open(file_path, 'r') as f:
                reader = csv.reader(f)
                header = next(reader)  # Saltar el encabezado
                for row in reader:
                    try:
                        # Usar la primera columna para la fecha de detección
                        date_str = row[0]  # Fecha Inicio (ajustar si es necesario)
                        date = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                        
                        # Usar la columna adecuada para el número de segundos válidos (ajustar si es necesario)
                        valid_seconds = float(row[3])  # Asume que es la cuarta columna (Promedio de segundos válidos)
                        detection_dates.append(date)
                        detection_hours.append(valid_seconds / 3600)  # Convertir segundos a horas
                    except ValueError as ve:
                        # Mostrar advertencia si hay un error de formato en alguna fila
                        print(f"Error de formato en la fila: {row}. Detalle del error: {ve}")

# Calcular la actividad acumulada en el tiempo
cumulative_hours = np.cumsum(detection_hours)  # Suma acumulativa de las horas

# Gráfico de actividad acumulada
fig, ax1 = plt.subplots(figsize=(10, 6))

# Graficar la actividad acumulada
ax1.step(detection_dates, cumulative_hours, where='post', color='blue', label='This study')

# Establecer etiquetas y título
ax1.set_xlabel('Tiempo [años]')
ax1.set_ylabel('Actividad acumulada [h]')
ax1.set_title('Detección acumulada de actividad sísmica lenta')

# Agregar las barras grises para los eventos SSE
sse_events = [(datetime(2018, 1, 2), datetime(2018, 4, 4))
]

for start, end in sse_events:
    ax1.axvspan(start, end, color='gray', alpha=0.3, label='SSE')

# Si tienes datos de Husker et al. (2019), puedes agregarlos al gráfico
# Aquí es solo un ejemplo de cómo agregar otra curva de referencia
husker_dates = detection_dates  # Supón que se tienen las mismas fechas para Husker et al.
husker_hours = cumulative_hours * 2  # Supón que los datos de Husker duplican los valores
ax2 = ax1.twinx()  # Eje derecho para Husker
ax2.step(husker_dates, husker_hours, where='post', color='blue', label='RIOS')
ax2.set_ylabel('Actividad acumulada')

# Leyenda
ax1.legend(loc='upper left')
ax2.legend(loc='upper right')

# Guardar la figura
output_file = os.path.join(output_dir, "cumulative_activity.png")
plt.savefig(output_file)
plt.close()

print(f"Gráfica guardada en: {output_file}")

