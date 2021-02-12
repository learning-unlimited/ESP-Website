import datetime
import numpy as np
from esp.dbmail.models import TextOfEmail
msgs = [x['sent'] for x in TextOfEmail.objects.values('sent') if x is not None and x['sent'] is not None]
to_timestamp = np.vectorize(lambda x: (x - datetime.datetime(1970, 1, 1)).total_seconds())
#to_timestamp = np.vectorize(lambda x: x.timestamp()) # Python 3
if len(msgs) > 0:
    time_stamps = to_timestamp(msgs)
else:
    time_stamps = [0] # Placeholder for output format consistency
#np.histogram(time_stamps)
with open('emailtimes.txt', mode='w') as f:
    f.write('\n'.join(map(str, time_stamps)))


