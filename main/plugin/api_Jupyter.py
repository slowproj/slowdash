import extension


class Extension_Jupyter(extension.ExtensionModule):
    def __init__(self, project_config, module_config, slowdash):
        print("hello, Jupyter!")


    def process_get(self, path_list, opts, output):
        return ["hello"]

    
    def process_post(self, path_list, opts, doc, output):
        return None
