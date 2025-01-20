#!/bin/sh

start_time="$(date -u +%s)"

## Relational
./oetl.sh Customer.json
./oetl.sh Product.json
./oetl.sh Vendor.json
./oetl.sh feedback.json

end_time1="$(date -u +%s)"
elapsed1="$(($end_time1-$start_time))"
echo "The importing time for Relation data is $elapsed1" >> orientDBImportingtime


## JSON
./oetl.sh Order.json

end_time2="$(date -u +%s)"
elapsed2="$(($end_time2-$end_time1))"
echo "The importing time for JSON data is $elapsed2" >> orientDBImportingtime

## Graph
./oetl.sh Post.json
./oetl.sh Knows.json
./oetl.sh PersonHasPost.json
./oetl.sh PostHasTag.json


end_time3="$(date -u +%s)"
elapsed3="$(($end_time3-$end_time2))"
echo "The importing time for JSON data is $elapsed2" >> orientDBImportingtime
