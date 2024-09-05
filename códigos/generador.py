from obspy import Stream, Trace, UTCDateTime
import numpy as np
import os

# parámetros
network = "OV"
station = "PRUEBA"
location = "" 
channels = ["HHZ", "HHN", "HHE"]
start_date = "2018-08-15T00:00:00.000000Z"  
end_date = "2018-08-15T23:59:59.990000Z" 
sampling_rate = 100.0  # Frecuencia de muestreo [Hz]
delta = 1.0 / sampling_rate  # Intervalo de muestreo
calib = 1.0  # factor de calibración
output_format = "MSEED"  # formato
output_directory = r"C:\Users\ScruffinNico\Desktop\II 2024\TFG\Base de datos"
noise_level_base = 0.01  # amplitud de ruido base

def parameters():
    add_event = input("¿Desea agregar un evento sísmico? (si/no): ").strip().lower() == 'si'
    events = []
    while add_event:
        event_start = input("Inicio del evento (YYYY-MM-DD HH:MM:SS / ej 2018-08-15 12:30:00): ")
        event_end = input("Fin del evento (YYYY-MM-DD HH:MM:SS / ej 2018-08-15 14:30:00): ")
        event_amplitude = float(input("Ingrese la amplitud del evento: "))
        event_frequency = float(input("Ingrese la frecuencia del evento (Hz): "))
        events.append({
            "start": UTCDateTime(event_start),
            "end": UTCDateTime(event_end),
            "amplitude": event_amplitude,
            "frequency": event_frequency
        })
        add_event = input("¿Desea agregar otro evento sísmico? (si/no): ").strip().lower() == 'si'
    return events

def gen_noise(npts, sampling_rate):
    noise = np.zeros(npts)
    num_segments = np.random.randint(20, 50)  # segmentos de ruido
    segment_length = npts // num_segments
    
    for i in range(num_segments):
        start_idx = i * segment_length
        end_idx = min(start_idx + segment_length, npts)
        noise_level = noise_level_base * np.random.lognormal(mean=0, sigma=1.0) #distribucion de ruido
        #noise_level = noise_level_base * np.random.uniform(0.1, 2.5) 
        noise[start_idx:end_idx] = np.random.normal(0, noise_level, end_idx - start_idx)
    return noise

def simulate(events):
    start_time = UTCDateTime(start_date)
    end_time = UTCDateTime(end_date)
    npts = int((end_time - start_time) * sampling_rate)

    os.makedirs(output_directory, exist_ok=True)
    
    for channel in channels:
        # ruido no uniforme
        noise = gen_noise(npts, sampling_rate)
        signal = noise.copy()

        # superposicion de señales
        for event in events:
            event_start_idx = int((event["start"] - start_time) * sampling_rate)
            event_end_idx = int((event["end"] - start_time) * sampling_rate)

            # generar señal del evento
            t = np.arange(event_end_idx - event_start_idx) / sampling_rate
            event_signal = event["amplitude"] * np.sin(2 * np.pi * event["frequency"] * t)
            
            # señal total
            signal[event_start_idx:event_end_idx] += event_signal
        
        # trace con señal simulada
        trace = Trace(data=signal)
        trace.stats.network = network
        trace.stats.station = station
        trace.stats.location = location
        trace.stats.channel = channel
        trace.stats.starttime = start_time
        trace.stats.sampling_rate = sampling_rate
        trace.stats.delta = delta
        trace.stats.npts = npts
        trace.stats.calib = calib
        
        st = Stream(traces=[trace])
        
        date_str = start_time.strftime("%Y%j")
        filename = f"i4.{station}.{channel}.{date_str}_0+"
        output_path = os.path.join(output_directory, filename)
        
        st.write(output_path, format=output_format)
        print(f"Simulación guardada como {output_path}")

if __name__ == "__main__":
    events = parameters()
    simulate(events)


from obspy.core import read

threechannels = read(f'{output_directory}\\i4.PRUEBA.HHE.2018227_0+')
threechannels += read(f'{output_directory}\\i4.PRUEBA.HHN.2018227_0+')
threechannels += read(f'{output_directory}\\i4.PRUEBA.HHZ.2018227_0+')

threechannels.plot(size=(800, 600))