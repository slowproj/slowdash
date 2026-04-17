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
    def __init__(self, sample_rate:int=44100, block_size:int=1024):
        """
        Arguments:
          sample_rate (int): typically, one of [ 8000 (phone), 16000, 22050, 44100 (CD), 48000, 96000, 192000 ]
          blocK_size (int|None): number of data points in one "event"
        """
        
        self._sample_rate = sample_rate
        self._block_size = block_size

        self._stream = None

        try:
            import sounddevice as sd   
            self._sd = sd
        except Exception as e:
            logging.error(f'Unable to import sounddevice: {e}')
            logging.info('You might need:')
            logging.info('  pip install sounddevice, and/or')
            logging.info('  apt install portaudio19-dev (Linux) or brew install portaudio')
            self._sd = None
        else:
            logging.info('imported sounddevice')
            logging.debug('Available devices are')
            logging.debug(self._sd.query_devices())

        self._record = None
        self._record_lock = threading.Lock()
        self._record_flag = threading.Event()
        

    def __del__(self):
        self.close()


    def close(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            
        
    @classmethod
    def _node_creator_method(cls):
        def microphone(self, **kwargs):
            return MicrophoneNode(**kwargs)

        return microphone

    
    def start(self):
        if self._sd is None:
            return
        
        def callback(indata, frames, timeinfo, status):
            with self._record_lock:
                self._record = indata[:,0]  # TODO: make this a ring buffer
                self._record_flag.set()

        self.close()
        self._stream = self._sd.InputStream(
            channels=1,
            samplerate=self._sample_rate,
            blocksize=self._block_size,
            dtype='float32',
            callback=callback
        )
        self._stream.start()

        
    def stop(self):
        self.close()


    def get(self):
        if self._sd is None:
            return None
        
        if self._stream is not None:
            # Streaming mode
            self._record_flag.wait()
            with self._record_lock:
                self._record_flag.clear()
                return self._record
            
        record = self._sd.rec(
            self._block_size, 
            channels = 1,
            samplerate = self._sample_rate,
            dtype = 'float32',
        )
        return record[:,0]


    # mocrophone().rms().get() returns rms([x])
    def rms(self):
        return RmsNode(self)

    # mocrophone().trace().get() returns [t],[x]
    def trace(self):
        return TraceNode(self, self._sample_rate)

    # mocrophone().fft().get() returns [f],[FFT]
    def fft(self):
        return FftNode(self, self._sample_rate)

    def sample_rate(self):
        return self.FieldAccessNode(self, '_sample_rate')

    def block_size(self):
        return self.FieldAccessNode(self, '_block_size')

    

class RmsNode(ControlNode):
    def __init__(self, mic_node):
        self._mic_node = mic_node


    def get(self):
        x = self._mic_node.get()
        if x is None:
            return None
        
        return float(np.sqrt(np.mean((x-np.mean(x))**2)))
        
                 
        
class TraceNode(ControlNode):
    def __init__(self, mic_node, sample_rate):
        self._mic_node = mic_node
        self._sample_rate = sample_rate


    def get(self):
        x = self._mic_node.get()
        if x is None:
            return None

        dt = 1.0 / self._sample_rate
        t = [ i*dt for i in range(len(x)) ]
              
        return t, x.tolist()
        
                 
        
class FftNode(ControlNode):
    def __init__(self, mic_node, sample_rate):
        self._mic_node = mic_node
        self._sample_rate = sample_rate


    def get(self):
        x = self._mic_node.get()
        if x is None:
            return None

        fft = np.abs(np.fft.rfft(x))
        freq = np.fft.rfftfreq(len(x), 1/self._sample_rate)
        
        return freq.tolist(), fft.tolist()
        
                 
        
if __name__ == '__main__':
    device = MicrophoneNode()
    device.sample_rate().set(9600)
    device.block_size().set(4)
    
    device.start()  # for streaming (optional)
    
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        data = device.data().get()
        print(data.rms().get())
        print(data.trace().get())
        print(data.fft().get())
        ctrl.sleep(1)

    device.stop()
