from esp.utils.web import render_to_response

def javascript_tests(request):
    return render_to_response('SpecRunner.html', request, {})
