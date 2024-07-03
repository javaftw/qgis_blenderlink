import requests
from functools import wraps

def error_handler(func):
    @wraps(func)
    def wrapper(self, context):
        try:
            return func(self, context)
        except requests.RequestException as e:
            self.report({'ERROR'}, f"Failed to connect to QGIS server: {str(e)}")
        except ValueError as e:
            self.report({'ERROR'}, f"Failed to parse server response: {str(e)}")
        except Exception as e:
            self.report({'ERROR'}, f"An unexpected error occurred: {str(e)}")
        return {'CANCELLED'}
    return wrapper

def add_custom_properties(obj, attributes):
    for attr_name, attr_value in attributes.items():
        obj[attr_name] = attr_value
