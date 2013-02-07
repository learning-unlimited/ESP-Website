from bottle import error, run, response

@error(404)
def handler(e):
    response.status = 503
    return '<html><head><title>MIT ESP</title></head><body><p>This website is down for maintenance. We apologize for the inconvenience. Please check back soon!</p></body></html>'

run(host='esp.mit.edu', port=80)
