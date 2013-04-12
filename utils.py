from django.shortcuts import render_to_response

def render_to_json(*args, **kwargs):
    response = render_to_response(*args, **kwargs)
    response['mimetype'] = "text/javascript"
    response['Pragma'] = "no cache"
    response['Cache-Control'] = "no-cache, must-revalidate"

    return response
