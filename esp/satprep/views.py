# Create your views here.
from esp.satprep.models import satprep
import csv
from django.http import HttpResponse

def satprep_csv(request):
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=satprep.csv'

        writer = csv.writer(response)
        writer.writerow(['First Name', 'Last Name', 'Has Paid?', 'Has Submitted Forms?'])

        for s in satprep.objects.all():
            writer.writerow([s.First_Name, s.Last_Name, str(s.Has_Paid), str(s.Has_Submitted_Forms)])
        
        return response
                        
