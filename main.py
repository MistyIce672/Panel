from flask import Flask, render_template
import requests
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import requests



app = Flask(__name__)
app.config['STATUS_FILE'] = 'status.json'

def get_urls():
	with open('status.json',"r") as f:
		urls = json.load(f)
	urls = urls['urls']
	return(urls)

def check_status():
    print("checking status")
    statuses = []
    urls = get_urls()
    for url in urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                status = 'up'
            else:
                status = 'down'
                send_discord_webhook(url)
        except:
        	send_discord_webhook(url)
        	status = 'down'
        statuses.append({'url': url, 'status': status, 'timestamp': datetime.now().isoformat()})
    return statuses

def update_status():
    with open(app.config['STATUS_FILE'], 'r') as f:
        status_data = json.load(f)
    statuses = check_status()
    status_data['statuses'].extend(statuses)
    with open(app.config['STATUS_FILE'], 'w') as f:
        json.dump(status_data, f)

def send_discord_webhook(site):
	url = 'webhook url'
	message = f'{site} did not respond properly'
	data = {
	  "content": None ,
	  "embeds": [
	    {
	      "title": "Site did not respond properly",
	      "color": 49919,
	      "fields": [
	        {
	          "name": "URL",
	          "value": site
	        },
	        {
	          "name": "To check downtime visit",
	          "value": "link to your site"
	        }
	      ]
	    }
	  ],
	  "attachments": []
	}
	response = requests.post(url, json=data)
	if response.status_code != 204:
		raise ValueError(f'Failed to send Discord webhook: {response.text}')


def get_last_10_hours_statuses(url=None):
    with open(app.config['STATUS_FILE'], 'r') as f:
        status_data = json.load(f)
    statuses = status_data['statuses']
    if url:
        statuses = [s for s in statuses if s['url'] == url]
    now = datetime.now()
    ten_hours_ago = now - timedelta(hours=10)
    last_10_hours_statuses = [s for s in statuses if datetime.fromisoformat(s['timestamp']) >= ten_hours_ago]
    return [(s['status'], datetime.fromisoformat(s['timestamp'])) for s in last_10_hours_statuses]

scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(update_status, 'interval', minutes=1)
scheduler.start()

@app.route('/')
def show_current_status():
    with open(app.config['STATUS_FILE'], 'r') as f:
        status_data = json.load(f)
    if len(status_data['statuses']) > 0:
        current_status = status_data['statuses'][-1]['status']
    else:
        current_status = "unknown"
    urls = get_urls()
    uptime_dict = {}
    for url in urls:
        statuses = get_last_10_hours_statuses(url)
        num_up = sum(1 for s in statuses if s[0] == 'up')
        uptime = 100.0 * num_up / len(statuses) if len(statuses) > 0 else 0
        uptime_dict[url] = uptime
    return render_template('index.html', current_status=current_status, uptime_dict=uptime_dict)

if __name__ == '__main__':
    update_status()
    app.run()
