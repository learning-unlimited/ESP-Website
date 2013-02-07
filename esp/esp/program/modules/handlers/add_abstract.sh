#!/bin/bash
for file in `ls *.py`
do
    if [[ `grep "abstract = True" $file | wc -l` -gt 0 ]]
    then
        echo "$file already has abstract option set"
    else
        echo -e "\n    class Meta:\n        abstract = True\n" >> $file
        echo "Added abstract option to $file"
    fi
done 
