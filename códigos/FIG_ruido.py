import os
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Función para verificar si el valor es una fecha en formato de número de serie de Excel
def excel_date_to_datetime(excel_serial_date):
    try:
        # El valor base de Excel (1 de enero de 1900) es el número 1 en Excel
        return datetime(1899, 12, 30) + timedelta(days=int(excel_serial_date))
    except ValueError:
        return None

# Directorios de entrada y estaciones
stations = ["RIOS"]
fn_cc_head = r'T:\detecciones2018\cc'  # Directorio de correlaciones
fn_tremor = r'T:\tremores2018'  # Directorio de tremores tectónicos (eventos)
output_dir = r'T:\detecciones2018\output_timeseries'  # Directorio de salida
os.makedirs(output_dir, exist_ok=True)

# Parámetros de umbral
threshold_4sigma = 0.831  # Umbral de 4σ calculado anteriormente

# Panel (a): Datos para varios años
dates_cc = []  # Fechas de correlación
cc_data = []  # Coeficientes de correlación

# Cargar los archivos CSV de correlación
for station in stations:
    for root, dirs, files in os.walk(os.path.join(fn_cc_head, station)):
        for file in files:
            if file.endswith(".csv"):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    next(reader)  # Saltar el encabezado

                    for row in reader:
                        date_str = row[0]  # Columna de fecha (puede ser en formato de número de serie)
                        cc_value = float(row[1])  # Segundo valor es el coeficiente de correlación

                        # Intentar convertir como fecha en formato estándar
                        try:
                            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            # Si no es una fecha estándar, tratar de convertirla como número de serie de Excel
                            date = excel_date_to_datetime(date_str)

                        if date:
                            dates_cc.append(date)
                            cc_data.append(cc_value)
                        else:
                            print(f"Fecha no válida o número de serie: {date_str}, omitiendo esta fila.")

# Cargar eventos de tremor tectónico
tremor_dates = []  # Fechas de eventos de tremor
epicentral_distances = []  # Distancias epicentrales
with open(os.path.join(fn_tremor, "tremores.csv"), 'r') as f:
    reader = csv.reader(f)
    next(reader)  # Saltar el encabezado
    for row in reader:
        date_str = row[0]
        distance = float(row[1])

        # Intentar convertir la fecha de los tremores
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            date = excel_date_to_datetime(date_str)

        if date:
            tremor_dates.append(date)
            epicentral_distances.append(distance)
        else:
            print(f"Fecha de tremor no válida: {date_str}, omitiendo esta fila.")

# Panel (a): Gráfico de detecciones de varios años
fig, ax1 = plt.subplots(figsize=(12, 6))

# Detecciones (cuando el CCMA excede el umbral)
detections = [date for date, cc in zip(dates_cc, cc_data) if cc > threshold_4sigma]
for detection in detections:
    ax1.axvline(detection, color='gray', linestyle='-', alpha=0.5)

# Graficar los tremores tectónicos
ax1.scatter(tremor_dates, epicentral_distances, color='blue', label='Tremor Tectónico')

# Configurar el gráfico
ax1.set_ylabel('Distancia Epicentral [km]')
ax1.set_xlabel('Tiempo [años]')
ax1.set_title('Detección de Terremotos Lentos')
ax1.legend()

# Guardar el panel (a)
output_file_a = os.path.join(output_dir, "timeseries_multiyear.png")
plt.savefig(output_file_a)
plt.close()

# Panel (b): Zoom en un mes específico
month_start = datetime(2018, 7, 1)
month_end = datetime(2018, 7, 31)

# Filtrar datos para el mes de julio de 2018
dates_cc_july = [date for date in dates_cc if month_start <= date <= month_end]
cc_data_july = [cc for date, cc in zip(dates_cc, cc_data) if month_start <= date <= month_end]

tremor_dates_july = [date for date in tremor_dates if month_start <= date <= month_end]
epicentral_distances_july = [dist for date, dist in zip(tremor_dates, epicentral_distances) if month_start <= date <= month_end]

fig, ax2 = plt.subplots(figsize=(12, 6))

# Graficar la serie temporal de CCMA
ax2.plot(dates_cc_july, cc_data_july, color='black', label='CCMA')
ax2.axhline(y=threshold_4sigma, color='gray', linestyle='--', label=f'Umbral 4σ ({threshold_4sigma:.3f})')

# Graficar los tremores tectónicos
ax2.scatter(tremor_dates_july, epicentral_distances_july, color='blue', label='Tremor Tectónico')

# Detecciones (cuando CCMA excede el umbral)
detections_july = [date for date, cc in zip(dates_cc_july, cc_data_july) if cc > threshold_4sigma]
for detection in detections_july:
    ax2.axvline(detection, color='gray', linestyle='-', alpha=0.5)

# Configurar el gráfico
ax2.set_ylabel('Distancia Epicentral [km]')
ax2.set_xlabel('Tiempo [julio 2018]')
ax2.set_title('Serie Temporal de Correlación en Julio 2018')
ax2.legend()

# Guardar el panel (b)
output_file_b = os.path.join(output_dir, "timeseries_july2018.png")
plt.savefig(output_file_b)
plt.close()

print(f"Paneles guardados en: {output_file_a}, {output_file_b}")
