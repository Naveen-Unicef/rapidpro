# How to use

- Clone this repo in your RapidPro project (into `temba` module)

```
$(env) git clone https://{user}@bitbucket.org/ilhasoft/rapidpro-migration-module.git
```

- Add `migrations` module to `INSTALLED_APPS` on settings file
```
INSTALLED_APPS = (
    ...
    'temba.migrations',
    ...
)
```

- Add the URL to access the migration form page (`temba/urls.py`)
```

urlpatterns = [
    ...
    url(r'^', include('temba.migrations.urls')),
    ...
]

```

- Register the permissions for `migrations` module on settings file
```
PERMISSIONS = {
    ...
    'migrations.migration': ('import',),
}

GROUP_PERMISSIONS = {
    ...
    "Administrators": (
        ...

        'migrations.migration_import'
    )
    ...
}
```

- Run the django migration command
```
$(env) python manage.py migrate
```

- After that, the migration form will be available on `http://{your-host}/migration/import/`