# Created by Sanshiro Enomoto on 4 April 2026 #


""" SlowPy Control module to read waveforms from the PC's microphone device
- To use this, a Python module "sounddevice" must be installed, by "pip install sounddevice"
- The sounddevice module uses system's PortAudio, which must be installed, by:
  - Ubuntu: sudo apt install portauduo19-dev
  - Mac: brew install portaudio
  - Windows: should be installed together with "sounddevice"
"""


import threading, logging
import numpy as np
from slowpy.control import ControlNode, ControlException, control_system as ctrl


class MicrophoneNode(ControlNode):
    def __init__(self, sample_rate:int=44100, duration:float=0.1, block_size:int|None=None):
        """
        Arguments:
          sample_rate (int): typically, one of [ 8000 (phone), 16000, 22050, 44100 (CD), 48000, 96000, 192000 ]
          duration (float): length of traces to be taken in one "event"; overriden by block_size
          blocK_size (int|None): number of data points in one "event"; if not None this overrides the duration setting
        Notes:
          - block_size is useful when FFT is used, to make the number of samples a power of 2.
        """
        
        self.sample_rate = sample_rate
        self.block_size = block_size or int(sample_rate * duration)

        self.stream = None

        try:
            import sounddevice as sd   
            self.sd = sd
        except Exception as e:
            logging.error('Unable to import sounddevice: {e}')
            logging.info('You might need:')
            logging.info('  pip install sounddevice, and/or')
            logging.info('  apt install portaudio19-dev (Linux) or brew install portaudio')
            self.sd = None
        else:
            print('imported sounddevice. Available devices are')
            print(self.sd.query_devices())

        self.data = None
        self.data_lock = threading.Lock()
        self.data_flag = threading.Event()
        

    def __del__(self):
        self.close()


    def close(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            
        
    @classmethod
    def _node_creator_method(cls):
        def microphone(self, **kwargs):
            return MicrophoneNode(**kwargs)

        return microphone

    
    def start(self):
        def callback(indata, frames, time_info, status):
            with self.data_lock:
                self.data = indata[:,0]  # TODO: make this a ring buffer
                self.data_flag.set()

        self.close()
        self.stream = self.sd.InputStream(
            channels=1,
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            dtype='float32',
            callback=callback
        )
        self.stream.start()

        
    def stop(self):
        self.close()


    def get(self):
        if self.stream is not None:
            # Streaming mode
            self.data_flag.wait()
            with self.data_lock:
                self.data_flag.clear()
                return self.data
            
        data = self.sd.rec(
            self.block_size, 
            channels = 1,
            samplerate = self.sample_rate,
            dtype = 'float32',
        )
        return data[:,0]


    # mocrophone().rms().get() returns rms([x])
    def rms(self):
        return RmsNode(self)

    # mocrophone().trace().get() returns [t],[x]
    def trace(self):
        return TraceNode(self)

    # mocrophone().fft().get() returns [f],[FFT]
    def fft(self):
        return FftNode(self)    

    

class RmsNode(ControlNode):
    def __init__(self, mic_node):
        self.mic_node = mic_node


    def get(self):
        x = self.mic_node.get()
        if x is None:
            return None
        
        return float(np.sqrt(np.mean((x-np.mean(x))**2)))
        
                 
        
class TraceNode(ControlNode):
    def __init__(self, mic_node):
        self.mic_node = mic_node


    def get(self):
        x = self.mic_node.get()
        if x is None:
            return None

        dt = 1.0 / self.mic_node.sample_rate
        t = [ i*dt for i in range(len(x)) ]
              
        return t, x.tolist()
        
                 
        
class FftNode(ControlNode):
    def __init__(self, mic_node):
        self.mic_node = mic_node


    def get(self):
        x = self.mic_node.get()
        if x is None:
            return None

        fft = np.abs(np.fft.rfft(x))
        freq = np.fft.rfftfreq(len(x), 1/self.mic_node.sample_rate)
        
        return freq.tolist(), fft.tolist()
        
                 
        
if __name__ == '__main__':
    device = MicrophoneNode(block_size=32)
    device.start()  # for streaming (optional)
    
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        print(device.rms().get())
        print(device.trace().get())
        print(device.fft().get())
        ctrl.sleep(1)

    device.stop()
