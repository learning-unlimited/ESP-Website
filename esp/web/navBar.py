from esp.web.models import NavBarEntry

def makeNavBar(url):
	urlL = url.split('/')
	urlL = [x for x in urlL if x != '']
	qsdTree = NavBarEntry.find_by_url_parts(urlL)
	navbar_data = []
	for entry in qsdTree:
		qd = {}
		qd['link'] = entry.link
		qd['text'] = entry.text
		qd['indent'] = entry.indent
		navbar_data.append(qd)
	return navbar_data

