[![Coverage Status](https://coveralls.io/repos/github/rapidpro/rapidpro/badge.svg?branch=master)](https://coveralls.io/github/rapidpro/rapidpro?branch=master)  

# RapidPro     

RapidPro is a hosted service for visually building interactive messaging applications.
To learn more, please visit the project site at http://rapidpro.github.io/rapidpro.

### Get Involved

To run RapidPro for development, follow the Quick Start guide at http://rapidpro.github.io/rapidpro/docs/development.

### License

In late 2014, Nyaruka partnered with UNICEF to expand on the capabilities of TextIt and release the source code as RapidPro under the Affero GPL (AGPL) license.

In brief, the Affero license states you can use the RapidPro source for any project free of charge, but that any changes you make to the source code must be available to others. Note that unlike the GPL, the AGPL requires these changes to be made public even if you do not redistribute them. If you host a version of RapidPro, you must make the same source you are hosting available for others.

RapidPro has dual copyright holders of UNICEF and Nyaruka.

The software is provided under AGPL-3.0. Contributions to this project are accepted under the same license.

# Steps to running

```
cd docker && docker build -t rapidpro/database . && cd ..
docker container create --name rapidpro-database rapidpro/database
docker container start rapidpro-database && docker container run -d redis
yarn global add coffeescript less
yarn install
python manage.py migrate
python manage.py runserver
```

# Main differences from official repo
* Settings is more flexible and efficient;
* Our requirements is more concise, clear and follow official good patterns;
