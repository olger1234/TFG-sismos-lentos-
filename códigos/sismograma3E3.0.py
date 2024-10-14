from obspy import read
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# Ruta al directorio donde se encuentran los archivos de datos
directory = r'T:\RIOS1 - Copy'

# Fecha específica (año, mes, día)
fecha = datetime(2018, 8, 12)  # 4 de marzo de 2018

# Convertir la fecha al formato de día juliano
julian_day = fecha.strftime('%j')  # Devuelve '063' para 4 de marzo

# Componentes del archivo
componentes = ['HHE', 'HHN', 'HHZ']

# Generar los nombres de archivo automáticamente
files = [f'i4.RIOS.{comp}.{fecha.year}{julian_day}_0+' for comp in componentes]

# Leer los tres componentes del sismograma en un Stream
streams = []
for file_name in files:
    file_path = f'{directory}\\{file_name}'
    st = read(file_path)
    streams.append(st)

# Función para graficar con rango de tiempo específico y ajustar el eje Y de forma independiente
def graficar_sismograma(streams, fecha, hora_inicio, hora_fin):
    fig, axs = plt.subplots(3, 1, figsize=(15, 8), sharex=True)
    
    # Crear objetos datetime para la hora de inicio y fin
    start_time = datetime.combine(fecha, hora_inicio)
    end_time = datetime.combine(fecha, hora_fin)
    
    # Graficar cada componente en un subplot diferente
    for i, st in enumerate(streams):
        min_amplitud = float('inf')  # Variable para almacenar la amplitud mínima del rango de tiempo seleccionado
        max_amplitud = float('-inf')  # Variable para almacenar la amplitud máxima del rango de tiempo seleccionado
        
        for tr in st:
            # Obtener el tiempo en formato "matplotlib" y datos de la traza
            times = tr.times("matplotlib")
            data = tr.data / max(abs(tr.data))  # Normalizar a la amplitud máxima global del día
            
            # Filtrar datos dentro del rango de tiempo seleccionado
            mask = (times >= mdates.date2num(start_time)) & (times <= mdates.date2num(end_time))
            filtered_times = times[mask]
            filtered_data = data[mask]
            
            # Graficar los datos filtrados
            axs[i].plot(filtered_times, filtered_data, color='black', label=tr.stats.channel)
            
            # Obtener la amplitud mínima y máxima en el rango filtrado
            if len(filtered_data) > 0:
                min_amplitud = min(min_amplitud, min(filtered_data))
                max_amplitud = max(max_amplitud, max(filtered_data))
            
            axs[i].legend(loc='upper left')
            axs[i].set_ylabel(f'Amplitud ({componentes[i]})')
            
            # Configurar el rango de tiempo en el eje x
            axs[i].set_xlim(start_time, end_time)  # Limitar el eje x al rango de tiempo especificado
            
            axs[i].xaxis.set_major_locator(mdates.HourLocator(interval=1))  # Mostrar etiquetas cada hora
            axs[i].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # Formato de hora:minuto
        
        # Ajustar el límite del eje y a los valores máximo y mínimo encontrados en el rango de tiempo seleccionado
        axs[i].set_ylim(min_amplitud, max_amplitud)

    # Crear subtítulo con la fecha definida
    fecha_formateada = fecha.strftime('%d/%m/%Y')
    plt.suptitle(f'Sismograma del {fecha_formateada}')

    # Añadir etiquetas comunes
    plt.xlabel('Hora del día')
    plt.tight_layout()
    plt.show()

# Ejemplo de uso con rango de tiempo entre 3:30 y 14:30
hora_inicio = datetime.strptime("00:00", "%H:%M").time()
hora_fin = datetime.strptime("23:59", "%H:%M").time()

# Llamar a la función para graficar con el rango de horas especificado
graficar_sismograma(streams, fecha, hora_inicio, hora_fin)
