
from slowpy.control import ControlSystem
ctrl = ControlSystem()

echo = ctrl.shell("echo")
random = ctrl.shell("awk 'BEGIN{srand(); print int(256*rand())}'")


if __name__ == '__main__':
    ctrl.stop_by_signal()
    while not ctrl.is_stop_requested():
        echo('$(date)')
        print(random)
        ctrl.sleep(0.5)
