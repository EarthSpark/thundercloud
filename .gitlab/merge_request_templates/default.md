## Description

A description of changes in this merge request.

Fixes [chXXXXXX]

## Testing

Verification instructions for the reviewer.

## Checklist

* [ ] No changed dependencies.
	* If yes:
		* [ ] They have been confirmed compatible with a base station
		* Provide a list of new/changed dependencies here (including justifications):
* [ ] No Celery queue changes.
	* If there are changes, link the accompanying infrastructure MR or Clubhouse ticket:
* [ ] No database changes.
	* If yes:
		* [ ] New schema migrations have a downgrade path
		* [ ] New database tables are configured to support SymmetricDS
		* [ ] [New migrations have been validated locally](https://sparkmeter.atlassian.net/wiki/spaces/SE/pages/706543661/Testing+ThunderCloud+Migration#Validating-Locally)
		* [ ] [Large data migrations have been profiled on a base station](https://sparkmeter.atlassian.net/wiki/spaces/SE/pages/706543661/Testing+ThunderCloud+Migration#Profiling-on-a-Base-Station)
