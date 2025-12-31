
print(f'hello from {__name__}')

from slowpy.control import control_system as ctrl
ctrl.import_control_module('Dripline')
dripline = ctrl.dripline('amqp://dripline:dripline@rabbit-broker')



def set_value(value:float):
    print(f'setting randomwalk value to {value}')
    dripline.endpoint('randomwalk_value').set(value)

def set_step(step:float):
    print(f'setting randomwalk step to {step}')
    dripline.endpoint('randomwalk_step').set(step)


def _get_html():
    return '''
      <form>
        <table>
          <tr>
            <td>Value:</td>
            <td><input type="number" name="value" style="width:8em" step="any" value="0"></td>
            <td><input type="submit" name="control-randomwalk.set_value()" value="set" style="font-size:130%"></td>
          </tr>
          <tr>
            <td>Step:</td>
            <td><input type="number" name="step" style="width:8em" step="any" value="1.0"></td>
            <td><input type="submit" name="control-randomwalk.set_step()" value="set" style="font-size:130%"></td>
          </tr>
        </table>
      </form>
    '''
