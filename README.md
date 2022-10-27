

#Redis

    docker run -p 6379:6379 --name some-redis -d redis

Check if Redis is running

    docker exec -it some-redis redis-cli ping

Install Celery and Redis

Add in the main FastAPI file:

    celery = Celery(
        __name__,
        broker="redis://127.0.0.1:6379/0",
        backend="redis://127.0.0.1:6379/0"
    )

### Test Celery

    celery -A server.celery worker --loglevel=info

Install Flower

celery -A server.celery flower --port=5555


Connecting to postgres inside docker

docker compose exec -u postgres postgres bash

Then 

psql -d cardanodatos -U cardanodatos --password

### Deploying 

Basic

Install Nginx

Install the prerequisites:

    sudo apt install curl gnupg2 ca-certificates lsb-release ubuntu-keyring

Import an official nginx signing key so apt could verify the packages authenticity. Fetch the key:

    curl https://nginx.org/keys/nginx_signing.key | gpg --dearmor \
        | sudo tee /usr/share/keyrings/nginx-archive-keyring.gpg >/dev/null

Verify that the downloaded file contains the proper key:

    gpg --dry-run --quiet --no-keyring --import --import-options import-show /usr/share/keyrings/nginx-archive-keyring.gpg

The output should contain the full fingerprint 573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62 as follows:

    pub   rsa2048 2011-08-19 [SC] [expires: 2024-06-14]
        573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62
    uid                      nginx signing key <signing-key@nginx.com>

If the fingerprint is different, remove the file.

To set up the apt repository for stable nginx packages, run the following command:

    echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
    http://nginx.org/packages/ubuntu `lsb_release -cs` nginx" \
        | sudo tee /etc/apt/sources.list.d/nginx.list

If you would like to use mainline nginx packages, run the following command instead:

    echo "deb [signed-by=/usr/share/keyrings/nginx-archive-keyring.gpg] \
    http://nginx.org/packages/mainline/ubuntu `lsb_release -cs` nginx" \
        | sudo tee /etc/apt/sources.list.d/nginx.list

Set up repository pinning to prefer our packages over distribution-provided ones:

    echo -e "Package: *\nPin: origin nginx.org\nPin: release o=nginx\nPin-Priority: 900\n" \
        | sudo tee /etc/apt/preferences.d/99nginx

To install nginx, run the following commands:

    sudo apt update
    sudo apt install nginx

### Configure ufw to enable nginx

Create ufw nginx conf file

    sudo vim /etc/ufw/applications.d/nginx

Add ufw nginx configurations

    [Nginx HTTP]
    title=Web Server (Nginx, HTTP)
    description=Small, but very powerful and efficient web server
    ports=80/tcp

    [Nginx HTTPS]
    title=Web Server (Nginx, HTTPS)
    description=Small, but very powerful and efficient web server
    ports=443/tcp

    [Nginx Full]
    title=Web Server (Nginx, HTTP + HTTPS)
    description=Small, but very powerful and efficient web server
    ports=80,443/tcp

    sudo ufw app update nginx
    sudo ufw allow 'Nginx HTTP'


Install gunicorn inside the virtualenv

poetry add gunicorn

Install pm2 

sudo npm install -g pm2

### Start FastApi app

    pm2 start "gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:cardanodatos" --name cardanoapi

Other pm2 commands

    pm2 ls
    pm2 restart <name of the app>

### Configure nginx 

In /etc/nginx/conf.d 

cp default.conf default.conf.disabled

Modify default.conf with:

    server {
            listen 80;

            server_name IPADDRESS example.com;

            location / {
            proxy_pass http://localhost:8000;
            }
    }

Restart nginx service

    sudo service nginx restart

Intialize github repo

git init
git checkout -b 1.initial-cardanoapi
git status
git add .

git commit -m "first commit with initial cardanoapi setup"
git remote add origin https://github.com/larestrepo/cardanoapi.git

git push -u origin 1.initial-cardanoapi 


### Work with alembic

    poetry add alembic

    alembic init alembic

    alembic revision --autogenerate -m "Creation of tables"

    alembic upgrade head

    