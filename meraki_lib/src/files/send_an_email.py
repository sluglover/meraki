import 

msg = EmailMessage()
msg['Subject'] = 'Horrible Json'
msg['From'] = 'ccorby@chiutility.com'
recipients = 'ccorby@baillie.com'
msg['To'] = recipients
with open('a.json', 'rb') as f:
    msg.add_attachment(f.read(), maintype=
