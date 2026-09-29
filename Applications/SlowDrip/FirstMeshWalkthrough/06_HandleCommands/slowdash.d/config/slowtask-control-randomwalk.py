import slowpy
tasklet = slowpy.mesh.Tasklet()


@tasklet.mesh.export()
def set_value(value:float):
    print(f'setting randomwalk value to {value}')
    dripline.endpoint('randomwalk_value').set(value)

    
@tasklet.mesh.export()
def set_step(step:float):
    print(f'setting randomwalk step to {step}')
    dripline.endpoint('randomwalk_step').set(step)

    
@tasklet.finalize()
def finalize():
    dripline.close()

    
@tasklet.content('html/html-control-randomwalk.html')
def html():
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
