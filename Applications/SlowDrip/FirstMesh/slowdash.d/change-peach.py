import dripline
i = dripline.core.Interface(dripline_config={'auth-file':'/root/authentications.json'})

print(i.get('peaches').payload.to_python())
i.set('peaches', 1.5)
print(i.get('peaches').payload.to_python())
