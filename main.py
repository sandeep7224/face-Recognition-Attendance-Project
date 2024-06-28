import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime
import sqlite3
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
import csv

# Initialize Database
def init_db():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Function to Mark Attendance
def markAttendance(name):
    now = datetime.now()
    dateString = now.strftime('%Y-%m-%d')
    timeString = now.strftime('%H:%M:%S')
    
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM attendance WHERE name = ? AND date = ?', (name, dateString))
    result = c.fetchone()

    if result is None:
        c.execute('INSERT INTO attendance (name, date, time) VALUES (?, ?, ?)', (name, dateString, timeString))
        conn.commit()
    
    conn.close()

# Function to Find Encodings
def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        try:
            encode = face_recognition.face_encodings(img)[0]
            encodeList.append(encode)
        except IndexError:
            print(f"Face not found in image {img}")
    return encodeList

# Global variable for video capture
cap = None

# Function to Start Attendance
def start_attendance():
    global cap
    path = 'ImagesAttendance'
    images = []
    classNames = []
    myList = os.listdir(path)

    for cl in myList:
        curImg = cv2.imread(f'{path}/{cl}')
        images.append(curImg)
        classNames.append(os.path.splitext(cl)[0])

    encodeListKnown = findEncodings(images)
    print('Encoding Complete')

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    face_detected = False

    def capture_frame():
        nonlocal face_detected
        if cap is None or not cap.isOpened():
            return

        success, img = cap.read()
        if not success:
            print("Failed to capture image")
            return

        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)
        
        facesCurFrame = face_recognition.face_locations(imgS)
        if facesCurFrame:
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)
        
            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                matchIndex = np.argmin(faceDis)
                
                if matches[matchIndex]:
                    name = classNames[matchIndex].upper()
                    y1, x2, y2, x1 = faceLoc
                    y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
                    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                    cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
                    markAttendance(name)
                    
                    if not face_detected:
                        print(f"Face detected: {name}. Next student, please.")
                        face_detected = True

        else:
            face_detected = False

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(img)
        img = ImageTk.PhotoImage(image=img)
        lbl_video.imgtk = img
        lbl_video.configure(image=img)
        lbl_video.after(10, capture_frame)

    lbl_video.after(10, capture_frame)

# Function to Stop Attendance
def stop_attendance():
    global cap
    if cap is not None:
        cap.release()
        cap = None
        lbl_video.config(image='')

# Function to View Attendance
def view_attendance():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT name, date, time FROM attendance')
    rows = c.fetchall()
    conn.close()

    view_window = tk.Toplevel(root)
    view_window.title("Attendance Records")
    view_window.geometry("800x400")

    tree = ttk.Treeview(view_window, columns=('Name', 'Date', 'Time'), show='headings')
    tree.heading('Name', text='Name')
    tree.heading('Date', text='Date')
    tree.heading('Time', text='Time')
    tree.pack(fill=tk.BOTH, expand=True)

    for row in rows:
        tree.insert('', tk.END, values=row)

# Function to Erase Attendance
def erase_attendance():
    if messagebox.askokcancel("Erase Data", "Are you sure you want to erase all attendance records?"):
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute('DELETE FROM attendance')
        conn.commit()
        conn.close()
        messagebox.showinfo("Data Erased", "All attendance records have been erased.")

# Function to Export Attendance to CSV
def export_to_csv():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT * FROM attendance')
    rows = c.fetchall()
    conn.close()

    with open('attendance_export.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['ID', 'Name', 'Date', 'Time'])
        writer.writerows(rows)
    
    messagebox.showinfo("Export Successful", "Attendance records have been exported to attendance_export.csv.")

# Function to Visualize Attendance Data
def visualize_data():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT date, COUNT(*) FROM attendance GROUP BY date')
    data = c.fetchall()
    conn.close()

    dates = [row[0] for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(10, 5))
    plt.bar(dates, counts, color='blue')
    plt.xlabel('Date')
    plt.ylabel('Number of Attendances')
    plt.title('Attendance Over Time')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Function to Calculate and Display Attendance Summary
def display_attendance_summary():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(DISTINCT name) FROM attendance WHERE date = ?', (today,))
    present_today = c.fetchone()[0]
    total_students = len(os.listdir('ImagesAttendance'))
    conn.close()
    print(f"Number of students present today: {present_today} out of {total_students}")

# Function to handle program termination
def on_closing():
    stop_attendance()
    display_attendance_summary()
    root.destroy()

# Login System
def login():
    username = login_username.get()
    password = login_password.get()
    if username == "admin" and password == "password":
        messagebox.showinfo("Login Successful", "Welcome!")
        login_window.destroy()
    else:
        messagebox.showerror("Login Failed", "Incorrect username or password.")

# Main GUI Setup
root = tk.Tk()
root.title("Attendance System")
root.geometry("900x600")
root.configure(bg='white')
root.protocol("WM_DELETE_WINDOW", on_closing)

# Create Frames
frame_top = tk.Frame(root, bg='darkblue')
frame_top.pack(side=tk.TOP, fill=tk.X)

frame_left = tk.Frame(root, bg='lightgrey')
frame_left.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

frame_right = tk.Frame(root, bg='white')
frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Top Frame Widgets
lbl_title = tk.Label(frame_top, text="Attendance System", font=("Arial", 24, 'bold'), bg='darkblue', fg='white')
lbl_title.pack(pady=10)

# Left Frame Widgets
btn_start = tk.Button(frame_left, text="Start Attendance", command=start_attendance, width=20, font=("Arial", 12, 'bold'))
btn_start.pack(pady=10)

btn_stop = tk.Button(frame_left, text="Stop Attendance", command=stop_attendance, width=20, font=("Arial", 12, 'bold'))
btn_stop.pack(pady=10)

btn_view = tk.Button(frame_left, text="View Attendance", command=view_attendance, width=20, font=("Arial", 12, 'bold'))
btn_view.pack(pady=10)

btn_erase = tk.Button(frame_left, text="Erase Attendance", command=erase_attendance, width=20, font=("Arial", 12, 'bold'))
btn_erase.pack(pady=10)

btn_export = tk.Button(frame_left, text="Export to CSV", command=export_to_csv, width=20, font=("Arial", 12, 'bold'))
btn_export.pack(pady=10)

btn_visualize = tk.Button(frame_left, text="Visualize Data", command=visualize_data, width=20, font=("Arial", 12, 'bold'))
btn_visualize.pack(pady=10)

# Right Frame Widgets
lbl_video = tk.Label(frame_right, bg='white')
lbl_video.pack(fill=tk.BOTH, expand=True)

# Login GUI Setup
login_window = tk.Toplevel(root)
login_window.title("Login")
login_window.geometry("400x400")
login_window.configure(bg='lightgrey')

lbl_login_title = tk.Label(login_window, text="Admin Login", font=("Arial", 18, 'bold'), bg='lightgrey')
lbl_login_title.pack(pady=10)

lbl_login_username = tk.Label(login_window, text="Username", font=("Arial", 12), bg='lightgrey')
lbl_login_username.pack(pady=5)
login_username = tk.Entry(login_window)
login_username.pack(pady=5)

lbl_login_password = tk.Label(login_window, text="Password", font=("Arial", 12), bg='lightgrey')
lbl_login_password.pack(pady=5)
login_password = tk.Entry(login_window, show='*')
login_password.pack(pady=5)

btn_login = tk.Button(login_window, text="Login", command=login, font=("Arial", 12, 'bold'))
btn_login.pack(pady=20)

# Initialize Database
init_db()

# Start Main Loop
root.withdraw()  # Hide the main window initially
root.wait_window(login_window)  # Wait until login window is closed
root.deiconify()  # Show the main window

root.mainloop()
