from flask import Flask, render_template,session,redirect,request
import requests
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import requests



app = Flask(__name__)
app.config['STATUS_FILE'] = 'status.json'
app.config['SECRET_KEY'] = "seceret_key?"

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
    print("updating")
    with open(app.config['STATUS_FILE'], 'r') as f:
        status_data = json.load(f)
    statuses = check_status()
    status_data['statuses'].extend(statuses)
    with open(app.config['STATUS_FILE'], 'w') as f:
        json.dump(status_data, f)

def send_discord_webhook(site):
    print("hooks")
    accounts = get_all_accounts()
    hooks = accounts["hooks"]
    for url in hooks:
        url = 'https://discord.com/api/webhooks/1082230304242143264/M6HDjS3gQVCzrUjLytl1LawsVVFq_uvl0srlnLYrCdFummzMj9DdHxEnDvGF6Wr-sRqT'
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
    	          "value": "https://panel.herotech.cf"
    	        }
    	      ]
    	    }
    	  ],
    	  "attachments": []
          }
        response = requests.post(url, json=data)
        print(response.status_code)
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
    if "password" not in session:
        return(redirect('/login'))
    accounts = get_all_accounts()
    password = accounts["password"]
    if session['password'] != password:
        return(redirect('/login'))
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

@app.route('/login',methods=["GET","POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        session["password"] = password
        return(redirect("/"))
    return(render_template('login.html'))

@app.route('/manage',methods=["GET","POST"])
def manage():
    if "password" not in session:
        return(redirect('/login'))
    accounts = get_all_accounts()
    password = accounts["password"]
    if session['password'] != password:
        return(redirect('/login'))
    if request.method == "POST":
        if request.form.get("login") == "token":
            token = request.form.get("token")
            accounts = get_all_accounts()
            accounts['urls'].append(token)
            save_all_accounts(accounts)
            sc = True
        if request.form.get("login") == "pass":
            old_password = request.form.get("old_password")
            new_password = request.form.get("new_password")
            if old_password == accounts['password']:
                accounts['password'] = new_password
                save_all_accounts(accounts)
                return(redirect('/login'))
            else:
                return("inccorect password")
        if request.form.get("login") == "web":
            url = request.form.get('url')
            accounts = get_all_accounts()
            accounts['hooks'].append(url)
            save_all_accounts(accounts)
            sc = True

        else:
            token = request.form.get("delete")
            remove_token_from_acc(token)
            sc = True
        
        if sc != True:
            return(sc)
    accounts = get_all_accounts()
    urls = accounts['urls']
    hooks = accounts['hooks']
    return(render_template('manage.html',urls = urls,hooks=hooks))


def remove_token_from_acc(token):
    accounts = get_all_accounts()
    if token in accounts['urls']:
        index = accounts['urls'].index(token)
        del accounts['urls'][index]
    elif token in accounts['hooks']:
        index = accounts['hooks'].index(token)
        del accounts['hooks'][index]
    save_all_accounts(accounts)
    return(True)

def get_all_accounts():
    with open('status.json','r') as f:
        accounts = json.load(f)
    return(accounts)

def save_all_accounts(accounts):
    with open('status.json','w') as f:
        json.dump(accounts, f)
    return(True)

if __name__ == '__main__':
    update_status()
    app.run()
