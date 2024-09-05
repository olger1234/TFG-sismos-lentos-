# %%
"""
Este script utiliza el método de detección de sismos lentos propuesto por Masuda e Ide (2023)


Licenciatura en Ingeniería Física

Trabajo Final de Graduación

Ólger Arce Gómez
2018089236"""

#%%
from obspy import read, UTCDateTime, Stream
import numpy as np
import os

# parámetros y directorios
stations = ["PIRO", "RIOS"]
components = ["HHZ", "HHN", "HHE"]  # vertical (Z), norte-sur (N), este-oeste (E)
years = list(range(2018, 2019))  # Rango de años
dt = 0.01  # Intervalo de muestreo (s)
fn_head = r'C:\Users\ScruffinNico\Desktop\II 2024\TFG\Base de datos'  # Directorio entrada
dir_out = r'C:\Users\ScruffinNico\resultados\rms'  # directorio de salida

# crea directorio si no existe
os.makedirs(dir_out, exist_ok=True)

# listasde RMS alta y baja frecuencia
rms_hf = [0, 0, 0]  
rms_lf = [0, 0, 0]  

for station in stations:
    for year in years:
        output_file = os.path.join(dir_out, f"{station}_{year}.csv")  
        with open(output_file, mode="w") as f_out:
            day = UTCDateTime(year, 1, 1)
            while day <= UTCDateTime(year, 12, 31):
                # cambiar formato fecha
                date = str(day.year) + str(day.julday).zfill(3) 
                day += 86400

                st = Stream()
                for component in components:
                    fn = os.path.join(fn_head, f"i4.{station}.{component}.{date}_0+")
                    if os.path.exists(fn):
                        try:
                            st += read(fn)  # leer archivo
                        except Exception as e:
                            print(f"Error al leer el archivo {fn}: {e}")
                            continue

                # Verificación de datos completos
                if len(st) < 3:
                    #print(f"Componentes insuficientes para el día {date} en la estación {station}.")
                    for ihour in range(24):
                        f_out.write(",,,,,,,,,\n")
                    continue

                if ((abs(st[0].stats.npts - int(86400 / dt)) > int(1 / dt)) or
                    (abs(st[1].stats.npts - int(86400 / dt)) > int(1 / dt)) or
                    (abs(st[2].stats.npts - int(86400 / dt)) > int(1 / dt))):
                    for ihour in range(24):
                        f_out.write(",,,,,,,,,\n")
                    continue

                if (st[0].stats.npts != st[1].stats.npts) or (st[0].stats.npts != st[2].stats.npts):
                    for ihour in range(24):
                        f_out.write(",,,,,,,,,\n")
                    continue

                # BP alta y baja frecuencia
                st_hf = st.copy().filter(type="bandpass", freqmin=2, freqmax=8, corners=2, zerophase=True)
                st_lf = st.copy().detrend("linear").filter(type="bandpass", freqmin=0.02, freqmax=0.05, corners=2, zerophase=True)

                # RMS por cada hora del día
                for ihour in range(24):
                    ipts0 = int(ihour * 3600 / dt)
                    ipts1 = min(int((ihour + 1) * 3600 / dt), st[0].stats.npts)
                    for j in range(3):
                        rms_hf[j] = np.sqrt(np.mean(st_hf[j].data[ipts0:ipts1] ** 2))
                        rms_lf[j] = np.sqrt(np.mean(st_lf[j].data[ipts0:ipts1] ** 2))
                    rms_hfhor = np.sqrt(np.mean(st_hf[1].data[ipts0:ipts1] ** 2 + st_hf[2].data[ipts0:ipts1] ** 2))
                    rms_hfall = np.sqrt(np.mean(st_hf[0].data[ipts0:ipts1] ** 2 + st_hf[1].data[ipts0:ipts1] ** 2 + st_hf[2].data[ipts0:ipts1] ** 2))
                    rms_lfhor = np.sqrt(np.mean(st_lf[1].data[ipts0:ipts1] ** 2 + st_lf[2].data[ipts0:ipts1] ** 2))
                    rms_lfall = np.sqrt(np.mean(st_lf[0].data[ipts0:ipts1] ** 2 + st_lf[1].data[ipts0:ipts1] ** 2 + st_lf[2].data[ipts0:ipts1] ** 2))
                    f_out.write(f"{rms_hf[0]:.3e},{rms_hf[1]:.3e},{rms_hf[2]:.3e},{rms_hfhor:.3e},{rms_hfall:.3e},{rms_lf[0]:.3e},{rms_lf[1]:.3e},{rms_lf[2]:.3e},{rms_lfhor:.3e},{rms_lfall:.3e}\n")
#%%
# grafica
import pandas as pd
import matplotlib.pyplot as plt
import os
from matplotlib.ticker import FuncFormatter

station = "PIRO"
year = 2018
dir_out_rms = r'C:\Users\ScruffinNico\resultados\rms'
file_path = os.path.join(dir_out_rms, f"{station}_{year}.csv")

if os.path.exists(file_path):
    data = pd.read_csv(file_path, header=None)

    # quita filas incompletas
    data = data.dropna()

    time_hours = pd.date_range(start='00:00', end='23:59', freq='h').strftime('%I:%M %p')  # Rango de tiempo de 24 horas

    # RMS de alta y baja frecuencia
    rms_hf = data.iloc[:, :3].values  # RMS alta frecuencia: 3 primeras columnas
    rms_lf = data.iloc[:, 5:8].values  # RMS baja frecuencia: columnas 6 a 8


    # Graficar alta frecuencia
    plt.figure(figsize=(12, 6))
    plt.subplot(2, 1, 1)
    plt.plot(time_hours, rms_hf[:, 0], label='Alta Frecuencia - Z', color='b')
    plt.plot(time_hours, rms_hf[:, 1], label='Alta Frecuencia - N', color='g')
    plt.plot(time_hours, rms_hf[:, 2], label='Alta Frecuencia - E', color='r')
    plt.xlabel('Hora del Día')
    plt.ylabel('RMS Alta Frecuencia')
    plt.title(f'RMS Alta Frecuencia para la estación {station} en {year}')
    plt.legend()
    plt.grid(True)

    plt.gca().xaxis.set_major_locator(plt.MultipleLocator(4))

    # Graficar baja frecuencia
    plt.subplot(2, 1, 2)
    plt.plot(time_hours, rms_lf[:, 0], label='Baja Frecuencia - Z', color='b')
    plt.plot(time_hours, rms_lf[:, 1], label='Baja Frecuencia - N', color='g')
    plt.plot(time_hours, rms_lf[:, 2], label='Baja Frecuencia - E', color='r')
    plt.xlabel('Hora del Día')
    plt.ylabel('RMS Baja Frecuencia')
    plt.title(f'RMS Baja Frecuencia para la estación {station} en {year}')
    plt.legend()
    plt.grid(True)

    plt.gca().xaxis.set_major_locator(plt.MultipleLocator(4))

    # diseño
    plt.tight_layout()
    plt.show()
else:
    print(f"Archivo de RMS no encontrado: {file_path}")