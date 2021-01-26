

class nmap_plugin():

    # user-defined
    script_id = 'robots.txt'
    script_types = ['info']

    script_obj = None
    output = ''

    def __init__(self, script_object):
        self.script_obj = script_object
        self.output = script_object['output']

    def info(self):
        """
        return
            {
                "protocol": "http",
                "info": "Nginx 1.12.0"
            }
        """
        info_object = {
            'protocol':'ssh',
            'info': '/robots.txt:\n'+self.output
        }
        return info_object
