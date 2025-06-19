import imapclient
import mailparser
import time
import re
import logging

logger = logging.getLogger(__name__)

def get_latest_verification_code(email, password, subject_match="schools", timeout=45):
    try:
        server = imapclient.IMAPClient('imap.gmail.com', ssl=True, timeout=15)
        server.login(email, password)
        server.select_folder('INBOX')
        since = time.time()
        while time.time() - since < timeout:
            messages = server.search(['UNSEEN'])
            if not messages:
                time.sleep(2)
                continue
            latest_uid = messages[-1]
            raw_message = server.fetch([latest_uid], ['RFC822'])
            raw_email = raw_message[latest_uid][b'RFC822']
            parsed = mailparser.parse_from_bytes(raw_email)
            subject = parsed.subject or ""
            if subject_match.lower() in subject.lower():
                body = parsed.text_plain[0] if parsed.text_plain else parsed.body
                code_match = re.search(r"\b\d{6}\b", body)
                if code_match:
                    server.logout()
                    return code_match.group(0)
            time.sleep(2)
        server.logout()
    except Exception as e:
        logger.error(f"IMAP error for {email}: {e}")
    return None
