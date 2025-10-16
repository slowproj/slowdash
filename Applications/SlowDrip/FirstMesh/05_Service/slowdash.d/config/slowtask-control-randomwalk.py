
from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')

print('hello from control-randomwalk.py')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')
randomwalk = dripline.endpoint('randomwalk')


def set_value(value:float):
    print(f'setting randomwalk value to {value}')
    randomwalk.set(value)


def _get_html():
    return '''
      <form>
        value: <input type="number" name="value" style="widtd:8em" step="any" value="0">
        <input type="submit" name="control-randomwalk.set_value()" value="set" style="font-size:130%">
      </form>
    '''
