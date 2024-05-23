FROM python:3.11

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN python3 -m pip install --no-cache-dir --upgrade pip
RUN python3 -m pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY . .

CMD ["panel", "serve", "/code/app.py", 
     "--address", "0.0.0.0", 
     "--port", "8080",  
     "--allow-websocket-origin", "*", 
     "--index", "app",
     "--basic-auth", "credentials.json",
     "--logout-template", "templates/logout.html",
     "--basic-login-template", "templates/login.html",
     "--cookie-secret", "my_super_safe_cookie_secret"]

RUN mkdir /.cache
RUN chmod 777 /.cache
