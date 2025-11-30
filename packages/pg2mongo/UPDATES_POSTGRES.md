

## on the vwinvoice_api
```bash

# add new field

#COALESCE(inv.driver_id, 0) AS driver_id, -> AFTER THIS FIELD
COALESCE(u.username, ''::character varying) AS "user.name",
COALESCE(driver."name", ''::character varying) AS "driver.name",

LEFT JOIN auth_user u ON u.id = inv.created_by_id
LEFT JOIN employee driver ON driver.id = inv.driver_id

```
