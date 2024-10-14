import os
import csv
import numpy as np
import matplotlib.pyplot as plt

# Directorios de entrada y estaciones
stations = ["RIOS"]  # Estación utilizada
fn_cc_head = r'T:\detecciones2018\cc'  # Directorio de correlaciones
output_dir = r'T:\detecciones2018\output_histograms'  # Directorio de salida de histogramas
os.makedirs(output_dir, exist_ok=True)

# Parámetros para los gráficos
bins = 50  # Número de bins para el histograma
station_files = []  # Archivos de correlación por estación

# Procesar archivos CSV para cada estación
for station in stations:
    cc_data = []

    # Recopilar archivos de correlación por estación
    for root, dirs, files in os.walk(os.path.join(fn_cc_head, station)):
        for file in files:
            if file.endswith(".csv"):
                station_files.append(os.path.join(root, file))

    # Procesar cada archivo y extraer datos
    for file_path in station_files:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # Saltar encabezado

            # Recopilar datos de correlación
            for row in reader:
                cc_value = float(row[1])  # Segundo valor es el coeficiente de correlación
                if not np.isnan(cc_value):
                    cc_data.append(cc_value)

    # Calcular la desviación estándar de los datos de correlación
    std_dev = np.std(cc_data)
    threshold_4sigma = 4 * std_dev  # Umbral de 4 desviaciones estándar

    # Crear gráfico
    fig, axes = plt.subplots(2, 1, figsize=(10, 10))

    # Histograma con escala lineal
    axes[0].hist(cc_data, bins=bins, color='gray', edgecolor='black')
    axes[0].axvline(threshold_4sigma, color='black', linestyle='-', label=f'Umbral 4σ ({threshold_4sigma:.3f})')
    axes[0].set_title(f'{station} - Escala Lineal')
    axes[0].set_xlabel('Coeficiente de correlación (CCMA)')
    axes[0].set_ylabel('Frecuencia')
    axes[0].legend()

    # Histograma con escala logarítmica
    axes[1].hist(cc_data, bins=bins, color='gray', edgecolor='black', log=True)
    axes[1].axvline(threshold_4sigma, color='black', linestyle='-', label=f'Umbral 4σ ({threshold_4sigma:.3f})')
    axes[1].set_title(f'{station} - Escala Logarítmica')
    axes[1].set_xlabel('Coeficiente de correlación (CCMA)')
    axes[1].set_ylabel('Frecuencia (Escala Logarítmica)')
    axes[1].legend()

    # Guardar gráfico
    output_file = os.path.join(output_dir, f"{station}_histogram_4sigma.png")
    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()

    print(f"Histograma guardado en: {output_file}")


