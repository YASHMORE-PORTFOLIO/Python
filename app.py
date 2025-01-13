import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import csv

# Create Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.secret_key = 'your_secret_key'  # Secret key for flash messages

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Function to handle database connection
def get_db_connection(user, password, database):
    return mysql.connector.connect(
        host='localhost',
        user=user,
        password=password,
        database=database
    )

# Home route for displaying the upload form
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle file upload and database insertion
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Get database connection details
        db_user = request.form['db_user']
        db_password = request.form['db_password']
        db_name = request.form['db_name']

        try:
            # Connect to the database
            conn = get_db_connection(db_user, db_password, db_name)
            cursor = conn.cursor()

            # Read the CSV file and prepare for insertion
            with open(file_path, 'r') as f:
                csv_reader = csv.reader(f)
                header = next(csv_reader)  # Get the header (column names)
                
                # Create table query
                table_name = os.path.splitext(filename)[0]  # Table name from file name
                columns = ', '.join([f"`{col.strip()}` TEXT" for col in header])  # Wrap column names with backticks
                
                # Create table if not exists
                create_table_query = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({columns})"
                cursor.execute(create_table_query)

                # Insert data into the table
                for row in csv_reader:
                    if len(row) == len(header):  # Ensure number of columns match
                        insert_query = f"INSERT INTO `{table_name}` ({', '.join([f'`{col.strip()}`' for col in header])}) VALUES ({', '.join(['%s'] * len(row))})"
                        cursor.execute(insert_query, tuple(row))
                    else:
                        flash(f"Warning: Skipping row due to column mismatch: {row}")
                
                conn.commit()

            flash(f"File '{filename}' uploaded and data inserted into the database successfully!")
            return redirect(url_for('index'))

        except mysql.connector.Error as e:
            flash(f"Error: {e}")
            return redirect(url_for('index'))
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()

    flash('Invalid file type. Please upload a CSV file.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
