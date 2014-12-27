from esp.web.util import render_to_response

def javascript_tests(request):
    return render_to_response('SpecRunner.html', request, {})
