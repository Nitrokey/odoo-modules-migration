# Odoo Modules Migration (OMM)

This tool aims to support the migration of Odoo installations by providing a current overview of the modules' migration state and Odoo's readiness for the migration. It can help in particular for Odoo systems with a large amount of OCA modules. The documentation assums to use [dob](https://github.com/initos/dob) as a deployment but it is not strictly required. OMM is primarily an internal tool but we are glad if you find it useful.


## Usage

Typically "source version" refers to the currently installed version (e.g. 12.0) and "target version" to the higher migration target version (e.g. 15.0). OMM can even be used to manage more than two versions.

1. Retrieve list of installed modules on production system, source version:
`docker-compose run --rm odoo psql -P pager=off -A -F ';' -c "SELECT name, author, state, auto_install FROM ir_module_module WHERE state = 'installed' ORDER BY name" 2> /dev/null 1> /tmp/installed-modules.csv`

2. Add the list to a modules.yaml database, e.g. `python3 omm.py import-csv installed-modules.csv modules.yaml 12.0`

3. Retrieve module list based on project.yaml on a test system, target version:

**WARNING: This will delete the database!**

```
docker-compose run --rm odoo stop && \  
docker-compose run --rm odoo dropdb odoo && \
docker-compose run --rm odoo createdb odoo && \
docker-compose run --rm odoo odoo update && \
docker-compose run --rm odoo psql -P pager=off -A -F ';' -c "SELECT name, author, state, auto_install FROM ir_module_module WHERE state = 'installed' ORDER BY name" 2> /dev/null 1> /tmp/installed-modules.csv
```

4. Add this list similarly as in step 2. Alternatively you can populate the modules.yaml with an empty set of modules, e.g. `python3 omm.py add-version modules.yaml 15.0`

5. Edit modules.yaml in a text editor and update "evaluation" field of your target version with the following values:
  * "not required" for modules which are, well, not required but also don't hurt if they are installed.
  * "required" for modules which must be migrated before a system migration can be commited.
  * "not desired" for modules which must not be installed before a system migration can be commited.
  * "desired" for modules which are nice to have but are no show stopper and which could be migrated after a system migration.
  * "doesn't matter" or "DM" for modules you don't have a specific requirement on. Technically any text other than empty and the above can be entered but I suggest to use a consistent terminology.

  Add arbitrary notes into the "comment" field, such as reasoning for your evaluation or "module has been renamed to X"

6. Analyse the current state, e.g. `python3 omm.py analyse modules.yaml 15.0`

Exemplary output:

```
Not desired but installed: account_bank_statement_import
Required but not installed: account_bank_statement_import_camt_oca
Not evaluated: account_bank_statement_import_online_paypal
Desired but not installed: account_bank_statement_import_txt_xlsx
Not required but installed: account_bank_statement_import
Required and migrated modules: 1
```

7. Update the installation status regularly by repeating the above procedure, potentially automated in the CI.


## License

[GNU General Public License Version 3](LICENSE)


## Ideas

Ideas for further improvements:

* Consider automatically installed modules during analyse.
* Add tasks, e.g. to be migrated, work in progress, migrated, not to be migrated, data migration required, data migration not required, waiting for 3rd party, to be purchased
