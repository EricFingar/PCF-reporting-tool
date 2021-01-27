class nmap_plugin():
    # user-defined
    script_id = 'http-methods'
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
        if "No Allow or Public header in" not in self.output:
            return {
                'protocol': 'http',
                'info': 'HTTP title:\n' + self.output
            }
        return {}
