"""Functions to send email reports."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from utils.common import console

load_dotenv()


# ===== EMAIL CONFIG (fill these) =====
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "prakhyatshetty710@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "oiwg ffrt jzgv jedi")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "prakhyatshetty709@gmail.com")



def send_report(results : list) -> None:
    """Send email report of price scraping results."""
    subject = "Price Tracker Report"
    html = """
    <html>
    <body>
    <h2>Price Tracker Report</h2>
    <table border="1" cellspacing="0" cellpadding="6" style="border-collapse: collapse;">
    <tr style="background-color: #f2f2f2;">
        <th>Product</th>
        <th>Current Price (₹)</th>
        <th>Original Price (₹)</th>
        <th>Discount (%)</th>
        <th>Desired Price (₹)</th>
        <th>Status</th>
        <th>Link</th>
    </tr>
    """

    for item in results:
        html += f"""
        <tr>
            <td>{item['name']}</td>
            <td>{item['current_price']}</td>
            <td>{item['original_price']}</td>
            <td>{item['discount']}%</td>
            <td>{item['threshold']}</td>
            <td>{item['status']}</td>
            <td><a href="{item['url']}">View</a></td>
        </tr>
        """

    html += "</table></body></html>"

    msg = MIMEMultipart("alternative")
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Subject"] = subject
    msg.attach(MIMEText(html, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        console.print("[OK] Email report sent!")
    except smtplib.SMTPException as e:
        console.print("[X] Failed to send email:", e)
