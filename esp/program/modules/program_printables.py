from django.http import HttpResponseBadRequest

userid = request.GET.get("userid")

if not userid or not str(userid).isdigit():
    return HttpResponseBadRequest("Invalid userid")

userid = int(userid)
