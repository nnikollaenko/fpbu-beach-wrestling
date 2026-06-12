# ── Email configuration ────────────────────────────────────────────────────────
# Gmail SMTP: you need a Gmail App Password (not your regular password).
# Steps to get one:
#   1. myaccount.google.com → Security → 2-Step Verification (enable if not done)
#   2. myaccount.google.com → Security → App passwords
#   3. Select app: Mail, device: Other → generate → copy 16-char password here
#
# When the federation gets its official email, change MAIL_SENDER and
# MAIL_RECIPIENT to that address and update MAIL_SMTP_HOST/PORT accordingly.

import os

MAIL_SMTP_HOST = 'smtp.gmail.com'
MAIL_SMTP_PORT = 587

MAIL_SENDER    = os.environ.get('MAIL_SENDER',    'nikolaenkoelizaveta@gmail.com')
MAIL_PASSWORD  = os.environ.get('MAIL_PASSWORD',  '')   # ← paste App Password here, or set env var
MAIL_RECIPIENT = os.environ.get('MAIL_RECIPIENT', 'nikolaenkoelizaveta@gmail.com')
