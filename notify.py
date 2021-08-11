import email, smtplib, ssl

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import json
from typing import Tuple, Optional, List

class Notifier:

    def __init__(self):
        self.subject = 'Updated Apple Restrictions'
        self.sender_email, self.password = self.read_key()
    
    def read_key(self, pth: str = 'key.json') -> Tuple[str, str]:
        user_pass = []
        with open(pth, 'rb') as key:
            js = json.load(key)
            user_pass.append(js['username'])
            user_pass.append(js['password'])
        
        return tuple(user_pass)
    
    def initialize_mime(self) -> MIMEMultipart:
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["Subject"] = self.subject

        return message

    def initialize_attachment(self, fp: str) -> MIMEBase:
        part = None
        with open(fp, 'rb') as attach_file:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attach_file.read())
        
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {fp}",
        )

        return part

    def send(self, to: str, body: str, attach_fp: Optional[List[str]] = []) -> None:
        message = self.initialize_mime()
        message.attach(MIMEText(body, "plain"))
        message["To"] = to

        for fp in attach_fp:
            part = self.initialize_attachment(fp)
            message.attach(part)
        
        text = message.as_string()

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(self.sender_email, self.password)
            server.sendmail(self.sender_email, to, text)