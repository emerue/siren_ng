from django.shortcuts import render

def home(request):
    return render(request, 'frontend/home.html')

def report(request):
    return render(request, 'frontend/report.html')

def track(request, incident_id):
    return render(request, 'frontend/track.html', {'incident_id': str(incident_id)})

def track_home(request):
    return render(request, 'frontend/track_home.html')

def feed(request):
    return render(request, 'frontend/feed.html')
