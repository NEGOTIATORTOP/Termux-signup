def parse_credentials_file(path):
    creds = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            email, password = line.split(":", 1)
            creds.append({"email": email.strip(), "password": password.strip()})
    return creds
