from flask import Flask, render_template, request, redirect, url_for, session, flash
import csv
from collections import defaultdict
from datetime import datetime, timedelta

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# Path to the CSV files
USERS_CSV_FILE = 'users.csv'
ENTRIES_CSV_FILE = 'entries.csv'

# Helper function to read CSV files
def read_csv(file_path):
    with open(file_path, 'r', newline='') as file:
        reader = csv.DictReader(file)
        return list(reader)

# Helper function to write to CSV files
def write_csv(data, file_path):
    fieldnames = data[0].keys()
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        city = request.form['city']
        gender = request.form['gender']
        username = request.form['username']
        password = request.form['password']

        # Check if username already exists
        if is_username_unique(username):
            # Append user data to the users CSV file
            with open(USERS_CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([name, email, phone, city, gender, username, password])

            # Automatically log the user in and redirect to the dashboard
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error_message = 'Username already exists. Please choose a different username.'

    # Populate form fields with submitted values if there was an error
    return render_template('register.html', error=error_message, 
                           submitted_name=request.form.get('name', ''),
                           submitted_email=request.form.get('email', ''),
                           submitted_phone=request.form.get('phone', ''),
                           submitted_city=request.form.get('city', ''),
                           submitted_username=request.form.get('username', ''))

def is_username_unique(username):
    with open(USERS_CSV_FILE, mode='r', newline='') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[5] == username:  # Checking if the username exists in the CSV file
                return False
    return True

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']

        # Read users data from CSV
        users = read_csv(USERS_CSV_FILE)

        # Check if the user exists and the password is correct
        user = next((u for u in users if u['username'] == username and u['password'] == password_input), None)

        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            error_message = 'Invalid username or password. Please try again.'

    return render_template('login.html', error=error_message, 
                           submitted_username=request.form.get('username', ''))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' in session:
        username = session['username']

        if request.method == 'POST':
            amounts = request.form.getlist('amount[]')
            times = request.form.getlist('time[]')
            dates = request.form.getlist('date[]')
            places = request.form.getlist('place[]')
            purposes = request.form.getlist('purpose[]')

            # Read existing entries data from CSV
            entries = read_csv(ENTRIES_CSV_FILE)

            # Append new entry data
            for amount, time, date, place, purpose in zip(amounts, times, dates, places, purposes):
                entries.append({'amount': amount, 'time': time, 'date': date, 'place': place, 'purpose': purpose, 'username': username})

            # Write updated entries data to CSV
            write_csv(entries, ENTRIES_CSV_FILE)

        # Read user's transactions data from CSV
        transactions = [entry for entry in read_csv(ENTRIES_CSV_FILE) if entry['username'] == username]

        return render_template('dashboard.html', username=username, transactions=transactions)
    else:
        return render_template('error1.html')

@app.route('/analysis')
def analysis():
    if 'username' in session:
        username = session['username']

        # Read transactions data for the logged-in user from the CSV file
        with open(ENTRIES_CSV_FILE, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            transactions = [row for row in reader if row['username'] == username]

        # Aggregate amounts by date
        date_amounts = defaultdict(float)
        for transaction in transactions:
            date_amounts[transaction['date']] += float(transaction['amount'])

        # Sort dates
        sorted_dates = sorted(date_amounts.keys(), key=lambda date: datetime.strptime(date, '%Y-%m-%d'))
        sorted_amounts = [date_amounts[date] for date in sorted_dates]

        # Prepare data for visualization
        date_amount_chart_data = {
            'labels': sorted_dates,
            'datasets': [{
                'label': 'Transaction Amount',
                'data': sorted_amounts,
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
                'borderWidth': 1
            }]
        }

        # Prepare data for amount by purpose (pie chart)
        purposes = [transaction['purpose'] for transaction in transactions]

        unique_purposes = list(set(purposes))
        purpose_amount_data = {}
        for purpose in unique_purposes:
            purpose_amount_data[purpose] = sum(float(transaction['amount']) for transaction in transactions if transaction['purpose'] == purpose)

        purpose_amount_chart_data = {
            'labels': unique_purposes,
            'datasets': [{
                'data': list(purpose_amount_data.values()),
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
                'borderWidth': 1
            }]
        }

        # Generate chart data for amount by time (line chart)
        time_labels = [f'{hour:02}:00' for hour in range(0, 24, 2)]
        time_amounts = defaultdict(float)
        time_counts = defaultdict(int)

        for transaction in transactions:
            transaction_time = datetime.strptime(transaction['time'], '%H:%M')
            rounded_hour = round(transaction_time.hour / 2) * 2  # Round to nearest 2-hour interval
            rounded_time = f'{rounded_hour:02}:00'
            time_amounts[rounded_time] += float(transaction['amount'])
            time_counts[rounded_time] += 1

        # Fill in missing intervals with 0 amounts
        for label in time_labels:
            if label not in time_amounts:
                time_amounts[label] = 0

        # Create sorted list of time amounts based on fixed labels
        amounts_by_time = [time_amounts[label] for label in time_labels]

        time_amount_chart_data = {
            'labels': time_labels,
            'datasets': [{
                'label': 'Transaction Amount',
                'data': amounts_by_time,
                'fill': False,
                'borderColor': 'rgb(75, 192, 192)',
                'lineTension': 0.1
            }]
        }

        # Aggregate amounts by day of the week
        day_labels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_amounts = defaultdict(float)

        for transaction in transactions:
            transaction_date = datetime.strptime(transaction['date'], '%Y-%m-%d')
            day_of_week = transaction_date.strftime('%A')
            day_amounts[day_of_week] += float(transaction['amount'])

        amounts_by_day = [day_amounts[day] for day in day_labels]

        day_amount_chart_data = {
            'labels': day_labels,
            'datasets': [{
                'label': 'Transaction Amount',
                'data': amounts_by_day,
                'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 1
            }]
        }

        return render_template('analysis.html',
                               date_amount_chart_data=date_amount_chart_data,
                               purpose_amount_chart_data=purpose_amount_chart_data,
                               time_amount_chart_data=time_amount_chart_data,
                               day_amount_chart_data=day_amount_chart_data)
    else:
        return render_template('error1.html')
    

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)
