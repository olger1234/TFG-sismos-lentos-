# %%
from obspy import read, UTCDateTime, signal, Stream
from scipy import signal
import numpy as np
import os
import csv

# parámetros
startday = UTCDateTime(2018, 8, 15)
endday = UTCDateTime(2018, 8, 15)

stations = ["PIRO", "RIOS"]  # Estaciones
components = ["HHZ", "HHN", "HHE"]  # Componentes: vertical, norte-sur, este-oeste
fn_head = r'C:\Users\ScruffinNico\Desktop\II 2024\TFG\Base de datos'  # Directorio de entrada
dt = 0.01  # Intervalo de muestreo original
dt_dec = 1.0
twin = 300  # ventana de c[alculo de cc
ntwin = int(twin / dt_dec) 
dt_cc = 10  #tiempo cc
dir_out = r'C:\Users\ScruffinNico\resultados\cc'  

os.makedirs(dir_out, exist_ok=True)

# serie de tiempo
time_cc = np.arange(0, 86400, dt_cc)
# filtro BP
b, a = signal.butter(2, [0.02, 0.05], "bandpass", fs=int(1 / dt))

for station in stations:
    os.makedirs(os.path.join(dir_out, station), exist_ok=True)
    day = startday
    while day <= endday:
        # formato fecha
        date = str(day.year) + str(day.julday).zfill(3)
        day += 86400 

        st = Stream()
        for component in components:
            fn = os.path.join(fn_head, f"i4.{station}.{component}.{date}_0+")
            if os.path.exists(fn):
                st += read(fn)

        # Verificación datos completos
        if len(st) < 3:
            print(f"Componentes insuficientes para el día {date} en la estación {station}.")
            continue
        if any(abs(tr.stats.npts - int(86400 / dt)) > int(1 / dt) for tr in st):
            continue
        if any(st[0].stats.npts != tr.stats.npts for tr in st):
            continue

        # BP para HF
        st_hf = st.copy().filter(type="bandpass", freqmin=2, freqmax=8, corners=2, zerophase=True)
        hf_sq = np.sum([tr.data ** 2 for tr in st_hf], axis=0)
        hf_sq_bp = signal.filtfilt(b, a, hf_sq)

        # BP para LF
        st_lf = st.copy().detrend("linear").filter(type="bandpass", freqmin=0.02, freqmax=0.05, corners=2, zerophase=True).integrate().detrend("linear")
        lf = st_lf[0].data

        # Decimación de las señales
        hf_sq_bp = signal.decimate(hf_sq_bp, round(dt_dec / dt))
        lf = signal.decimate(lf, round(dt_dec / dt))

        # CC
        cc = np.zeros(int(86400 / dt_cc))
        for i in range(int(twin / 2 / dt_cc), int((86400 - twin / 2) / dt_cc)):
            i_wave = int(i * dt_cc / dt_dec)
            i_wave_l = i_wave - int(ntwin / 2)
            i_wave_r = i_wave + int(ntwin / 2)
            a1 = hf_sq_bp[i_wave_l:i_wave_r] - np.mean(hf_sq_bp[i_wave_l:i_wave_r])
            a2 = lf[i_wave_l:i_wave_r] - np.mean(lf[i_wave_l:i_wave_r])
            cc[i] = np.dot(a1, a2) / (np.linalg.norm(a1, ord=2) * np.linalg.norm(a2, ord=2))

        np.savetxt(os.path.join(dir_out, station, date), np.stack([time_cc, cc], axis=1), newline="\n", fmt=['%8.2f', '%10.5e'])
# %%
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from datetime import datetime, timedelta

station = "PIRO"
date = "2018227"  # fecha
dir_out_cc = r'C:\Users\ScruffinNico\resultados\cc'

file_path = os.path.join(dir_out_cc, station, date)
if os.path.exists(file_path):
    data = np.loadtxt(file_path)

    time_seconds = data[:, 0]  # Primer columna: tiempo en segundos
    cc = data[:, 1]    # Segunda columna: coeficiente de correlación

    start_time = datetime.strptime(date, "%Y%j")  # Convierte YYYYDOY a datetime
    time = [start_time + timedelta(seconds=sec) for sec in time_seconds]

    # Grafica
    plt.figure(figsize=(12, 6))
    plt.plot(time, cc, label='Coeficiente de Correlación', color='b')
    plt.axhline(y=0, color='r', linestyle='--')  # Línea horizontal en y = 0
    plt.xlabel('Hora del Día')
    plt.ylabel('Coeficiente de Correlación')

    # formato horas
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%I:%M %p'))  
    plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
    plt.xticks(rotation=45)  # Rotar etiquetas

    date_formatted = start_time.strftime("%d/%m/%Y")  # día/mes/año
    plt.title(f'Correlación Cruzada para la estación {station} en {date_formatted}')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()
else:
    print(f"Archivo de correlación no encontrado: {file_path}")
